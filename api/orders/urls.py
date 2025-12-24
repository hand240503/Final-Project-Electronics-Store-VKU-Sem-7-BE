from django.urls import path
from .views import OrderCreateView, OrdersByUserView, OrderDetailView, CancelOrderAPIView, ReturnOrderAPIView,CancelReturnRequestAPIView
from . import views

urlpatterns = [

    path('admin/', views.orders_list, name="orders_list"),
    path('admin/<int:pk>/', views.orders_detail, name="orders_detail"),
    path('admin/<int:order_id>/approve-next/', views.orders_approve_next, name="orders_approve_next"),

    path('create/', OrderCreateView.as_view(), name='order-create'),
    path('user/<int:user_id>/', OrdersByUserView.as_view(), name='orders-by-user'),
    path('<int:order_id>/', OrderDetailView.as_view(), name='order-detail'),
    path('cancel/<int:order_id>/', CancelOrderAPIView.as_view(), name='cancel-order'),
    path('return/<int:order_id>/', ReturnOrderAPIView.as_view(), name='return-order'),
    path('cancel-return/<int:order_id>/', CancelReturnRequestAPIView.as_view(), name='cancel-return-request'),

    path('admin/returns/', views.returns_list, name='returns_list'),
    path('admin/returns/<int:order_id>/', views.returns_detail, name='returns_detail'),
    path('admin/returns/<int:order_id>/approve/', views.approve_return, name='approve_return'),
    path('admin/returns/<int:order_id>/reject/', views.reject_return, name='reject_return'),
    path('admin/returns/<int:order_id>/complete/', views.complete_return, name='complete_return'),

]
