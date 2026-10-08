from django.urls import path
from .views import RegionListView, UserListView, TelegramUserView, CheckCodeView, \
    UserCheckView, InfoView, StoreListView

urlpatterns = [
    path('<int:chat_id>/', TelegramUserView.as_view(), name='telegram_user'),
    path('regions/', RegionListView.as_view(), name='regions'),
    path('check/<int:chat_id>/', UserCheckView.as_view(), name='check-user'),
    path('users/', UserListView.as_view(), name='users'),
    path('bonus/<str:code>/', CheckCodeView.as_view(), name='check-code'),
    path('info/', InfoView.as_view(), name='info'),
    path('stores/<int:chat_id>/', StoreListView.as_view(), name='stores'),
]
