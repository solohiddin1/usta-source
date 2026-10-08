import time

from celery import shared_task
from django.utils import timezone

from .models import Notification, TelegramUser
from .utils import send_telegram_message

# Telegram caps a media group at 10 items and throttles bulk sending at ~30 messages/s.
MAX_IMAGES = 10
SEND_INTERVAL = 0.05


def build_payload(chat_id, text, images):
    if not images:
        return {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, "sendMessage"
    if len(images) == 1:
        return {"chat_id": chat_id, "photo": images[0], "caption": text,
                "parse_mode": "HTML"}, "sendPhoto"
    media = [{"type": "photo", "media": url} for url in images]
    media[0].update({"caption": text, "parse_mode": "HTML"})
    return {"chat_id": chat_id, "media": media}, "sendMediaGroup"


@shared_task
def broadcast_notification(notification_id):
    notification = Notification.objects.filter(id=notification_id).first()
    if not notification:
        return
    images = [image.image_url for image in notification.images.all()[:MAX_IMAGES]]
    sent = 0
    failed = 0
    for chat_id in TelegramUser.objects.values_list('chat_id', flat=True).iterator():
        data, method = build_payload(chat_id, notification.text, images)
        try:
            ok = send_telegram_message(data, method).status_code == 200
        except Exception:
            # A user who blocked the bot, or a transient network error, must not
            # abandon the rest of the broadcast.
            ok = False
        if ok:
            sent += 1
        else:
            failed += 1
        time.sleep(SEND_INTERVAL)
    Notification.objects.filter(id=notification_id).update(
        status=Notification.SENT,
        sent_at=timezone.now(),
        sent_count=sent,
        failed_count=failed,
    )
