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
from notificacao.models import Notificacao
from bipy3.forms import LoginForm

from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.db.models import Max, Q

from datetime import datetime, timedelta, date
import json
import logging
import requests
import os

logger = logging.getLogger('django')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
with open(os.path.join(os.path.join(BASE_DIR, 'bipy3_conf'), 'keys.txt')) as keys_file:
    for line in keys_file:
        key_value_pair = line.strip().split('=')
        if key_value_pair[0] == 'api-secret':
            CHAVE_BOT_API_INTERNA = key_value_pair[1]
            break


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
                        request.session['nome_loja'] = loja.nome
                        redirect = '/pedidos/'
                        if 'next' in request.POST:
                            redirect = request.POST['next']
                            if redirect[0] != '/':
                                redirect = '/' + redirect
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


def valida_chamada_interna(request):
    if 'chave_bot_api_interna' not in request.data or \
                    request.data.get('chave_bot_api_interna') != CHAVE_BOT_API_INTERNA:
        return Response({"success": False, "type": 400, "message": u'Chamada inválida.'},
                        status=status.HTTP_400_BAD_REQUEST)
    return None


class AdicionarClienteView(views.APIView):
    authentication_classes = (BasicAuthentication,)
    permission_classes = (IsAdminUser,)
    parser_classes = (JSONParser,)

    def post(self, request, *args, **kwargs):
        nao_valido = valida_chamada_interna(request)
        if nao_valido:
            return nao_valido
        try:
            cliente = Cliente.objects.get(chave_facebook=request.data.get('id_cliente'))
        except Cliente.DoesNotExist:
            cliente = Cliente()
            cliente.chave_facebook = request.data.get('id_cliente')
        cliente.nome = request.data.get('nome_cliente', None)
        cliente.foto = request.data.get('foto_cliente', None)
        cliente.save()
        return Response({"success": True})


class EnviarPedidoView(views.APIView):
    authentication_classes = (BasicAuthentication,)
    permission_classes = (IsAdminUser,)
    parser_classes = (JSONParser,)

    def post(self, request, *args, **kwargs):
        nao_valido = valida_chamada_interna(request)
        if nao_valido:
            return nao_valido
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
            cliente_id = self.persistencia(request, numero_pedido, data_hora_pedido, loja.id)
        request.data['numero_pedido'] = numero_pedido
        request.data['card_uid'] = data_pedido.strftime('%Y%m%d') + repr(numero_pedido)
        logger.debug('-=-=-=-=-=-=-=- num pedido 3: ' + repr(request.data['numero_pedido']))
        if loja and cliente_id is not None:
            del request.data['id_loja']
            del request.data['id_cliente']
            del request.data['chave_bot_api_interna']
            notificacao_uuid = salva_notificacao(request.data, loja.id, cliente_id)
            request.data['notificacao_uuid'] = str(cliente_id) + '_' + str(loja.id) + '_' + str(notificacao_uuid)
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
            return cliente.id
        return None


