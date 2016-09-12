# -*- coding: utf-8 -*-
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.parsers import JSONParser
from rest_framework import views, status
from rest_framework.response import Response

from bipy3.websocket import ws
from pedido.models import Pedido, ItemPedido
from cliente.models import Cliente
from loja.models import Loja
from bipy3.forms import LoginForm

from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.db.models import Max, Q

from datetime import datetime, timedelta, date
import json
import logging
import requests

logger = logging.getLogger('django')


class LoginView(views.APIView):
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        form = LoginForm(request.POST)
        if form.is_valid():
            username = request.POST['username']
            senha = request.POST['senha']
            user = authenticate(username=username, password=senha)
            if user is not None:
                lojas = user.groups.all()
                if len(lojas) == 0:
                    logout(request)
                    return Response({"success": False, "type": 401, "message": u'Usuário sem acesso a qualquer loja.'},
                                    status=status.HTTP_401_UNAUTHORIZED)
                elif len(lojas) == 1:
                    try:
                        loja = Loja.objects.get(group=lojas[0].id)
                        login(request, user)
                        request.session['id_loja'] = loja.id
                        request.session['id_fb_loja'] = loja.id_loja_facebook
                        redirect = '/pedidos/'
                        if 'next' in request.POST:
                            redirect = '/' + request.POST['next']
                        return Response({"success": True, "redirect": redirect})
                    except Loja.DoesNotExist:
                        logout(request)
                        return Response(
                            {"success": False, "type": 401, "message": u'Usuário sem acesso a qualquer loja.'},
                            status=status.HTTP_401_UNAUTHORIZED)
                logout(request)
                lojas_resultado = []
                for loja in lojas:
                    lojas_resultado.append({"id": loja.id, "nome": loja.name})
                return Response({"success": True, "lojas": lojas_resultado})
            else:
                return Response({"success": False, "type": 403, "message": u'Usuário e/ou senha inválido(s).'},
                                status=status.HTTP_403_FORBIDDEN)
        return Response({"success": False, "type": 400, "message": u'Usuário e senha são campos obrigatórios.'},
                        status=status.HTTP_400_BAD_REQUEST)


class EnviarPedidoView(views.APIView):
    authentication_classes = (BasicAuthentication,)
    permission_classes = (IsAdminUser,)
    parser_classes = (JSONParser,)

    def post(self, request, *args, **kwargs):
        try:
            loja = Loja.objects.get(id_loja_facebook=request.data.get('id_loja'))
        except Loja.DoesNotExist:
            logger.error('-=-=-=-=-=-=-=- loja inexistente para facebook page_id: ' +
                         repr(request.data.get('id_loja')))
            return Response({"success": False})
        with transaction.atomic():
            data_hora_pedido = datetime.now()
            data_pedido = date.today()
            max_numero_pedido = Pedido.objects.select_for_update()\
                .filter(loja=loja.id, data=data_pedido) \
                .aggregate(Max('numero'))
            logger.debug('-=-=-=-=-=-=-=- num pedido 1: ' + repr(max_numero_pedido))
            if max_numero_pedido.get('numero__max'):
                numero_pedido = int(max_numero_pedido.get('numero__max'))
                numero_pedido += 1
            else:
                numero_pedido = 1
            logger.debug('-=-=-=-=-=-=-=- num pedido 2: ' + repr(numero_pedido))
            self.persistencia(request, numero_pedido, data_hora_pedido, loja.id)
        request.data['numero_pedido'] = numero_pedido
        request.data['card_uid'] = data_pedido.strftime('%Y%m%d') + repr(numero_pedido)
        logger.debug('-=-=-=-=-=-=-=- num pedido 3: ' + repr(request.data['numero_pedido']))
        if loja:
            websocket = ws.Websocket()
            websocket.publicar_mensagem(loja.id, json.dumps(request.data))
            return Response({"success": True})
        else:
            return Response({"success": False})

    def persistencia(self, request, numero_pedido, data_hora_pedido, loja_id):
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
            pedido.loja_id = loja_id
            pedido.status = 'solicitado'
            pedido.mesa = request.data.get('mesa', None)
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
        id_loja = request.session['id_loja']
        logger.debug('-=-=-=-=-=-=-=- uid: ' + repr(uid))
        logger.debug('-=-=-=-=-=-=-=- status: ' + repr(status))
        logger.debug('-=-=-=-=-=-=-=- id_loja: ' + repr(id_loja))
        data_pedido = datetime.strptime(uid[:8], '%Y%m%d')
        try:
            pedido = Pedido.objects.get(loja=id_loja, numero=int(uid[8:]), data=data_pedido)
        except Pedido.DoesNotExist:
            return Response({"success": False})
        except Pedido.MultipleObjectsReturned:
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
        data_pedido = datetime.strptime(uid[:8], '%Y%m%d')
        id_loja = request.session['id_loja']
        pedido = self.atualiza_historico(data_pedido, numero, 'bot', request.data.get('message'), id_loja)
        if not pedido:
            return Response({"success": False})
        chave_facebook = pedido.cliente.chave_facebook
        logger.debug('-=-=-=-=-=-=-=- fb uid: ' + chave_facebook)
        data = {
            'entry': [
                {
                    'messaging': [
                        {
                            'sender': {
                                'id': chave_facebook
                            },
                            'dashboard': {
                                'message': request.data.get('message'),
                                'uid': uid
                            },
                            'recipient': {
                                'id': request.session['id_fb_loja']
                            }
                        }
                    ]
                }
            ]
        }
        url = 'https://localhost:5002/webhook'
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(data), headers=headers, verify=False)
        logger.debug('------======------- response: ' + repr(response))
        return Response({"success": True})

    def atualiza_historico(self, data_pedido, numero, ator, mensagem, loja_id):
        with transaction.atomic():
            pedido = Pedido.objects.select_for_update().filter(loja=loja_id, numero=numero, data=data_pedido)\
                .select_related('cliente')
            if not pedido:
                return None
            else:
                for um_pedido in pedido:
                    um_pedido.historico.append({ator: mensagem})
                    um_pedido.save()
                    return um_pedido


