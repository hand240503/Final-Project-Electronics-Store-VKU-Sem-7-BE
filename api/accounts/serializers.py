from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserAddress, Profile


class ProfileSerializer(serializers.ModelSerializer):
    birthday = serializers.DateField(
        format="%Y-%m-%d",
        input_formats=["%Y-%m-%d", "%d/%m/%Y"],
        required=False,
        allow_null=True
    )

    class Meta:
        model = Profile
        fields = [
            'id',
            'name',
            'bio',
            'gender',
            'birthday',
            'personal_info',
            'phone',
            'email'
        ]


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

        # Lấy hoặc tạo profile cho user
        profile, created = Profile.objects.get_or_create(
            user=self.user,
            defaults={
                'name': self.user.first_name,
                'email': self.user.email
            }
        )

        # Lấy tất cả địa chỉ của user
        addresses = self.user.addresses.all()

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

        # Thêm user info, profile và addresses vào response
        data["user"] = {
            "id": self.user.id,
            "username": self.user.username,
            "email": self.user.email,
            "first_name": self.user.first_name,
            "is_active": self.user.is_active,
            "addresses": address_list,
            "profile": ProfileSerializer(profile).data  # Thêm profile vào response
        }

        return data


class UserDetailSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "is_active",
            "date_joined",
            "profile"
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