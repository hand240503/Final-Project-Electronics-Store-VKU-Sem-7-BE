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

        # Lấy tất cả địa chỉ của user
        addresses = self.user.addresses.all()  # Sử dụng related_name 'addresses'

        # Chuyển thành dict để trả về JSON
        address_list = []
        for addr in addresses:
            address_list.append({
                "id": addr.id,
                "full_name": addr.full_name,
                "phone": addr.phone,
                "address_line": addr.address_line,
                "ward": addr.ward,
                "district": addr.district,
                "city": addr.city,
                "is_default": addr.is_default,
            })

        # Thêm user info và addresses vào response
        data["user"] = {
            "id": self.user.id,
            "username": self.user.username,
            "email": self.user.email,
            "first_name": self.user.first_name,
            "is_active": self.user.is_active,
            "addresses": address_list
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