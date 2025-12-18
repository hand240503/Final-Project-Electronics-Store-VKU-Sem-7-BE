from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    MyTokenObtainPairView,
    RegisterView,
    VerifyOTPView,
    UserDetailView,
    AddUserAddressView,
    UserAddressByUserIdView,
    UpdateUserAddressView,
    DeleteUserAddressView,
)

urlpatterns = [
    path('login/', MyTokenObtainPairView.as_view(), name='api-login'),
    path('register/', RegisterView.as_view(), name='api-register'), 
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path("users/<int:user_id>/", UserDetailView.as_view(), name="user-detail"),
    path('addresses/add/', AddUserAddressView.as_view(), name='add-user-address'),
    path('addresses/user/<int:user_id>/', UserAddressByUserIdView.as_view(), name='user-address-by-user'),
    path('addresses/<int:address_id>/update/', UpdateUserAddressView.as_view(), name='update_address'),
    path('addresses/<int:address_id>/delete/', DeleteUserAddressView.as_view(), name='delete_address'),
]