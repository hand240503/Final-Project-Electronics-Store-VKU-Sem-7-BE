from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify

# ==========================
# BRANDS
# ==========================
class Brand(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    logo_url = models.URLField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'brands'

    def __str__(self):
        return self.name


# ==========================
# CATEGORIES
# ==========================
class Category(models.Model):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children'
    )
    image = models.URLField(null=True, blank=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    class Meta:
        db_table = 'categories'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            # tạo slug từ name
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            # kiểm tra duplicate trong database
            while Category.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
# ==========================
# PRODUCTS
# ==========================
class Product(models.Model):
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    rating = models.FloatField(default=0)
    num_reviews = models.IntegerField(default=0)
    is_available = models.BooleanField(default=True)

    # Thuộc tính trạng thái
    is_popular = models.BooleanField(default=False)
    is_sale = models.BooleanField(default=False)
    is_best_sale = models.BooleanField(default=False)

    # Tùy chọn nâng cao
    sold = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products'

    def __str__(self):
        return self.name

    # ==========================
    # CÁC HÀM LẤY DỮ LIỆU
    # ==========================

    # Lấy theo thuộc tính
    @classmethod
    def get_popular_attr(cls, limit=10):
        return cls.objects.filter(is_available=True, is_popular=True)[:limit]

    @classmethod
    def get_sale_attr(cls, limit=10):
        return cls.objects.filter(is_available=True, is_sale=True)[:limit]

    @classmethod
    def get_best_sale_attr(cls, limit=10):
        return cls.objects.filter(is_available=True, is_best_sale=True)[:limit]

    # Lấy theo tính toán
    @classmethod
    def get_popular(cls, limit=10):
        return cls.objects.filter(is_available=True).order_by('-rating', '-num_reviews')[:limit]

    @classmethod
    def get_sale(cls, limit=10):
        return cls.objects.filter(
            discount_price__isnull=False,
            discount_price__lt=models.F('price'),
            is_available=True
        ).order_by('-updated_at')[:limit]

    @classmethod
    def get_best_sale(cls, limit=10):
        return cls.objects.filter(is_available=True).order_by('-sold', '-rating')[:limit]


# ==========================
# PRODUCT VARIANTS
# ==========================
class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=255, blank=True, null=True)  # ví dụ: "Red - L"
    sku = models.CharField(max_length=50, blank=True, null=True)
    color = models.CharField(max_length=50, blank=True, null=True)
    size = models.CharField(max_length=20, blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = 'product_variants'

    def __str__(self):
        return f"{self.product.name} - {self.name or self.size or self.color}"


# ==========================
# REVIEWS
# ==========================
class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField()  # 1–5
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reviews'

    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.rating}⭐)"


# ==========================
# SHIPPING INFO
# ==========================
class ShippingInfo(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='shipping_info')
    info = models.TextField()

    class Meta:
        db_table = 'shipping_info'

    def __str__(self):
        return f"Shipping info for {self.product.name}"


# ==========================
# RETURN POLICY
# ==========================
class ReturnPolicy(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='return_policy')
    policy_text = models.TextField()

    class Meta:
        db_table = 'return_policy'

    def __str__(self):
        return f"Return policy for {self.product.name}"


# ==========================
# NOTIFICATIONS
# ==========================
class Notification(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='notifications')
    email = models.EmailField(max_length=255)
    notified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'

    def __str__(self):
        return f"Notify {self.email} for {self.product.name}"


# ==========================
# DOCUMENTS / IMAGES
# ==========================
class Document(models.Model):
    FILE = 'file'
    IMAGE = 'image'
    VIDEO = 'video'

    TYPE_CHOICES = [
        (FILE, 'File'),
        (IMAGE, 'Image'),
        (VIDEO, 'Video'),
    ]

    title = models.CharField(max_length=255, blank=True, null=True)
    file = models.FileField(upload_to='documents/')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=FILE)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'documents'

    def __str__(self):
        return self.title or f"Document #{self.id}"


class ProductDocument(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='documents')
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    is_main = models.BooleanField(default=False)

    class Meta:
        db_table = 'product_documents'

    def __str__(self):
        return f"{self.product.name} - {self.document.title or self.document.file.name}"
