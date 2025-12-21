from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import datetime

class RegistrationOTP(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=4)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        """Kiểm tra OTP còn hiệu lực trong 5 phút"""
        return timezone.now() <= self.created_at + datetime.timedelta(minutes=5)

    def __str__(self):
        return f"{self.user.email} - {self.otp}"

class UserAddress(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='addresses'
    )
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    address_line = models.CharField(max_length=255)
    ward = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_address'
        verbose_name = 'User Address'
        verbose_name_plural = 'User Addresses'

    def __str__(self):
        return f"{self.full_name} - {self.city}"



class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    bio = models.TextField(
        blank=True,
        null=True
    )

    gender = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    birthday = models.DateField(
        blank=True,
        null=True
    )
    # Lưu dạng YYYY-MM-DD trong DB

    personal_info = models.TextField(
        blank=True,
        null=True
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    email = models.EmailField(
        blank=True,
        null=True
    )

    class Meta:
        db_table = 'user_profile'

    def __str__(self):
        return f"Profile of {self.user.username}"