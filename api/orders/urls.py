from django.urls import path
from .views import OrderCreateView, OrdersByUserView, OrderDetailView, CancelOrderAPIView
from . import views

urlpatterns = [

    path('', views.orders_list, name="orders_list"),
    path('<int:pk>/', views.orders_detail, name="orders_detail"),
    path('<int:order_id>/status/', views.orders_approve_next, name="orders_approve_next"),

    path('create/', OrderCreateView.as_view(), name='order-create'),
    path('user/<int:user_id>/', OrdersByUserView.as_view(), name='orders-by-user'),
    path('<int:order_id>/', OrderDetailView.as_view(), name='order-detail'),
    path('cancel/<int:order_id>/',
         CancelOrderAPIView.as_view(), name='cancel-order'),


]
