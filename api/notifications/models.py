
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class NotificationType(models.Model):
    """Quản lý các loại thông báo"""
    type_code = models.CharField(max_length=50, unique=True)
    type_name = models.CharField(max_length=100)
    icon = models.CharField(max_length=100, blank=True)  # Icon class
    default_color = models.CharField(max_length=20, default='#9E9E9E')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notification_types'
        
    def __str__(self):
        return self.type_name


class Notification(models.Model):
    """Model lưu trữ thông báo cho người dùng"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.ForeignKey(NotificationType, on_delete=models.SET_NULL, null=True)
    
    title = models.CharField(max_length=255)
    content = models.TextField()
    redirect_url = models.URLField(max_length=500, blank=True, null=True)
    image_url = models.URLField(max_length=500, blank=True, null=True)
    
    # Metadata bổ sung (order_id, product_id, etc.) dạng JSON
    metadata = models.JSONField(default=dict, blank=True)
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    def mark_as_read(self):
        """Đánh dấu thông báo đã đọc"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    @property
    def is_expired(self):
        """Kiểm tra thông báo có hết hạn không"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False