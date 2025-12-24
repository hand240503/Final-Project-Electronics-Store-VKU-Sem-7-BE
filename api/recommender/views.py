"""
Recommendation API Views
Location: api/recommender/views.py

API Endpoints:
    GET /api/recommendations/popular/              - Sản phẩm phổ biến
    GET /api/products/{id}/similar/                - Sản phẩm tương tự (CF)
    GET /api/products/{id}/recommendations/        - Smart recommendations
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from api.recommender.services import RecommendationService
from api.products.serializers import ProductSerializer
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# 1. POPULAR PRODUCTS - Cold Start
# =============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def get_popular_products(request):
    """
    GET /api/recommendations/popular/
    
    Lấy danh sách sản phẩm phổ biến (best sellers)
    Endpoint này public, không cần authentication
    
    Use case: Homepage, cold start, new users
    
    Query params:
        - limit: số lượng sản phẩm muốn lấy (mặc định: 10)
    
    Response:
        {
            "count": 10,
            "results": [
                {
                    "id": 1,
                    "name": "iPhone 15 Pro",
                    "price": 20000000,
                    "rating_count": 150,
                    "avg_rating": 4.5,
                    "recommendation_score": 0.9
                }
            ]
        }
    """
    try:
        limit = int(request.query_params.get('limit', 10))
        
        # Get popular products
        popular_products = RecommendationService.get_popular_products(limit=limit)
        
        # Serialize
        serializer = ProductSerializer(popular_products, many=True)
        
        # Attach metadata
        results = []
        for i, product_data in enumerate(serializer.data):
            if hasattr(popular_products[i], 'rating_count'):
                product_data['rating_count'] = popular_products[i].rating_count
            if hasattr(popular_products[i], 'avg_rating'):
                product_data['avg_rating'] = float(popular_products[i].avg_rating or 0)
            if hasattr(popular_products[i], 'recommendation_score'):
                product_data['recommendation_score'] = popular_products[i].recommendation_score
            results.append(product_data)
        
        return Response({
            'count': len(results),
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error in get_popular_products: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# =============================================================================
# 2. SIMILAR PRODUCTS - Item-based Collaborative Filtering
# =============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def get_similar_products(request, product_id):
    """
    GET /api/products/{product_id}/similar/
    
    Lấy sản phẩm tương tự dựa trên Item-based Collaborative Filtering
    
    Use case: 
        - Product detail page: "Sản phẩm tương tự"
        - "Customers who bought this also bought"
    
    Collaborative Filtering Logic:
        - Nếu nhiều users cùng rate cao 2 products → 2 products tương tự
        - Dựa trên behavior patterns, không cần biết product attributes
        - Tự động học từ user interactions
    
    Query params:
        - limit: số lượng sản phẩm (default: 10)
    
    Response:
        {
            "product_id": 1,
            "product_name": "iPhone 15 Pro",
            "count": 5,
            "results": [
                {
                    "id": 28,
                    "name": "AirPods Pro 2",
                    "price": 5000000,
                    "similarity_score": 0.416
                },
                {
                    "id": 4,
                    "name": "MacBook Pro 16",
                    "price": 50000000,
                    "similarity_score": 0.305
                }
            ]
        }
    
    Example:
        GET /api/products/1/similar/?limit=5
        
        Returns top 5 products similar to product #1 based on:
        - Users who liked product #1 also liked these products
        - Similarity scores from collaborative filtering matrix
    """
    try:
        limit = int(request.query_params.get('limit', 10))
        
        # Get similar products via CF
        similar_products = RecommendationService.get_similar_products(
            product_id=product_id,
            limit=limit
        )
        
        # Get source product info
        from api.products.models import Product
        try:
            source_product = Product.objects.get(id=product_id)
            product_name = source_product.name
        except Product.DoesNotExist:
            return Response(
                {'error': f'Product {product_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Serialize
        serializer = ProductSerializer(similar_products, many=True)
        
        # Attach similarity scores
        results = []
        for i, product_data in enumerate(serializer.data):
            if hasattr(similar_products[i], 'similarity_score'):
                product_data['similarity_score'] = float(
                    similar_products[i].similarity_score
                )
            results.append(product_data)
        
        return Response({
            'product_id': product_id,
            'product_name': product_name,
            'count': len(results),
            'algorithm': 'item_based_collaborative_filtering',
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error in get_similar_products: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# =============================================================================
# 3. SMART RECOMMENDATIONS - Hybrid Approach
# =============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def get_product_recommendations(request, product_id):
    """
    GET /api/products/{product_id}/recommendations/
    
    Smart recommendations: Kết hợp CF + Popular
    
    Use case: Đảm bảo luôn có recommendations ngay cả khi CF không đủ data
    
    Logic:
        1. Ưu tiên similar products (collaborative filtering)
        2. Nếu không đủ, bổ sung popular products
        3. Đảm bảo luôn trả về đủ số lượng
    
    Query params:
        - limit: số lượng recommendations (default: 10)
    
    Response:
        {
            "product_id": 1,
            "product_name": "iPhone 15 Pro",
            "strategy": "hybrid",
            "similar_count": 7,
            "popular_count": 3,
            "total": 10,
            "results": [...]
        }
    
    Example:
        GET /api/products/1/recommendations/?limit=10
        
        Returns:
        - 7 similar products (if available via CF)
        - 3 popular products (to fill remaining slots)
    """
    try:
        limit = int(request.query_params.get('limit', 10))
        
        # Get hybrid recommendations
        recommendations = RecommendationService.get_recommendations_for_product(
            product_id=product_id,
            limit=limit
        )
        
        # Get source product
        from api.products.models import Product
        try:
            source_product = Product.objects.get(id=product_id)
            product_name = source_product.name
        except Product.DoesNotExist:
            return Response(
                {'error': f'Product {product_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Count similar vs popular
        similar_count = sum(1 for p in recommendations if hasattr(p, 'similarity_score'))
        popular_count = len(recommendations) - similar_count
        
        # Serialize
        serializer = ProductSerializer(recommendations, many=True)
        
        # Attach scores
        results = []
        for i, product_data in enumerate(serializer.data):
            if hasattr(recommendations[i], 'similarity_score'):
                product_data['similarity_score'] = float(
                    recommendations[i].similarity_score
                )
                product_data['source'] = 'collaborative_filtering'
            elif hasattr(recommendations[i], 'recommendation_score'):
                product_data['recommendation_score'] = float(
                    recommendations[i].recommendation_score
                )
                product_data['source'] = 'popular'
            results.append(product_data)
        
        return Response({
            'product_id': product_id,
            'product_name': product_name,
            'strategy': 'hybrid',
            'similar_count': similar_count,
            'popular_count': popular_count,
            'total': len(results),
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error in get_product_recommendations: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# =============================================================================
# BONUS: Statistics endpoint
# =============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def recommendation_stats(request):
    """
    GET /api/recommendations/stats/
    
    Thống kê về recommendation system
    
    Response:
        {
            "total_similarities": 470,
            "avg_similarity": 0.18,
            "max_similarity": 0.436,
            "total_products": 45,
            "products_with_similarities": 42,
            "coverage": "93.3%"
        }
    """
    try:
        from api.recommender.models import ProductSimilarity
        from django.db.models import Avg, Max, Count
        
        # Query stats
        stats_query = ProductSimilarity.objects.aggregate(
            total=Count('id'),
            avg_score=Avg('similarity_score'),
            max_score=Max('similarity_score')
        )
        
        # Count products with similarities
        products_with_sim = ProductSimilarity.objects.values(
            'source_id'
        ).distinct().count()
        
        from api.products.models import Product
        total_products = Product.objects.count()
        
        coverage = (products_with_sim / total_products * 100) if total_products > 0 else 0
        
        return Response({
            'total_similarities': stats_query['total'],
            'avg_similarity': round(float(stats_query['avg_score'] or 0), 3),
            'max_similarity': round(float(stats_query['max_score'] or 0), 3),
            'total_products': total_products,
            'products_with_similarities': products_with_sim,
            'coverage': f"{coverage:.1f}%"
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )