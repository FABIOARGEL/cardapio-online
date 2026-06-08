"""
Restaurant, Product, Stats, and Coupon API views.
"""
from __future__ import annotations

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
import json

from apps.core.authentication import JWTAuthentication
from apps.core.permissions import IsAuthenticated, IsOwner
from apps.restaurants.serializers import (
    CreateCouponSerializer,
    CreatePratoSerializer,
    CreateRestaurantSerializer,
    UpdateCouponSerializer,
    UpdatePratoSerializer,
    UpdateRestaurantSerializer,
)
from apps.restaurants.services import (
    CouponService,
    PratoService,
    RestaurantService,
    StatsService,
)


class RestaurantListView(APIView):
    def get(self, request):
        service = RestaurantService()
        page = int(request.query_params.get('page', 1))
        search = request.query_params.get('search')
        category = request.query_params.get('category')
        result = service.list_restaurants(page=page, search=search, category=category)
        return Response(result)


class RestaurantCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOwner]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        user_auth = JWTAuthentication().authenticate(request)
        if not user_auth:
            return Response({'error': 'Não autenticado.'}, status=status.HTTP_401_UNAUTHORIZED)
        user = user_auth[0]

        if hasattr(request.data, 'dict'):
            data = request.data.dict()
        else:
            data = request.data.copy()

        for field in ['contato', 'endereco', 'horarios_funcionamento']:
            if field in data and isinstance(data[field], str):
                try:
                    data[field] = json.loads(data[field])
                except json.JSONDecodeError:
                    pass
        
        if 'contato' not in data or not isinstance(data['contato'], dict):
            data['contato'] = {}
        data['contato']['email'] = user.email

        serializer = CreateRestaurantSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        service = RestaurantService()
        result = service.create_restaurant(
            owner_id=str(request.user.id),
            data=serializer.validated_data,
            cover_image=request.FILES.get('cover_image'),
        )
        return Response(result, status=status.HTTP_201_CREATED)


