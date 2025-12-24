"""
Product Recommendation Service
Location: api/recommender/services.py

2 chức năng chính:
1. Popular products (cold start)
2. Similar products (item-based collaborative filtering)
"""

from django.db.models import Count, Avg
from api.products.models import Product
from api.recommender.models import ProductSimilarity
import logging

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    Service class để xử lý recommendation logic
    """
    
    # Constants
    DEFAULT_LIMIT = 10
    POPULAR_MIN_RATINGS = 5
    MIN_SIMILARITY_SCORE = 0.02  # Ngưỡng similarity tối thiểu
    
    # =========================================================================
    # 1. POPULAR PRODUCTS - Cold Start
    # =========================================================================
    
    @classmethod
    def get_popular_products(cls, limit=DEFAULT_LIMIT):
        """
        Lấy danh sách sản phẩm phổ biến (best sellers)
        Dùng cho: Cold start - khi user chưa có lịch sử
        
        Logic:
            1. Đếm số lượng ratings của mỗi sản phẩm
            2. Tính điểm rating trung bình
            3. Lọc sản phẩm có ít nhất POPULAR_MIN_RATINGS đánh giá
            4. Sắp xếp theo: avg_rating (ưu tiên) -> rating_count
            5. Lấy top N sản phẩm
        
        Args:
            limit: Số lượng sản phẩm tối đa (default: 10)
            
        Returns:
            List of Product objects với attributes:
                - rating_count: Số lượng đánh giá
                - avg_rating: Điểm trung bình (0-5)
                - recommendation_score: Điểm normalized (0-1)
        
        Example:
            >>> products = RecommendationService.get_popular_products(5)
            >>> for p in products:
            ...     print(f"{p.name}: {p.avg_rating}/5")
            iPhone 15 Pro: 4.5/5
            MacBook Pro: 4.3/5
        """
        try:
            products = Product.objects.annotate(
                rating_count=Count('ratings'),
                avg_rating=Avg('ratings__score')
            ).filter(
                rating_count__gte=cls.POPULAR_MIN_RATINGS
            ).order_by(
                '-avg_rating',
                '-rating_count'
            )[:limit]
            
            product_list = list(products)
            
            for product in product_list:
                product.recommendation_score = float(product.avg_rating or 0) / 5.0
            
            logger.info(f"Returned {len(product_list)} popular products")
            return product_list
            
        except Exception as e:
            logger.error(f"Error getting popular products: {str(e)}")
            return list(Product.objects.all()[:limit])
    
    # =========================================================================
    # 2. SIMILAR PRODUCTS - Item-based Collaborative Filtering
    # =========================================================================
    
    @classmethod
    def get_similar_products(cls, product_id, limit=DEFAULT_LIMIT):
        """
        Lấy sản phẩm tương tự dựa trên Item-based Collaborative Filtering
        
        Dùng cho: Trang chi tiết sản phẩm - "Sản phẩm tương tự"
        
        Logic:
            1. Query ProductSimilarity table với source_id = product_id
            2. Sắp xếp theo similarity_score giảm dần
            3. Lấy top N products có similarity cao nhất
            4. Trả về danh sách products với similarity_score
        
        Collaborative Filtering principle:
            - Nếu nhiều users cùng thích product A và product B
            - → A và B có similarity cao
            - → User thích A thì sẽ được recommend B
        
        Args:
            product_id: ID của sản phẩm gốc
            limit: Số lượng sản phẩm tương tự tối đa (default: 10)
            
        Returns:
            List of Product objects với attribute:
                - similarity_score: Độ tương đồng với product gốc (0-1)
        
        Example:
            >>> # User đang xem iPhone 15 Pro (id=1)
            >>> similar = RecommendationService.get_similar_products(1, 5)
            >>> for p in similar:
            ...     print(f"{p.name}: {p.similarity_score:.3f}")
            AirPods Pro: 0.416
            MacBook Pro: 0.305
            Apple Watch: 0.277
            iPad Pro: 0.247
            Magic Keyboard: 0.234
        """
        try:
            # 1. Query similarities từ database
            # Lấy tất cả products có similarity với product_id
            similarities = ProductSimilarity.objects.filter(
                source_id=product_id,
                similarity_score__gte=cls.MIN_SIMILARITY_SCORE
            ).select_related('target').order_by(
                '-similarity_score'
            )[:limit]
            
            if not similarities.exists():
                logger.warning(f"No similarities found for product {product_id}")
                # Fallback: trả về popular products
                return cls.get_popular_products(limit)
            
            # 2. Extract products và attach similarity_score
            similar_products = []
            for sim in similarities:
                product = sim.target
                # Attach similarity score vào product object
                product.similarity_score = float(sim.similarity_score)
                similar_products.append(product)
            
            logger.info(
                f"Found {len(similar_products)} similar products for product {product_id}"
            )
            return similar_products
            
        except Product.DoesNotExist:
            logger.error(f"Product {product_id} does not exist")
            return []
        except Exception as e:
            logger.error(f"Error getting similar products: {str(e)}")
            # Fallback: trả về popular products
            return cls.get_popular_products(limit)
    
    # =========================================================================
    # 3. SMART RECOMMENDATION - Kết hợp cả 2 strategies
    # =========================================================================
    
    @classmethod
    def get_recommendations_for_product(cls, product_id, limit=DEFAULT_LIMIT):
        """
        Smart recommendation: Kết hợp similar products + popular products
        
        Logic:
            1. Lấy similar products trước (collaborative filtering)
            2. Nếu không đủ, bổ sung popular products
            3. Đảm bảo luôn trả về đủ số lượng recommendations
        
        Args:
            product_id: ID của sản phẩm gốc
            limit: Số lượng recommendations tối đa
            
        Returns:
            List of Product objects với similarity_score hoặc recommendation_score
        
        Example:
            >>> # Hybrid approach
            >>> recs = RecommendationService.get_recommendations_for_product(1, 10)
            >>> # Trả về: 7 similar + 3 popular (nếu similar < 10)
        """
        try:
            # 1. Lấy similar products
            similar = cls.get_similar_products(product_id, limit)
            
            # 2. Nếu đủ số lượng, return luôn
            if len(similar) >= limit:
                return similar[:limit]
            
            # 3. Nếu không đủ, bổ sung popular products
            remaining = limit - len(similar)
            
            # Exclude products đã có trong similar
            similar_ids = [p.id for p in similar]
            similar_ids.append(product_id)  # Exclude product gốc
            
            popular = Product.objects.annotate(
                rating_count=Count('ratings'),
                avg_rating=Avg('ratings__score')
            ).filter(
                rating_count__gte=cls.POPULAR_MIN_RATINGS
            ).exclude(
                id__in=similar_ids
            ).order_by(
                '-avg_rating',
                '-rating_count'
            )[:remaining]
            
            # Attach recommendation_score
            popular_list = []
            for product in popular:
                product.recommendation_score = float(product.avg_rating or 0) / 5.0
                popular_list.append(product)
            
            # Combine similar + popular
            recommendations = similar + popular_list
            
            logger.info(
                f"Returned {len(similar)} similar + {len(popular_list)} popular "
                f"for product {product_id}"
            )
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error in smart recommendations: {str(e)}")
            return cls.get_popular_products(limit)


# ============================================================================
# UTILITY FUNCTIONS - Shortcuts
# ============================================================================

def get_popular_products(limit=10):
    """Shortcut function for popular products"""
    return RecommendationService.get_popular_products(limit)


def get_similar_products(product_id, limit=10):
    """Shortcut function for similar products"""
    return RecommendationService.get_similar_products(product_id, limit)


def get_recommendations(product_id, limit=10):
    """Shortcut function for smart recommendations"""
    return RecommendationService.get_recommendations_for_product(product_id, limit)


# ============================================================================
# GIẢI THÍCH COLLABORATIVE FILTERING
# ============================================================================
"""
ITEM-BASED COLLABORATIVE FILTERING - Cách hoạt động:

1. BUILD SIMILARITY MATRIX (đã làm với item_similarity_calculator):
   
   User behavior:
   - User A: iPhone 5★, MacBook 5★, AirPods 4★
   - User B: iPhone 5★, MacBook 4★, Apple Watch 5★
   - User C: iPhone 4★, AirPods 5★, Apple Watch 4★
   
   → Tính similarity:
   iPhone ↔ MacBook: 0.85 (nhiều users thích cả 2)
   iPhone ↔ AirPods: 0.72 (khá nhiều users thích cả 2)
   iPhone ↔ Apple Watch: 0.68 (một số users thích cả 2)

2. MAKE RECOMMENDATIONS (service này):
   
   User D đang xem iPhone
   → Query ProductSimilarity WHERE source = iPhone
   → Return: MacBook (0.85), AirPods (0.72), Apple Watch (0.68)
   
3. WHY IT WORKS:
   
   ✓ User behavior patterns
   ✓ Brand loyalty (Apple users → Apple products)
   ✓ Category coherence (laptop users → accessories)
   ✓ Complementary products (camera → memory cards)

4. ADVANTAGES:
   
   ✓ No need to know user's preferences
   ✓ Works on product detail pages
   ✓ Captures implicit relationships
   ✓ Scalable (precomputed similarities)

5. USE CASES:
   
   ✓ "Customers who bought this also bought..."
   ✓ "Similar products"
   ✓ "You might also like"
   ✓ "Frequently bought together"
"""