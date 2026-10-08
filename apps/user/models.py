from django.db import models
from django.conf import settings


class Region(models.Model):
    name = models.CharField(max_length=100, verbose_name="Имя")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Регион"
        verbose_name_plural = 'Регионы'


class Info(models.Model):
    link = models.CharField(max_length=100, verbose_name="Ссылка на телеграмму")

    def __str__(self):
        return self.link

    class Meta:
        verbose_name = "Связаться с нами"
        verbose_name_plural = "Связаться с нами"


class InfoPhone(models.Model):
    info = models.ForeignKey(Info, models.CASCADE, 'phones')
    phone = models.CharField(max_length=100, verbose_name="Телефон")

    def __str__(self):
        return self.phone


class Store(models.Model):
    name = models.CharField(max_length=100, verbose_name="Имя")
    region = models.ForeignKey(Region, models.CASCADE, 'stores', verbose_name="Регион")
    longitude = models.CharField(max_length=100)
    latitude = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.region}, {self.name}"

    class Meta:
        verbose_name_plural = 'Магазины'
        verbose_name = 'Магазин'


class StorePhone(models.Model):
    phone = models.CharField(max_length=100, verbose_name="Телефон магазина")
    store = models.ForeignKey(Store, models.CASCADE, 'phones')

    def __str__(self):
        return self.phone


class Notification(models.Model):
    DRAFT = 'draft'
    QUEUED = 'queued'
    SENT = 'sent'
    STATUSES = [(DRAFT, 'Черновик'), (QUEUED, 'В очереди'), (SENT, 'Отправлено')]

    text = models.TextField(verbose_name="Текст")
    status = models.CharField(max_length=10, choices=STATUSES, default=DRAFT, verbose_name="Статус")
    sent_count = models.IntegerField(default=0, verbose_name="Доставлено")
    failed_count = models.IntegerField(default=0, verbose_name="Не доставлено")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Созданный на")
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Отправлено в")

    def __str__(self):
        return self.text[:50]

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'


class NotificationImage(models.Model):
    notification = models.ForeignKey(Notification, models.CASCADE, 'images')
    image = models.FileField(upload_to='notifications/', verbose_name="Изображение")

    def __str__(self):
        return self.image.name

    class Meta:
        verbose_name = 'Изображение'
        verbose_name_plural = 'Изображения'

    @property
    def image_url(self):
        # Telegram fetches the file itself, so it needs an absolute, publicly served URL.
        return f"{settings.BASE_URL}{self.image.url}"


class TelegramUser(models.Model):
    name = models.CharField(max_length=120, verbose_name="Имя")
    chat_id = models.BigIntegerField(unique=True)
    phone = models.CharField(max_length=100, verbose_name="Телефон")
    region = models.ForeignKey(Region, models.SET_NULL, null=True, blank=True, verbose_name="Регион")
    lang = models.CharField(max_length=2, verbose_name="Язык")
    summa = models.IntegerField(default=0, verbose_name="Сумма")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Созданный на")

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['summa']
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
