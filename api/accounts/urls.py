from django.urls import path
from .views import MyTokenObtainPairView, RegisterView, VerifyOTPView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('login/', MyTokenObtainPairView.as_view(), name='api-login'),
    path('register/', RegisterView.as_view(), name='api-register'), 
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]