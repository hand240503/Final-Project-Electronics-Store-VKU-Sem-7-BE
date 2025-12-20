from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as http_status
from rest_framework.permissions import IsAuthenticated
from .models import Order, OrderItem
from api.cart.models import CartItem
from api.products.models import Product, ProductVariant
from django.contrib.auth.models import User
from .serializers import OrderSerializer
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

class OrderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        data = request.data

        # Tạo order
        order = Order.objects.create(
            user=user,
            total_price=data.get('totalPrice'),
            has_insurance=data.get('hasInsurance', False),
            address_full_name=data['address']['full_name'],
            address_phone=data['address']['phone'],
            address_line=data['address']['address_line'],
            ward=data['address'].get('ward'),
            district=data['address'].get('district'),
            city=data['address'].get('city'),
            note=data.get('note', ''),
            discount_code=data.get('discountCode'),
            order_code=data.get('orderCode', '')
        )

        # Tạo order items và xóa khỏi giỏ hàng
        for item in data.get('items', []):
            product = Product.objects.get(id=item['product_id'])
            variant_id = item.get('variant_id')
            variant = ProductVariant.objects.get(id=variant_id) if variant_id else None

            OrderItem.objects.create(
                order=order,
                product=product,
                variant=variant,
                quantity=item['quantity'],
                price=item['price']
            )

            # Xóa sản phẩm khỏi giỏ hàng của user nếu có
            CartItem.objects.filter(
                cart__user=user,
                product=product,
                variant_id=variant_id
            ).delete()

        return Response(
            {"message": "Order created successfully", "order_id": order.id},
            status=http_status.HTTP_201_CREATED
        )

class OrdersByUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=http_status.HTTP_404_NOT_FOUND)

        orders = Order.objects.filter(user=user).order_by('-created_at')
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data, status=http_status.HTTP_200_OK)

class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=http_status.HTTP_404_NOT_FOUND)

        serializer = OrderSerializer(order, context={'request': request})
        return Response(serializer.data, status=http_status.HTTP_200_OK)

class CancelOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({"success": False, "message": "Đơn hàng không tồn tại"}, status=http_status.HTTP_404_NOT_FOUND)

        if order.status != 0:  # Chỉ cho hủy đơn "Chờ người bán gửi hàng"
            return Response({"success": False, "message": "Không thể hủy đơn hàng này"}, status=http_status.HTTP_400_BAD_REQUEST)

        order.status = 5  # 5 = Đã hủy
        order.save()

        return Response({"success": True, "message": "Đã hủy đơn hàng"})
    

@require_http_methods(["GET"])
def orders_list(request):
    orders = Order.objects.all()

    return render(request, "orders_list.html", {
        "orders": orders,
    })

def orders_approve_next(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if order.status < 3:
        order.status += 1
        order.save()
    else:
        messages.info(request, "Đơn hàng đã hoàn tất, không thể duyệt tiếp")

    return redirect("orders_list")

@require_http_methods(["GET"])
def orders_detail(request, pk):
    orders = get_object_or_404(Order, pk=pk)

    if request.method == "POST":
        new_status = request.POST.get("status")
        orders.status = int(new_status)
        orders.save()

        messages.success(request, "Cập nhật trạng thái đơn hàng thành công!")
        return redirect("order_detail", order_id=orders.id)

    return render(request, "orders_detail.html", {
        "order": orders,
    })


