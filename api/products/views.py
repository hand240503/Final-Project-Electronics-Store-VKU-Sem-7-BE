from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Category, Product
from .serializers import CategoryParentFESerializer, ProductsByCategoryFESerializer,ProductDetailSerializer

# ==========================
# Lấy danh sách category cha + subcategories
# ==========================
class CategoryParentsAPIView(APIView):
    def get(self, request):
        categories = Category.objects.filter(parent=None)
        serializer = CategoryParentFESerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ==========================
# Lấy sản phẩm theo category cụ thể
# ==========================
class CategoryProductsAPIView(APIView):
    def get(self, request, category_id):
        if category_id == 0:
            # Lấy 6 sản phẩm bất kỳ theo type: popular/sale/best_seller
            mode = request.GET.get('type', None)  # ?type=popular
            fake_category = Category(id=0, name='All Products', slug='all')
            serializer = ProductsByCategoryFESerializer(fake_category, context={'mode': mode})
        else:
            category = Category.objects.filter(id=category_id).first()
            if not category:
                return Response({'detail': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)
            serializer = ProductsByCategoryFESerializer(category)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ==========================
# Lấy sản phẩm tất cả category con của parent
# ==========================
class ParentCategoryProductsAPIView(APIView):
    def get(self, request, parent_id):
        if parent_id == 0:
            mode = request.GET.get('type', None)
            fake_category = Category(id=0, name='All Products', slug='all')
            serializer = ProductsByCategoryFESerializer(fake_category, context={'mode': mode})
        else:
            parent = Category.objects.filter(id=parent_id).first()
            if not parent:
                return Response({'detail': 'Parent category not found'}, status=status.HTTP_404_NOT_FOUND)
            serializer = ProductsByCategoryFESerializer(parent, context={'mode': 'parent'})
        return Response(serializer.data, status=status.HTTP_200_OK)

# ======================================================
#   Lấy chi tiết sản phẩm theo ID
# ======================================================
class ProductDetailAPIView(APIView):
    """
    GET /api/products/<int:product_id>/
    Trả về chi tiết sản phẩm (brand, variants, reviews, images,...)
    """
    def get(self, request, product_id):
        product = Product.objects.filter(id=product_id, is_available=True).first()
        if not product:
            return Response(
                {"detail": "Product not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ProductDetailSerializer(product, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)