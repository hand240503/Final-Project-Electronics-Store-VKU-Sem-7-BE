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
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta

# ===== IMPORT NOTIFICATION SERVICE =====
from utils.notification_service import NotificationService


class OrderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        data = request.data

        # Tạo order
        order = Order.objects.create(
            user=user,
            total_price=data.get("totalPrice"),
            has_insurance=data.get("hasInsurance", False),
            address_full_name=data["address"]["full_name"],
            address_phone=data["address"]["phone"],
            address_line=data["address"]["address_line"],
            ward=data["address"].get("ward"),
            district=data["address"].get("district"),
            city=data["address"].get("city"),
            note=data.get("note", ""),
            discount_code=data.get("discountCode"),
            order_code=data.get("orderCode", ""),
        )

        # Tạo order items và xóa khỏi giỏ hàng
        for item in data.get("items", []):
            product = Product.objects.get(id=item["product_id"])
            variant_id = item.get("variant_id")
            variant = ProductVariant.objects.get(id=variant_id) if variant_id else None

            OrderItem.objects.create(
                order=order,
                product=product,
                variant=variant,
                quantity=item["quantity"],
                price=item["price"],
            )

            # Xóa sản phẩm khỏi giỏ hàng của user nếu có
            CartItem.objects.filter(
                cart__user=user, product=product, variant_id=variant_id
            ).delete()

        # ===== GỬI NOTIFICATION ĐẶT HÀNG THÀNH CÔNG =====
        try:
            NotificationService.send_order_notification(
                user_id=user.id, order_id=order.id, status="placed"
            )
        except Exception as e:
            print(f"Error sending notification: {e}")

        return Response(
            {"message": "Order created successfully", "order_id": order.id},
            status=http_status.HTTP_201_CREATED,
        )


class OrdersByUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=http_status.HTTP_404_NOT_FOUND
            )

        orders = Order.objects.filter(user=user).order_by("-created_at")
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data, status=http_status.HTTP_200_OK)


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response(
                {"error": "Order not found"}, status=http_status.HTTP_404_NOT_FOUND
            )

        serializer = OrderSerializer(order, context={"request": request})
        return Response(serializer.data, status=http_status.HTTP_200_OK)


