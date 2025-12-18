from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserAddress
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Optional: thêm info vào token payload
        token["email"] = user.email
        token["first_name"] = user.first_name

        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        # =========================
        # THÊM USER INFO VÀO RESPONSE
        # =========================
        data["user"] = {
            "id": self.user.id,
            "username": self.user.username,
            "email": self.user.email,
            "first_name": self.user.first_name,
            "is_active": self.user.is_active,
        }

        return data

class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "is_active",
            "date_joined",
        ]

class UserAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAddress
        fields = [
            'id',
            'full_name',
            'phone',
            'address_line',
            'ward',
            'district',
            'city',
            'is_default',
        ]