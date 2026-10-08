from pytz import timezone
from .models import Category, Product, Cart, Instruction, Order
from user.models import TelegramUser
from user.utils import send_telegram_message
from django.conf import settings
from rest_framework import generics, response
from .serializers import ProductSerializer, CategorySerializer, CartSerializer, OrderSerializer, OrderProductSerializer, \
    InstructionSerializer


class InstructionView(generics.GenericAPIView):
    serializer_class = InstructionSerializer
    queryset = Instruction.objects.all()

    def get(self, request, *args, **kwargs):
        obj = Instruction.objects.filter(id=self.kwargs.get('pk')).first()
        serializer = InstructionSerializer(obj)
        return response.Response(serializer.data)

    def post(self, request, *args, **kwargs):
        obj = Instruction.objects.filter(id=self.kwargs.get('pk')).first()
        if obj:
            request.data['id'] = obj.id
            serializer = InstructionSerializer(obj, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        else:
            serializer = InstructionSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return response.Response(serializer.data)


class OrderView(generics.GenericAPIView):
    serializer_class = OrderSerializer

    def post(self, request, *args, **kwargs):
        user = TelegramUser.objects.filter(chat_id=self.kwargs['chat_id']).first()
        if not user:
            return response.Response({'error': 'User not found'}, status=404)
        data = request.data
        data['user'] = user.id
        serializer = OrderSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        user.summa -= order.total
        user.save()
        products_uz = ""
        phones = ""
        for i in order.store.phones.all():
            phones += f"{i.phone}\n"
        products_ru = ""
        for i in order.products.all():
            products_uz += f"Nomi: {i.product.name_uz}\nSoni: {i.count}\nNarxi: {i.product.price} so'm\n"
            products_ru += f"Продукт: {i.product.name_ru}\nКоличество: {i.count}\nСтоимость: {i.product.price}Сум\n"
        txt = f"Buyurtma raqami: {order.id}\nFoydalanuvchi: {user.phone}\nViloyat: {order.store.region.name_uz}\nMahsulotlar: \n{products_uz}"
        txt += f"Dukon: {order.store.name_uz}\nBuyurtma vaqti: {order.created_at.astimezone(tz=timezone('Asia/Tashkent')).strftime('%d-%m-%Y %H:%M')}"
        payload = {
            "chat_id": settings.GROUP_ID,
            "text": txt,
            "parse_mode": "HTML"
        }
        res = send_telegram_message(payload)
        if res.status_code != 200:
            return response.Response({'error': 'Failed to send message to Telegram'}, status=500)
        if user.lang == "uz":
            txt = f"Buyurtma raqami: {order.id}\nMahsulotlar:\n{products_uz}Dukon nomi: {order.store.name_uz}\nViloyat: {order.store.region.name_uz}\nJami: {order.total} so'm\n5 kundan so'ng olishingiz mumkin\nTelefonlar: {phones}\n"
        elif user.lang == "ru":
            txt = f"Номер заказа: {order.id}\nПродукты:\n{products_ru}Название магазина: {order.store.name_ru}\nРегион: {order.store.region.name_ru}\nВы можете получить его через 5 дней\nИтого: {order.total} Сум\nТелефоны: {phones}\n"
        payload = {
            "chat_id": user.chat_id,
            "text": txt,
            "parse_mode": "HTML"
        }
        mes = send_telegram_message(payload)
        payload = {"chat_id": user.chat_id, "latitude": order.store.latitude, "longitude": order.store.longitude,
                   "reply_parameters": {"message_id": mes.json()['result']['message_id']}}
        send_telegram_message(payload, "sendLocation")
        user.carts.all().delete()
        return response.Response({'success': True})


class OrderConfirmView(generics.GenericAPIView):
    """Marks an order received — the bot calls this when the user answers "yes" to the
    5-day survey. Scoped by chat_id so an order id alone cannot complete someone else's."""
    serializer_class = OrderSerializer

    def post(self, request, *args, **kwargs):
        order = Order.objects.filter(id=self.kwargs['order_id'],
                                     user__chat_id=self.kwargs['chat_id']).first()
        if not order:
            return response.Response({'error': 'Order not found'}, status=404)
        order.is_completed = True
        order.save(update_fields=['is_completed'])
        return response.Response({'success': True})


class CategoryListView(generics.ListAPIView):
    serializer_class = CategorySerializer
    queryset = Category.objects.all()

    def get(self, request, *args, **kwargs):
        categories = Category.objects.prefetch_related('sub_categories').all()
        serializer = CategorySerializer(categories, many=True)
        data = serializer.data
        for category in data:
            sub_categories = category['sub_categories']
            filtered_sub_categories = [sub for sub in sub_categories if sub['parent'] is None]
            category['sub_categories'] = filtered_sub_categories
        return response.Response(data)


class ProductListView(generics.GenericAPIView):
    serializer_class = ProductSerializer

    def get(self, request, *args, **kwargs):
        user = TelegramUser.objects.filter(chat_id=self.kwargs['chat_id']).first()
        data = list()
        for i in Product.objects.filter(category_id=self.kwargs['subcategory_id']).order_by('order'):
            d = ProductSerializer(i).data
            if Cart.objects.filter(product_id=i.id, user_id=user.id).exists():
                d['has_in_cart'] = True
            else:
                d['has_in_cart'] = False
            data.append(d)
        return response.Response(data)


class ProductDetailView(generics.RetrieveAPIView):
    serializer_class = ProductSerializer
    queryset = Product.objects.all()

    def get(self, request, *args, **kwargs):
        user = TelegramUser.objects.filter(chat_id=self.kwargs['chat_id']).first()
        serializer = ProductSerializer(self.get_object()).data
        if Cart.objects.filter(product_id=self.kwargs['pk'], user_id=user.id).exists():
            serializer['has_in_cart'] = True
        else:
            serializer['has_in_cart'] = False
        return response.Response(serializer)


class CartListView(generics.ListAPIView):
    serializer_class = CartSerializer

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return CartSerializer
        return OrderProductSerializer

    def get_queryset(self):
        return Cart.objects.filter(user__chat_id=self.kwargs['chat_id'])

    def post(self, request, *args, **kwargs):
        user = TelegramUser.objects.filter(chat_id=self.kwargs['chat_id']).first()
        if not user:
            return response.Response({'error': 'User not found'}, status=404)
        product_id = self.request.data['product']
        count = int(self.request.data['count'])
        # Upsert: re-adding a product must not create a second row for it.
        cart = Cart.objects.filter(user_id=user.id, product_id=product_id).first()
        if cart:
            cart.count = count
            cart.save()
        else:
            Cart.objects.create(user_id=user.id, product_id=product_id, count=count)
        return response.Response({'success': True})


class CartItemView(generics.GenericAPIView):
    serializer_class = CartSerializer

    def get_queryset(self):
        return Cart.objects.filter(user__chat_id=self.kwargs['chat_id'],
                                   product_id=self.kwargs['product_id'])

    def patch(self, request, *args, **kwargs):
        cart = self.get_queryset().first()
        if not cart:
            return response.Response({'error': 'Cart item not found'}, status=404)
        count = int(request.data['count'])
        if count < 1:
            # Dropping to zero means the user removed the item.
            self.get_queryset().delete()
            return response.Response({'success': True})
        cart.count = count
        cart.save()
        return response.Response({'success': True})

    def delete(self, request, *args, **kwargs):
        # filter().delete() also clears duplicate rows left by the old create() behaviour.
        deleted, _ = self.get_queryset().delete()
        if not deleted:
            return response.Response({'error': 'Cart item not found'}, status=404)
        return response.Response({'success': True})