class StatusPedidoView(views.APIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        if 'id_loja' not in request.session:
            return Response({"success": False, "type": 403, "message": u'Sessão inválida.'},
                            status=status.HTTP_403_FORBIDDEN)
        uid = request.data.get('uid')
        status_loja = request.data.get('status')
        id_loja = request.session['id_loja']
        logger.debug('-=-=-=-=-=-=-=- uid: ' + repr(uid))
        logger.debug('-=-=-=-=-=-=-=- status: ' + repr(status_loja))
        logger.debug('-=-=-=-=-=-=-=- id_loja: ' + repr(id_loja))
        data_pedido = datetime.strptime(uid[:8], '%Y%m%d')
        try:
            pedido = Pedido.objects.get(loja=id_loja, numero=int(uid[8:]), data=data_pedido)
        except Pedido.DoesNotExist:
            return Response({"success": False})
        except Pedido.MultipleObjectsReturned:
            return Response({"success": False})
        if status_loja == 'solicitado':
            pedido.status = 'solicitado'
        elif status_loja == 'em-processo':
            pedido.status = 'emprocessamento'
        elif status_loja == 'concluido':
            pedido.status = 'concluido'
        elif status_loja == 'entregue':
            pedido.status = 'entregue'
        elif status_loja == 'cancelado':
            pedido.status = 'cancelado'
        pedido.save()
        return Response({"success": True})


class EnviarMensagemView(views.APIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        if 'id_loja' not in request.session:
            return Response({"success": False, "type": 403, "message": u'Sessão inválida.'},
                            status=status.HTTP_403_FORBIDDEN)
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
                    if not um_pedido.historico:
                        um_pedido.historico = []
                    um_pedido.historico.append({ator: mensagem})
                    um_pedido.save()
                    return um_pedido


class EnviarMensagemBotView(views.APIView):
    authentication_classes = (BasicAuthentication,)
    permission_classes = (IsAdminUser,)

    def post(self, request, *args, **kwargs):
        nao_valido = valida_chamada_interna(request)
        if nao_valido:
            return nao_valido
        try:
            loja = Loja.objects.get(id_loja_facebook=request.data.get('id_loja'))
        except Loja.DoesNotExist:
            logger.error('-=-=-=-=-=-=-=- loja inexistente para facebook page_id: ' +
                         repr(request.data.get('id_loja')))
            return Response({"success": False})
        try:
            cliente = Cliente.objects.get(chave_facebook=request.data.get('id_cliente'))
        except Cliente.DoesNotExist:
            logger.error('-=-=-=-=-=-=-=- usuario inexistente para facebook user_id: ' +
                         repr(request.data.get('id_cliente')))
            return Response({"success": False})
        uid = request.data.get('uid')
        logger.debug('-=-=-=-=-=-=-=- mensagem bot ' + repr(uid))
        data_pedido = datetime.strptime(uid[:8], '%Y%m%d')
        self.atualiza_historico(data_pedido, int(uid[8:]), 'cliente', request.data.get('cliente'), loja.id)
        if loja:
            del request.data['id_loja']
            del request.data['id_cliente']
            del request.data['chave_bot_api_interna']
            notificacao_uuid = salva_notificacao(request.data, loja.id, cliente.id)
            request.data['notificacao_uuid'] = str(cliente.id) + '_' + str(loja.id) + '_' + str(notificacao_uuid)
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
        nao_valido = valida_chamada_interna(request)
        if nao_valido:
            return nao_valido
        try:
            loja = Loja.objects.get(id_loja_facebook=request.data.get('id_loja'))
        except Loja.DoesNotExist:
            logger.error('-=-=-=-=-=-=-=- loja inexistente para facebook page_id: ' +
                         repr(request.data.get('id_loja')))
            return Response({"success": False})
        try:
            cliente = Cliente.objects.get(chave_facebook=request.data.get('id_cliente'))
        except Cliente.DoesNotExist:
            logger.error('-=-=-=-=-=-=-=- cliente inexistente para facebook user_id: ' +
                         repr(request.data.get('id_cliente')))
            return Response({"success": False})
        mesa_anterior = request.data.get('mesa_anterior', None)
        pedidos_payload = []
        data_corte = datetime.now() + timedelta(hours=-3)
        if mesa_anterior:
            pedidos = Pedido.objects.filter(
                Q(loja=loja.id, cliente=cliente.id, mesa=mesa_anterior),
                Q(data__gt=data_corte.date()) | Q(data=data_corte.date(), hora__gte=data_corte.time()))\
                .order_by('-data', '-hora')
            if pedidos:
                mesa = request.data.get('mesa')
                for pedido in pedidos:
                    pedido.mesa = mesa
                    pedido.save()
                    pedidos_payload.append({'uid': pedido.data.strftime('%Y%m%d') + repr(int(pedido.numero)),
                                            'mesa': mesa})
        notificacoes = Notificacao.objects.filter(loja=loja.id, cliente=cliente.id, dt_visto__isnull=True)
        notificacoes_payload = []
        if notificacoes:
            mesa = request.data.get('mesa')
            for notificacao in notificacoes:
                notificacao.info['mesa'] = mesa
                notificacao.save()
                notificacoes_payload.append({'notificacao_uuid': str(notificacao.cliente_id) + '_' +
                                            str(notificacao.loja_id) + '_' +
                                            str(notificacao.uuid)})
        if pedidos or notificacoes:
            payload = {'origem': 'troca_mesa', 'pedidos': pedidos_payload, 'nome_cliente': cliente.nome,
                       'foto_cliente': cliente.foto, 'mesa': mesa, 'notificacoes': notificacoes_payload}
            if mesa_anterior:
                payload['mesa_anterior'] = mesa_anterior
                notificacao_uuid = salva_notificacao(payload, loja.id, cliente.id)
                payload['notificacao_uuid'] = str(cliente.id) + '_' + str(loja.id) + '_' + str(notificacao_uuid)
            websocket = ws.Websocket()
            websocket.publicar_mensagem(loja.id, json.dumps(payload))
        return Response({"success": True})


class PedirCardapioView(views.APIView):
    authentication_classes = (BasicAuthentication,)
    permission_classes = (IsAdminUser,)

    def post(self, request, *args, **kwargs):
        return gera_notificacao(request, 'cardapio')


class ChamarGarcomView(views.APIView):
    authentication_classes = (BasicAuthentication,)
    permission_classes = (IsAdminUser,)

    def post(self, request, *args, **kwargs):
        return gera_notificacao(request, 'garcom')


class PedirContaView(views.APIView):
    authentication_classes = (BasicAuthentication,)
    permission_classes = (IsAdminUser,)

    def post(self, request, *args, **kwargs):
        return gera_notificacao(request, 'conta')


def gera_notificacao(request, origem):
    nao_valido = valida_chamada_interna(request)
    if nao_valido:
        return nao_valido
    logger.debug('-=-=-=- 1 -=-=-=-')
    try:
        loja = Loja.objects.get(id_loja_facebook=request.data.get('id_loja'))
    except Loja.DoesNotExist:
        logger.error('-=-=-=-=-=-=-=- loja inexistente para facebook page_id: ' +
                     repr(request.data.get('id_loja')))
        return Response({"success": False})
    logger.debug('-=-=-=- 2 -=-=-=-')
    try:
        cliente = Cliente.objects.get(chave_facebook=request.data.get('id_cliente'))
    except Cliente.DoesNotExist:
        logger.error('-=-=-=-=-=-=-=- usuario inexistente para facebook user_id: ' +
                     repr(request.data.get('id_cliente')))
        return Response({"success": False})
    logger.debug('-=-=-=- 3 -=-=-=-')
    payload = {'origem': origem, 'nome_cliente': request.data.get('nome_cliente'),
               'mesa': request.data.get('mesa')}
    foto = request.data.get('foto_cliente', None)
    if foto:
        payload['foto_cliente'] = foto
    logger.debug('-=-=-=- 4 -=-=-=-')
    notificacao_uuid = salva_notificacao(payload, loja.id, cliente.id)
    payload['notificacao_uuid'] = str(cliente.id) + '_' + str(loja.id) + '_' + str(notificacao_uuid)
    websocket = ws.Websocket()
    websocket.publicar_mensagem(loja.id, json.dumps(payload))
    return Response({"success": True})


def salva_notificacao(payload, loja_id, cliente_id):
    notificacao = Notificacao()
    notificacao.loja_id = loja_id
    notificacao.cliente_id = cliente_id
    notificacao.info = payload
    notificacao.save()
    return notificacao.uuid


class NotificacaoLidaView(views.APIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        if 'id_loja' not in request.session:
            return Response({"success": False, "type": 403, "message": u'Sessão inválida.'},
                            status=status.HTTP_403_FORBIDDEN)
        notificacao_uuid = request.data.get('notificacao_uuid')
        dados = notificacao_uuid.split('_', 2)
        id_loja = request.session['id_loja']
        logger.debug('-=-=-=-=-=-=-=- id loja sessao: ' + str(id_loja))
        logger.debug('-=-=-=-=-=-=-=- id loja dashboard: ' + dados[1])
        if dados[1] != str(id_loja):
            return Response({"success": False, "type": 400, "message": u'Dados inválidos.'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            notificacao = Notificacao.objects.get(uuid=dados[2], loja=id_loja, cliente=dados[0])
            notificacao.dt_visto = datetime.today()
            notificacao.save()
        except Notificacao.DoesNotExist:
            logger.error('-=-=-=-=-=-=-=- notificação inexistente para uuid: ' + notificacao_uuid)
            return Response({"success": False})
        return Response({"success": True})
