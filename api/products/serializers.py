from rest_framework import serializers
from .models import Category, Product, Brand

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
            return main_doc.document.file.url
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
        """
        obj: Category instance
        Nếu obj.id = 0 -> lấy sản phẩm bất kỳ theo type: popular/sale/best_seller
        Nếu obj.id != 0 -> lấy theo category hoặc parent category
        """
        mode = getattr(self.context, 'mode', None) or self.context.get('mode', None)
        limit = 6

        if getattr(obj, 'id', 0) == 0:
            # Lấy sản phẩm bất kỳ theo type
            if mode == 'popular':
                products = Product.objects.filter(is_popular=True, is_available=True)[:limit]
            elif mode == 'sale':
                products = Product.objects.filter(is_sale=True, is_available=True)[:limit]
            elif mode == 'best_seller':
                products = Product.objects.filter(is_best_seller=True, is_available=True)[:limit]
            else:
                products = Product.objects.filter(is_available=True)[:limit]
        else:
            # Lấy theo category
            if mode == 'parent':
                # Lấy tất cả sản phẩm của category con
                subcategories = obj.children.all()
                products = Product.objects.filter(category__in=subcategories, is_available=True)[:limit]
            else:
                # Lấy sản phẩm trực tiếp thuộc category
                products = obj.products.filter(is_available=True)[:limit]

        return ProductFESerializer(products, many=True).data
