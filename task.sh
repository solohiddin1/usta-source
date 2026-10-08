#!/bin/sh
cd /app

python manage.py shell <<'EOF'
import datetime
import traceback
from django.db import transaction
from django.utils import timezone
from product.models import Order, UserSumma
from user.utils import send_telegram_message


def order_lines(order, lang):
    lines = ""
    for item in order.products.all():
        if lang == 'uz':
            lines += f"Nomi: {item.product.name_uz}\nSoni: {item.count}\nNarxi: {item.product.price} so'm\n"
        else:
            lines += f"Продукт: {item.product.name_ru}\nКоличество: {item.count}\nСтоимость: {item.product.price} Сум\n"
    return lines


def send_question():
    five_days_ago = timezone.now() - datetime.timedelta(days=5)
    orders = (Order.objects.filter(created_at__date=five_days_ago.date())
              .select_related('user', 'store')
              .prefetch_related('products__product'))
    for order in orders:
        try:
            data = {"chat_id": order.user.chat_id, "parse_mode": "HTML"}
            # The order id travels in callback_data: the bot splits on "_" to report
            # which order was confirmed.
            if order.user.lang == 'uz':
                data["text"] = (f"<b>{order.id}</b>-raqamli buyurtmani qabul qildingizmi?\n\n"
                                f"{order_lines(order, 'uz')}"
                                f"Do'kon: {order.store.name_uz}\n"
                                f"Jami: {order.total} so'm")
                data["reply_markup"] = {
                    "inline_keyboard": [
                        [{"text": "Ha✅", "callback_data": f"yes_{order.id}"},
                         {"text": "Yo'q❌", "callback_data": f"no_{order.id}"}]]}
            elif order.user.lang == 'ru':
                data["text"] = (f"Вы получили заказ <b>№{order.id}</b>?\n\n"
                                f"{order_lines(order, 'ru')}"
                                f"Магазин: {order.store.name_ru}\n"
                                f"Итого: {order.total} Сум")
                data["reply_markup"] = {
                    "inline_keyboard": [
                        [{"text": "Да✅", "callback_data": f"yes_{order.id}"},
                         {"text": "Нет❌", "callback_data": f"no_{order.id}"}]]}
            else:
                continue
            send_telegram_message(data)
        except Exception:
            # One unsendable order must not abandon the rest of the batch.
            traceback.print_exc()


def process_user_points():
    one_year_ago = timezone.now() - datetime.timedelta(days=365)
    one_week_left = timezone.now() - datetime.timedelta(days=365 - 7)

    # is_expired makes this idempotent: without it every nightly run would deduct the
    # same point again, forever.
    expired_points = UserSumma.objects.filter(created_at__lte=one_year_ago, is_expired=False)
    for point in expired_points.select_related('user'):
        with transaction.atomic():
            user = point.user
            # Never drive a balance negative — the bonus may already have been spent.
            user.summa = max(0, user.summa - point.summa)
            user.save()
            point.is_expired = True
            point.save(update_fields=['is_expired'])

    # Warn exactly once, on the day a point has 7 days left. The old range() had its
    # bounds the wrong way round and therefore never matched anything.
    points_soon_to_expire = UserSumma.objects.filter(created_at__date=one_week_left.date(),
                                                     is_expired=False).select_related('user')
    for point in points_soon_to_expire:
        data = {"chat_id": point.user.chat_id}
        if point.user.lang == 'uz':
            data["text"] = "Balingizni foydalaning, yuqsa 1 haftadan keyin o'chib ketadi."
        else:
            data["text"] = "Используйте свои баллы, если они пропадут через 1 неделю."
        send_telegram_message(data)


# Django's shell execs this whole heredoc as a single block, so an unguarded failure in
# one job cancels every job after it. process_user_points() does fail — it reads
# point.bonus, which UserSumma does not have — and that silently cancelled the survey.
for job in (send_question, process_user_points):
    try:
        job()
    except Exception:
        traceback.print_exc()
EOF
echo "Cronjob has successfully completed!"
