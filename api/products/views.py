from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import CategoryParentFESerializer, ProductsByCategoryFESerializer,ProductDetailSerializer
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from .models import Product, Document, ProductDocument, Category
from .forms import ProductForm
from django.core.files.base import ContentFile
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .serializers import ProductSearchSerializer

import requests

@require_http_methods(["GET"])
def product_list(request):
    products = Product.objects.all().order_by('id')
    
    paginator = Paginator(products, 10) 
    page = request.GET.get('page')
    
    try:
        products = paginator.page(page)
    except PageNotAnInteger:

        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)
    
    return render(request, "product_list.html", {
        "products": products,
        "page_obj": products,
        "is_paginated": paginator.num_pages > 1
    })

@require_http_methods(["GET", "POST"])
def product_create(request):
    image_obj = None 

    if request.method == "POST":
        image_url = request.POST.get("image_url", "").strip()
        form = ProductForm(request.POST, request.FILES)

        if form.is_valid():
            product = form.save()

            if image_url:
                try:
                    response = requests.get(image_url)
                    if response.status_code == 200:
                        doc = Document()
                        doc.file.save(
                            "product_image.jpg",
                            ContentFile(response.content),
                            save=True
                        )
                        doc.save()

                        product.document = doc
                        product.save()

                        image_obj = doc

                except Exception as e:
                    print("Lỗi tải ảnh từ URL:", e)

            return redirect("product_detail", pk=product.pk)
        else:
            print(form.errors)
    else:
        form = ProductForm()

    return render(request, "product_add.html", {
        "form": form,
        "image": image_obj,
    })


@require_http_methods(["GET"])
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    main_image = product.documents.filter(is_main=True).select_related("document").first()

    if not main_image:
        main_image = product.documents.select_related("document").first()

    return render(request, "product_detail.html", {
        "product": product,
        "image": main_image,
    })

@require_http_methods(["GET", "POST"])
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)

    main_image = product.documents.filter(is_main=True).select_related("document").first()
    if not main_image:
        main_image = product.documents.select_related("document").first()

    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)

        if form.is_valid():
            form.save()

            image_url = request.POST.get("image_url", "").strip()

            if image_url:
                product.documents.update(is_main=False)

                doc = Document.objects.create(
                    file=image_url   
                )

                ProductDocument.objects.create(
                    product=product,
                    document=doc,
                    is_main=True
                )

            return redirect("product_list")
        else:
            print(form.errors)
    else:
        form = ProductForm(instance=product)


    return render(
        request,
        "product_update.html",
        {
            "form": form,
            "product": product,
            "image": main_image,
        }
    )

@require_http_methods(["POST"])
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)

    product_docs = ProductDocument.objects.filter(product=product)

    for pdoc in product_docs:
        doc = pdoc.document

        if doc.file and doc.file.name:
            doc.file.delete(save=False)

        doc.delete() 

    product_docs.delete()

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
            # Lấy 6 sản phẩm bất kỳ theo type: popular/sale/best_seller
            mode = request.GET.get('type', None)  # ?type=popular
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
    