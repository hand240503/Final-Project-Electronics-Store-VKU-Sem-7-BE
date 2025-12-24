"""
Recommendation API Views - Simplified Version
Location: api/recommender/views.py

API Endpoints:
    GET /api/recommendations/popular/  - Lấy sản phẩm phổ biến
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from api.recommender.services import RecommendationService
from api.products.serializers import ProductSerializer
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_popular_products(request):
    """
    GET /api/recommendations/popular/
    
    Lấy danh sách sản phẩm phổ biến (best sellers)
    Endpoint này public, không cần authentication
    
    Query params:
        - limit: số lượng sản phẩm muốn lấy (mặc định: 10)
    
    Response:
        {
            "count": 10,
            "results": [
                {
                    "id": 1,
                    "name": "iPhone 13",
                    "price": 20000000,
                    ...
                    "rating_count": 150,      # Số lượng đánh giá
                    "avg_rating": 4.5         # Điểm trung bình
                }
            ]
        }
    """
    try:
        # 1. Lấy tham số limit từ query string
        # Nếu không có thì mặc định là 10
        limit = int(request.query_params.get('limit', 10))
        
        # 2. Gọi service để lấy danh sách sản phẩm phổ biến
        # Service sẽ sắp xếp theo số lượng rating và điểm rating
        popular_products = RecommendationService.get_popular_products(limit=limit)
        
        # 3. Serialize products thành JSON
        # many=True vì có nhiều sản phẩm
        serializer = ProductSerializer(popular_products, many=True)
        
        # 4. Thêm thông tin rating vào response
        results = []
        for i, product_data in enumerate(serializer.data):
            # Kiểm tra xem product có rating_count không
            if hasattr(popular_products[i], 'rating_count'):
                product_data['rating_count'] = popular_products[i].rating_count
            
            # Kiểm tra xem product có avg_rating không
            if hasattr(popular_products[i], 'avg_rating'):
                product_data['avg_rating'] = float(popular_products[i].avg_rating or 0)
            
            results.append(product_data)
        
        # 5. Trả về response với status 200 OK
        return Response({
            'count': len(results),
            'results': results
        })
        
    except Exception as e:
        # Log lỗi để debug
        logger.error(f"Error in get_popular_products: {str(e)}")
        
        # Trả về response lỗi với status 500
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )