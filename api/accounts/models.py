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
