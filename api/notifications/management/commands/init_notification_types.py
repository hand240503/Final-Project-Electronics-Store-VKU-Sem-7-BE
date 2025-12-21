from django.core.management.base import BaseCommand
from api.notifications.models import NotificationType

class Command(BaseCommand):
    help = 'Initialize notification types'

    def handle(self, *args, **options):
        notification_types = [
            {
                'type_code': 'order_placed',
                'type_name': 'Đặt hàng thành công',
                'icon': 'shopping-cart',
                'default_color': '#4CAF50'
            },
            {
                'type_code': 'order_shipped',
                'type_name': 'Đơn hàng đang vận chuyển',
                'icon': 'truck',
                'default_color': '#2196F3'
            },
            {
                'type_code': 'order_delivered',
                'type_name': 'Giao hàng thành công',
                'icon': 'check-circle',
                'default_color': '#8BC34A'
            },
            {
                'type_code': 'product_update',
                'type_name': 'Cập nhật sản phẩm',
                'icon': 'package',
                'default_color': '#FF9800'
            },
            {
                'type_code': 'promotion',
                'type_name': 'Khuyến mãi',
                'icon': 'gift',
                'default_color': '#E91E63'
            },
            {
                'type_code': 'system',
                'type_name': 'Thông báo hệ thống',
                'icon': 'bell',
                'default_color': '#9E9E9E'
            }
        ]
        
        for nt_data in notification_types:
            NotificationType.objects.get_or_create(
                type_code=nt_data['type_code'],
                defaults=nt_data
            )
        
        self.stdout.write(self.style.SUCCESS('Successfully initialized notification types'))