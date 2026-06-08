"""
Views da API de Avaliações.
"""
from __future__ import annotations

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.core.authentication import JWTAuthentication
from apps.reviews.serializers import CreateReviewSerializer, UpdateReviewSerializer
from apps.reviews.services import ReviewService


class ReviewListView(APIView):
    def get(self, request):
        """Lista avaliações para um restaurante (público)."""
        restaurant_id = request.query_params.get('restaurant_id')
        if not restaurant_id:
            return Response(
                {'error': 'restaurant_id é obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        service = ReviewService()
        page = int(request.query_params.get('page', 1))
        result = service.list_restaurant_reviews(restaurant_id, page=page)
        return Response(result)

    def post(self, request):
        """Cria uma avaliação (cliente autenticado)."""
        auth = JWTAuthentication()
        user_auth = auth.authenticate(request)
        if not user_auth:
            return Response(
                {'error': 'Autenticação necessária.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        user = user_auth[0]

        serializer = CreateReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = ReviewService()
        try:
            result = service.create_review(
                customer_id=str(user.id),
                customer_name=user.nome,
                **serializer.validated_data,
            )
            return Response(result, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ReviewDetailView(APIView):
    def put(self, request, review_id):
        """Edita uma avaliação existente (cliente autenticado)."""
        auth = JWTAuthentication()
        user_auth = auth.authenticate(request)
        if not user_auth:
            return Response(
                {'error': 'Autenticação necessária.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        user = user_auth[0]
        
        serializer = UpdateReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        service = ReviewService()
        try:
            result = service.update_review(
                customer_id=str(user.id),
                review_id=review_id,
                **serializer.validated_data
            )
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, review_id):
        """Exclui uma avaliação existente (cliente autenticado)."""
        auth = JWTAuthentication()
        user_auth = auth.authenticate(request)
        if not user_auth:
            return Response(
                {'error': 'Autenticação necessária.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        user = user_auth[0]
        
        # Precisamos do restaurante_id. Podemos passar via query_params ou no body
        restaurante_id = request.query_params.get('restaurante_id') or request.data.get('restaurante_id')
        if not restaurante_id:
            return Response(
                {'error': 'restaurante_id é obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        service = ReviewService()
        try:
            service.delete_review(
                customer_id=str(user.id),
                restaurante_id=restaurante_id,
                review_id=review_id
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
