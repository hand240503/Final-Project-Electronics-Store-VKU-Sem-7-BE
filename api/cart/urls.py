from django.urls import path
from .views import CheckoutAPIView, AddToCartAPIView, CartDetailAPIView, UpdateCartItemAPIView, DeleteCartItemAPIView

urlpatterns = [
    path('checkout/', CheckoutAPIView.as_view(), name='cart-checkout'),
    path('add/', AddToCartAPIView.as_view(), name='add-to-cart'),
    path('<int:user_id>/', CartDetailAPIView.as_view(), name='cart-detail'),
    path('<int:cart_item_id>/update/', UpdateCartItemAPIView.as_view(), name='update-cart-item'),
    path('<int:cart_item_id>/delete/', DeleteCartItemAPIView.as_view(), name='delete-cart-item'),
] 