class CancelOrderAPIView(APIView):
    """
    POST /api/orders/cancel/{order_id}/
    Hủy đơn hàng

    Logic: Chỉ cho phép hủy đơn ở trạng thái "Chờ xác nhận" (status = 0)
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response(
                {"success": False, "message": "Đơn hàng không tồn tại"},
                status=http_status.HTTP_404_NOT_FOUND,
            )

        if order.status != 0:  # Chỉ cho hủy đơn "Chờ xác nhận"
            return Response(
                {
                    "success": False,
                    "message": "Chỉ có thể hủy đơn hàng ở trạng thái 'Chờ xác nhận'",
                },
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        order.status = 5  # 5 = Cancelled
        order.save()

        # ===== GỬI NOTIFICATION ĐƠN HÀNG BỊ HỦY =====
        try:
            NotificationService.send_noti(
                user_id=request.user.id,
                type_code="order_cancelled",
                title="Đơn hàng đã hủy",
                content=f"Đơn hàng {order.order_code} đã được hủy thành công",
                redirect_url=f"{order.id}",
                metadata={"order_id": order.id, "order_code": order.order_code},
            )
        except Exception as e:
            print(f"Error sending notification: {e}")

        return Response({"success": True, "message": "Đã hủy đơn hàng"})


class ReturnOrderAPIView(APIView):
    """
    POST /api/orders/return/{order_id}/
    Yêu cầu trả hàng

    Logic:
    - Đơn hàng phải ở trạng thái "Đã giao" (status = 3)
    - is_return phải = 2 (chưa xử lý - mặc định)
    - Thời gian kể từ khi giao hàng (status = 3) không quá 7 ngày
    - Sau khi yêu cầu: status = 4 (Đang trong quá trình trả hàng), is_return = 2 (Đang xem xét)
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            print(
                f"[RETURN ORDER] Order {order_id} not found for user {request.user.id}"
            )
            return Response(
                {"success": False, "message": "Đơn hàng không tồn tại"},
                status=http_status.HTTP_404_NOT_FOUND,
            )

        print(
            f"[RETURN ORDER] Order {order_id} - Status: {order.status}, is_return: {order.is_return}, updated_at: {order.updated_at}"
        )

        # Kiểm tra trạng thái đơn hàng - Phải ở trạng thái "Đã giao" (3)
        if order.status != 3:
            print(f"[RETURN ORDER] Invalid status: {order.status} (expected 3)")
            return Response(
                {
                    "success": False,
                    "message": f"Chỉ có thể trả hàng đơn đã giao thành công. Trạng thái hiện tại: {order.get_status_display()}",
                },
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        # Kiểm tra is_return - Phải = 2 (chưa xử lý)
        if order.is_return != 2:
            print(f"[RETURN ORDER] Invalid is_return: {order.is_return} (expected 2)")
            if order.is_return == 1:
                return Response(
                    {
                        "success": False,
                        "message": "Yêu cầu trả hàng đã được chấp nhận trước đó",
                    },
                    status=http_status.HTTP_400_BAD_REQUEST,
                )
            elif order.is_return == 0:
                return Response(
                    {"success": False, "message": "Yêu cầu trả hàng đã bị từ chối"},
                    status=http_status.HTTP_400_BAD_REQUEST,
                )
            else:
                return Response(
                    {
                        "success": False,
                        "message": "Đơn hàng này đang được xem xét trả hàng",
                    },
                    status=http_status.HTTP_400_BAD_REQUEST,
                )

        # Kiểm tra thời gian (7 ngày kể từ khi giao hàng - status = 3)
        # updated_at là lúc order thay đổi status lần cuối
        days_since_delivered = (timezone.now() - order.updated_at).days

        print(f"[RETURN ORDER] Days since delivered: {days_since_delivered}")

        if days_since_delivered > 7:
            return Response(
                {
                    "success": False,
                    "message": f"Đã quá thời hạn trả hàng (7 ngày). Đơn hàng được giao {days_since_delivered} ngày trước.",
                },
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        print(f"[RETURN ORDER] All checks passed. Processing return...")

        # Cập nhật trạng thái trả hàng
        order.status = 4  # 4 = Đang trong quá trình trả hàng
        # is_return giữ nguyên = 2 (Đang xem xét)
        order.save()

        print(
            f"[RETURN ORDER] Order {order_id} updated successfully - Status: 4, is_return: 2"
        )

        # ===== GỬI NOTIFICATION YÊU CẦU TRẢ HÀNG =====
        try:
            NotificationService.send_noti(
                user_id=request.user.id,
                type_code="order_returned",
                title="Yêu cầu trả hàng đã được gửi",
                content=f"Yêu cầu trả hàng cho đơn {order.order_code} đang được xem xét. Chúng tôi sẽ xử lý trong 24-48h.",
                redirect_url=f"{order.id}",
                metadata={
                    "order_id": order.id,
                    "order_code": order.order_code,
                    "return_date": timezone.now().isoformat(),
                },
            )
        except Exception as e:
            print(f"Error sending notification: {e}")

        return Response(
            {
                "success": True,
                "message": "Yêu cầu trả hàng đã được gửi thành công",
                "data": {
                    "order_id": order.id,
                    "order_code": order.order_code,
                    "status": order.status,
                    "is_return": order.is_return,
                    "message": "Đơn hàng đang được xem xét trả hàng",
                },
            }
        )


class CancelReturnRequestAPIView(APIView):
    """
    POST /api/orders/cancel-return/{order_id}/
    Hủy yêu cầu trả hàng (user tự hủy)
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response(
                {"success": False, "message": "Đơn hàng không tồn tại"},
                status=http_status.HTTP_404_NOT_FOUND,
            )

        # Chỉ cho phép hủy khi status = 4 và is_return = 2 (đang xem xét)
        if order.status != 4 or order.is_return != 2:
            return Response(
                {"success": False, "message": "Không thể hủy yêu cầu này"},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        # Đưa về trạng thái "Đã giao"
        order.status = 3
        order.save()

        try:
            NotificationService.send_noti(
                user_id=request.user.id,
                type_code="return_cancelled",
                title="Đã hủy yêu cầu trả hàng",
                content=f"Yêu cầu trả hàng cho đơn {order.order_code} đã được hủy.",
                redirect_url=f"{order.id}",
                metadata={"order_id": order.id, "order_code": order.order_code},
            )
        except Exception as e:
            print(f"Error sending notification: {e}")

        return Response({"success": True, "message": "Đã hủy yêu cầu trả hàng"})


# ===== ADMIN VIEWS =====
@require_http_methods(["GET"])
def orders_list(request):
    orders = Order.objects.all().order_by("-created_at")
    search_query = request.GET.get('search', '').strip()
    
    # Tìm kiếm theo mã đơn hàng và tên khách hàng
    if search_query:
        orders = orders.filter(
            Q(order_code__icontains=search_query) |
            Q(address_full_name__icontains=search_query)
        )
    
    context = {
        'orders': orders,
        'search_query': search_query,
    }
    return render(request, "orders_list.html", context)


def orders_approve_next(request, order_id):
    """
    Duyệt đơn hàng sang trạng thái tiếp theo
    0 (Chờ xác nhận) -> 1 (Chờ lấy hàng) -> 2 (Chờ giao hàng) -> 3 (Đã giao)
    """
    order = get_object_or_404(Order, id=order_id)

    if order.status < 3:  # Từ 0 -> 1 -> 2 -> 3
        order.status += 1
        order.save()

        # ===== GỬI NOTIFICATION KHI THAY ĐỔI TRẠNG THÁI =====
        try:
            if order.status == 1:  # Chờ lấy hàng
                NotificationService.send_noti(
                    user_id=order.user.id,
                    type_code="order_confirmed",
                    title="Đơn hàng đã được xác nhận",
                    content=f"Đơn hàng {order.order_code} đã được xác nhận và đang chờ lấy hàng.",
                    redirect_url=f"{order.id}",
                    metadata={"order_id": order.id, "order_code": order.order_code},
                )
            elif order.status == 2:  # Chờ giao hàng
                NotificationService.send_order_notification(
                    user_id=order.user.id, order_id=order.id, status="shipped"
                )
            elif order.status == 3:  # Đã giao
                NotificationService.send_order_notification(
                    user_id=order.user.id, order_id=order.id, status="delivered"
                )
        except Exception as e:
            print(f"Error sending notification: {e}")

        messages.success(
            request, f"Đơn hàng đã chuyển sang trạng thái: {order.get_status_display()}"
        )
    else:
        messages.info(request, "Đơn hàng đã ở trạng thái cuối, không thể duyệt tiếp")

    return redirect("orders_list")


@require_http_methods(["GET", "POST"])
def orders_detail(request, pk):
    """
    Chi tiết đơn hàng và xử lý thay đổi trạng thái

    Status:
    0 = Chờ xác nhận
    1 = Chờ lấy hàng
    2 = Chờ giao hàng
    3 = Đã giao
    4 = Đang trong quá trình trả hàng
    5 = Đã hủy

    is_return (khi status = 4):
    0 = Không được trả hàng
    1 = Được trả hàng
    2 = Đang xem xét (mặc định)
    """
    order = get_object_or_404(Order, pk=pk)

    if request.method == "POST":
        new_status = int(request.POST.get("status"))
        is_return_action = request.POST.get("is_return_action")  # approve/reject

        old_status = order.status

        # Xử lý yêu cầu trả hàng (nếu có)
        if is_return_action and order.status == 4:
            if is_return_action == "approve":
                order.is_return = 1  # Chấp nhận trả hàng
                messages.success(request, "Đã chấp nhận yêu cầu trả hàng!")

                try:
                    NotificationService.send_noti(
                        user_id=order.user.id,
                        type_code="return_approved",
                        title="Yêu cầu trả hàng đã được chấp nhận",
                        content=f"Yêu cầu trả hàng cho đơn {order.order_code} đã được chấp nhận. Vui lòng gửi hàng về địa chỉ của chúng tôi.",
                        redirect_url=f"{order.id}",
                        metadata={"order_id": order.id, "order_code": order.order_code},
                    )
                except Exception as e:
                    print(f"Error sending notification: {e}")

            elif is_return_action == "reject":
                order.is_return = 0  # Từ chối trả hàng
                order.status = 3  # Đưa về trạng thái "Đã giao"
                messages.warning(request, "Đã từ chối yêu cầu trả hàng!")

                try:
                    NotificationService.send_noti(
                        user_id=order.user.id,
                        type_code="return_rejected",
                        title="Yêu cầu trả hàng bị từ chối",
                        content=f"Yêu cầu trả hàng cho đơn {order.order_code} không được chấp nhận.",
                        redirect_url=f"{order.id}",
                        metadata={"order_id": order.id, "order_code": order.order_code},
                    )
                except Exception as e:
                    print(f"Error sending notification: {e}")

            order.save()
            return redirect("orders_detail", pk=order.id)

        # Thay đổi status thông thường
        order.status = new_status
        order.save()

        # ===== GỬI NOTIFICATION KHI ADMIN THAY ĐỔI TRẠNG THÁI =====
        try:
            if new_status == 1:  # Chờ lấy hàng
                NotificationService.send_noti(
                    user_id=order.user.id,
                    type_code="order_confirmed",
                    title="Đơn hàng đã được xác nhận",
                    content=f"Đơn hàng {order.order_code} đã được xác nhận.",
                    redirect_url=f"{order.id}",
                    metadata={"order_id": order.id, "order_code": order.order_code},
                )
            elif new_status == 2:  # Chờ giao hàng
                NotificationService.send_order_notification(
                    user_id=order.user.id, order_id=order.id, status="shipped"
                )
            elif new_status == 3:  # Đã giao
                NotificationService.send_order_notification(
                    user_id=order.user.id, order_id=order.id, status="delivered"
                )
            elif new_status == 5:  # Đã hủy
                NotificationService.send_noti(
                    user_id=order.user.id,
                    type_code="order_cancelled",
                    title="Đơn hàng đã hủy",
                    content=f"Đơn hàng {order.order_code} đã bị hủy",
                    redirect_url=f"{order.id}",
                    metadata={"order_id": order.id, "order_code": order.order_code},
                )
        except Exception as e:
            print(f"Error sending notification: {e}")

        messages.success(request, "Cập nhật trạng thái đơn hàng thành công!")
        return redirect("orders_detail", pk=order.id)

    return render(request, "orders_detail.html", {"order": order})


@require_http_methods(["GET"])
def returns_list(request):
    """
    GET /admin/returns/
    Hiển thị danh sách yêu cầu trả hàng
    """

    pending_returns = Order.objects.filter(status=4, is_return=2).order_by(
        "-updated_at"
    )

    approved_returns = Order.objects.filter(is_return=1).order_by("-updated_at")

    rejected_returns = Order.objects.filter(is_return=0).order_by("-updated_at")

    # TẤT CẢ
    all_returns = Order.objects.filter(is_return__in=[0, 1, 2]).order_by("-updated_at")

    statistics = {
        "pending": pending_returns.count(),
        "approved": approved_returns.count(),
        "rejected": rejected_returns.count(),
        "total": all_returns.count(),
    }

    # 👇 MẶC ĐỊNH = all
    tab = request.GET.get("tab", "all")
    search_query = request.GET.get("search", "")

    # Lọc theo tab
    if tab == "pending":
        orders = pending_returns
    elif tab == "approved":
        orders = approved_returns
    elif tab == "rejected":
        orders = rejected_returns
    else:  # all
        orders = all_returns
        tab = "all"

    # Search
    if search_query:
        orders = orders.filter(
            Q(order_code__icontains=search_query)
            | Q(address_full_name__icontains=search_query)
            | Q(address_phone__icontains=search_query)
        )

    context = {
        "orders": orders,
        "statistics": statistics,
        "current_tab": tab,
        "search_query": search_query,
    }

    return render(request, "returns_list.html", context)


@require_http_methods(["GET"])
def returns_detail(request, order_id):
    """
    GET /admin/returns/{order_id}/
    Hiển thị chi tiết yêu cầu trả hàng
    """
    order = get_object_or_404(Order, id=order_id)

    # Chỉ cho phép xem nếu đơn có trạng thái liên quan đến trả hàng
    if order.status != 4 and order.is_return == 2:
        messages.error(request, "Đơn hàng không có yêu cầu trả hàng")
        return redirect("returns_list")

    context = {
        "order": order,
        "days_since_delivery": (timezone.now() - order.updated_at).days,
    }

    return render(request, "returns_detail.html", context)


@require_http_methods(["POST"])
def approve_return(request, order_id):
    """
    POST /admin/returns/{order_id}/approve/
    Chấp nhận yêu cầu trả hàng
    Cập nhật: is_return = 1 (Returned)
    """
    order = get_object_or_404(Order, id=order_id)

    # Kiểm tra điều kiện
    if order.status != 4 or order.is_return != 2:
        messages.error(
            request,
            f"Chỉ có thể chấp nhận yêu cầu đơn đã giao và chưa xử lý. Hiện tại: status={order.status}, is_return={order.is_return}",
        )
        return redirect("returns_detail", order_id=order.id)

    # Cập nhật trạng thái
    order.is_return = 1  # 1 = Returned (được trả hàng)
    order.save()

    print(f"[ADMIN RETURN] Order {order_id} return approved - is_return set to 1")

    # Gửi thông báo cho user
    try:
        NotificationService.send_noti(
            user_id=order.user.id,
            type_code="return_approved",
            title="Yêu cầu trả hàng đã được chấp nhận",
            content=f"Yêu cầu trả hàng cho đơn {order.order_code} đã được chấp nhận. Vui lòng gửi hàng về địa chỉ của chúng tôi trong vòng 7 ngày.",
            redirect_url=f"{order.id}",
            metadata={
                "order_id": order.id,
                "order_code": order.order_code,
                "approved_date": timezone.now().isoformat(),
            },
        )
    except Exception as e:
        print(f"Error sending notification: {e}")

    messages.success(
        request, f"✓ Đã chấp nhận yêu cầu trả hàng cho đơn {order.order_code}"
    )
    return redirect("returns_detail", order_id=order.id)


@require_http_methods(["POST"])
def reject_return(request, order_id):
    """
    POST /admin/returns/{order_id}/reject/
    Từ chối yêu cầu trả hàng
    Cập nhật: is_return = 0 (No return)
    """
    order = get_object_or_404(Order, id=order_id)

    # Kiểm tra điều kiện
    if order.status != 4 or order.is_return != 2:
        messages.error(request, "Chỉ có thể từ chối yêu cầu đang chờ xử lý")
        return redirect("returns_detail", order_id=order.id)

    # Lấy lý do từ chối
    reason = request.POST.get("reason", "Không đủ điều kiện trả hàng")

    # Cập nhật trạng thái
    order.is_return = 0  # 0 = No return (không được trả hàng)
    order.status = 3  # Đưa về trạng thái "Đã giao" (3)
    order.save()

    print(f"[ADMIN RETURN] Order {order_id} return rejected - is_return set to 0")

    # Gửi thông báo cho user
    try:
        NotificationService.send_noti(
            user_id=order.user.id,
            type_code="return_rejected",
            title="Yêu cầu trả hàng bị từ chối",
            content=f"Yêu cầu trả hàng cho đơn {order.order_code} không được chấp nhận. Lý do: {reason}",
            redirect_url=f"{order.id}",
            metadata={
                "order_id": order.id,
                "order_code": order.order_code,
                "rejected_date": timezone.now().isoformat(),
                "reason": reason,
            },
        )
    except Exception as e:
        print(f"Error sending notification: {e}")

    messages.warning(
        request, f"✓ Đã từ chối yêu cầu trả hàng cho đơn {order.order_code}"
    )
    return redirect("returns_detail", order_id=order.id)


@require_http_methods(["POST"])
def complete_return(request, order_id):
    """
    POST /admin/returns/{order_id}/complete/
    Hoàn thành xử lý trả hàng (đã xác nhận nhận lại hàng)
    Cập nhật: status = 6 (Completed), is_return = 1
    """
    order = get_object_or_404(Order, id=order_id)

    # Chỉ cho phép nếu is_return = 1 (Returned - đã chấp nhận)
    if order.is_return != 1:
        messages.error(request, "Chỉ có thể hoàn thành trả hàng khi đã chấp nhận")
        return redirect("returns_detail", order_id=order.id)

    # Cập nhật status thành Completed (6)
    old_status = order.status
    order.status = 6  # 6 = Completed
    received_date = timezone.now()
    order.save()

    print(
        f"[ADMIN RETURN] Order {order_id} - completed return. Status: {old_status} → 6, is_return: 1"
    )

    # Gửi thông báo cho user
    try:
        NotificationService.send_noti(
            user_id=order.user.id,
            type_code="return_completed",
            title="Trả hàng hoàn tất",
            content=f"Chúng tôi đã nhận được hàng trả cho đơn {order.order_code}. Sẽ xử lý hoàn tiền trong 3-5 ngày làm việc.",
            redirect_url=f"{order.id}",
            metadata={
                "order_id": order.id,
                "order_code": order.order_code,
                "completed_date": received_date.isoformat(),
            },
        )
    except Exception as e:
        print(f"Error sending notification: {e}")

    messages.success(
        request, f"✓ Đã hoàn thành xử lý trả hàng cho đơn {order.order_code}"
    )
    return redirect("returns_detail", order_id=order.id)




class ProcessedReturnOrdersView(APIView):
    """
    GET /api/orders/processed-returns/{user_id}/
    Lấy danh sách đơn hàng đang trả hàng đã được xử lý (approved/rejected)
    
    Logic:
    - status = 4 (Đang trong quá trình trả hàng)
    - is_return != 2 (0=từ chối hoặc 1=chấp nhận, không phải đang xem xét)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        # Kiểm tra user tồn tại
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, 
                status=http_status.HTTP_404_NOT_FOUND
            )

        # Chỉ cho phép user xem đơn hàng của chính mình (hoặc admin)
        if request.user.id != user_id and not request.user.is_staff:
            return Response(
                {"error": "Permission denied"}, 
                status=http_status.HTTP_403_FORBIDDEN
            )

        # Lấy các đơn hàng status=4 và is_return!=2
        orders = Order.objects.filter(
            user=user,
            status=4,
        ).exclude(
            is_return=2
        ).order_by('-updated_at')

        serializer = OrderSerializer(orders, many=True)
        
        return Response({
            "user_id": user_id,
            "total_orders": orders.count(),
            "orders": serializer.data
        }, status=http_status.HTTP_200_OK)