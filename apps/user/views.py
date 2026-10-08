from rest_framework import generics, response
from .serializers import RegionSerializer, TelegramUserSerializer, UserSerializer, PhoneSerializer, \
    InfoSerializer, StoreSerializer
from .models import TelegramUser, Region, Info, Store
from . import leo_client
import re


NOT_FOUND_MESSAGE = {"success": False, "message_uz": "Bunday code mavjud emas!",
                      "message_ru": "Такого кода не существует!"}


def _decode_bonus_code(raw_code):
    """usta-source's own checksum scheme for physical codes: strip and validate the
    trailing 4-digit/letter checksum, return the canonical code leo's BonusCode catalog
    was seeded with (see apps/shared/management/commands/migrate_from_usta.py in leo),
    or None if the raw code is malformed."""
    number2 = re.search(r"(\d{4})(\D*$)", raw_code)
    if number2 is None:
        return None
    code2 = raw_code.replace(number2.group(0), "")
    number1 = re.search(r"([A-Z]$)", code2)
    if number1 is None:
        return None
    code2 = code2[::-1].replace(number1.group(0), "", 1)[::-1]
    number = number2.group(1)
    if 0 >= int(number) >= 9999:
        return None
    letter_index = ord(number1.group(0)) - ord('A')
    if int(number) % 26 != letter_index:
        return None
    return f"{code2}A0000{number2.group(2)}"


class StoreListView(generics.ListAPIView):
    serializer_class = StoreSerializer

    def get_queryset(self):
        user = TelegramUser.objects.filter(chat_id=self.kwargs['chat_id']).first()
        return Store.objects.filter(region_id=user.region_id)


class RegionListView(generics.ListAPIView):
    serializer_class = RegionSerializer
    queryset = Region.objects.all()


class InfoView(generics.GenericAPIView):
    serializer_class = InfoSerializer

    def get(self, request, *args, **kwargs):
        obj = Info.objects.first()
        serializer = self.serializer_class(obj)
        return response.Response(serializer.data)


class  CheckCodeView(generics.GenericAPIView):
    """leo is the source of truth for the bonus-code catalog and balance — this view
    only decodes usta-source's own checksum format locally, then delegates the actual
    lookup/redeem to leo (apps/integrations in leo) so a code can't be spent twice
    across the two systems. See CLAUDE.md and the migrate_from_usta command in leo."""
    serializer_class = PhoneSerializer

    def get(self, request, *args, **kwargs):
        code = _decode_bonus_code(self.kwargs['code'])
        if code is None:
            return response.Response(NOT_FOUND_MESSAGE, status=404)
        try:
            leo_client.check_bonus_code(code)
        except leo_client.LeoAPIError as e:
            message = e.payload.get('error', {}).get('message_language', {})
            return response.Response(
                {"success": False, "message_uz": message.get('uz', NOT_FOUND_MESSAGE['message_uz']),
                 "message_ru": message.get('ru', NOT_FOUND_MESSAGE['message_ru'])},
                status=404,
            )
        return response.Response({"success": True})

    def post(self, request, *args, **kwargs):
        code = _decode_bonus_code(self.kwargs['code'])
        if code is None:
            return response.Response(NOT_FOUND_MESSAGE, status=404)

        user = TelegramUser.objects.filter(chat_id=request.data['chat_id']).first()
        if not user:
            return response.Response({'success': False, 'message': 'User not found!'}, status=404)

        try:
            result = leo_client.redeem_bonus_code(user.chat_id, code)
        except leo_client.LeoAPIError as e:
            message = e.payload.get('error', {}).get('message_language', {})
            return response.Response(
                {"success": False, "message_uz": message.get('uz', "Bonus code mavjud emas"),
                 "message_ru": message.get('ru', "Бонусный код недоступен")},
                status=404,
            )

        awarded = result['result']['awarded']
        user.summa = result['result']['balance']
        user.save(update_fields=['summa'])
        return response.Response({
            "success": True,
            "message_uz": f"Hisobingizga {awarded} so'm qo'shildi!\nBu so'm 1 yil davomida amal qiladi\nAgar so'mdan foydalanmasangiz 1 yildan so'ng o'chib ketadi!",
            "message_ru": f"{awarded} сум добавлены к вашему счету!\n этот сум действителен в течение 1 года\nесли вы не используете сум, он исчезнет через 1 год!",
        })


class UserCheckView(generics.GenericAPIView):
    serializer_class = UserSerializer

    def get(self, request, *args, **kwargs):
        obj = TelegramUser.objects.filter(chat_id=self.kwargs['chat_id']).first()
        if not obj:
            return response.Response({"success": False, "message": "User not found!"}, status=404)
        return response.Response({"success": True, "message": "User found!"})


class TelegramUserView(generics.GenericAPIView):
    serializer_class = TelegramUserSerializer

    def get(self, request, *args, **kwargs):
        obj = TelegramUser.objects.filter(chat_id=self.kwargs['chat_id']).first()
        if not obj:
            return response.Response({'success': False, 'message': 'User not found!'}, status=404)
        serializer = TelegramUserSerializer(obj).data
        region = Region.objects.get(id=serializer['region'])
        serializer.update({'region': region.name})
        return response.Response(serializer)

    def patch(self, request, *args, **kwargs):
        obj = TelegramUser.objects.filter(chat_id=kwargs['chat_id']).first()
        if not obj:
            return response.Response({'success': False, 'message': 'User not found!'}, status=404)
        serializer = TelegramUserSerializer(instance=obj, data=self.request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return response.Response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = TelegramUserSerializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        user.summa += 50000
        user.save()
        try:
            # Best-effort: the leo User also gets lazily created on first bonus
            # redemption (apps/integrations/services.py: resolve_telegram_user), so a
            # registration-time leo outage doesn't need to block the bot's own signup.
            leo_client.provision_user(user.chat_id, phone=user.phone, first_name=user.name)
        except leo_client.LeoAPIError:
            pass
        return response.Response(serializer.data)


class UserListView(generics.ListAPIView):
    serializer_class = UserSerializer
    queryset = TelegramUser.objects.all()
