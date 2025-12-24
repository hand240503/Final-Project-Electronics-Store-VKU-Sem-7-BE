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
from django.db.models import Q

import requests
import cloudinary.uploader  # ← THÊM IMPORT NÀY

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