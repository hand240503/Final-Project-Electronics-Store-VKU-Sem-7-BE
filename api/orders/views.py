from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Order, OrderItem
from api.products.models import Product, ProductVariant
from django.contrib.auth.models import User

class OrderCreateView(APIView):
    def post(self, request):
        user = request.user
        data = request.data

        # Tạo order
        order = Order.objects.create(
            user=user,
            total_price = data.get('totalPrice'),
            has_insurance=data.get('hasInsurance', False),
            address_full_name=data['address']['full_name'],
            address_phone=data['address']['phone'],
            address_line=data['address']['address_line'],
            ward=data['address'].get('ward'),
            district=data['address'].get('district'),
            city=data['address'].get('city'),
            note=data.get('note', ''),               # thêm trường note
            discount_code=data.get('discountCode')   # thêm trường discount_code
        )

        # Tạo order items
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

        return Response({"message": "Order created successfully", "order_id": order.id}, status=status.HTTP_201_CREATED)
