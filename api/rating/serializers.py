from rest_framework import serializers
from api.rating.models import CollectorLog, Rating


class TrackBehaviorSerializer(serializers.Serializer):
    """Serializer for tracking user behavior"""
    product_id = serializers.IntegerField(required=True)
    event = serializers.ChoiceField(
        choices=['details', 'moreDetails', 'addToCart', 'buy'],
        required=True
    )
    session_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    device_type = serializers.CharField(max_length=50, required=False, default='unknown')
    platform = serializers.CharField(max_length=50, required=False, default='web')
    metadata = serializers.JSONField(required=False, default=dict)


class CollectorLogSerializer(serializers.ModelSerializer):
    """Serializer for CollectorLog model"""
    user_username = serializers.CharField(source='user.username', read_only=True, allow_null=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = CollectorLog
        fields = [
            'id',
            'user',
            'user_username',
            'product',
            'product_name',
            'event',
            'session_id',
            'device_type',
            'platform',
            'metadata',
            'ip_address',
            'timestamp'
        ]
        read_only_fields = ['id', 'timestamp', 'user_username', 'product_name']


class ImplicitRatingSerializer(serializers.ModelSerializer):
    """Serializer for Implicit Rating"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = Rating
        fields = [
            'id',
            'product',
            'product_name',
            'score',
            'confidence',
            'source',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'product_name']