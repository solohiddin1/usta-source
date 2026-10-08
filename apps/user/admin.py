from django.contrib import admin
from .models import Region, TelegramUser, InfoPhone, Info, StorePhone, Store, Notification, \
    NotificationImage
from .translations import CustomAdmin
from .tasks import broadcast_notification
from product.models import UserSumma, Order


class StorePhoneInline(admin.StackedInline):
    model = StorePhone
    extra = 0


class InfoPhoneInline(admin.StackedInline):
    model = InfoPhone
    extra = 0


class UserSummaInline(admin.StackedInline):
    model = UserSumma
    extra = 0
    fields = ['code', 'created_at']
    # created_at is auto_now_add, so it is not editable and the form drops it unless it
    # is declared readonly — that is why the redemption date was not showing.
    readonly_fields = ['created_at']


class OrderInline(admin.TabularInline):
    model = Order
    extra = 0
    can_delete = False
    show_change_link = True
    fields = ['id', 'products_list', 'store', 'total', 'is_completed', 'created_at']
    readonly_fields = ['id', 'products_list', 'store', 'total', 'is_completed', 'created_at']

    def has_add_permission(self, request, obj):
        return False

    @admin.display(description="Продукты")
    def products_list(self, obj):
        if not obj.pk:
            return ""
        return ", ".join(f"{item.product.name} x{item.count}" for item in obj.products.all())


@admin.register(Store)
class StoreAdmin(CustomAdmin):
    inlines = [StorePhoneInline]
    list_display = ['id', 'name', 'region']
    list_filter = ['region']


@admin.register(Info)
class InfoAdmin(admin.ModelAdmin):
    inlines = [InfoPhoneInline]
    list_display = ['id', 'link']


@admin.register(Region)
class RegionAdmin(CustomAdmin):
    list_display = ["id", "name"]


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ["phone", "name", "region", "summa", "lang", "created_at"]
    inlines = [UserSummaInline, OrderInline]


class NotificationImageInline(admin.StackedInline):
    model = NotificationImage
    extra = 1


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    inlines = [NotificationImageInline]
    list_display = ['id', 'short_text', 'status', 'sent_count', 'failed_count', 'created_at',
                    'sent_at']
    list_filter = ['status', 'created_at']
    readonly_fields = ['status', 'sent_count', 'failed_count', 'created_at', 'sent_at']
    actions = ['send_to_all_users']

    @admin.display(description="Текст")
    def short_text(self, obj):
        return obj.text[:60]

    @admin.action(description="Отправить всем пользователям")
    def send_to_all_users(self, request, queryset):
        # Already-sent broadcasts are skipped so a mis-click cannot blast every user a
        # second time. Queued ones stay re-sendable, which is the only way to retry after
        # a worker outage.
        already_sent = queryset.filter(status=Notification.SENT).count()
        pending = list(queryset.exclude(status=Notification.SENT).values_list('pk', flat=True))
        for pk in pending:
            Notification.objects.filter(pk=pk).update(status=Notification.QUEUED)
            broadcast_notification.delay(pk)
        message = f"{len(pending)}: поставлено в очередь на отправку."
        if already_sent:
            message += f" {already_sent} уже отправлено — пропущено."
        self.message_user(request, message)
