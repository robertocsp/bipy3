# -*- coding: utf-8 -*-
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.parsers import JSONParser
from rest_framework import views
from rest_framework.response import Response

from marvinpub.websocket import ws
from pedido.models import Pedido, ItemPedido
from cliente.models import Cliente

from django.db import transaction
from django.db.models import Max

import datetime
import json
import logging

logger = logging.getLogger('django')


class EnviarPedidoView(views.APIView):
    authentication_classes = (BasicAuthentication,)
    permission_classes = (IsAdminUser,)
    parser_classes = (JSONParser,)

    def post(self, request, *args, **kwargs):
        with transaction.atomic():
            cliente = request.data.get('id_loja', None)
            data_hora_pedido = datetime.datetime.now()
            data_pedido = datetime.date.today()
            max_numero_pedido = Pedido.objects.select_for_update()\
                .filter(loja=cliente, data=data_pedido) \
                .aggregate(Max('numero'))
            logger.debug('-=-=-=-=-=-=-=- num pedido 1: ' + repr(max_numero_pedido))
            if max_numero_pedido.get('numero__max'):
                numero_pedido = int(max_numero_pedido.get('numero__max'))
                numero_pedido += 1
            else:
                numero_pedido = 1
            logger.debug('-=-=-=-=-=-=-=- num pedido 2: ' + repr(numero_pedido))
            persistencia(request, numero_pedido, data_hora_pedido)
        request.data['numero_pedido'] = numero_pedido
        request.data['card_uid'] = data_pedido.strftime('%Y%m%d') + repr(numero_pedido)
        logger.debug('-=-=-=-=-=-=-=- num pedido 3: ' + repr(request.data['numero_pedido']))
        if cliente:
            websocket = ws.Websocket()
            websocket.publicar_mensagem(cliente, json.dumps(request.data))
            return Response({"success": True})
        else:
            return Response({"success": False})


def persistencia(request, numero_pedido, data_hora_pedido):
    if request.data.get('origem') == 'Telegram' or request.data.get('origem') == 'fbmessenger':
        origem = request.data.get('origem').lower()
        if request.data.get('origem') == 'Telegram':
            try:
                cliente = Cliente.objects.get(chave_telegram=request.data.get('id_cliente'))
            except Cliente.DoesNotExist:
                cliente = Cliente()
                cliente.nome = request.data.get('nome_cliente', None)
                cliente.chave_telegram = request.data.get('id_cliente', None)
                cliente.save()
        elif request.data.get('origem') == 'fbmessenger':
            try:
                cliente = Cliente.objects.get(chave_facebook=request.data.get('id_cliente'))
            except Cliente.DoesNotExist:
                cliente = Cliente()
                cliente.nome = request.data.get('nome_cliente', None)
                cliente.chave_facebook = request.data.get('id_cliente', None)
                cliente.foto = request.data.get('foto_cliente', None)
                cliente.save()
        pedido = Pedido()
        pedido.numero = numero_pedido
        pedido.cliente = cliente
        pedido.historico = request.data.get('mensagem', None)
        pedido.data = data_hora_pedido.strftime('%Y-%m-%d')
        pedido.hora = data_hora_pedido.strftime('%H:%M:%S')
        pedido.origem = origem
        pedido.loja_id = request.data.get('id_loja', None)
        pedido.status = 'solicitado'
        pedido.save()  # TODO tratar exceção
        itens_pedido = request.data.get('itens_pedido', None)
        for item in itens_pedido:
            item_pedido = ItemPedido()
            item_pedido.pedido = pedido
            item_pedido.produto = item['descricao']
            item_pedido.quantidade = item['quantidade']
            item_pedido.save()


class StatusPedidoView(views.APIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        uid = request.data.get('uid')
        status = request.data.get('status')
        logger.debug('-=-=-=-=-=-=-=- uid: ' + repr(uid))
        logger.debug('-=-=-=-=-=-=-=- status: ' + repr(status))
        data_pedido = datetime.datetime.strptime(uid[:8], '%Y%m%d')
        try:
            pedido = Pedido.objects.get(numero=int(uid[8:]), data=data_pedido)
        except Pedido.DoesNotExist:
            # no employee found
            return Response({"success": False})
        except Pedido.MultipleObjectsReturned:
            # what to do if multiple employees have been returned?
            return Response({"success": False})
        if status == 'solicitado':
            pedido.status = 'solicitado'
        elif status == 'em-processo':
            pedido.status = 'emprocessamento'
        elif status == 'concluido':
            pedido.status = 'concluido'
        elif status == 'entregue':
            pedido.status = 'entregue'
        elif status == 'cancelado':
            pedido.status = 'cancelado'
        pedido.save()
        return Response({"success": True})


class EnviarMensagemView(views.APIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        uid = request.data.get('uid')
        numero = int(uid[8:])
        data_pedido = datetime.datetime.strptime(uid[:8], '%Y%m%d')
        pedido = Pedido.objects\
            .filter(numero=numero, data=data_pedido)\
            .select_related('cliente')
        for um_pedido in pedido:
            chave_facebook = um_pedido.cliente.chave_facebook
            logger.debug('-=-=-=-=-=-=-=- fb uid: ' + chave_facebook)
        data = {}
        # TODO enviar mensagem para cliente
        return Response({"success": True})
