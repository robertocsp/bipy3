# -*- coding: utf-8 -*-
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.parsers import JSONParser
from rest_framework import views
from rest_framework.response import Response

from marvinpub.websocket import ws
from pedido.models import Pedido
from cliente.models import Cliente

import datetime
import json

class EnviarPedidoView(views.APIView):
    permission_classes = (IsAdminUser,)
    # permission_classes = (AllowAny,)
    parser_classes = (JSONParser,)

    def post(self, request, *args, **kwargs):
        #persistencia(request)
        cliente = request.data.get('id_loja', None)
        if cliente:
            websocket = ws.Websocket()
            websocket.publicar_mensagem(cliente, json.dumps(request.data))
            return Response({"success": True})
        else:
            return Response({"success": False})


def persistencia(request):
    if request.data.get('origem') == 'Telegram' or request.data.get('origem') == 'Facebook':
        origem = request.data.get('origem').lower()
        if request.data.get('origem') == 'Telegram':
            try:
                cliente = Cliente.objects.get(chave_telegram=request.data.get('id_cliente'))
            except Cliente.DoesNotExist:
                cliente = Cliente()
                cliente.nome = request.data.get('nome_cliente', None)
                cliente.chave_telegram = request.data.get('id_cliente', None)
                cliente.save()
        elif request.data.get('origem') == 'Facebook':
            try:
                cliente = Cliente.objects.get(chave_facebook=request.data.get('id_cliente'))
            except Cliente.DoesNotExist:
                cliente = Cliente()
                cliente.nome = request.data.get('nome_cliente', None)
                cliente.chave_facebook = request.data.get('id_cliente', None)
                cliente.save()
        pedido = Pedido()
        pedido.cliente = cliente
        pedido.historico = request.data.get('mensagem', None)
        pedido.data = datetime.datetime.now().strftime('%Y-%m-%d')
        pedido.hora = datetime.datetime.now().strftime('%H:%M:%S')
        pedido.origem = origem
        pedido.loja_id = request.data.get('id_loja', None)
        pedido.save()  # TODO tratar exceção
