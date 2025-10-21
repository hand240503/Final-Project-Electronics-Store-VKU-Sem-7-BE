# api/accounts/views.py

import random
import threading
from django.contrib.auth.models import User
from django.conf import settings
from django.core.mail import send_mail

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import MyTokenObtainPairSerializer
from .models import RegistrationOTP
from utils.email_utils import send_otp_email

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class RegisterView(APIView):
    def post(self, request, *args, **kwargs):
        data = request.data
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return Response({"detail": "Email and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            return Response({"detail": "Email is already registered."}, status=status.HTTP_400_BAD_REQUEST)

        # username chính là email
        user = User.objects.create_user(username=email, email=email, password=password, is_active=False)

        # Tạo OTP
        otp_code = str(random.randint(1000, 9999))
        RegistrationOTP.objects.create(user=user, otp=otp_code)

        # Trả phản hồi cho client ngay
        response = Response({
            "detail": "User created. OTP has been sent to your email.",
            "email": user.email,
        }, status=status.HTTP_201_CREATED)

        # Gửi mail ở background
        threading.Thread(target=send_otp_email, args=(email, otp_code)).start()

        return response

class VerifyOTPView(APIView):
    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")

        if not email or not otp:
            return Response({"detail": "Email and OTP are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
            otp_record = RegistrationOTP.objects.get(user=user)
        except (User.DoesNotExist, RegistrationOTP.DoesNotExist):
            return Response({"detail": "Invalid email or OTP."}, status=status.HTTP_400_BAD_REQUEST)

        if not otp_record.is_valid():
            return Response({"detail": "OTP expired."}, status=status.HTTP_400_BAD_REQUEST)

        if otp_record.otp != otp:
            return Response({"detail": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

        # Xác nhận thành công, kích hoạt user
        user.is_active = True
        user.save()  # lưu thay đổi

        # Tạo token
        refresh = RefreshToken.for_user(user)

        # Xóa OTP sau khi xác thực
        otp_record.delete()

        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "username": user.username,
            "email": user.email,
        }, status=status.HTTP_200_OK)
