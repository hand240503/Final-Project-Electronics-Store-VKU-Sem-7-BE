from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import CategoryParentFESerializer, ProductsByCategoryFESerializer, ProductDetailSerializer,ReviewSerializer
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from .models import Product, Document, ProductDocument, Category
from .forms import ProductForm
from django.core.files.base import ContentFile
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .serializers import ProductSearchSerializer
from .serializers import get_valid_url 
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import requests
import cloudinary.uploader
from .models import Review
from django.db.models import Avg, Count
from api.orders.models import Order, OrderItem

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
    paginator = Paginator(products, 3)
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_order_reviews(request, order_id):
    """
    API để người dùng rating tất cả sản phẩm trong đơn hàng với cùng 1 rating
    
    URL: /api/orders/{order_id}/rating/
    
    Body request:
    {
        "rating": 5,  # Bắt buộc, từ 1-5, áp dụng cho tất cả sản phẩm
        "comment": "Đơn hàng tuyệt vời!"  # Không bắt buộc
    }
    """
    try:
        # Lấy order và kiểm tra quyền sở hữu
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        return Response(
            {"error": "Đơn hàng không tồn tại hoặc bạn không có quyền truy cập"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Kiểm tra trạng thái order (chỉ cho phép đánh giá khi đã giao hàng)
    if order.status != 3:  # 3 = Delivered
        return Response(
            {"error": "Chỉ có thể đánh giá đơn hàng đã được giao"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Lấy rating từ request
    rating_value = request.data.get('rating')
    comment = request.data.get('comment', '')
    
    # Validate rating
    if not rating_value:
        return Response(
            {"error": "Vui lòng cung cấp rating"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        rating_value = int(rating_value)
        if rating_value < 1 or rating_value > 5:
            raise ValueError
    except (ValueError, TypeError):
        return Response(
            {"error": "Rating phải là số nguyên từ 1 đến 5"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    #  BƯỚC 1: Lấy tất cả OrderItem trong order này
    order_items = OrderItem.objects.filter(order_id=order_id).select_related('product')
    if not order_items.exists():
        return Response(
            {"error": "Đơn hàng không có sản phẩm nào"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    created_reviews = []
    updated_reviews = []
    skipped_products = []
    
    #  BƯỚC 2: Lặp qua từng OrderItem, lấy product_id và tạo/update review
    for order_item in order_items:
        # Bỏ qua nếu không có product (đã bị xóa)
        if not order_item.product:
            skipped_products.append(f"OrderItem #{order_item.id} (product đã bị xóa)")
            continue
        
        #  Lấy product_id từ OrderItem
        product_id = order_item.product.id
        print(product_id)
        product = order_item.product
        
        # Kiểm tra xem user đã review product này chưa
        existing_review = Review.objects.filter(
            product_id=product_id,  # Sử dụng product_id từ OrderItem
            user=request.user
        ).first()
        
        if existing_review:
            # Cập nhật review cũ
            
            existing_review.rating = rating_value
            existing_review.comment = comment
            existing_review.save()
            updated_reviews.append({
                "product_id": product_id,
                "product_name": product.name,
                "review_id": existing_review.id
            })
        else:
            # Tạo review mới
            review = Review.objects.create(
                product_id=product_id,  # Lưu product_id từ OrderItem
                user=request.user,
                rating=rating_value,
                comment=comment
            )
            created_reviews.append({
                "product_id": product_id,
                "product_name": product.name,
                "review_id": review.id
            })
        
        # Cập nhật rating trung bình cho product
        reviews_aggregate = Review.objects.filter(product_id=product_id).aggregate(
            avg_rating=Avg('rating'),
            total_reviews=Count('id')
        )
        
        product.rating = round(reviews_aggregate['avg_rating'] or 0, 2)
        product.num_reviews = reviews_aggregate['total_reviews'] or 0
        product.save(update_fields=['rating', 'num_reviews'])
    
    # Tạo response
    total_reviews = len(created_reviews) + len(updated_reviews)
    
    response_data = {
        "message": f"Đã đánh giá thành công {total_reviews} sản phẩm từ đơn hàng #{order.order_code}",
        "order_id": order_id,
        "order_code": order.order_code,
        "rating": rating_value,
        "comment": comment,
        "total_products_reviewed": total_reviews,
        "created": len(created_reviews),
        "updated": len(updated_reviews),
        "created_reviews": created_reviews,
        "updated_reviews": updated_reviews,
    }
    
    if skipped_products:
        response_data["skipped"] = skipped_products
    
    return Response(response_data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_order_products_for_review(request, order_id):
    """
    API để lấy danh sách sản phẩm trong đơn hàng để đánh giá
    """
    try:
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        return Response(
            {"error": "Đơn hàng không tồn tại hoặc bạn không có quyền truy cập"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Lấy tất cả order items
    order_items = OrderItem.objects.filter(order=order).select_related('product')
    
    products_data = []
    for item in order_items:
        if not item.product:
            continue
            
        # Kiểm tra xem đã review chưa
        existing_review = Review.objects.filter(
            product=item.product,
            user=request.user
        ).first()
        
        product_data = {
            "product_id": item.product.id,
            "product_name": item.product.name,
            "quantity": item.quantity,
            "price": float(item.price),
            "already_reviewed": existing_review is not None,
        }
        
        if existing_review:
            product_data["existing_review"] = {
                "rating": existing_review.rating,
                "comment": existing_review.comment,
            }
        
        products_data.append(product_data)
    
    return Response({
        "order_id": order.id,
        "order_code": order.order_code,
        "products": products_data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_product_rating(request, order_id):
    """
    API để người dùng rating tất cả sản phẩm trong đơn hàng
    
    URL: /api/products/{order_id}/rating/
    
    Body request:
    {
        "rating": 5,  # Bắt buộc, từ 1-5
        "comment": "Sản phẩm tuyệt vời!"  # Không bắt buộc
    }
    """
    # 🔍 DEBUG: Log thông tin request
    print("=" * 60)
    print(f"🔍 CREATE_PRODUCT_RATING - Request Info:")
    print(f"URL order_id parameter: {order_id}")
    print(f"User: {request.user.username} (ID: {request.user.id})")
    print(f"Request data: {request.data}")
    print("=" * 60)
    
    try:
        # Lấy order và kiểm tra quyền sở hữu
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        return Response(
            {"error": "Đơn hàng không tồn tại hoặc bạn không có quyền truy cập"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Kiểm tra trạng thái order
    if order.status != 3:  # 3 = Returned (theo model của bạn)
        return Response(
            {"error": "Chỉ có thể đánh giá đơn hàng đã được giao"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Lấy dữ liệu từ request
    rating_value = request.data.get('rating')
    comment = request.data.get('comment', '')
      
    # Validate rating
    if not rating_value:
        return Response(
            {"error": "Vui lòng cung cấp rating"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        rating_value = int(rating_value)
        if rating_value < 1 or rating_value > 5:
            raise ValueError
    except (ValueError, TypeError):
        return Response(
            {"error": "Rating phải là số nguyên từ 1 đến 5"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Lấy tất cả OrderItem trong order
    order_items = OrderItem.objects.filter(order_id=order_id).select_related('product')
    
    if not order_items.exists():
        return Response(
            {"error": "Đơn hàng không có sản phẩm nào"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    
    created_reviews = []
    updated_reviews = []
    skipped_products = []
    
    # Lặp qua từng OrderItem
    for order_item in order_items:
        if not order_item.product:
            skipped_products.append(f"OrderItem #{order_item.id} (product đã bị xóa)")
            continue
        
        product = order_item.product
        product_id = product.id
        
        # Kiểm tra xem user đã review product này chưa
        existing_review = Review.objects.filter(
            product=product,
            user=request.user
        ).first()
        
        if existing_review:
            
            # Cập nhật review cũ
            existing_review.rating = rating_value
            existing_review.comment = comment
            existing_review.save()
            
            updated_reviews.append({
                "product_id": product_id,
                "product_name": product.name,
                "review_id": existing_review.id
            })
        else:           
            # Tạo review mới
            review = Review.objects.create(
                product=product,  # Truyền object, không phải ID
                user=request.user,
                rating=rating_value,
                comment=comment
            )
            
            created_reviews.append({
                "product_id": product_id,
                "product_name": product.name,
                "review_id": review.id
            })
    
        reviews_aggregate = Review.objects.filter(product=product).aggregate(
            avg_rating=Avg('rating'),
            total_reviews=Count('id')
        )
        
        old_rating = product.rating
        old_num_reviews = product.num_reviews
        
        product.rating = round(reviews_aggregate['avg_rating'] or 0, 2)
        product.num_reviews = reviews_aggregate['total_reviews'] or 0
        product.save(update_fields=['rating', 'num_reviews'])
    
    # Tạo response
    total_reviews = len(created_reviews) + len(updated_reviews)
    
    response_data = {
        "message": f"Đã đánh giá thành công {total_reviews} sản phẩm từ đơn hàng #{order.order_code}",
        "order_id": order_id,
        "order_code": order.order_code,
        "rating": rating_value,
        "comment": comment,
        "total_products_reviewed": total_reviews,
        "created": len(created_reviews),
        "updated": len(updated_reviews),
        "created_reviews": created_reviews,
        "updated_reviews": updated_reviews,
    }
    
    if skipped_products:
        response_data["skipped"] = skipped_products

    return Response(response_data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
def get_product_reviews(request, product_id):
    """
    API để lấy danh sách reviews của sản phẩm
    """
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response(
            {"error": "Sản phẩm không tồn tại"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    reviews = Review.objects.filter(product=product).order_by('-created_at')
    serializer = ReviewSerializer(reviews, many=True)
    
    return Response({
        "product_id": product.id,
        "product_name": product.name,
        "average_rating": product.rating,
        "total_reviews": product.num_reviews,
        "reviews": serializer.data
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_product_review(request, review_id):
    """
    API để xóa review của chính mình
    """
    try:
        review = Review.objects.get(id=review_id, user=request.user)
    except Review.DoesNotExist:
        return Response(
            {"error": "Review không tồn tại hoặc bạn không có quyền xóa"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    product = review.product
    review.delete()
    

    reviews_aggregate = Review.objects.filter(product=product).aggregate(
        avg_rating=Avg('rating'),
        total_reviews=Count('id')
    )
    
    product.rating = round(reviews_aggregate['avg_rating'] or 0, 2)
    product.num_reviews = reviews_aggregate['total_reviews'] or 0
    product.save(update_fields=['rating', 'num_reviews'])
    
    return Response(
        {"message": "Xóa đánh giá thành công"},
        status=status.HTTP_200_OK
    )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_product_review(request, review_id):
    """
    API để xóa review của chính mình
    """
    try:
        review = Review.objects.get(id=review_id, user=request.user)
    except Review.DoesNotExist:
        return Response(
            {"error": "Review không tồn tại hoặc bạn không có quyền xóa"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    product = review.product
    review.delete()
    
    # Cập nhật lại rating của product
    from django.db.models import Avg, Count
    reviews_aggregate = Review.objects.filter(product=product).aggregate(
        avg_rating=Avg('rating'),
        total_reviews=Count('id')
    )
    
    product.rating = round(reviews_aggregate['avg_rating'] or 0, 2)
    product.num_reviews = reviews_aggregate['total_reviews'] or 0
    product.save(update_fields=['rating', 'num_reviews'])
    
    return Response(
        {"message": "Xóa đánh giá thành công"},
        status=status.HTTP_200_OK
    )