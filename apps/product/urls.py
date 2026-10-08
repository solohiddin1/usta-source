from django.urls import path
from .views import CategoryListView, ProductListView, ProductDetailView, CartListView, CartItemView, OrderView, \
    OrderConfirmView, InstructionView

urlpatterns = [
    path('categories/', CategoryListView.as_view(), name='categories'),
    path('products/<int:subcategory_id>/<int:chat_id>/', ProductListView.as_view(), name='products'),
    path('<int:pk>/<int:chat_id>/', ProductDetailView.as_view(), name='product-detail'),
    path('my-cart/<int:chat_id>/', CartListView.as_view(), name='cart'),
    path('my-cart/<int:chat_id>/<int:product_id>/', CartItemView.as_view(), name='cart-item'),
    path('order/<int:chat_id>/', OrderView.as_view(), name='order'),
    path('order/<int:chat_id>/<int:order_id>/confirm/', OrderConfirmView.as_view(), name='order-confirm'),
    path('instruction/<int:pk>/', InstructionView.as_view(), name='instruction')
]
