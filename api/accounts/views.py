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

from .serializers import MyTokenObtainPairSerializer, ProfileSerializer
from .models import RegistrationOTP, UserAddress
from utils.email_utils import send_otp_email
from .serializers import UserDetailSerializer
from rest_framework.permissions import IsAuthenticated
from .serializers import UserAddressSerializer
from .models import Profile
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
            return Response(
                {"detail": "Email and password are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(email=email).exists():
            return Response(
                {"detail": "Email is already registered."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # =============================
        # GEN FIRST NAME TỪ EMAIL
        # =============================
        first_name = email.split("@")[0]

        # =============================
        # CREATE USER
        # =============================
        user = User.objects.create_user(
            username=email,      # username = email
            email=email,
            password=password,
            first_name=first_name,
            is_active=False      # chờ verify OTP
        )

        # =============================
        # CREATE PROFILE (Tự động)
        # =============================
        Profile.objects.create(
            user=user,
            name=first_name,  # Set name = first_name ban đầu
            email=email       # Set email vào profile
        )

        # =============================
        # CREATE OTP
        # =============================
        otp_code = str(random.randint(1000, 9999))
        RegistrationOTP.objects.create(user=user, otp=otp_code)

        # =============================
        # RESPONSE NGAY
        # =============================
        response = Response(
            {
                "detail": "User created. OTP has been sent to your email.",
                "email": user.email,
                "first_name": user.first_name
            },
            status=status.HTTP_201_CREATED
        )

        # =============================
        # SEND MAIL BACKGROUND
        # =============================
        threading.Thread(
            target=send_otp_email,
            args=(email, otp_code)
        ).start()

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
        user.save()

        # Tạo token
        refresh = RefreshToken.for_user(user)

        # Lấy hoặc tạo profile
        profile, created = Profile.objects.get_or_create(
            user=user,
            defaults={
                'name': user.first_name,
                'email': user.email
            }
        )

        # Xóa OTP sau khi xác thực
        otp_record.delete()

        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
            },
            "profile": ProfileSerializer(profile).data
        }, status=status.HTTP_200_OK)


class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Lấy hoặc tạo profile
        profile, created = Profile.objects.get_or_create(
            user=user,
            defaults={
                'name': user.first_name,
                'email': user.email
            }
        )

        data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "is_active": user.is_active,
            "date_joined": user.date_joined,
            "profile": ProfileSerializer(profile).data
        }

        return Response(data, status=status.HTTP_200_OK)


class ProfileDetailView(APIView):
    """
    GET /api/accounts/profile/
    Lấy profile của user hiện tại
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Lấy hoặc tạo profile
        profile, created = Profile.objects.get_or_create(
            user=request.user,
            defaults={
                'name': request.user.first_name,
                'email': request.user.email
            }
        )

        return Response(
            ProfileSerializer(profile).data,
            status=status.HTTP_200_OK
        )


class UpdateProfileView(APIView):
    """
    PUT /api/accounts/profile/update/
    Cập nhật profile của user hiện tại
    """
    permission_classes = [IsAuthenticated]

    def put(self, request):
        # Lấy hoặc tạo profile
        profile, created = Profile.objects.get_or_create(
            user=request.user,
            defaults={
                'name': request.user.first_name,
                'email': request.user.email
            }
        )

        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        
        if not serializer.is_valid():
            return Response(
                {
                    "detail": "Invalid data",
                    "errors": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        updated_profile = serializer.save()

        return Response(
            {
                "detail": "Profile updated successfully",
                "profile": ProfileSerializer(updated_profile).data
            },
            status=status.HTTP_200_OK
        )


class AddUserAddressView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UserAddressSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    "detail": "Invalid data",
                    "errors": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Nếu address mới là default → bỏ default address cũ
        if serializer.validated_data.get('is_default', False):
            UserAddress.objects.filter(
                user=request.user,
                is_default=True
            ).update(is_default=False)

        address = serializer.save(user=request.user)

        return Response(
            {
                "detail": "Address added successfully",
                "data": UserAddressSerializer(address).data
            },
            status=status.HTTP_201_CREATED
        )


class UserAddressByUserIdView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        # Nếu không phải admin → chỉ được xem address của chính mình
        if not request.user.is_staff and request.user.id != user_id:
            return Response(
                {"detail": "You do not have permission to view this user's addresses."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        addresses = UserAddress.objects.filter(user=user).order_by('-is_default', '-created_at')

        serializer = UserAddressSerializer(addresses, many=True)

        return Response(
            {
                "user_id": user.id,
                "email": user.email,
                "addresses": serializer.data
            },
            status=status.HTTP_200_OK
        )


class UpdateUserAddressView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, address_id):
        try:
            address = UserAddress.objects.get(id=address_id)
        except UserAddress.DoesNotExist:
            return Response({"detail": "Address not found"}, status=status.HTTP_404_NOT_FOUND)

        # Kiểm tra quyền
        if not request.user.is_staff and address.user != request.user:
            return Response({"detail": "You do not have permission to update this address."}, status=status.HTTP_403_FORBIDDEN)

        serializer = UserAddressSerializer(address, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({"detail": "Invalid data", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        # Nếu set default → bỏ default address cũ
        if serializer.validated_data.get('is_default', False):
            UserAddress.objects.filter(user=address.user, is_default=True).exclude(id=address.id).update(is_default=False)

        updated_address = serializer.save()

        return Response({
            "detail": "Address updated successfully",
            "data": UserAddressSerializer(updated_address).data
        }, status=status.HTTP_200_OK)


class DeleteUserAddressView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, address_id):
        try:
            address = UserAddress.objects.get(id=address_id)
        except UserAddress.DoesNotExist:
            return Response({"detail": "Address not found"}, status=status.HTTP_404_NOT_FOUND)

        # Kiểm tra quyền
        if not request.user.is_staff and address.user != request.user:
            return Response({"detail": "You do not have permission to delete this address."}, status=status.HTTP_403_FORBIDDEN)

        address.delete()
        return Response({"detail": "Address deleted successfully"}, status=status.HTTP_200_OK)