# api/notifications/urls.py (hoặc api/urls.py)

from django.urls import path
from api.notifications.views import (
    NotificationListView,
    NotificationDetailView,
    NotificationUnreadView,
    NotificationUnreadCountView,
    NotificationMarkReadView,
    NotificationMarkAllReadView,
    NotificationDeleteReadView,
)

urlpatterns = [
    # Danh sách và chi tiết
    path('', NotificationListView.as_view(), name='notification-list'),
    path('<int:pk>/', NotificationDetailView.as_view(), name='notification-detail'),
    
    # Chưa đọc
    path('unread/', NotificationUnreadView.as_view(), name='notification-unread'),
    path('unread-count/', NotificationUnreadCountView.as_view(), name='notification-unread-count'),
    
    # Đánh dấu đã đọc
    path('<int:pk>/mark-read/', NotificationMarkReadView.as_view(), name='notification-mark-read'),
    path('mark-all-read/', NotificationMarkAllReadView.as_view(), name='notification-mark-all-read'),
    
    # Xóa
    path('delete-read/', NotificationDeleteReadView.as_view(), name='notification-delete-read'),
]

"""
=== CÁC API ENDPOINTS ===

1. GET    /api/notifications/
   - Lấy danh sách tất cả notifications
   - Response: {count: int, notifications: [...]}

2. GET    /api/notifications/{id}/
   - Lấy chi tiết 1 notification
   - Response: {id, title, content, ...}

3. DELETE /api/notifications/{id}/
   - Xóa 1 notification
   - Response: {message: "Notification deleted successfully"}

4. GET    /api/notifications/unread/
   - Lấy danh sách chưa đọc
   - Response: {count: int, notifications: [...]}

5. GET    /api/notifications/unread-count/
   - Lấy số lượng chưa đọc (dùng cho badge)
   - Response: {unread_count: int}

6. POST   /api/notifications/{id}/mark-read/
   - Đánh dấu 1 notification đã đọc
   - Response: {message: "...", notification: {...}}

7. POST   /api/notifications/mark-all-read/
   - Đánh dấu tất cả đã đọc
   - Response: {message: "All notifications marked as read"}

8. DELETE /api/notifications/delete-read/
   - Xóa tất cả notifications đã đọc
   - Response: {message: "...", deleted_count: int}
"""