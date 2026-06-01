"""
Authentication API views.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.authentication.serializers import (
    RegisterSerializer,
    LoginSerializer,
    GoogleOAuthSerializer,
    TokenRefreshSerializer,
    UpdateProfileSerializer,
    UpdatePasswordSerializer,
    AddressSerializer,
)
from apps.authentication.services import AuthService
from apps.core.authentication import JWTAuthentication
from apps.core.permissions import IsAuthenticated


class RegisterView(APIView):
    """POST /api/auth/register/ — Create a new user account."""

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = AuthService()
        try:
            result = service.register(**serializer.validated_data)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(result, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """POST /api/auth/login/ — Authenticate with email/password."""

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = AuthService()
        try:
            result = service.login(**serializer.validated_data)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(result, status=status.HTTP_200_OK)


class GoogleOAuthView(APIView):
    """POST /api/auth/google/ — Authenticate via Google OAuth 2.0."""

    def post(self, request):
        serializer = GoogleOAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = AuthService()
        try:
            result = service.google_oauth(**serializer.validated_data)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(result, status=status.HTTP_200_OK)


class TokenRefreshView(APIView):
    """POST /api/auth/refresh/ — Get a new access token."""

    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = AuthService()
        try:
            result = service.refresh_token(
                serializer.validated_data['refresh_token']
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(result, status=status.HTTP_200_OK)


class LogoutView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response(
            {'message': 'Logout realizado com sucesso.'},
            status=status.HTTP_200_OK,
        )


class MeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(request.user.to_dict(), status=status.HTTP_200_OK)


class ProfileUpdateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):
        serializer = UpdateProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = AuthService()
        try:
            result = service.update_profile(str(request.user.id), serializer.validated_data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class PasswordUpdateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):
        serializer = UpdatePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = AuthService()
        try:
            service.update_password(
                str(request.user.id),
                serializer.validated_data['senha_atual'],
                serializer.validated_data['nova_senha']
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': 'Senha atualizada com sucesso.'})


class AddressListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(request.user.to_dict().get('enderecos', []))

    def post(self, request):
        serializer = AddressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = AuthService()
        try:
            result = service.add_address(str(request.user.id), serializer.validated_data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_201_CREATED)


class AddressDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, index):
        service = AuthService()
        try:
            result = service.remove_address(str(request.user.id), int(index))
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)
