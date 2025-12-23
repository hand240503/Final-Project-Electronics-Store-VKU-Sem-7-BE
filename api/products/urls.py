from django.urls import path
from .views import (
    CategoryParentsAPIView,
    CategoryProductsAPIView,
    ParentCategoryProductsAPIView,
    ProductDetailAPIView,
    ProductSearchView,
)
from . import views

urlpatterns = [
    path('admin/', views.product_list, name="product_list"),
    path('admin/create/', views.product_create, name="product_create"),
    path('admin/<int:pk>/', views.product_detail, name="product_detail"),
    path('admin/<int:pk>/edit/', views.product_update, name="product_update"),
    path('admin/<int:pk>/delete/', views.product_delete, name="product_delete"),
    # Lấy danh sách category cha + subcategories
    path('categories-parents/', CategoryParentsAPIView.as_view(), name='category-parents'),

    # Lấy sản phẩm theo category cụ thể
    # Nếu category_id = 0, có thể truyền ?type=popular/sale/best_seller
    path('categories/<int:category_id>/', CategoryProductsAPIView.as_view(), name='category-products'),

    # Lấy sản phẩm tất cả category con của parent
    # Nếu parent_id = 0, có thể truyền ?type=popular/sale/best_seller
    path('parent-categories/<int:parent_id>/', ParentCategoryProductsAPIView.as_view(), name='parent-category-products'),
    path('app/<int:product_id>/', ProductDetailAPIView.as_view(), name='product-detail'),

    # Tìm kiếm sản phẩm theo tên
    path('search/', ProductSearchView.as_view(), name='product-search'),
]


