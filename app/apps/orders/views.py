"""
Views da API de Pedidos.

Refatorado:
- Verificações de ownership com exceções de domínio
- Sem cláusulas except genéricas
"""
from __future__ import annotations

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.core.authentication import JWTAuthentication
from apps.core.enums import StatusPedido, PerfilUsuario
from apps.core.permissions import IsAuthenticated
from apps.orders.serializers import (
    CriarPedidoSerializer,
    AtualizarStatusPedidoSerializer,
    ValidarCupomSerializer,
)
from apps.orders.services import ServicoPedido
from apps.restaurants.repositories import RepositorioRestaurante


class ListaPedidosView(APIView):
    """GET / POST /api/orders/"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Lista pedidos do usuário autenticado (cliente ou dono)."""
        servico = ServicoPedido()
        pagina = int(request.query_params.get('page', 1))
        usuario = request.user

        if usuario.papel == PerfilUsuario.CLIENTE:
            resultado = servico.listar_pedidos_cliente(str(usuario.id), pagina=pagina)
        else:
            restaurante_id = request.query_params.get('restaurant_id')
            if not restaurante_id:
                return Response(
                    {'error': 'restaurant_id é obrigatório.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            filtro_status = request.query_params.get('status')
            resultado = servico.listar_pedidos_restaurante(
                restaurante_id, filtro_status=filtro_status, pagina=pagina,
            )
        return Response(resultado)

    def post(self, request):
        """Cria um novo pedido (somente clientes)."""
        if request.user.papel != PerfilUsuario.CLIENTE:
            return Response(
                {'error': 'Apenas clientes podem criar pedidos.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = CriarPedidoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        servico = ServicoPedido()
        resultado = servico.criar_pedido(
            cliente_id=str(request.user.id),
            dados=serializer.validated_data,
        )
        return Response(resultado, status=status.HTTP_201_CREATED)


class DetalhePedidoView(APIView):
    """GET /api/orders/:id/"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        servico = ServicoPedido()
        resultado = servico.buscar_pedido(order_id)
        if not resultado:
            return Response(
                {'error': 'Pedido não encontrado.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Verificação de ownership
        if request.user.papel == PerfilUsuario.CLIENTE:
            if str(resultado['cliente_id']) != str(request.user.id):
                return Response(
                    {'error': 'Acesso negado.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
        elif request.user.papel == PerfilUsuario.DONO:
            repo = RepositorioRestaurante()
            restaurante = repo.buscar_por_id_e_dono(resultado['restaurante_id'], str(request.user.id))
            if not restaurante:
                return Response(
                    {'error': 'Acesso negado.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        return Response(resultado)


class StatusPedidoView(APIView):
    """PATCH /api/orders/:id/status/"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, order_id):
        serializer = AtualizarStatusPedidoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        servico = ServicoPedido()

        # Buscar pedido para verificação de permissão
        pedido = servico.buscar_pedido(order_id)
        if not pedido:
            return Response(
                {'error': 'Pedido não encontrado.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        novo_status = serializer.validated_data['status']

        # Verificação de permissão por perfil
        if request.user.papel == PerfilUsuario.CLIENTE:
            if str(pedido['cliente_id']) != str(request.user.id):
                return Response({'error': 'Acesso negado.'}, status=status.HTTP_403_FORBIDDEN)
            if novo_status != StatusPedido.CANCELADO:
                return Response(
                    {'error': 'Clientes só podem cancelar pedidos.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
        elif request.user.papel == PerfilUsuario.DONO:
            repo = RepositorioRestaurante()
            restaurante = repo.buscar_por_id_e_dono(pedido['restaurante_id'], str(request.user.id))
            if not restaurante:
                return Response({'error': 'Acesso negado.'}, status=status.HTTP_403_FORBIDDEN)

        resultado = servico.atualizar_status(
            pedido_id=order_id,
            novo_status=novo_status,
            alterado_por=str(request.user.id),
            motivo=serializer.validated_data.get('motivo_cancelamento'),
        )
        return Response(resultado)


class ValidarCupomView(APIView):
    """POST /api/orders/validate-coupon/"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ValidarCupomSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        servico = ServicoPedido()
        resultado = servico.validar_cupom(
            serializer.validated_data['restaurante_id'],
            serializer.validated_data['codigo'],
            float(serializer.validated_data['total_carrinho']),
        )
        return Response(resultado)
