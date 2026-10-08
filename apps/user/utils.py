from requests import post
from django.conf import settings


def send_telegram_message(data: dict, method: str = "sendMessage"):
    res = post(f"https://api.telegram.org/bot{settings.BOT_TOKEN}/{method}", json=data)
    return res
