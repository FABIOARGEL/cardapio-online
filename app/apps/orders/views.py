"""
Order API views.

Refactored:
- Proper ownership checks with domain exceptions
- No generic except clauses
"""
from __future__ import annotations

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.core.authentication import JWTAuthentication
from apps.core.enums import OrderStatus, UserRole
from apps.core.permissions import IsAuthenticated
from apps.orders.serializers import (
    CreateOrderSerializer,
    UpdateOrderStatusSerializer,
    ValidateCouponSerializer,
)
from apps.orders.services import OrderService
from apps.restaurants.repositories import RestaurantRepository


class OrderListView(APIView):
    """GET / POST /api/orders/"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List orders for the authenticated user (customer or owner)."""
        service = OrderService()
        page = int(request.query_params.get('page', 1))
        user = request.user

        if user.role == UserRole.CUSTOMER:
            result = service.list_customer_orders(str(user.id), page=page)
        else:
            restaurant_id = request.query_params.get('restaurant_id')
            if not restaurant_id:
                return Response(
                    {'error': 'restaurant_id é obrigatório.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            status_filter = request.query_params.get('status')
            result = service.list_restaurant_orders(
                restaurant_id, status_filter=status_filter, page=page,
            )
        return Response(result)

    def post(self, request):
        """Create a new order (customer only)."""
        if request.user.role != UserRole.CUSTOMER:
            return Response(
                {'error': 'Apenas clientes podem criar pedidos.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = CreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = OrderService()
        result = service.create_order(
            customer_id=str(request.user.id),
            data=serializer.validated_data,
        )
        return Response(result, status=status.HTTP_201_CREATED)


class OrderDetailView(APIView):
    """GET /api/orders/:id/"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        service = OrderService()
        result = service.get_order(order_id)
        if not result:
            return Response(
                {'error': 'Pedido não encontrado.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Ownership check
        if request.user.role == UserRole.CUSTOMER:
            if str(result['customer_id']) != str(request.user.id):
                return Response(
                    {'error': 'Acesso negado.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
        elif request.user.role == UserRole.OWNER:
            repo = RestaurantRepository()
            restaurant = repo.find_by_id_and_owner(result['restaurant_id'], str(request.user.id))
            if not restaurant:
                return Response(
                    {'error': 'Acesso negado.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        return Response(result)


class OrderStatusView(APIView):
    """PATCH /api/orders/:id/status/"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, order_id):
        serializer = UpdateOrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = OrderService()

        # Fetch order for permission check
        order = service.get_order(order_id)
        if not order:
            return Response(
                {'error': 'Pedido não encontrado.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        new_status = serializer.validated_data['status']

        # Role-based permission check
        if request.user.role == UserRole.CUSTOMER:
            if str(order['customer_id']) != str(request.user.id):
                return Response({'error': 'Acesso negado.'}, status=status.HTTP_403_FORBIDDEN)
            if new_status != OrderStatus.CANCELLED:
                return Response(
                    {'error': 'Clientes só podem cancelar pedidos.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
        elif request.user.role == UserRole.OWNER:
            repo = RestaurantRepository()
            restaurant = repo.find_by_id_and_owner(order['restaurant_id'], str(request.user.id))
            if not restaurant:
                return Response({'error': 'Acesso negado.'}, status=status.HTTP_403_FORBIDDEN)

        result = service.update_status(
            order_id=order_id,
            new_status=new_status,
            changed_by=str(request.user.id),
            reason=serializer.validated_data.get('cancellation_reason'),
        )
        return Response(result)


class ValidateCouponView(APIView):
    """POST /api/orders/validate-coupon/"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ValidateCouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = OrderService()
        result = service.validate_coupon(
            serializer.validated_data['restaurant_id'],
            serializer.validated_data['code'],
            float(serializer.validated_data['cart_total']),
        )
        return Response(result)
