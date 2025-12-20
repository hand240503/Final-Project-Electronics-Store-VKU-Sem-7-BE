from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction

from api.cart.models import Cart, CartItem
from api.orders.models import Order, OrderItem
from api.products.models import Product, ProductVariant
from api.products.serializers import ProductSerializer

class CheckoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        user = request.user

        try:
            cart = Cart.objects.get(user=user)
        except Cart.DoesNotExist:
            return Response(
                {"success": False, "message": "Giỏ hàng không tồn tại"},
                status=404
            )

        if not cart.items.exists():
            return Response(
                {"success": False, "message": "Giỏ hàng trống"},
                status=400
            )

        address = request.data.get("address", {})

        order = Order.objects.create(
            user=user,
            total_price=cart.total_price,  # Tính tổng động
            has_insurance=cart.has_insurance,
            address_full_name=address.get("full_name", ""),
            address_phone=address.get("phone", ""),
            address_line=address.get("address_line", ""),
            ward=address.get("ward"),
            district=address.get("district"),
            city=address.get("city"),
            status=0
        )

        # Tạo OrderItem dựa trên giá hiện tại của sản phẩm/variant
        for item in cart.items.all():
            price = item.variant.price if item.variant else item.product.price
            OrderItem.objects.create(
                order=order,
                product=item.product,
                variant=item.variant,
                quantity=item.quantity,
                price=price
            )

        cart.items.all().delete()  # Xóa các item sau khi checkout

        return Response({
            "success": True,
            "message": "Tạo đơn hàng thành công",
            "order_id": order.id
        })


class AddToCartAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        user = request.user

        product_id = request.data.get("product_id")
        variant_id = request.data.get("variant_id")
        quantity = int(request.data.get("quantity", 1))

        if not product_id:
            return Response(
                {"success": False, "message": "Thiếu product_id"},
                status=400
            )

        if quantity <= 0:
            return Response(
                {"success": False, "message": "Số lượng phải lớn hơn 0"},
                status=400
            )

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {"success": False, "message": "Sản phẩm không tồn tại"},
                status=404
            )

        variant = None
        if variant_id:
            try:
                variant = ProductVariant.objects.get(id=variant_id, product=product)
            except ProductVariant.DoesNotExist:
                return Response(
                    {"success": False, "message": "Variant không hợp lệ"},
                    status=404
                )

        cart, _ = Cart.objects.get_or_create(user=user)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            variant=variant,
            defaults={"quantity": quantity}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        # Tính tổng tiền động dựa trên giá hiện tại
        total_price = sum(
            (item.variant.price if item.variant else item.product.price) * item.quantity
            for item in cart.items.all()
        )

        return Response({
            "success": True,
            "message": "Đã thêm vào giỏ hàng",
            "cart": {
                "total_price": total_price,
                "total_items": sum(item.quantity for item in cart.items.all())
            }
        })

class CartDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        if request.user.id != user_id:
            return Response(
                {"success": False, "message": "Không có quyền truy cập giỏ hàng này"},
                status=403
            )

        try:
            cart = Cart.objects.get(user_id=user_id)
        except Cart.DoesNotExist:
            return Response(
                {"success": False, "message": "Giỏ hàng không tồn tại"},
                status=404
            )

        items_data = []
        total_price = 0

        for item in cart.items.all():
            product_serializer = ProductSerializer(item.product, context={'request': request})
            product_data = product_serializer.data

            # Giá luôn lấy từ Product.price
            price = item.product.price
            item_total = price * item.quantity
            total_price += item_total

            items_data.append({
                "cart_item_id": item.id,
                "product": product_data,      # trả về product đã có main_image
                "variant_id": item.variant.id if item.variant else None,
                "variant_name": item.variant.name if item.variant else None,
                "quantity": item.quantity,
                "unit_price": price,
                "total_price": item_total,
            })

        return Response({
            "success": True,
            "cart": {
                "user_id": cart.user.id,
                "items": items_data,
                "total_price": total_price,
                "total_items": sum(item['quantity'] for item in items_data)
            }
        })

class UpdateCartItemAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, cart_item_id):
        """
        body: { "quantity": 3 }
        """
        quantity = int(request.data.get("quantity", 0))
        if quantity <= 0:
            return Response({"success": False, "message": "Số lượng phải lớn hơn 0"}, status=400)

        try:
            cart_item = CartItem.objects.get(id=cart_item_id, cart__user=request.user)
        except CartItem.DoesNotExist:
            return Response({"success": False, "message": "Cart item không tồn tại"}, status=404)

        cart_item.quantity = quantity
        cart_item.save()

        # Tính lại tổng tiền
        cart = cart_item.cart
        total_price = sum(
            (item.variant.price if item.variant else item.product.price) * item.quantity
            for item in cart.items.all()
        )

        return Response({
            "success": True,
            "message": "Cập nhật số lượng thành công",
            "cart": {
                "total_price": total_price,
                "total_items": sum(item.quantity for item in cart.items.all())
            }
        })


class DeleteCartItemAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def delete(self, request, cart_item_id):
        try:
            cart_item = CartItem.objects.get(id=cart_item_id, cart__user=request.user)
        except CartItem.DoesNotExist:
            return Response({"success": False, "message": "Cart item không tồn tại"}, status=404)

        cart = cart_item.cart
        cart_item.delete()

        total_price = sum(
            (item.variant.price if item.variant else item.product.price) * item.quantity
            for item in cart.items.all()
        )

        return Response({
            "success": True,
            "message": "Đã xóa sản phẩm khỏi giỏ hàng",
            "cart": {
                "total_price": total_price,
                "total_items": sum(item.quantity for item in cart.items.all())
            }
        })