class EnviarMensagemBotView(views.APIView):
    authentication_classes = (BasicAuthentication,)
    permission_classes = (IsAdminUser,)

    def post(self, request, *args, **kwargs):
        try:
            loja = Loja.objects.get(id_loja_facebook=request.data.get('id_loja'))
        except Loja.DoesNotExist:
            logger.error('-=-=-=-=-=-=-=- loja inexistente para facebook page_id: ' +
                         repr(request.data.get('id_loja')))
            return Response({"success": False})
        uid = request.data.get('uid')
        logger.debug('-=-=-=-=-=-=-=- mensagem bot ' + repr(uid))
        data_pedido = datetime.strptime(uid[:8], '%Y%m%d')
        self.atualiza_historico(data_pedido, int(uid[8:]), 'cliente', request.data.get('cliente'), loja.id)
        if loja:
            websocket = ws.Websocket()
            websocket.publicar_mensagem(loja.id, json.dumps(request.data))
            return Response({"success": True})
        else:
            return Response({"success": False})

    def atualiza_historico(self, data_pedido, numero, ator, mensagem, loja_id):
        with transaction.atomic():
            pedido = Pedido.objects.select_for_update().filter(loja=loja_id, numero=numero, data=data_pedido)
            if not pedido:
                return None
            else:
                for um_pedido in pedido:
                    um_pedido.historico.append({ator: mensagem})
                    um_pedido.save()
                    return um_pedido


class TrocarMesaView(views.APIView):
    authentication_classes = (BasicAuthentication,)
    permission_classes = (IsAdminUser,)

    def post(self, request, *args, **kwargs):
        try:
            loja = Loja.objects.get(id_loja_facebook=request.data.get('id_loja'))
        except Loja.DoesNotExist:
            logger.error('-=-=-=-=-=-=-=- loja inexistente para facebook page_id: ' +
                         repr(request.data.get('id_loja')))
            return Response({"success": False})
        try:
            cliente = Cliente.objects.get(chave_facebook=request.data.get('id_cliente'))
        except Cliente.DoesNotExist:
            logger.error('-=-=-=-=-=-=-=- cliente inexistente para facebook id: ' +
                         repr(request.data.get('id_cliente')))
            return Response({"success": False})
        data_corte = datetime.now() + timedelta(hours=-3)
        pedidos = Pedido.objects.filter(
            Q(loja=loja.id, cliente=cliente.id),
            Q(data__gt=data_corte.date()) | Q(data=data_corte.date(), hora__gte=data_corte.time()))
        if pedidos:
            pedidos_payload = []
            mesa = request.data.get('mesa')
            for pedido in pedidos:
                pedido.mesa = mesa
                pedido.save()
                pedidos_payload.append({'uid': pedido.data.strftime('%Y%m%d') + repr(int(pedido.numero)),
                                        'mesa': mesa})
            payload = {'origem': 'troca_mesa', 'pedidos': pedidos_payload, 'nome_cliente': cliente.nome,
                       'foto_cliente': cliente.foto, 'mesa': mesa}
            mesa_anterior = request.data.get('mesa_anterior', None)
            if mesa_anterior:
                payload['mesa_anterior'] = mesa_anterior
            websocket = ws.Websocket()
            websocket.publicar_mensagem(loja.id, json.dumps(payload))
        return Response({"success": True})


class PedirCardapioView(views.APIView):
    authentication_classes = (BasicAuthentication,)
    permission_classes = (IsAdminUser,)

    def post(self, request, *args, **kwargs):
        try:
            loja = Loja.objects.get(id_loja_facebook=request.data.get('id_loja'))
        except Loja.DoesNotExist:
            logger.error('-=-=-=-=-=-=-=- loja inexistente para facebook page_id: ' +
                         repr(request.data.get('id_loja')))
            return Response({"success": False})
        payload = {'origem': 'cardapio', 'nome_cliente': request.data.get('nome_cliente'),
                   'mesa': request.data.get('mesa')}
        foto = request.data.get('foto_cliente', None)
        if foto:
            payload['foto_cliente'] = foto
        websocket = ws.Websocket()
        websocket.publicar_mensagem(loja.id, json.dumps(payload))
        return Response({"success": True})
