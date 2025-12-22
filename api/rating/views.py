from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.contrib.auth.models import User
from api.products.models import Product
from api.rating.models import CollectorLog, Rating
from django.utils import timezone
import uuid


class TrackUserBehaviorView(APIView):
    """
    API để theo dõi hành vi người dùng
    
    POST /api/track-behavior/
    Body:
    {
        "product_id": 1,
        "event": "details",  // details, moreDetails, addToCart, buy
        "session_id": "optional-session-id",
        "device_type": "desktop",  // mobile, tablet, desktop
        "platform": "web",  // web, android, ios
        "metadata": {
            "variant_id": 1,
            "quantity": 2,
            "price": 1000000
        }
    }
    """
    permission_classes = [AllowAny]  # Cho phép anonymous users

    def post(self, request):
        # Validate required fields
        product_id = request.data.get('product_id')
        event = request.data.get('event')
        
        if not product_id:
            return Response(
                {"error": "product_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not event:
            return Response(
                {"error": "event is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate event type
        valid_events = [choice[0] for choice in CollectorLog.EVENT_CHOICES]
        if event not in valid_events:
            return Response(
                {
                    "error": f"Invalid event type. Must be one of: {', '.join(valid_events)}"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if product exists
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {"error": f"Product with id {product_id} not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get or create session_id
        session_id = request.data.get('session_id')
        if not session_id:
            # Generate session_id from Django session or create new one
            if hasattr(request, 'session') and request.session.session_key:
                session_id = request.session.session_key
            else:
                session_id = str(uuid.uuid4())
        
        # Get user (None if not authenticated)
        user = request.user if request.user.is_authenticated else None
        
        # Get additional metadata
        device_type = request.data.get('device_type', 'unknown')
        platform = request.data.get('platform', 'web')
        metadata = request.data.get('metadata', {})
        
        # Get IP address
        ip_address = self.get_client_ip(request)
        
        # Create collector log
        try:
            collector_log = CollectorLog.objects.create(
                user=user,
                product=product,
                event=event,
                session_id=session_id,
                device_type=device_type,
                platform=platform,
                metadata=metadata,
                ip_address=ip_address
            )
            
            # Get implicit rating if user is authenticated
            implicit_rating = None
            if user:
                implicit_rating_obj = Rating.objects.filter(
                    user=user,
                    product=product,
                    rating_type=Rating.IMPLICIT
                ).first()
                
                if implicit_rating_obj:
                    implicit_rating = {
                        'score': implicit_rating_obj.score,
                        'confidence': implicit_rating_obj.confidence,
                        'source': implicit_rating_obj.source
                    }
            
            return Response(
                {
                    "success": True,
                    "message": "Behavior tracked successfully",
                    "data": {
                        "log_id": collector_log.id,
                        "user": user.username if user else None,
                        "session_id": session_id,
                        "product_id": product.id,
                        "product_name": product.name,
                        "event": event,
                        "timestamp": collector_log.timestamp.isoformat(),
                        "implicit_rating": implicit_rating
                    }
                },
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return Response(
                {"error": f"Failed to track behavior: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class GetUserInteractionsView(APIView):
    """
    API để lấy lịch sử tương tác của user
    
    GET /api/user-interactions/
    GET /api/user-interactions/?limit=20
    """
    
    def get(self, request):
        if not request.user.is_authenticated:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        limit = int(request.query_params.get('limit', 50))
        
        interactions = CollectorLog.get_user_interactions(
            user=request.user,
            limit=limit
        )
        
        data = [{
            'id': log.id,
            'product_id': log.product.id,
            'product_name': log.product.name,
            'event': log.event,
            'device_type': log.device_type,
            'platform': log.platform,
            'timestamp': log.timestamp.isoformat()
        } for log in interactions]
        
        return Response({
            'success': True,
            'count': len(data),
            'interactions': data
        })


class GetProductInteractionsView(APIView):
    """
    API để lấy số lượng tương tác của sản phẩm
    
    GET /api/product-interactions/{product_id}/
    GET /api/product-interactions/{product_id}/?event=buy
    """
    permission_classes = [AllowAny]
    
    def get(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {"error": f"Product with id {product_id} not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        event = request.query_params.get('event')
        
        # Get total interactions
        total_interactions = CollectorLog.get_product_interactions(
            product=product,
            event=event
        )
        
        # Get breakdown by event type if no specific event
        breakdown = {}
        if not event:
            for event_choice in CollectorLog.EVENT_CHOICES:
                event_type = event_choice[0]
                count = CollectorLog.get_product_interactions(
                    product=product,
                    event=event_type
                )
                breakdown[event_type] = count
        
        return Response({
            'success': True,
            'product_id': product.id,
            'product_name': product.name,
            'total_interactions': total_interactions,
            'event_filter': event,
            'breakdown': breakdown if breakdown else None
        })


class GetTrendingProductsView(APIView):
    """
    API để lấy sản phẩm trending
    
    GET /api/trending-products/
    GET /api/trending-products/?days=7&limit=10
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        days = int(request.query_params.get('days', 7))
        limit = int(request.query_params.get('limit', 10))
        
        trending = CollectorLog.get_trending_products(days=days, limit=limit)
        
        data = []
        for item in trending:
            try:
                product = Product.objects.get(id=item['product'])
                data.append({
                    'product_id': product.id,
                    'product_name': product.name,
                    'interaction_count': item['interaction_count']
                })
            except Product.DoesNotExist:
                continue
        
        return Response({
            'success': True,
            'period_days': days,
            'count': len(data),
            'trending_products': data
        })