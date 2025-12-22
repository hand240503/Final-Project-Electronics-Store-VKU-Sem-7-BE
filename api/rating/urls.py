
from django.urls import path
from .views import (
    TrackUserBehaviorView,
    GetUserInteractionsView,
    GetProductInteractionsView,
    GetTrendingProductsView
)

urlpatterns = [
    # Track user behavior
    path('track-behavior/', TrackUserBehaviorView.as_view(), name='track-behavior'),
    
    # Get user interactions history
    path('user-interactions/', GetUserInteractionsView.as_view(), name='user-interactions'),
    
    # Get product interactions statistics
    path('product-interactions/<int:product_id>/', GetProductInteractionsView.as_view(), name='product-interactions'),
    
    # Get trending products
    path('trending-products/', GetTrendingProductsView.as_view(), name='trending-products'),
]