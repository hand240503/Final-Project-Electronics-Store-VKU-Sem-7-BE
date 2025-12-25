from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import CategoryParentFESerializer, ProductsByCategoryFESerializer, ProductDetailSerializer
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from .models import Product, Document, ProductDocument, Category
from .forms import ProductForm
from django.core.files.base import ContentFile
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .serializers import ProductSearchSerializer
from .serializers import get_valid_url 
from django.db.models import Q
from rest_framework.decorators import api_view 

import requests
import cloudinary.uploader

@require_http_methods(["GET"])
def product_list(request):
    """
    GET /admin/products/
    Hiển thị danh sách sản phẩm với phân trang và tìm kiếm
    """
    # Lấy từ khóa tìm kiếm từ query params
    search_query = request.GET.get('search', '').strip()
    
    # Lấy tất cả sản phẩm
    products = Product.objects.all().order_by('-created_at')
    
    # Áp dụng tìm kiếm nếu có
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(id__icontains=search_query)
        )
    
    # Phân trang - 10 sản phẩm trên mỗi trang
    paginator = Paginator(products, 10)
    page = request.GET.get('page')
    
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        # Nếu page không phải số, lấy trang 1
        page_obj = paginator.page(1)
    except EmptyPage:
        # Nếu page vượt quá số trang, lấy trang cuối cùng
        page_obj = paginator.page(paginator.num_pages)
    
    context = {
        'page_obj': page_obj,
        'products': page_obj.object_list,  # Danh sách sản phẩm của trang hiện tại
        'search_query': search_query,
        'is_paginated': paginator.num_pages > 1,
    }
    
    return render(request, "product_list.html", context)

@require_http_methods(["GET", "POST"])
def product_create(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)

        if form.is_valid():
            product = form.save()

            # Xử lý upload ảnh lên Cloudinary
            image_files = [
                request.FILES.get("image_1"),
                request.FILES.get("image_2"),
                request.FILES.get("image_3"),
            ]

            for index, image_file in enumerate(image_files):
                if not image_file:
                    continue

                try:
                    # Upload lên Cloudinary
                    upload_result = cloudinary.uploader.upload(
                        image_file,
                        folder="products",
                        resource_type="image",
                        transformation=[
                            {'width': 800, 'height': 800, 'crop': 'limit'},
                            {'quality': 'auto'}
                        ]
                    )

                    # Lưu URL vào database
                    doc = Document.objects.create(
                        file=upload_result['secure_url'],
                        type=Document.IMAGE
                    )

                    ProductDocument.objects.create(
                        product=product,
                        document=doc,
                        is_main=(index == 0)
                    )

                except Exception as e:
                    print(f"Error uploading image: {e}")

            return redirect("product_detail", pk=product.pk)
    else:
        form = ProductForm()

    return render(request, "product_add.html", {"form": form})


@require_http_methods(["GET"])
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    images = product.documents.select_related("document")
    main_image = images.filter(is_main=True).first()
    if not main_image:
        main_image = images.first()

    return render(request, "product_detail.html", {
        "product": product,
        "image": main_image,
        "images": images,
    })


@require_http_methods(["GET", "POST"])
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    images = list(product.documents.select_related("document").all())

    while len(images) < 3:
        images.append(None)

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)

        if form.is_valid():
            form.save()

            # Lấy danh sách ảnh hiện tại (tối đa 3)
            current_images = list(product.documents.select_related("document").all())
            
            # Danh sách 3 ảnh mới (có thể None nếu không upload)
            new_image_files = [
                request.FILES.get("image_1"),
                request.FILES.get("image_2"),
                request.FILES.get("image_3"),
            ]

            # Xử lý từng ảnh riêng biệt
            for index, new_file in enumerate(new_image_files):
                if new_file:  # Có upload ảnh mới
                    # Xóa ảnh cũ ở vị trí này (nếu có)
                    if index < len(current_images) and current_images[index]:
                        old_doc = current_images[index]
                        try:
                            # Xóa ảnh cũ trên Cloudinary
                            image_url = str(old_doc.document.file)
                            url_parts = image_url.split('/')
                            public_id = '/'.join(url_parts[-2:]).split('.')[0]
                            cloudinary.uploader.destroy(public_id)
                            print(f"Deleted old image: {public_id}")
                        except Exception as e:
                            print(f"Error deleting old image: {e}")
                        
                        # Xóa record cũ
                        old_doc.delete()
                        old_doc.document.delete()
                    
                    # Upload ảnh mới
                    try:
                        upload_result = cloudinary.uploader.upload(
                            new_file,
                            folder="products",
                            resource_type="image",
                            transformation=[
                                {'width': 800, 'height': 800, 'crop': 'limit'},
                                {'quality': 'auto'}
                            ]
                        )

                        # Tạo document mới
                        doc = Document.objects.create(
                            file=upload_result['secure_url'],
                            type=Document.IMAGE
                        )

                        # Tạo ProductDocument với is_main cho ảnh đầu tiên
                        ProductDocument.objects.create(
                            product=product,
                            document=doc,
                            is_main=(index == 0)
                        )
                        
                        print(f"Uploaded new image at position {index + 1}")

                    except Exception as e:
                        print(f"Error uploading image {index + 1}: {e}")

            return redirect("product_detail", pk=product.pk)
    else:
        form = ProductForm(instance=product)

    return render(
        request,
        "product_update.html",
        {
            "form": form,
            "product": product,
            "images": images,
        }
    )


