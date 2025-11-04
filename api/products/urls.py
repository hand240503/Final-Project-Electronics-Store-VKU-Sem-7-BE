from django.urls import path
from .views import (
    CategoryParentsAPIView,
    CategoryProductsAPIView,
    ParentCategoryProductsAPIView,
    ProductDetailAPIView,
)

urlpatterns = [
    # Lấy danh sách category cha + subcategories
    path('categories-parents/', CategoryParentsAPIView.as_view(), name='category-parents'),

    # Lấy sản phẩm theo category cụ thể
    # Nếu category_id = 0, có thể truyền ?type=popular/sale/best_seller
    path('categories/<int:category_id>/', CategoryProductsAPIView.as_view(), name='category-products'),

    # Lấy sản phẩm tất cả category con của parent
    # Nếu parent_id = 0, có thể truyền ?type=popular/sale/best_seller
    path('parent-categories/<int:parent_id>/', ParentCategoryProductsAPIView.as_view(), name='parent-category-products'),
    path('<int:product_id>/', ProductDetailAPIView.as_view(), name='product-detail'),
]
