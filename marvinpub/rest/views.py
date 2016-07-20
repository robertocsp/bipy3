# -*- coding: utf-8 -*-
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.parsers import JSONParser
from rest_framework import views
from rest_framework.response import Response

from marvinpub.websocket import ws
from pedido.models import Pedido
from cliente.models import Cliente

import datetime

class EnviarPedidoView(views.APIView):
    # Guly, troquei para AllowAny por enquanto. (rfh)
    # permission_classes = (IsAdminUser,)
    permission_classes = (AllowAny,)
    parser_classes = (JSONParser,)

    def post(self, request, *args, **kwargs):
        cliente = request.data.get('cliente', None)
        mensagem = request.data.get('mensagem', None)
        persistencia(request)
        if mensagem:
            websocket = ws.Websocket()
            websocket.publicar_mensagem(cliente, mensagem)
            return Response({"success": True})
        else:
            return Response({"success": False})


def persistencia(request):
    if request.data.get('origem') == 'Telegram':
        try:
            cliente = Cliente.objects.get(chave_telegram=request.data.get('id_cliente'))
        except Cliente.DoesNotExist:
            cliente = Cliente()
            cliente.nome = request.data.get('nome_cliente', None)
            cliente.chave_telegram = request.data.get('id_cliente', None)
            cliente.save()

        pedido = Pedido()
        pedido.cliente = cliente
        pedido.historico = request.data.get('mensagem', None)
        pedido.data = datetime.datetime.now().strftime('%Y-%m-%d')
        pedido.hora = datetime.datetime.now().strftime('%H:%M:%S')
        pedido.origem = 'telegram'
        pedido.loja_id = request.data.get('id_loja', None)
        pedido.save() # TODO tratar exceção
