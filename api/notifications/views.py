# api/notifications/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from api.notifications.models import Notification
from api.notifications.serializers import NotificationSerializer, NotificationListSerializer
from utils.notification_service import NotificationService


class NotificationListView(APIView):
    """
    GET /api/notifications/
    Lấy danh sách tất cả notifications của user hiện tại
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        notifications = Notification.objects.filter(
            user=request.user
        ).select_related('notification_type').order_by('-created_at')
        
        serializer = NotificationListSerializer(notifications, many=True)
        return Response({
            'count': notifications.count(),
            'notifications': serializer.data
        })


class NotificationDetailView(APIView):
    """
    GET /api/notifications/{id}/
    Chi tiết một notification
    
    DELETE /api/notifications/{id}/
    Xóa một notification
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        notification = get_object_or_404(
            Notification, 
            pk=pk, 
            user=request.user
        )
        serializer = NotificationSerializer(notification)
        return Response(serializer.data)
    
    def delete(self, request, pk):
        notification = get_object_or_404(
            Notification, 
            pk=pk, 
            user=request.user
        )
        notification.delete()
        return Response(
            {'message': 'Notification deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )


class NotificationUnreadView(APIView):
    """
    GET /api/notifications/unread/
    Lấy danh sách thông báo chưa đọc
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        notifications = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).select_related('notification_type').order_by('-created_at')
        
        serializer = NotificationListSerializer(notifications, many=True)
        return Response({
            'count': notifications.count(),
            'notifications': serializer.data
        })


class NotificationUnreadCountView(APIView):
    """
    GET /api/notifications/unread-count/
    Lấy số lượng thông báo chưa đọc (dùng cho badge icon)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        count = NotificationService.get_unread_count(request.user.id)
        return Response({'unread_count': count})


class NotificationMarkReadView(APIView):
    """
    POST /api/notifications/{id}/mark-read/
    Đánh dấu một thông báo đã đọc
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        notification = get_object_or_404(
            Notification, 
            pk=pk, 
            user=request.user
        )
        notification.mark_as_read()
        
        serializer = NotificationSerializer(notification)
        return Response({
            'message': 'Notification marked as read',
            'notification': serializer.data
        })


class NotificationMarkAllReadView(APIView):
    """
    POST /api/notifications/mark-all-read/
    Đánh dấu tất cả thông báo đã đọc
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        NotificationService.mark_all_as_read(request.user.id)
        return Response({'message': 'All notifications marked as read'})


class NotificationDeleteReadView(APIView):
    """
    DELETE /api/notifications/delete-read/
    Xóa tất cả thông báo đã đọc
    """
    permission_classes = [IsAuthenticated]
    
    def delete(self, request):
        deleted_count = Notification.objects.filter(
            user=request.user,
            is_read=True
        ).delete()[0]
        
        return Response({
            'message': f'Deleted {deleted_count} read notifications',
            'deleted_count': deleted_count
        })