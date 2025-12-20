from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from api.products.models import Product, ProductVariant
import uuid  # dùng để tạo order_code tự động

class Order(models.Model):
    STATUS_CHOICES = [
        (0, 'Pending'),           # just created
        (1, 'Confirmed'),         # order confirmed
        (2, 'Delivered'),         # order delivered
        (3, 'Returned'),          # customer returned
        (4, 'Cancelled'),         # order cancelled
        (5, 'Completed'),         # order completed
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    order_code = models.CharField(max_length=20, unique=True, editable=False, default='TEMPORDER')
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    has_insurance = models.BooleanField(default=False)
    address_full_name = models.CharField(max_length=255)
    address_phone = models.CharField(max_length=20)
    address_line = models.CharField(max_length=255)
    ward = models.CharField(max_length=255, blank=True, null=True)
    district = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    discount_code = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.IntegerField(choices=STATUS_CHOICES, default=0)  # default 0 = Pending

    class Meta:
        db_table = 'orders'

    def save(self, *args, **kwargs):
        if not self.order_code:
            # Tạo mã order_code dạng: ORD + 8 ký tự ngẫu nhiên
            self.order_code = f"ORD{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.order_code} by {self.user.username}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'order_items'

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