@require_http_methods(["POST"])
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product_docs = ProductDocument.objects.filter(product=product)

    for pdoc in product_docs:
        # Xóa ảnh trên Cloudinary
        try:
            # Convert FieldFile to string
            image_url = str(pdoc.document.file)
            
            url_parts = image_url.split('/')
            public_id = '/'.join(url_parts[-2:]).split('.')[0]
            
            cloudinary.uploader.destroy(public_id)
            print(f"Deleted image from Cloudinary: {public_id}")
        except Exception as e:
            print(f"Error deleting image from Cloudinary: {e}")
        
        pdoc.document.delete()
        pdoc.delete()

    product.delete()
    return redirect("product_list")



# ==========================
# Lấy danh sách category cha + subcategories
# ==========================
class CategoryParentsAPIView(APIView):
    def get(self, request):
        categories = Category.objects.filter(parent=None)
        serializer = CategoryParentFESerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ==========================
# Lấy sản phẩm theo category cụ thể
# ==========================
class CategoryProductsAPIView(APIView):
    def get(self, request, category_id):
        if category_id == 0:
            mode = request.GET.get('type', None)
            fake_category = Category(id=0, name='All Products', slug='all')
            serializer = ProductsByCategoryFESerializer(fake_category, context={'mode': mode})
        else:
            category = Category.objects.filter(id=category_id).first()
            if not category:
                return Response({'detail': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)
            serializer = ProductsByCategoryFESerializer(category)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ==========================
# Lấy sản phẩm tất cả category con của parent
# ==========================
class ParentCategoryProductsAPIView(APIView):
    def get(self, request, parent_id):
        if parent_id == 0:
            mode = request.GET.get('type', None)
            fake_category = Category(id=0, name='All Products', slug='all')
            serializer = ProductsByCategoryFESerializer(fake_category, context={'mode': mode})
        else:
            parent = Category.objects.filter(id=parent_id).first()
            if not parent:
                return Response({'detail': 'Parent category not found'}, status=status.HTTP_404_NOT_FOUND)
            serializer = ProductsByCategoryFESerializer(parent, context={'mode': 'parent'})
        return Response(serializer.data, status=status.HTTP_200_OK)


# ======================================================
#   Lấy chi tiết sản phẩm theo ID
# ======================================================
class ProductDetailAPIView(APIView):
    """
    GET /api/products/<int:product_id>/
    Trả về chi tiết sản phẩm (brand, variants, reviews, images,...)
    """
    def get(self, request, product_id):
        product = Product.objects.filter(id=product_id, is_available=True).first()
        if not product:
            return Response(
                {"detail": "Product not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ProductDetailSerializer(product, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


# ======================================================
#   Tìm kiếm sản phẩm theo tên
# ======================================================
class ProductSearchView(APIView):
    def get(self, request):
        query = request.query_params.get('q', '').strip()
        
        if not query:
            return Response(
                {'error': 'Vui lòng nhập từ khóa tìm kiếm'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        products = Product.search_by_name(query, limit=5)
        serializer = ProductSearchSerializer(
            products,
            many=True,
            context={'request': request}
        )
        
        return Response({
            'query': query,
            'count': products.count(),
            'results': serializer.data
        })



@api_view(['GET'])
def get_products_info_for_chatbot(request):
    """
    API endpoint để lấy thông tin sản phẩm cho chatbot AI
    GET /api/products/chatbot-info/
    
    Query params:
    - q: tìm kiếm theo tên sản phẩm
    - category: lọc theo category ID
    - limit: giới hạn số lượng (mặc định 20)
    """
    try:
        # Lấy query params
        search_query = request.query_params.get('q', '').strip()
        category_id = request.query_params.get('category', None)
        limit = int(request.query_params.get('limit', 20))
        
        # Base queryset - chỉ lấy sản phẩm available
        products = Product.objects.filter(is_available=True).select_related(
            'brand', 'category'
        ).prefetch_related(
            'documents__document'
        )
        
        # Áp dụng filter
        if search_query:
            products = products.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        if category_id:
            products = products.filter(category_id=category_id)
        
        # Giới hạn số lượng
        products = products[:limit]
        
        # Format dữ liệu cho chatbot (theo format ProductModel của Flutter)
        products_data = []
        for product in products:
            # ✅ Lấy ảnh chính giống ProductSearchSerializer
            main_doc = product.documents.filter(is_main=True).first()
            main_image_url = None
            if main_doc and main_doc.document and main_doc.document.file:
                url = main_doc.document.file.url
                main_image_url = get_valid_url(request, url)
            
            # Tính giá và giảm giá
            original_price = float(product.price)
            discount_price = float(product.discount_price) if product.discount_price else None
            discount_percent = None
            if discount_price:
                discount_percent = round(((original_price - discount_price) / original_price) * 100)
            
            # ✅ Format theo ProductModel Flutter
            product_info = {
                'id': product.id,
                'name': product.name,  # Flutter dùng 'name' để map sang 'title'
                'description': product.description,
                'brand': {
                    'name': product.brand.name if product.brand else ''
                },
                'category': product.category.name if product.category else None,
                'price': str(int(original_price)),  # ✅ Chuyển sang int trước để bỏ .0
                'discount_price': str(int(discount_price)) if discount_price else None,  # ✅ Same
                'main_image': main_image_url,
                'rating': float(product.rating),
                'num_reviews': product.num_reviews,
                'sold': product.sold,
                'is_popular': product.is_popular,
                'is_sale': product.is_sale,
                'is_best_sale': product.is_best_sale,
            }
            products_data.append(product_info)
        
        # Lấy thêm thông tin categories để chatbot có thể tư vấn
        categories = Category.objects.filter(parent__isnull=False).values('id', 'name', 'parent__name')
        categories_data = [
            {
                'id': cat['id'],
                'name': cat['name'],
                'parent': cat['parent__name']
            }
            for cat in categories
        ]
        
        return Response({
            'success': True,
            'total_products': len(products_data),
            'products': products_data,
            'categories': categories_data,
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_product_detail_for_chatbot(request, product_id):
    """
    API endpoint để lấy chi tiết 1 sản phẩm cho chatbot
    GET /api/products/chatbot-info/<int:product_id>/
    """
    try:
        product = Product.objects.filter(
            id=product_id,
            is_available=True
        ).select_related('brand', 'category').prefetch_related(
            'variants',
            'documents__document',
            'reviews__user',
            'shipping_info',
            'return_policy'
        ).first()
        
        if not product:
            return Response({
                'success': False,
                'error': 'Sản phẩm không tồn tại hoặc không còn bán'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # ✅ Ảnh chính giống ProductSearchSerializer
        main_doc = product.documents.filter(is_main=True).first()
        main_image_url = None
        if main_doc and main_doc.document and main_doc.document.file:
            url = main_doc.document.file.url
            main_image_url = get_valid_url(request, url)
        
        # ✅ Các ảnh phụ cũng dùng get_valid_url
        other_images = []
        for img in product.documents.filter(is_main=False):
            if img.document and img.document.file:
                url = img.document.file.url
                other_images.append(get_valid_url(request, url))
        
        # Variants
        variants_data = []
        for variant in product.variants.all():
            variants_data.append({
                'id': variant.id,
                'name': variant.name,
                'color': variant.color,
                'size': variant.size,
                'stock': variant.stock,
                'price': str(variant.price) if variant.price else None,
                'discount_price': str(variant.discount_price) if variant.discount_price else None,
            })
        
        # Reviews
        reviews_data = []
        for review in product.reviews.all()[:5]:  # Lấy 5 review mới nhất
            reviews_data.append({
                'user': review.user.username,
                'rating': review.rating,
                'comment': review.comment,
                'created_at': review.created_at.strftime('%d/%m/%Y')
            })
        
        # Shipping info
        shipping_info = []
        for info in product.shipping_info.all():
            shipping_info.append(info.info)
        
        # Return policy
        return_policy = []
        for policy in product.return_policy.all():
            return_policy.append(policy.policy_text)
        
        # Tính giá
        original_price = float(product.price)
        discount_price = float(product.discount_price) if product.discount_price else None
        discount_percent = None
        if discount_price:
            discount_percent = round(((original_price - discount_price) / original_price) * 100)
        
        # ✅ Format theo ProductModel Flutter
        product_data = {
            'id': product.id,
            'name': product.name,
            'description': product.description,
            'brand': {
                'id': product.brand.id if product.brand else None,
                'name': product.brand.name if product.brand else '',
            },
            'category': {
                'id': product.category.id if product.category else None,
                'name': product.category.name if product.category else None,
            },
            'price': str(int(original_price)),  # ✅ Chuyển sang int trước
            'discount_price': str(int(discount_price)) if discount_price else None,  # ✅ Same
            'rating': float(product.rating),
            'num_reviews': product.num_reviews,
            'sold': product.sold,
            'is_popular': product.is_popular,
            'is_sale': product.is_sale,
            'is_best_sale': product.is_best_sale,
            'main_image': main_image_url,
            'other_images': other_images,
            'variants': variants_data,
            'reviews': reviews_data,
            'shipping_info': shipping_info,
            'return_policy': return_policy,
        }
        
        return Response({
            'success': True,
            'product': product_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)