"""
Product Recommendation Service - Simplified Version
Location: api/recommender/services.py

Chỉ giữ lại chức năng lấy sản phẩm phổ biến (popular products)
"""

from django.db.models import Count, Avg
from api.products.models import Product
import logging

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    Service class để xử lý recommendation logic
    """
    
    # Constants
    DEFAULT_LIMIT = 10
    POPULAR_MIN_RATINGS = 5  # Số rating tối thiểu để coi là "popular"
    
    @classmethod
    def get_popular_products(cls, limit=DEFAULT_LIMIT):
        """
        Lấy danh sách sản phẩm phổ biến (best sellers)
        Dùng cho cold start - khi user chưa có lịch sử
        
        Logic:
            1. Đếm số lượng ratings của mỗi sản phẩm
            2. Tính điểm rating trung bình
            3. Lọc sản phẩm có ít nhất POPULAR_MIN_RATINGS đánh giá
            4. Sắp xếp theo: avg_rating (ưu tiên) -> rating_count
            5. Lấy top N sản phẩm
        
        Args:
            limit: Số lượng sản phẩm tối đa muốn lấy (default: 10)
            
        Returns:
            List of Product objects với các attributes:
                - rating_count: Số lượng đánh giá
                - avg_rating: Điểm trung bình (0-5)
                - recommendation_score: Điểm normalized (0-1)
        """
        try:
            # 1. Annotate: thêm field tính toán vào QuerySet
            products = Product.objects.annotate(
                rating_count=Count('ratings'),
                avg_rating=Avg('ratings__score')
            ).filter(
                # 2. Filter: chỉ lấy sản phẩm có đủ ratings
                rating_count__gte=cls.POPULAR_MIN_RATINGS
            ).order_by(
                # 3. Sort: ưu tiên avg_rating cao, sau đó rating_count nhiều
                '-avg_rating',
                '-rating_count'
            )[:limit]
            
            # 4. Convert QuerySet thành list
            product_list = list(products)
            
            # 5. Attach recommendation_score (normalized về 0-1)
            for product in product_list:
                product.recommendation_score = float(product.avg_rating or 0) / 5.0
            
            logger.info(f"Returned {len(product_list)} popular products")
            return product_list
            
        except Exception as e:
            logger.error(f"Error getting popular products: {str(e)}")
            return list(Product.objects.all()[:limit])