from django.contrib import admin
from .models import Category, Product, ProductImage, Order, OrderProduct, SubCategory, Bonus, UserSumma
from .translations import CustomAdmin, StackedAdmin


class OrderProductInline(admin.TabularInline):
    model = OrderProduct
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderProductInline]
    list_display = ['id', 'user', 'store', 'total', 'is_completed', 'created_at']
    list_filter = ['created_at', 'store', 'is_completed']


@admin.register(UserSumma)
class UserSummaAdmin(admin.ModelAdmin):
    list_display = ['user', 'code', 'summa', 'is_expired', 'created_at']
    list_filter = ['created_at', 'is_expired', 'user']


class SubCategoryInline(StackedAdmin):
    model = SubCategory
    extra = 0


@admin.register(Category)
class CategoryAdmin(CustomAdmin):
    list_display = ['id', 'name']
    inlines = [SubCategoryInline]


class ProductImageInline(admin.StackedInline):
    model = ProductImage
    extra = 0


class ProductBonusInline(admin.StackedInline):
    model = Bonus
    extra = 0


@admin.register(Product)
class ProductAdmin(CustomAdmin):
    inlines = [ProductImageInline, ProductBonusInline]
    list_display = ['id', 'name', 'price', 'category']
