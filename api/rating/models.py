from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from api.products.models import Product


# ==========================
# RATING SYSTEM
# ==========================
class Rating(models.Model):
    """
    Bảng lưu trữ đánh giá của user về sản phẩm
    Hỗ trợ cả explicit (đánh giá trực tiếp) và implicit (từ hành vi)
    """
    EXPLICIT = 'explicit'
    IMPLICIT = 'implicit'
    
    RATING_TYPE_CHOICES = [
        (EXPLICIT, 'Explicit Rating'),  # User đánh giá trực tiếp (review, rating)
        (IMPLICIT, 'Implicit Rating'),  # Suy luận từ hành vi (view, cart, buy)
    ]

    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='ratings'
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='user_ratings'
    )
    
    # Rating score: 1-5 cho explicit, tính toán cho implicit
    score = models.FloatField(
        validators=[MinValueValidator(1.0), MaxValueValidator(5.0)]
    )
    
    rating_type = models.CharField(
        max_length=20, 
        choices=RATING_TYPE_CHOICES,
        default=EXPLICIT
    )
    
    # Confidence score: độ tin cậy của rating (0-1)
    # Explicit = 1.0, Implicit tùy thuộc vào hành động
    confidence = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    
    # Metadata
    source = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Nguồn gốc rating: review, purchase, view, etc."
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ratings'
        unique_together = ['user', 'product', 'rating_type']
        indexes = [
            models.Index(fields=['user', 'product']),
            models.Index(fields=['rating_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.product.name}: {self.score} ({self.rating_type})"

    @classmethod
    def calculate_implicit_rating(cls, user, product, event_type):
        """
        Tính toán implicit rating dựa trên loại event
        
        Event weights (raw):
        - details: 15
        - moreDetails: 35
        - addToCart: 50
        - buy: 100
        
        Converted to 1-5 scale:
        - details: 15/100 * 4 + 1 = 1.6 (confidence: 0.15)
        - moreDetails: 35/100 * 4 + 1 = 2.4 (confidence: 0.35)
        - addToCart: 50/100 * 4 + 1 = 3.0 (confidence: 0.50)
        - buy: 100/100 * 4 + 1 = 5.0 (confidence: 1.0)
        """
        # Raw weights từ yêu cầu
        raw_weights = {
            'details': 15,
            'moreDetails': 35,
            'addToCart': 50,
            'buy': 100,
        }
        
        if event_type not in raw_weights:
            return None
        
        raw_weight = raw_weights[event_type]
        max_weight = 100  # buy = 100 là max
        
        # Convert sang scale 1-5: (raw/max * 4) + 1
        score = (raw_weight / max_weight * 4) + 1
        
        # Confidence = raw_weight / max_weight
        confidence = raw_weight / max_weight
        
        # Lấy hoặc tạo implicit rating
        rating, created = cls.objects.update_or_create(
            user=user,
            product=product,
            rating_type=cls.IMPLICIT,
            defaults={
                'score': round(score, 2),
                'confidence': confidence,
                'source': event_type
            }
        )
        
        return rating

    @classmethod
    def get_combined_rating(cls, user, product):
        """
        Kết hợp explicit và implicit rating
        Ưu tiên explicit nếu có, nếu không dùng implicit
        """
        explicit = cls.objects.filter(
            user=user,
            product=product,
            rating_type=cls.EXPLICIT
        ).first()
        
        if explicit:
            return explicit.score
        
        implicit = cls.objects.filter(
            user=user,
            product=product,
            rating_type=cls.IMPLICIT
        ).first()
        
        return implicit.score if implicit else None


# ==========================
# COLLECTOR LOG
# ==========================
class CollectorLog(models.Model):
    """
    Bảng log để thu thập các hành động của user
    Dùng cho phân tích hành vi và recommendation system
    """
    DETAILS = 'details'
    MORE_DETAILS = 'moreDetails'
    BUY = 'buy'
    ADD_TO_CART = 'addToCart'
    
    EVENT_CHOICES = [
        (DETAILS, 'View Details'),
        (MORE_DETAILS, 'View More Details'),
        (BUY, 'Purchase'),
        (ADD_TO_CART, 'Add to Cart'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='collector_logs',
        null=True,
        blank=True,
        help_text="Null for anonymous users"
    )
    
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='collector_logs'
    )
    
    event = models.CharField(
        max_length=20,
        choices=EVENT_CHOICES
    )
    
    # Session tracking
    session_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Session ID cho anonymous users"
    )
    
    # Device & Platform info
    device_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="mobile, tablet, desktop"
    )
    
    platform = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="web, android, ios"
    )
    
    # Additional metadata
    metadata = models.JSONField(
        blank=True,
        null=True,
        help_text="Additional data: variant_id, quantity, price, etc."
    )
    
    # IP and location (optional)
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True
    )
    
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'collector_logs'
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['product', 'event']),
            models.Index(fields=['session_id']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        user_info = self.user.username if self.user else f"Session: {self.session_id}"
        return f"{user_info} - {self.event} - {self.product.name}"

    def save(self, *args, **kwargs):
        """
        Override save để tự động tạo implicit rating
        khi có event quan trọng
        """
        super().save(*args, **kwargs)
        
        # Chỉ tạo implicit rating cho user đã đăng nhập
        if self.user and self.event in ['buy', 'addToCart', 'moreDetails', 'details']:
            Rating.calculate_implicit_rating(
                user=self.user,
                product=self.product,
                event_type=self.event
            )

    @classmethod
    def get_user_interactions(cls, user, limit=50):
        """Lấy lịch sử tương tác của user"""
        return cls.objects.filter(user=user).order_by('-timestamp')[:limit]

    @classmethod
    def get_product_interactions(cls, product, event=None):
        """Lấy số lượng tương tác của sản phẩm"""
        query = cls.objects.filter(product=product)
        if event:
            query = query.filter(event=event)
        return query.count()

    @classmethod
    def get_trending_products(cls, days=7, limit=10):
        """
        Lấy sản phẩm trending dựa trên interactions
        trong X ngày gần đây
        """
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models import Count
        
        start_date = timezone.now() - timedelta(days=days)
        
        return cls.objects.filter(
            timestamp__gte=start_date
        ).values('product').annotate(
            interaction_count=Count('id')
        ).order_by('-interaction_count')[:limit]


# ==========================
# USER PREFERENCES (Optional)
# ==========================
class UserPreference(models.Model):
    """
    Bảng lưu preferences của user
    Có thể dùng cho recommendation system
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='preferences'
    )
    
    # Danh sách category yêu thích
    favorite_categories = models.ManyToManyField(
        'products.Category',
        blank=True,
        related_name='favorited_by'
    )
    
    # Danh sách brand yêu thích
    favorite_brands = models.ManyToManyField(
        'products.Brand',
        blank=True,
        related_name='favorited_by'
    )
    
    # Price range preferences
    min_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    max_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_preferences'

    def __str__(self):
        return f"Preferences of {self.user.username}"