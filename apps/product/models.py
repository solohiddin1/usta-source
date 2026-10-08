from django.db import models
from django.conf import settings
from user.models import TelegramUser, Store


class Instruction(models.Model):
    id = models.IntegerField(primary_key=True)
    file_id = models.CharField(max_length=255)
    message_lang = models.CharField(max_length=100)
    message_id = models.IntegerField()
    message_text = models.TextField()
    from_id = models.CharField(max_length=255)
    message_type = models.CharField(max_length=100)

    def __str__(self):
        return self.message_id


class Category(models.Model):
    name = models.CharField(max_length=250, verbose_name="Имя")
    icon = models.ImageField(upload_to='categories/')

    @property
    def icon_url(self):
        return f"{settings.BASE_URL}{self.icon.url}"

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Категории'
        verbose_name = 'Категория'


class SubCategory(models.Model):
    name = models.CharField(max_length=250, verbose_name="Имя")
    parent = models.ForeignKey('self', models.CASCADE, 'children', null=True, blank=True,
                               limit_choices_to={'parent': None})
    icon = models.ImageField(upload_to='subcategories/', null=True, blank=True)
    category = models.ForeignKey(Category, models.CASCADE, 'sub_categories')

    def __str__(self):
        return self.name

    @property
    def icon_url(self):
        return f"{settings.BASE_URL}{self.icon.url}" if self.icon else None


class Product(models.Model):
    category = models.ForeignKey(SubCategory, models.CASCADE, 'products', verbose_name="Категория")
    name = models.CharField(max_length=250, verbose_name="Имя")
    order = models.IntegerField(default=1, verbose_name="Порядковый номер")
    price = models.IntegerField(verbose_name="Цена")
    description = models.TextField(verbose_name="Описание")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукты'


class Bonus(models.Model):
    product = models.ForeignKey(Product, models.CASCADE, 'bonuses')
    code = models.CharField(max_length=100, unique=True, verbose_name="Код")
    summa = models.IntegerField(default=1, verbose_name="Сумма")

    def __str__(self):
        return self.code

    class Meta:
        verbose_name = 'Бонус'
        verbose_name_plural = 'Бонус'


class UserSumma(models.Model):
    user = models.ForeignKey(TelegramUser, models.CASCADE, 'points')
    bonus = models.ForeignKey(Bonus, models.SET_NULL, 'redemptions', null=True, blank=True,
                              verbose_name="Бонус")
    code = models.CharField(max_length=500)
    # The amount granted at redemption time — Bonus.summa may be edited later, and the
    # expiry job must give back exactly what was given.
    summa = models.IntegerField(default=0, verbose_name="Сумма")
    is_expired = models.BooleanField(default=False, verbose_name="Истёк")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products')

    def __str__(self):
        return self.product.name

    @property
    def image_url(self):
        return f"{settings.BASE_URL}{self.image.url}"


class Order(models.Model):
    user = models.ForeignKey(TelegramUser, models.CASCADE, 'orders', verbose_name="Пользователь")
    total = models.IntegerField(default=1, verbose_name="общая сумма")
    store = models.ForeignKey(Store, models.CASCADE, 'orders', verbose_name="Магазин")
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Созданный на")

    def __str__(self):
        return self.user.name

    class Meta:
        verbose_name_plural = 'Заказы'
        verbose_name = 'Заказ'


class OrderProduct(models.Model):
    order = models.ForeignKey(Order, models.CASCADE, 'products')
    product = models.ForeignKey(Product, models.CASCADE, 'orders', verbose_name="Продукт")
    count = models.IntegerField(default=1, verbose_name="Количество")

    def __str__(self):
        return self.product.name


class Cart(models.Model):
    user = models.ForeignKey(TelegramUser, models.CASCADE, 'carts')
    product = models.ForeignKey(Product, models.CASCADE, 'carts')
    count = models.IntegerField(default=1)

    def __str__(self):
        return self.user.name

    class Meta:
        unique_together = ('user', 'product')
