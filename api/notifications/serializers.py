from api.notifications.models import Notification, NotificationType
from rest_framework import serializers

class NotificationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationType
        fields = ['id', 'type_code', 'type_name', 'icon', 'default_color']


class NotificationSerializer(serializers.ModelSerializer):
    notification_type = NotificationTypeSerializer(read_only=True)
    is_expired = serializers.ReadOnlyField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'notification_type', 'title', 'content',
            'redirect_url', 'image_url', 'metadata', 'is_read',
            'created_at', 'read_at', 'expires_at', 'is_expired'
        ]
        read_only_fields = ['user', 'created_at', 'read_at']


class NotificationListSerializer(serializers.ModelSerializer):
    """Serializer đơn giản cho danh sách"""
    type_name = serializers.CharField(source='notification_type.type_name', read_only=True)
    type_icon = serializers.CharField(source='notification_type.icon', read_only=True)
    type_color = serializers.CharField(source='notification_type.default_color', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'content', 'redirect_url', 'image_url',
            'type_name', 'type_icon', 'type_color',
            'is_read', 'created_at'
        ]