from rest_framework import serializers
from .models import (
    Category, Product, Brand,
    ProductVariant, Review, ShippingInfo, ReturnPolicy, ProductDocument
)
from urllib.parse import unquote

# ==========================
# Helper: Chuẩn hóa URL
# ==========================
def get_valid_url(request, url):
    if not url:
        return None
    url = unquote(url).strip()
    if url.startswith('/'):
        url = url[1:]
    if url.startswith('https:/') and not url.startswith('https://'):
        url = url.replace('https:/', 'https://', 1)
    elif url.startswith('http:/') and not url.startswith('http://'):
        url = url.replace('http:/', 'http://', 1)
    if url.startswith('http://') or url.startswith('https://'):
        return url
    if request:
        return request.build_absolute_uri(url)
    return url

# ==========================
# Serializer Brand
# ==========================
class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id', 'name', 'logo_url']


# ==========================
# Serializer Product cho FE
# ==========================
class ProductFESerializer(serializers.ModelSerializer):
    brand = BrandSerializer(read_only=True)
    main_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'discount_price',
            'sold', 'brand', 'main_image'
        ]

    def get_main_image(self, obj):
        main_doc = obj.documents.filter(is_main=True).first()
        if main_doc and main_doc.document and main_doc.document.file:
            url = main_doc.document.file.url
            request = self.context.get('request')
            return get_valid_url(request, url)
        return None


# ==========================
# Serializer Category Parent
# ==========================
class CategoryParentFESerializer(serializers.ModelSerializer):
    svgSrc = serializers.SerializerMethodField()
    subCategories = serializers.SerializerMethodField()
    slug = serializers.CharField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'svgSrc', 'slug', 'subCategories']

    def get_svgSrc(self, obj):
        return None

    def get_subCategories(self, obj):
        children = obj.children.all()
        return [
            {
                "id": c.id,
                "name": c.name,
                "svgSrc": None,
                "slug": c.slug
            }
            for c in children
        ]


# ==========================
# Serializer lấy sản phẩm theo category hoặc parent
# ==========================
class ProductsByCategoryFESerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'products']

    def get_products(self, obj):
        mode = getattr(self.context, 'mode', None) or self.context.get('mode', None)
        limit = 6

        if getattr(obj, 'id', 0) == 0:
            if mode == 'popular':
                products = Product.objects.filter(is_popular=True, is_available=True)[:limit]
            elif mode == 'sale':
                products = Product.objects.filter(is_sale=True, is_available=True)[:limit]
            elif mode == 'best_seller':
                products = Product.objects.filter(is_best_seller=True, is_available=True)[:limit]
            else:
                products = Product.objects.filter(is_available=True)[:limit]
        else:
            if mode == 'parent':
                subcategories = obj.children.all()
                products = Product.objects.filter(category__in=subcategories, is_available=True)[:limit]
            else:
                products = obj.products.filter(is_available=True)[:limit]

        return ProductFESerializer(products, many=True, context=self.context).data


# ======================================================
# Serializer chi tiết sản phẩm theo ID
# ======================================================

class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ['id', 'name', 'color', 'size', 'stock', 'price', 'discount_price']


class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'user', 'rating', 'comment', 'created_at']


class ShippingInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingInfo
        fields = ['id', 'info']


class ReturnPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = ReturnPolicy
        fields = ['id', 'policy_text']


class ProductImageSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductDocument
        fields = ['id', 'is_main', 'file_url']

    def get_file_url(self, obj):
        if obj.document and obj.document.file:
            request = self.context.get('request')
            url = obj.document.file.url
            return get_valid_url(request, url)
        return None


class ProductDetailSerializer(serializers.ModelSerializer):
    brand = BrandSerializer()
    variants = ProductVariantSerializer(many=True)
    reviews = ReviewSerializer(many=True)
    shipping_info = ShippingInfoSerializer(many=True)
    return_policy = ReturnPolicySerializer(many=True)
    main_image = serializers.SerializerMethodField()
    other_images = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'discount_price',
            'rating', 'num_reviews', 'is_available',
            'brand', 'variants', 'reviews', 'shipping_info', 'return_policy',
            'main_image', 'other_images',
        ]

    def get_main_image(self, obj):
        main = obj.documents.filter(is_main=True).first()
        if main and main.document and main.document.file:
            url = main.document.file.url
            request = self.context.get('request')
            return get_valid_url(request, url)
        return None

    def get_other_images(self, obj):
        images = obj.documents.filter(is_main=False)
        request = self.context.get('request')
        urls = []
        for img in images:
            if img.document and img.document.file:
                url = img.document.file.url
                urls.append(get_valid_url(request, url))
        return urls
