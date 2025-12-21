# utils/notification_service.py
from api.notifications.models import Notification, NotificationType
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Service để gửi và quản lý thông báo"""
    
    @staticmethod
    def send_noti(
        user_id: int,
        type_code: str = 'system',
        title: str = 'Thông báo',
        content: str = '',
        redirect_url: Optional[str] = None,
        image_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_in_days: Optional[int] = None
    ) -> Optional[Notification]:
        """
        Gửi thông báo cho người dùng
        
        Args:
            user_id: ID người dùng
            type_code: Mã loại thông báo ('order_placed', 'product_update', etc.)
            title: Tiêu đề thông báo
            content: Nội dung thông báo
            redirect_url: URL sẽ chuyển đến khi click
            image_url: URL hình ảnh thumbnail
            metadata: Dữ liệu bổ sung dạng dict
            expires_in_days: Số ngày hết hạn (None = không hết hạn)
            
        Returns:
            Notification object hoặc None nếu thất bại
        """
        try:
            # Lấy user
            user = User.objects.get(id=user_id)
            
            # Lấy notification type
            notification_type = NotificationType.objects.filter(
                type_code=type_code,
                is_active=True
            ).first()
            
            if not notification_type:
                logger.warning(f"Notification type '{type_code}' not found or inactive")
                notification_type = None
            
            # Tính thời gian hết hạn
            expires_at = None
            if expires_in_days:
                expires_at = timezone.now() + timedelta(days=expires_in_days)
            
            # Tạo notification
            notification = Notification.objects.create(
                user=user,
                notification_type=notification_type,
                title=title,
                content=content,
                redirect_url=redirect_url or '',
                image_url=image_url or '',
                metadata=metadata or {},
                expires_at=expires_at
            )
            
            logger.info(f"Notification created: {notification.id} for user {user_id}")
            return notification
            
        except User.DoesNotExist:
            logger.error(f"User {user_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error creating notification: {str(e)}")
            return None
    
    @staticmethod
    def send_order_notification(user_id: int, order_id: int, status: str):
        """Gửi thông báo về đơn hàng"""
        status_config = {
            'placed': {
                'type_code': 'order_placed',
                'title': 'Đặt hàng thành công',
                'content': f'Đơn hàng #{order_id} của bạn đã được đặt thành công!'
            },
            'shipped': {
                'type_code': 'order_shipped',
                'title': 'Đơn hàng đang vận chuyển',
                'content': f'Đơn hàng #{order_id} đang trên đường giao đến bạn!'
            },
            'delivered': {
                'type_code': 'order_delivered',
                'title': 'Giao hàng thành công',
                'content': f'Đơn hàng #{order_id} đã được giao thành công!'
            }
        }
        
        config = status_config.get(status, status_config['placed'])
        
        return NotificationService.send_noti(
            user_id=user_id,
            type_code=config['type_code'],
            title=config['title'],
            content=config['content'],
            redirect_url=f'/orders/{order_id}',
            metadata={'order_id': order_id, 'status': status}
        )
    
    @staticmethod
    def send_product_update_notification(user_id: int, product_id: int, product_name: str):
        """Gửi thông báo cập nhật sản phẩm"""
        return NotificationService.send_noti(
            user_id=user_id,
            type_code='product_update',
            title='Cập nhật sản phẩm',
            content=f'Sản phẩm "{product_name}" có cập nhật mới!',
            redirect_url=f'/products/{product_id}',
            metadata={'product_id': product_id}
        )
    
    @staticmethod
    def send_promotion_notification(user_id: int, promotion_title: str, promotion_url: str):
        """Gửi thông báo khuyến mãi"""
        return NotificationService.send_noti(
            user_id=user_id,
            type_code='promotion',
            title='Khuyến mãi đặc biệt',
            content=promotion_title,
            redirect_url=promotion_url,
            expires_in_days=7  # Khuyến mãi hết hạn sau 7 ngày
        )
    
    @staticmethod
    def get_unread_count(user_id: int) -> int:
        """Lấy số thông báo chưa đọc"""
        return Notification.objects.filter(
            user_id=user_id,
            is_read=False
        ).count()
    
    @staticmethod
    def mark_all_as_read(user_id: int):
        """Đánh dấu tất cả thông báo đã đọc"""
        Notification.objects.filter(
            user_id=user_id,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
    
    @staticmethod
    def delete_old_notifications(days: int = 30):
        """Xóa thông báo cũ hơn X ngày"""
        cutoff_date = timezone.now() - timedelta(days=days)
        deleted_count = Notification.objects.filter(
            created_at__lt=cutoff_date
        ).delete()[0]
        logger.info(f"Deleted {deleted_count} old notifications")
        return deleted_count