class RestaurantDetailView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request, restaurant_id):
        service = RestaurantService()
        result = service.get_restaurant(restaurant_id)
        if not result:
            return Response(
                {'error': 'Restaurante não encontrado.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(result)

    def put(self, request, restaurant_id):
        auth = JWTAuthentication()
        user_auth = auth.authenticate(request)
        if not user_auth or user_auth[0].papel != 'dono':
            return Response({'error': 'Sem permissão.'}, status=status.HTTP_403_FORBIDDEN)
        user = user_auth[0]

        if hasattr(request.data, 'dict'):
            data = request.data.dict()
        else:
            data = request.data.copy()

        for field in ['contato', 'endereco', 'horarios_funcionamento']:
            if field in data and isinstance(data[field], str):
                try:
                    data[field] = json.loads(data[field])
                except json.JSONDecodeError:
                    pass

        if 'contato' not in data or not isinstance(data['contato'], dict):
            data['contato'] = {}
        data['contato']['email'] = user.email

        serializer = UpdateRestaurantSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        service = RestaurantService()
        result = service.update_restaurant(
            restaurant_id=restaurant_id,
            owner_id=str(user.id),
            data=serializer.validated_data,
            cover_image=request.FILES.get('cover_image'),
            logo_image=request.FILES.get('logo_image'),
        )
        return Response(result)

    def delete(self, request, restaurant_id):
        auth = JWTAuthentication()
        user_auth = auth.authenticate(request)
        if not user_auth or user_auth[0].papel != 'dono':
            return Response({'error': 'Sem permissão.'}, status=status.HTTP_403_FORBIDDEN)
        user = user_auth[0]

        service = RestaurantService()
        service.delete_restaurant(restaurant_id=restaurant_id, owner_id=str(user.id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class RestaurantSlugView(APIView):
    def get(self, request, slug):
        service = RestaurantService()
        result = service.get_restaurant_by_slug(slug)
        if not result:
            return Response(
                {'error': 'Restaurante não encontrado.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(result)


class OwnerRestaurantsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOwner]

    def get(self, request):
        service = RestaurantService()
        result = service.list_owner_restaurants(str(request.user.id))
        return Response(result)


class OwnerRestaurantDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOwner]

    def get(self, request, restaurant_id):
        service = RestaurantService()
        result = service.get_restaurant_detail_for_owner(restaurant_id, str(request.user.id))
        return Response(result)


class PratoListView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request, restaurant_id):
        service = PratoService()
        category = request.query_params.get('category')
        result = service.list_pratos(restaurant_id, category=category)
        return Response(result)

    def post(self, request, restaurant_id):
        auth = JWTAuthentication()
        user_auth = auth.authenticate(request)
        if not user_auth or user_auth[0].papel != 'dono':
            return Response({'error': 'Sem permissão.'}, status=status.HTTP_403_FORBIDDEN)
        user = user_auth[0]

        serializer = CreatePratoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = PratoService()
        images = request.FILES.getlist('images')
        if not images and request.FILES.get('image'):
            images = [request.FILES.get('image')]

        result = service.add_prato(
            restaurant_id=restaurant_id,
            owner_id=str(user.id),
            data=serializer.validated_data,
            images=images,
        )
        return Response(result, status=status.HTTP_201_CREATED)


class AllPratosView(APIView):
    def get(self, request):
        service = PratoService()
        page = int(request.query_params.get('page', 1))
        search = request.query_params.get('search')
        category = request.query_params.get('category')
        result = service.list_all_pratos(page=page, search=search, category=category)
        return Response(result)


class PratoDetailView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def put(self, request, restaurant_id, prato_id):
        auth = JWTAuthentication()
        user_auth = auth.authenticate(request)
        if not user_auth or user_auth[0].papel != 'dono':
            return Response({'error': 'Sem permissão.'}, status=status.HTTP_403_FORBIDDEN)
        user = user_auth[0]

        serializer = UpdatePratoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = PratoService()
        images = request.FILES.getlist('images')
        if not images and request.FILES.get('image'):
            images = [request.FILES.get('image')]

        result = service.update_prato(
            restaurant_id=restaurant_id,
            prato_id=prato_id,
            owner_id=str(user.id),
            data=serializer.validated_data,
            images=images,
        )
        return Response(result)

    def delete(self, request, restaurant_id, prato_id):
        auth = JWTAuthentication()
        user_auth = auth.authenticate(request)
        if not user_auth or user_auth[0].papel != 'dono':
            return Response({'error': 'Sem permissão.'}, status=status.HTTP_403_FORBIDDEN)
        user = user_auth[0]

        service = PratoService()
        service.remove_prato(
            restaurant_id=restaurant_id,
            prato_id=prato_id,
            owner_id=str(user.id),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class StatsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOwner]

    def get(self, request, restaurant_id):
        service = StatsService()
        result = service.get_dashboard_stats(restaurant_id, str(request.user.id))
        return Response(result)


class OrderHistoryView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOwner]

    def get(self, request, restaurant_id):
        service = StatsService()
        result = service.get_order_history(
            restaurant_id=restaurant_id,
            owner_id=str(request.user.id),
            page=int(request.query_params.get('page', 1)),
            status_filter=request.query_params.get('status'),
            date_from=request.query_params.get('date_from'),
            date_to=request.query_params.get('date_to'),
        )
        return Response(result)


class CouponListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOwner]

    def get(self, request, restaurant_id):
        service = CouponService()
        result = service.list_coupons(restaurant_id, str(request.user.id))
        return Response(result)

    def post(self, request, restaurant_id):
        serializer = CreateCouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = CouponService()
        result = service.add_coupon(
            restaurant_id=restaurant_id,
            owner_id=str(request.user.id),
            data=serializer.validated_data,
        )
        return Response(result, status=status.HTTP_201_CREATED)


class CouponDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOwner]

    def put(self, request, restaurant_id, coupon_id):
        serializer = UpdateCouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = CouponService()
        result = service.update_coupon(
            restaurant_id=restaurant_id,
            coupon_id=coupon_id,
            owner_id=str(request.user.id),
            data=serializer.validated_data,
        )
        return Response(result)

    def delete(self, request, restaurant_id, coupon_id):
        service = CouponService()
        service.remove_coupon(
            restaurant_id=restaurant_id,
            coupon_id=coupon_id,
            owner_id=str(request.user.id),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
