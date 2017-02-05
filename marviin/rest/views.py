# -*- coding: utf-8 -*-
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.parsers import JSONParser
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework import views, status
from rest_framework.response import Response

from marviin.websocket import ws
from pedido.models import Pedido, ItemPedido
from cliente.models import Cliente
from loja.models import Loja, Questionario, Apps, DemoSms, DemoEmail
from notificacao.models import Notificacao
from fb_acesso.models import Fb_acesso
from pedido.templatetags.pedido_tags import minutos_passados
from upload_cardapio.models import Cardapio
from estados.models import Estado
from cidades.models import Cidade
from marviin.cliente_marviin.models import Endereco, Facebook
from marviin.user_profile.models import Profile
from marviin.forms import LoginForm
from utils.helper import *
from utils.auth import check_valid_login
from utils.aescipher import AESCipher
from pesquisa.models import Recomendar

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User, Group
from django.db import transaction
from django.db.models import Max, Q
from django.conf import settings
from django.http import HttpResponse
from django.core.mail import EmailMessage
from django.core import signing

from string import Template
from datetime import datetime, timedelta, date
import json
import logging
import requests
import os
import codecs
import string
import random
import unicodedata
import base64

logger = logging.getLogger('django')


def fail_response(status_code, message):
    response = HttpResponse(json.dumps({"success": False, "type": status_code,
                                        "message": message}),
                            content_type='application/json')
    response.status_code = status_code
    return response


class LoginView(views.APIView):
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        form = LoginForm(request.POST)
        if form.is_valid():
            username = request.POST['username']
            senha = request.POST['senha']
            try:
                user_login = User.objects.get(email=username)
                if user_login.is_active:
                    user = authenticate(username=user_login.username, password=senha)
                else:
                    return fail_response(403, u'Usuário desabilitado.')
            except User.DoesNotExist:
                user = None
            if user is not None:
                lojas = Loja.objects.raw('select l.* from loja_loja l inner join auth_user_groups g '
                                         'on l.group_id = g.group_id where g.user_id = %s and exists (select 1 from '
                                         'loja_apps a where l.id = a.loja_id and a.ativa = 1) order by l.nome',
                                         [user.id])
                lojas_resultado = []
                for loja in lojas:
                    lojas_resultado.append({"id": loja.id, "nome": loja.nome})
                if len(lojas_resultado) == 0:
                    logout(request)
                    return fail_response(401, u'Usuário sem acesso a qualquer loja.')
                elif len(lojas_resultado) == 1:
                    login(request, user)
                    request.session['id_loja'] = lojas[0].id
                    request.session['nome_loja'] = lojas[0].nome
                    apps = Apps.objects.filter(loja_id=lojas[0].id)
                    loja_apps = []
                    for app in apps:
                        loja_apps.append(app.app)
                    if len(loja_apps) == 0:
                        return fail_response(500, u'Desculpe, mas ocorreu um erro inesperado, por favor tente '
                                                  u'novamente, obrigado.')
                    request.session['loja_apps'] = loja_apps
                    redirect = '/pedidos/'
                    if 'next' in request.POST:
                        redirect = request.POST['next']
                        if redirect[0] != '/':
                            redirect = '/' + redirect
                    return Response({"success": True, "redirect": redirect})
                logout(request)
                return Response({"success": True, "lojas": lojas_resultado})
            else:
                return fail_response(403, u'Usuário e/ou senha inválido(s).')
        return fail_response(400, u'Usuário e senha são campos obrigatórios.')


def valida_chamada_interna(request):
    if 'chave_bot_api_interna' in request.data:
        chave_bot_api_interna = request.data.get('chave_bot_api_interna')
    elif 'chave_bot_api_interna' in request.GET:
        chave_bot_api_interna = request.GET['chave_bot_api_interna']
    elif 'chave_bot_api_interna' in request.POST:
        chave_bot_api_interna = request.POST['chave_bot_api_interna']
    else:
        chave_bot_api_interna = None
    if chave_bot_api_interna is None or chave_bot_api_interna != settings.CHAVE_BOT_API_INTERNA:
        return Response({"success": False, "type": 400, "message": u'Chamada inválida.'},
                        status=status.HTTP_400_BAD_REQUEST)
    return None


class PesquisaRecomendarView(views.APIView):
    authentication_classes = (BasicAuthentication,)
    permission_classes = (IsAdminUser,)

    def post(self, request):
        nao_valido = valida_chamada_interna(request)
        if nao_valido:
            return nao_valido
        pesquisa_recomendar = Recomendar()
        pesquisa_recomendar.app = request.data.get('app', None)
        pesquisa_recomendar.loja_id = request.data.get('id_loja', None)
        pesquisa_recomendar.cliente = request.data.get('id_cliente', None)
        pesquisa_recomendar.resposta = request.data.get('resposta', None)
        try:
            pesquisa_recomendar.save()
        except:
            logger.error('Nao foi possivel salvar a pesquisa:', exc_info=True)
        return Response({"success": True})


class ClienteView(views.APIView):
    authentication_classes = (BasicAuthentication,)
    permission_classes = (IsAdminUser,)
    parser_classes = (JSONParser,)

    def post(self, request):
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
        cliente.genero = request.data.get('genero', None)
        cliente.save()
        return Response({"success": True})


class ClienteTouchView(views.APIView):
    authentication_classes = (BasicAuthentication,)
    permission_classes = (IsAdminUser,)

    def post(self, request, fbpk=None):
        logger.debug('-=-=-=- 1 -=-=-=-' + repr(fbpk))
        nao_valido = valida_chamada_interna(request)
        if nao_valido:
            return nao_valido
        try:
            cliente = Cliente.objects.get(chave_facebook=fbpk)
            cliente.save()
        except Cliente.DoesNotExist:
            pass
        return Response({"success": True})


class PedidoChatView(views.APIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request, uid=None):
        if 'id_loja' not in request.session:
            return Response({"success": False, "type": 403, "message": u'Sessão inválida.'},
                            status=status.HTTP_403_FORBIDDEN)
        id_loja = request.session['id_loja']
        numero = int(uid[8:])
        data_pedido = datetime.strptime(uid[:8], '%Y%m%d')
        pedido = Pedido.objects.filter(loja=id_loja, numero=numero, data=data_pedido).select_related('cliente')
        if pedido:
            for um_pedido in pedido:
                minutos = minutos_passados(um_pedido.data, um_pedido.hora)
                pedido_chat = {'origem': um_pedido.origem, 'nome_cliente': um_pedido.cliente.nome, 'card_uid': uid,
                               'historico_mensagem': um_pedido.historico, 'foto_cliente': um_pedido.cliente.foto,
                               'minutos_passados': minutos,
                               'start': False if um_pedido.status == 'entregue' or um_pedido.status == 'cancelado'
                               else True}
                return Response({'success': True, 'chat': pedido_chat})
        else:
            return Response({'success': False})


def envia_sms_pedido(sms_id, loja_id, telefone, pedido, data_hora_pedido):
    data = {'sendSmsRequest': {}}
    data['sendSmsRequest']['from'] = 'Pedido Marviin'
    data['sendSmsRequest']['to'] = '55' + telefone
    data['sendSmsRequest']['schedule'] = data_hora_pedido.replace(microsecond=0).isoformat()
    data['sendSmsRequest']['msg'] = pedido
    data['sendSmsRequest']['callbackOption'] = 'FINAL'
    data['sendSmsRequest']['id'] = sms_id
    data['sendSmsRequest']['aggregateId'] = loja_id
    url = 'https://api-rest.zenvia360.com.br/services/send-sms'
    headers = {'content-type': 'application/json',
               'Authorization': 'Basic ' + base64.b64encode(
                   settings.SMS_USER + ':' + settings.SMS_PASSWORD)}
    logger.info('sms:: ' + repr(data))
    response = requests.post(url, data=json.dumps(data), headers=headers)
    logger.info(repr(response))


def envia_email_pedido(sms_id, loja_id, telefone, pedido, data_hora_pedido):
    pass


def monta_pedido_sms(request_data):
    descricao_pedido = None
    mesa = request_data.get('mesa', None)
    itens_pedido = request_data.get('itens_pedido', None)
    for item in itens_pedido:
        if descricao_pedido is None:
            descricao_pedido = u'Mesa ' + mesa
        descricao_pedido += u'\n' + str(item['quantidade']) + u': ' + item['descricao']
    return '' if descricao_pedido is None else descricao_pedido


class EnviarPedidoView(views.APIView):
    authentication_classes = (BasicAuthentication,)
    permission_classes = (IsAdminUser,)
    parser_classes = (JSONParser,)

    def post(self, request, *args, **kwargs):
        nao_valido = valida_chamada_interna(request)
        if nao_valido:
            return nao_valido
        try:
            loja = Loja.objects.get(pk=request.data.get('id_loja'))
        except Loja.DoesNotExist:
            logger.error('-=-=-=-=-=-=-=- loja inexistente para id: ' +
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
            del request.data['app']
            try:
                demosms = DemoSms.objects.get(loja=loja)
                if demosms.quantidade < 30:
                    envia_sms_pedido(str(loja.id) + '_' + request.data['card_uid'], str(loja.id),
                                     digitos(loja.telefone1), monta_pedido_sms(request.data), data_hora_pedido)
                    demosms.quantidade += 1
                    demosms.save()
            except DemoSms.DoesNotExist:
                pass
            try:
                demoemail = DemoEmail.objects.get(loja=loja)
                if demoemail.quantidade < 30:
                    envia_email_pedido(str(loja.id) + '_' + request.data['card_uid'], str(loja.id),
                                       digitos(loja.telefone1), monta_pedido_sms(request.data), data_hora_pedido)
                    demoemail.quantidade += 1
                    demoemail.save()
            except DemoEmail.DoesNotExist:
                pass
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
            pedido.app = request.data.get('app')
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
        status_pedido = request.data.get('status')
        id_loja = request.session['id_loja']
        logger.debug('-=-=-=-=-=-=-=- uid: ' + repr(uid))
        logger.debug('-=-=-=-=-=-=-=- status: ' + repr(status_pedido))
        logger.debug('-=-=-=-=-=-=-=- id_loja: ' + repr(id_loja))
        data_pedido = datetime.strptime(uid[:8], '%Y%m%d')
        try:
            pedido = Pedido.objects.get(loja=id_loja, numero=int(uid[8:]), data=data_pedido)
        except Pedido.DoesNotExist:
            return Response({"success": False})
        except Pedido.MultipleObjectsReturned:
            return Response({"success": False})
        response = {"success": True}
        if status_pedido == 'solicitado':
            pedido.status = 'solicitado'
            response['start'] = True
        elif status_pedido == 'em-processo':
            pedido.status = 'emprocessamento'
            response['start'] = True
        elif status_pedido == 'concluido':
            pedido.status = 'concluido'
            response['start'] = True
        elif status_pedido == 'entregue':
            pedido.status = 'entregue'
            response['stop'] = True
        elif status_pedido == 'cancelado':
            pedido.status = 'cancelado'
            response['stop'] = True
        pedido.save()
        response['origem'] = 'sync_status'
        response['uid'] = uid
        response['sync_uid'] = request.data.get('sync_uid')
        response['status_pedido'] = status_pedido
        websocket = ws.Websocket()
        websocket.publicar_mensagem(id_loja, json.dumps(response))
        return Response(response)


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
        try:
            chave_facebook = pedido.cliente.chave_facebook
        except AttributeError:
            if pedido is None:
                return fail_response(400, u'Pedido não encontrado.')
            elif pedido == 1:
                return fail_response(500, u'Não é possível enviar mensagem para um pedido realizado a mais de 24 '
                                          u'horas.')
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
                                'id': request.session['id_loja']
                            }
                        }
                    ]
                }
            ]
        }
        webhook_url = settings.FB_APPS[pedido.app]['webhook']
        headers = {'content-type': 'application/json'}
        response = requests.post(webhook_url, data=json.dumps(data), headers=headers, verify=False)
        logger.debug('------======------- response: ' + repr(response))
        response_ws = {'origem': 'sync_chat', 'uid': uid, 'sync_uid': request.data.get('sync_uid'),
                       'message': request.data.get('message')}
        websocket = ws.Websocket()
        websocket.publicar_mensagem(id_loja, json.dumps(response_ws))
        return Response({"success": True})

    def atualiza_historico(self, data_pedido, numero, ator, mensagem, loja_id):
        with transaction.atomic():
            pedido = Pedido.objects.select_for_update().filter(loja=loja_id, numero=numero, data=data_pedido)\
                .select_related('cliente').select_related('loja')
            if not pedido:
                return None
            else:
                for um_pedido in pedido:
                    data_hora_filtro = datetime.today() - timedelta(days=1)
                    data_hora_pedido = datetime.combine(um_pedido.data, um_pedido.hora)
                    logger.debug('-=-=-=-=-=-=-=- data e hora pedido: ' + repr(data_hora_pedido))
                    logger.debug('-=-=-=-=-=-=-=- data e hora filtro: ' + repr(data_hora_filtro))
                    if data_hora_pedido < data_hora_filtro:
                        logger.debug('-=-=-=-=-=-=-=- mais de 24 horas')
                        return 1
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
            loja = Loja.objects.get(pk=request.data.get('id_loja'))
        except Loja.DoesNotExist:
            logger.error('-=-=-=-=-=-=-=- loja inexistente para id: ' +
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


class LogOutMarviinView(views.APIView):
    authentication_classes = (BasicAuthentication,)
    permission_classes = (IsAdminUser,)

    def post(self, request, *args, **kwargs):
        nao_valido = valida_chamada_interna(request)
        if nao_valido:
            return nao_valido
        psid = request.data.get('psid')
        auth_code = request.data.get('auth_code')
        try:
            cliente = Cliente.objects.select_related('cliente_marviin').get(chave_facebook=psid)
        except Cliente.DoesNotExist:
            logger.error('-=-=-=-=-=-=-=- usuario nao encontrado, psid: ' + psid)
            return Response({"success": False})
        if cliente.cliente_marviin is None or cliente.cliente_marviin.authorization_code is None:
            logger.error('-=-=-=-=-=-=-=- usuario nao logado: ' + psid)
            return Response({"success": False})
        logger.debug('-=-=-=-=-=-=-=- auth code banco: ' + cliente.cliente_marviin.authorization_code)
        logger.debug('-=-=-=-=-=-=-=- auth code logout: ' + auth_code)
        if cliente.cliente_marviin.authorization_code.split('#')[0] == auth_code:
            cliente.cliente_marviin.authorization_code = None
            cliente.cliente_marviin.save()
            return Response({"success": True})
        else:
            logger.error('-=-=-=-=-=-=-=- authorization code invalido, psid: ' + psid)
            return Response({"success": False})


class LinkToMarviinView(views.APIView):
    authentication_classes = (BasicAuthentication,)
    permission_classes = (IsAdminUser,)

    def post(self, request, *args, **kwargs):
        nao_valido = valida_chamada_interna(request)
        if nao_valido:
            return nao_valido
        psid = request.data.get('psid')
        auth_code = request.data.get('auth_code')
        try:
            raw_auth_code = signing.loads(auth_code, max_age=300)  # max ages em segundos (5 minutos)
        except signing.BadSignature:
            logger.error('-=-=-=-=-=-=-=- codigo de autorizacao invalido, psid: ' + psid + '; auth_code: ' + auth_code)
            raw_auth_code = signing.loads(auth_code)
            try:
                cliente_marviin = Facebook.objects.get(authorization_code=auth_code + '#' + raw_auth_code)
                cliente_marviin.authorization_code = None
                cliente_marviin.save()
                add_cliente_marviin_cliente_fb(psid, cliente_marviin)
            except Facebook.DoesNotExist:
                pass
            return Response({"success": False})
        try:
            cliente_marviin = Facebook.objects.get(authorization_code=auth_code + '#' + raw_auth_code)
        except Facebook.DoesNotExist:
            logger.error(
                '-=-=-=-=-=-=-=- codigo de autorizacao nao encontrado, psid: ' + psid + '; auth_code: ' + auth_code +
                '; raw_auth_code: ' + raw_auth_code)
            return Response({"success": False})
        return add_cliente_marviin_cliente_fb(psid, cliente_marviin)


def add_cliente_marviin_cliente_fb(psid, cliente_marviin):
    try:
        cliente = Cliente.objects.get(chave_facebook=psid)
        cliente.cliente_marviin = cliente_marviin
        cliente.save()
    except Cliente.DoesNotExist:
        logger.error('-=-=-=-=-=-=-=- usuario nao encontrado, psid: ' + psid)
        return Response({"success": False})
    return Response({"success": True})


class CheckLoginValidView(views.APIView):
    authentication_classes = (BasicAuthentication,)
    permission_classes = (IsAdminUser,)

    def post(self, request, *args, **kwargs):
        nao_valido = valida_chamada_interna(request)
        if nao_valido:
            return nao_valido
        psid = request.data.get('psid')
        try:
            cliente = Cliente.objects.select_related('cliente_marviin').get(chave_facebook=psid)
        except Cliente.DoesNotExist:
            logger.error('-=-=-=-=-=-=-=- usuario nao encontrado, psid: ' + psid)
            return Response({"success": False})
        if cliente.cliente_marviin is None or cliente.cliente_marviin.authorization_code is None:
            logger.error('-=-=-=-=-=-=-=- usuario nao logado: ' + psid)
            return Response({"success": False})
        authorization_code = cliente.cliente_marviin.authorization_code.split('#')[0]
        try:
            signing.loads(authorization_code, max_age=600)  # max ages em segundos (10 minutos)
            return Response({"success": True})
        except signing.BadSignature:
            logger.error('-=-=-=-=-=-=-=- usuario com login efetuado a mais de 10 minutos: ' + psid)
            return Response({"success": False})


class EnderecoClienteView(views.APIView):
    permission_classes = (AllowAny,)

    def get(self, request, psid=None):
        valid, cliente = check_valid_login(request, psid, logger)
        if not valid:
            return fail_response(400, u'Desculpe, mas não consegui recuperar seus endereços, por favor, refaça o login '
                                      u'e tente novamente.')
        enderecos = Endereco.objects.filter(user=cliente.cliente_marviin.id, tipo=1).order_by('-padrao', 'endereco')
        enderecos_resultado = []
        if enderecos:
            for endereco in enderecos:
                logger.debug('-=-=-=- endereco::' + endereco.endereco)
                enderecos_resultado.append({"id": endereco.id, "endereco": endereco.endereco,
                                            "complemento": endereco.complemento, "bairro": endereco.bairro,
                                            "cep": endereco.cep, "estado": endereco.estado, "cidade": endereco.cidade,
                                            "padrao": endereco.padrao})
        return Response(enderecos_resultado)

    def post(self, request, psid=None):
        valid, cliente = check_valid_login(request, psid, logger)
        if not valid:
            return fail_response(400, u'Desculpe, não foi possível validar seus dados. Por favor, refaça o login e '
                                      u'tente novamente.')
        logger.debug('------======------- cliente.chave_facebook: ' + repr(cliente.chave_facebook))
        data = {
            'entry': [
                {
                    'messaging': [
                        {
                            'sender': {
                                'id': cliente.chave_facebook
                            },
                            'webview': {
                                'postload': 'endereco_selecionado',
                            },
                            'recipient': {
                                'id': '-'  # loja já tem que estar selecionada no bot
                            }
                        }
                    ]
                }
            ]
        }
        app = None  # TODO estará na sessão do cliente
        webhook_url = settings.FB_APPS[app]['webhook']
        headers = {'content-type': 'application/json'}
        response = requests.post(webhook_url, data=json.dumps(data), headers=headers, verify=False)
        logger.debug('------======------- response: ' + repr(response))
        return Response({"success": True})


class LojaView(views.APIView):
    permission_classes = (AllowAny,)

    def get(self, request, psidappid=None):
        resultado, psid, appid = self.valida_acesso(psidappid)
        if resultado is not None:
            return resultado
        if 'term' not in request.GET:
            return Response([]), None, None
        termo = request.GET['term']
        if len(termo) < 3:
            return Response([]), None, None
        lojas = Loja.objects.raw('select l.* from loja_loja l inner join loja_apps a '
                                 'on l.id = a.loja_id where a.ativa = 1 and a.app = %s and l.nome like %s '
                                 'order by l.nome', [appid, '%'+termo+'%'])
        lojas_resultado = []
        for loja in lojas:
            lojas_resultado.append({"value": loja.id, "label": loja.nome})
        return Response(lojas_resultado)

    def post(self, request, psidappid=None):
        resultado, psid, appid = self.valida_acesso(psidappid)
        if resultado is not None:
            return resultado
        if 'loja' not in request.POST:
            logger.error('------======------- loja invalida')
            return fail_response(400, u'Desculpe, não foi possível validar os dados. Por favor, saia e entre novamente '
                                      u'na página.')
        logger.debug('------======------- cliente.chave_facebook: ' + repr(psid))
        data = {
            'entry': [
                {
                    'messaging': [
                        {
                            'sender': {
                                'id': psid
                            },
                            'webview': {
                                'type': 'loja_selecionada',
                                'welcome_message': u'Olá $arg1, como posso ajudá-lo(a)?'
                            },
                            'recipient': {
                                'id': request.POST['loja']
                            }
                        }
                    ]
                }
            ]
        }
        webhook_url = settings.FB_APPS[appid]['webhook']
        headers = {'content-type': 'application/json'}
        response = requests.post(webhook_url, data=json.dumps(data), headers=headers, verify=False)
        logger.debug('------======------- response: ' + repr(response))
        return Response({"success": True})

    def valida_acesso(self, psidappid):
        if psidappid is None:
            logger.error('------======------- psidappid is None')
            return fail_response(400, u'Desculpe, não foi possível validar os dados. Por favor, saia e entre novamente '
                                      u'na página.'), None, None
        logger.debug('-=-=-=-=-=-=-=- key before :: ' + settings.SECRET_KEY[:32])
        key32 = '{: <32}'.format(settings.SECRET_KEY[:32]).encode("utf-8")
        logger.debug('-=-=-=-=-=-=-=- key after :: ' + key32)
        logger.debug('-=-=-=-=-=-=-=- enc psidappid :: ' + psidappid)
        n_psidappid = unicodedata.normalize('NFKD', psidappid).encode('ascii', 'ignore')
        cipher = AESCipher(key=key32)
        try:
            d_psidappid = cipher.decrypt(n_psidappid)
            logger.debug('-=-=-=-=-=-=-=- dec psidappid :: ' + d_psidappid)
        except TypeError:
            logger.error('-=-=-=-=-=-=-=- encrypt_psidappid invalido: ' + psidappid)
            return fail_response(400, u'Desculpe, não foi possível validar os dados. Por favor, saia e entre novamente '
                                      u'na página.'), None, None
        split_psidappid = d_psidappid.split('#')
        if len(split_psidappid) != 2:
            logger.error('-=-=-=-=-=-=-=- tamanho psidappid invalido: ' + repr(len(split_psidappid)))
            return fail_response(400, u'Desculpe, não foi possível validar os dados. Por favor, saia e entre novamente '
                                      u'na página.'), None, None
        psid = split_psidappid[0]
        appid = split_psidappid[1]
        try:
            Cliente.objects.get(chave_facebook=psid)
        except Cliente.DoesNotExist:
            logger.error('-=-=-=-=-=-=-=- cliente invalido: ' + psid)
            return fail_response(400, u'Desculpe, não foi possível validar os dados. Por favor, saia e entre novamente '
                                      u'na página.'), None, None
        return None, psid, appid


class TrocarMesaView(views.APIView):
    authentication_classes = (BasicAuthentication,)
    permission_classes = (IsAdminUser,)

    def post(self, request, *args, **kwargs):
        nao_valido = valida_chamada_interna(request)
        if nao_valido:
            return nao_valido
        try:
            loja = Loja.objects.get(pk=request.data.get('id_loja'))
        except Loja.DoesNotExist:
            logger.error('-=-=-=-=-=-=-=- loja inexistente para id: ' +
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
        pedidos = None
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
        loja = Loja.objects.get(pk=request.data.get('id_loja'))
    except Loja.DoesNotExist:
        logger.error('-=-=-=-=-=-=-=- loja inexistente para id: ' +
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


class AcessoBotV3View(views.APIView):
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        modulos = request.data.getlist('modulo')  # retorna um array
        logger.debug('-=-=-=-=-=-=-=- modulos: ' + repr(modulos))
        modulos_contratados = None
        for modulo in modulos:
            if modulo == 'indoor':
                if modulos_contratados is None:
                    modulos_contratados = u''
                else:
                    modulos_contratados += u', '
                modulos_contratados += u'Atendimento'
            elif modulo == 'delivery':
                if modulos_contratados is None:
                    modulos_contratados = u''
                else:
                    modulos_contratados += u', '
                modulos_contratados += u'Delivery'
            elif modulo == 'demoEmail':
                if modulos_contratados is None:
                    modulos_contratados = u''
                else:
                    modulos_contratados += u', '
                modulos_contratados += u'Demo E-mail'
            elif modulo == 'demoSMS':
                if modulos_contratados is None:
                    modulos_contratados = u''
                else:
                    modulos_contratados += u', '
                modulos_contratados += u'Demo SMS'
        if modulos_contratados is None:
            return fail_response(400, u'{"type": "mod", "object": "Não foi possível definir o produto contratado."}')
        modulos_contratados = rreplace(modulos_contratados, ',', ' e', 1)
        loja_existente = False
        possui_login = request.data.get('tipo_cadastro_usuario') == '1'
        cnpj = digitos(request.data.get('cnpj_estabelecimento'))
        try:
            loja = Loja.objects.get(cnpj=cnpj)
            loja_existente = True
        except Loja.DoesNotExist:
            loja = Loja()
        if not loja_existente and 'indoor' not in modulos:
            return fail_response(400, u'{"type": "mod", "object": "Para novos estabelecimentos é necessário a '
                                      u'contratação do módulo principal, o de Atendimento."}')
        if not possui_login and loja_existente:
            return fail_response(400, u'{"type": "loja", "object": "CNPJ já existe cadastrado em nosso sistema, por '
                                      u'favor utilize seu usuário e senha."}')
        nome = request.data.get('nome_dashboard')
        nome_estabelecimento = request.data.get('nome_estabelecimento')
        telefone1 = request.data.get('tel_estabelecimento')
        cnpj = cnpj
        cep = request.data.get('cep_estabelecimento')
        endereco = request.data.get('endereco_estabelecimento')
        complemento = request.data.get('complemento_estabelecimento')
        bairro = request.data.get('bairro_estabelecimento')
        estado = request.data.get('estado_estabelecimento')
        cidade = request.data.get('cidade_estabelecimento')
        if possui_login and not loja_existente and (nome_estabelecimento is None or telefone1 is None or
                                                    cnpj is None or cep is None or endereco is None or
                                                    bairro is None or estado is None or cidade is None or
                                                    nome is None):
            return fail_response(400, u'{"type": "loja", "object": "CNPJ não encontrado, por favor preencha os dados '
                                      u'do novo estabelecimento."}')
        if nome_estabelecimento is not None and telefone1 is not None and cnpj is not None and cep is not None and \
            endereco is not None and bairro is not None and estado is not None and cidade is not None and \
            nome is not None:
            loja.nome = nome
            loja.nome_estabelecimento = nome_estabelecimento
            loja.telefone1 = telefone1
            loja.cnpj = cnpj
            loja.cep = cep
            loja.endereco = endereco
            loja.complemento = complemento
            loja.bairro = bairro
            loja.estado = estado
            loja.cidade = cidade
        tipo = u'Novo estabelecimento' if not loja_existente else u'Estabelecimento existente'
        body = u'<h2>Informações do Estabelecimento</h2><br>' \
               u'<strong>' + tipo + u'</strong><br><br>' \
               u'<strong>Nome:</strong> ' + loja.nome_estabelecimento + u'<br><br>' \
               u'<strong>Telefone:</strong> ' + loja.telefone1 + u'<br><br>' \
               u'<strong>CNPJ:</strong> ' + loja.cnpj + u'<br><br>' \
               u'<strong>CEP:</strong> ' + loja.cep + u'<br><br>' \
               u'<strong>Endereço:</strong> ' + loja.endereco + u'<br><br>' \
               u'<strong>Complemento:</strong> ' + loja.complemento + u'<br><br>' \
               u'<strong>Bairro:</strong> ' + loja.bairro + u'<br><br>' \
               u'<strong>Estado:</strong> ' + loja.estado + u'<br><br>' \
               u'<strong>Cidade:</strong> ' + loja.cidade + u'<br><br>' \
               u'<strong>Módulo(s):</strong> ' + modulos_contratados + u'<br><br>' \
               u'<h2>Informações do Usuário</h2><br>'
        if possui_login:  # tenho login
            login = request.data.get('login_usuario')
            senha = request.data.get('senha_usuario')
            user = User.objects.filter(email=login).select_related('profile').first()
            if user is None:
                return fail_response(400, u'{"type": "cred", "object": "Login e/ou senha inválidos. Caso tenha '
                                          u'esquecido sua senha, clique em \'Esqueci minha senha\'."}')
            if user.check_password(senha) is False:
                return fail_response(400, u'{"type": "cred", "object": "Login e/ou senha inválidos. Caso tenha '
                                          u'esquecido sua senha, clique em \'Esqueci minha senha\'."}')
            body += u'<strong>Tipo:</strong> Já possui login<br><br>' \
                    u'<strong>Login:</strong> ' + login + u'<br><br>' \
                    u'<strong>Nome:</strong> ' + user.first_name + ' ' + user.last_name + u'<br><br>' \
                    u'<strong>Email:</strong> ' + user.email + u'<br><br>' \
                    u'<strong>Telefone:</strong> ' + user.profile.telefone + u'<br><br>'
            if loja.group is None:
                grupo = Group(name=loja.nome)
                grupo.save()
                grupo.user_set.add(user)
                grupo.save()
                loja.group = grupo
            if not loja_existente:
                loja.nome_contato = user.first_name + ' ' + user.last_name
                loja.email = user.email
                loja.telefone2 = user.profile.telefone
                loja.save()
            # envio de email para o cliente sobre sua nova aquisicao, FALTOU FALAR DA COBRANCA
            with codecs.open(os.path.join(os.path.join(os.path.join(os.path.join(settings.BASE_DIR, 'marviin'),
                                                                    'templates'),
                                                       'acesso'), 'email-inscricao.html'),
                             encoding='utf-8') as email_inscricao:
                body_incompleto = email_inscricao.read().replace('\n', '')
            body_template = Template(body_incompleto)
            body_inscricao = body_template.substitute(arg1=user.first_name)
            enviar_email(u'Obrigado por contratar o módulo de '+modulos_contratados+u' Marviin', body_inscricao,
                         [user.email])
            response = Response({"success": True, "message": u'Tudo pronto, fácil assim, você já pode começar a '
                                                             u'utilizar seu novo produto. Acesse sua caixa postal '
                                                             u'eletrônica, pois enviamos um e-mail com informações '
                                                             u'importantes.'})
        else:  # nao tenho login
            try:
                User.objects.get(email=request.data.get('email_usuario'))
                return fail_response(400, u'{"type": "cred", "object": "E-mail já cadastrado no Marviin. Utilize a '
                                          u'opção \'Já tenho login\'. Caso tenha esquecido sua senha, clique em '
                                          u'\'Esqueci minha senha\'."}')
            except User.DoesNotExist:
                pass
            loja.nome_contato = request.data.get('nome_usuario') + ' ' + request.data.get('sobrenome_usuario')
            loja.email = request.data.get('email_usuario')
            loja.telefone2 = request.data.get('tel_usuario')
            loja.token_login = signing.dumps([request.data.get('nome_usuario'), request.data.get('sobrenome_usuario')],
                                             compress=True)
            loja.save()
            body += u'<strong>Tipo:</strong> NÃO possui login<br><br>' \
                    u'<strong>Nome:</strong> ' + loja.nome_contato + u'<br><br>' \
                    u'<strong>Email:</strong> ' + loja.email + u'<br><br>' \
                    u'<strong>Telefone:</strong> ' + loja.telefone2
            # envio de email para cliente poder cadastrar sua senha.
            with codecs.open(os.path.join(os.path.join(os.path.join(os.path.join(settings.BASE_DIR, 'marviin'),
                                                                    'templates'),
                                                       'acesso'), 'email-senha.html'), encoding='utf-8') as email_senha:
                body_incompleto = email_senha.read().replace('\n', '')
            body_template = Template(body_incompleto)
            body_senha = body_template.substitute(arg1=request.data.get('nome_usuario'),
                                                  arg2='https://acesso.marviin.com.br/confirmacao.html?'
                                                       'token=' + loja.token_login)
            enviar_email(u'Cadastre sua senha e já comece a usar o Marviin', body_senha, [loja.email])
            response = Response({"success": True, "message": u'Legal! Para completar seu cadastro, acesse seu e-mail e '
                                                             u'siga as instruções para cadastrar sua senha.'})
        loja_apps = []
        if loja_existente:
            apps = Apps.objects.filter(loja_id=loja.id)
            for app in apps:
                loja_apps.append(app.app)
        for modulo in modulos:
            if modulo not in loja_apps:
                apps = Apps()
                apps.loja = loja
                apps.app = modulo
                if possui_login:
                    apps.ativa = True
                apps.save()
                if modulo == 'demoSMS':
                    demosms = DemoSms()
                    demosms.loja = loja
                    demosms.quantidade = 0
                    demosms.save()
                elif modulo == 'demoEmail':
                    demoemail = DemoEmail()
                    demoemail.loja = loja
                    demoemail.quantidade = 0
                    demoemail.save()
        if response.status_code == 200:
            # envio de email para o comercial sobre solicitacao de acesso.
            enviar_email(u'[Solicitação de Acesso] Dados da solicitação', body, ['comercial@marviin.com.br'])
        return response


'''
class AcessoBotV2View(views.APIView):
    permission_classes = (AllowAny,)
    renderer_classes = (TemplateHTMLRenderer,)

    def post(self, request, *args, **kwargs):
        user_code = request.data.get('code')
        app_id = request.data.get('client_id')
        fb_code_to_token = Template('https://graph.facebook.com/v2.8/oauth/access_token?'
                                    'client_id=$arg1&'
                                    'client_secret=$arg2&'
                                    'code=$arg3&'
                                    'redirect_uri=https://acesso.marviin.com.br/')
        url_code_to_token = fb_code_to_token.substitute(arg1=app_id,
                                                        arg2=settings.FB_APPS[app_id]['secret'],
                                                        arg3=user_code)
        response = fb_request(fb_url=url_code_to_token)
        if response is None:
            return fail_response(500, u'{"type": "msg", "object": "Cód. 1: Não foi possível completar a solicitação. '
                                      u'Por favor, tente em instantes."}')
        code_to_token = response.json()
        logger.debug('-=-=-=- url_code_to_token json ' + repr(code_to_token))
        if 'access_token' not in code_to_token:
            return fail_response(500, u'{"type": "msg", "object": "Cód. 2: Não foi possível completar a solicitação. '
                                      u'Por favor, tente em instantes."}')
        access_token = code_to_token['access_token']
        fb_check_token = Template('https://graph.facebook.com/debug_token?input_token=$arg1&access_token=$arg2|$arg3')
        url_check_token = fb_check_token.substitute(arg1=access_token,
                                                    arg2=app_id,
                                                    arg3=settings.FB_APPS[app_id]['secret'])
        response = fb_request(fb_url=url_check_token)
        if response is None:
            return fail_response(500, u'{"type": "msg", "object": "Cód. 3: Não foi possível completar a solicitação. '
                                      u'Por favor, tente em instantes."}')
        token_info = response.json()
        logger.debug('-=-=-=- url_check_token json ' + repr(token_info))
        if 'data' not in token_info:
            return fail_response(500, u'{"type": "msg", "object": "Cód. 4: Não foi possível completar a solicitação. '
                                      u'Por favor, tente em instantes."}')
        if token_info['data']['app_id'] != app_id:
            return fail_response(500, u'{"type": "msg", "object": "Cód. 5: Não foi possível completar a solicitação '
                                      u'por motivo de inconsistência. Por favor, tente novamente."}')
        user_id = token_info['data']['user_id']
        fb_user_info = Template('https://graph.facebook.com/v2.8/$arg1?access_token=$arg2')
        url_user_info = fb_user_info.substitute(arg1=user_id,
                                                arg2=access_token)
        response = fb_request(fb_url=url_user_info)
        if response is None:
            return fail_response(500, u'{"type": "msg", "object": "Cód. 6: Não foi possível completar a solicitação. '
                                      u'Por favor, tente em instantes."}')
        user_info = response.json()
        logger.debug('-=-=-=- url_user_info json ' + repr(user_info))
        if 'name' not in user_info:
            return fail_response(500, u'{"type": "msg", "object": "Cód. 7: Não foi possível completar a solicitação. '
                                      u'Por favor, tente em instantes."}')
        fb_user_permissions = Template('https://graph.facebook.com/v2.8/$arg1/permissions?access_token=$arg2')
        url_user_permissions = fb_user_permissions.substitute(arg1=user_id,
                                                              arg2=access_token)
        response = fb_request(fb_url=url_user_permissions)
        if response is None:
            return fail_response(500, u'{"type": "msg", "object": "Cód. 8: Não foi possível completar a solicitação. '
                                      u'Por favor, tente em instantes."}')
        user_permissions = response.json()
        logger.debug('-=-=-=- url_user_permissions json ' + repr(user_permissions))
        if 'data' not in user_permissions:
            return fail_response(500, u'{"type": "msg", "object": "Cód. 9: Não foi possível completar a solicitação. '
                                      u'Por favor, tente em instantes."}')
        not_granted = []
        for user_permission in user_permissions['data']:
            if user_permission['status'] != 'granted':
                not_granted.append(user_permission['permission'])
        if len(not_granted) > 0:
            return fail_response(400, '{"type": "perm", "object": '+json.dumps(not_granted)+'}')
        fb_user_accounts = Template('https://graph.facebook.com/v2.8/$arg1/accounts?access_token=$arg2')
        url_user_accounts = fb_user_accounts.substitute(arg1=user_id,
                                                        arg2=access_token)
        response = fb_request(fb_url=url_user_accounts)
        if response is None:
            return fail_response(500, u'{"type": "msg", "object": "Cód. 10: Não foi possível completar a solicitação. '
                                      u'Por favor, tente em instantes."}')
        user_accounts = response.json()
        logger.debug('-=-=-=- url_user_accounts json ' + repr(user_accounts))
        if 'data' not in user_accounts:
            return fail_response(500, u'{"type": "msg", "object": "Cód. 11: Não foi possível completar a solicitação. '
                                      u'Por favor, tente em instantes."}')
        FbContasUsuario.objects.filter(app_scoped_user_id=user_id).delete()
        FbContasUsuario.objects.bulk_create(
            [FbContasUsuario(page_id=page['id'], page_name=page['name'], page_access_token=page['access_token'],
                             app_scoped_user_id=user_id)
             for page in user_accounts['data']]
        )
        remove_not_eligible_pages(user_id)
        pages = FbContasUsuario.objects.filter(app_scoped_user_id=user_id).order_by('page_name')
        if len(pages) == 0:
            return fail_response(400, u'{"type": "acc", "object": "'+user_info['name']+u', todas suas páginas já '
                                      u'utilizam algum módulo nosso. Qualquer dúvida entre em contato conosco."}')
        return Response({"success": True, "client_id": app_id, "user_name": user_info['name'],
                         "pages": [{"id": page.page_id, "name": page.page_name} for page in pages]},
                        template_name='campos-solicitacao.html')


class AcessoBotV2Passo2View(views.APIView):
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        dados_acesso = json.loads(request.data.get('dados_acesso'))
        pid = dados_acesso['pid']
        try:
            page = FbContasUsuario.objects.get(page_id=pid)
        except FbContasUsuario.DoesNotExist:
            return fail_response(400, u'{"type": "pid", "object": "Cód. 1: Não foi possível validar os dados '
                                      u'enviados."}')
        try:
            loja = Loja.objects.get(id_loja_facebook=pid)
        except Loja.DoesNotExist:
            loja = Loja()
        loja.id_loja_facebook = pid
        loja.nome = dados_acesso['nome_dashboard']
        loja.nome_estabelecimento = dados_acesso['nome_estabelecimento']
        loja.telefone1 = dados_acesso['tel_estabelecimento']
        loja.cnpj = re.sub(r'\D', '', dados_acesso['cnpj_estabelecimento'])
        loja.cep = dados_acesso['cep_estabelecimento']
        loja.endereco = dados_acesso['endereco_estabelecimento']
        loja.complemento = dados_acesso['complemento_estabelecimento']
        loja.bairro = dados_acesso['bairro_estabelecimento']
        loja.estado = dados_acesso['estado_estabelecimento']
        loja.cidade = dados_acesso['cidade_estabelecimento']
        # TODO associar modulo(s) a loja
        if dados_acesso['modulo'] == 'indoor':
            modulo_contratado = u'Atendimento'
        elif dados_acesso['modulo'] == 'delivery':
            modulo_contratado = u'Delivery'
        else:
            modulo_contratado = u'Inválido, código: ' + dados_acesso['modulo']
        body = u'<h2>Informações do Estabelecimento</h2><br>' \
               u'<strong>Nome:</strong> ' + dados_acesso['nome_estabelecimento'] + u'<br><br>' \
               u'<strong>Telefone:</strong> ' + dados_acesso['tel_estabelecimento'] + u'<br><br>' \
               u'<strong>CNPJ:</strong> ' + dados_acesso['cnpj_estabelecimento'] + u'<br><br>' \
               u'<strong>CEP:</strong> ' + dados_acesso['cep_estabelecimento'] + u'<br><br>' \
               u'<strong>Endereço:</strong> ' + dados_acesso['endereco_estabelecimento'] + u'<br><br>' \
               u'<strong>Complemento:</strong> ' + dados_acesso['complemento_estabelecimento'] + u'<br><br>' \
               u'<strong>Bairro:</strong> ' + dados_acesso['bairro_estabelecimento'] + u'<br><br>' \
               u'<strong>Estado:</strong> ' + dados_acesso['estado_estabelecimento'] + u'<br><br>' \
               u'<strong>Cidade:</strong> ' + dados_acesso['cidade_estabelecimento'] + u'<br><br>' \
               u'<strong>Módulo:</strong> ' + modulo_contratado + u'<br><br>' \
               u'<h2>Informações do Usuário</h2><br>'
        if dados_acesso['tipo_cadastro_usuario'] == '1':  # tenho login
            login = dados_acesso['login_usuario']
            senha = dados_acesso['senha_usuario']
            user = User.objects.filter(email=login).select_related('profile').first()
            if user is None:
                return fail_response(400, u'{"type": "cred", "object": "Login e/ou senha inválidos. Caso tenha '
                                          u'esquecido sua senha, clique em \'Esqueci minha senha\'."}')
            if user.check_password(senha) is False:
                return fail_response(400, u'{"type": "cred", "object": "Login e/ou senha inválidos. Caso tenha '
                                          u'esquecido sua senha, clique em \'Esqueci minha senha\'."}')
            body += u'<strong>Tipo:</strong> Já possui login<br><br>' \
                    u'<strong>Login:</strong> ' + login + u'<br><br>' \
                    u'<strong>Nome:</strong> ' + user.first_name + ' ' + user.last_name + u'<br><br>' \
                    u'<strong>Email:</strong> ' + user.email + u'<br><br>' \
                    u'<strong>Telefone:</strong> ' + user.profile.telefone + u'<br><br>'
            response, config_problem = fb_subscribe(page.page_id, page.page_access_token,
                                                    app_scoped_user_id=page.app_scoped_user_id,
                                                    modulo=dados_acesso['modulo'])
            logger.debug('response ' + repr(response))
            logger.debug('-=-=-=- config_problem ' + repr(config_problem))
            if response.status_code == 200:
                grupo = Group(name=dados_acesso['nome_dashboard'])
                grupo.save()
                grupo.user_set.add(user)
                grupo.save()
                loja.group = grupo
                loja.nome_contato = user.first_name + ' ' + user.last_name
                loja.email = user.email
                loja.telefone2 = user.profile.telefone
                loja.save()
                # envio de email para o cliente sobre sua nova aquisicao, FALTOU FALAR DA COBRANCA
                with codecs.open(os.path.join(os.path.join(os.path.join(os.path.join(settings.BASE_DIR, 'marviin'),
                                                                        'templates'),
                                                           'acesso'), 'email-inscricao.html'),
                                 encoding='utf-8') as email_inscricao:
                    body_incompleto = email_inscricao.read().replace('\n', '')
                body_template = Template(body_incompleto)
                body_inscricao = body_template.substitute(arg1=user.first_name)
                enviar_email(u'Obrigado por assinar o módulo de '+modulo_contratado+u' Marviin', body_inscricao,
                             [user.email])
            if response.status_code != 200 or config_problem is not None:
                if config_problem is None:
                    body += u'<strong>Problema no registro da página:</strong> ' + response.content + u'<br><br>'
                else:
                    body += u'<strong>Problema de configuração da página:</strong> ' + config_problem + u'<br><br>'
                # envio de email para suporte marviin com mensagem de erro
                enviar_email(u'[Solicitação de Acesso] Problema na solicitação', body, ['suporte@marviin.com.br'])
        else:  # nao tenho login
            try:
                User.objects.get(email=dados_acesso['email_usuario'])
                return fail_response(400, u'{"type": "cred", "object": "E-mail já cadastrado no Marviin. Utilize a '
                                          u'opção \'Já tenho login\'. Caso tenha esquecido sua senha, clique em '
                                          u'\'Esqueci minha senha\'."}')
            except User.DoesNotExist:
                pass
            loja.nome_contato = dados_acesso['nome_usuario'] + ' ' + dados_acesso['sobrenome_usuario']
            loja.email = dados_acesso['email_usuario']
            loja.telefone2 = dados_acesso['tel_usuario']
            loja.token_login = signing.dumps([dados_acesso['nome_usuario'], dados_acesso['sobrenome_usuario']],
                                             compress=True)
            loja.save()
            response = Response({"success": True, "message": u'Legal! Para completar seu cadastro, acesse seu e-mail e '
                                                             u'siga as instruções para cadastrar sua senha.'})
            body += u'<strong>Tipo:</strong> NÃO possui login<br><br>' \
                    u'<strong>Nome:</strong> ' + loja.nome_contato + u'<br><br>' \
                    u'<strong>Email:</strong> ' + loja.email + u'<br><br>' \
                    u'<strong>Telefone:</strong> ' + loja.telefone2
            # envio de email para cliente poder cadastrar sua senha.
            with codecs.open(os.path.join(os.path.join(os.path.join(os.path.join(settings.BASE_DIR, 'marviin'),
                                                                    'templates'),
                                                       'acesso'), 'email-senha.html'), encoding='utf-8') as email_senha:
                body_incompleto = email_senha.read().replace('\n', '')
            body_template = Template(body_incompleto)
            body_senha = body_template.substitute(arg1=dados_acesso['nome_usuario'],
                                                  arg2='https://acesso.marviin.com.br/confirmacao.html?'
                                                       'token=' + loja.token_login)
            enviar_email(u'Cadastre sua senha e já comece a usar o Marviin', body_senha, [loja.email])
        if response.status_code == 200:
            # envio de email para o comercial sobre solicitacao de acesso.
            enviar_email(u'[Solicitação de Acesso] Dados da solicitação', body, ['comercial@marviin.com.br'])
        return response
'''

class ValidaTokenView(views.APIView):
    permission_classes = (AllowAny,)
    renderer_classes = (TemplateHTMLRenderer,)

    def post(self, request, *args, **kwargs):
        token_param = request.data.get('token')
        token2_param = request.data.get('token2')

        if token_param is None and token2_param is None:
            return fail_response(400, u'{"type": "token", "object": "Token inválido."}')
        if token_param is not None:
            token = token_param
        else:
            token = token2_param
        token = ''.join(token.split(' '))
        logger.debug('===---=-=--=--=-=-= token validacao::: ' + token)
        try:
            signing.loads(token, max_age=172800)  # max ages em segundos (2 dias)
        except signing.BadSignature:
            return fail_response(400, u'{"type": "token", "object": "Token expirado."}')
        if token_param is not None:
            try:
                Loja.objects.get(token_login=token)
            except Loja.DoesNotExist:
                return fail_response(400, u'{"type": "token", "object": "Token inválido."}')
            template_data = {"token": token, "title": 'Para finalizar seu cadastro, insira abaixo uma senha.',
                             "method": 'cria_senha'}
        else:
            try:
                Profile.objects.get(token_senha=token)
            except Profile.DoesNotExist:
                return fail_response(400, u'{"type": "token", "object": "Token inválido."}')
            template_data = {"token": token, "title": 'Insira abaixo sua nova senha.',
                             "method": 'cria_senha2'}
        return Response(template_data, template_name='campos-senha.html')


class CriaSenhaView(views.APIView):
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        token = request.data.get('token')
        if token is None:
            return fail_response(400, u'{"type": "token", "object": "Token expirado."}')
        token = ''.join(token.split(' '))
        logger.debug('===---=-=--=--=-=-= token validacao::: ' + token)
        try:
            decoded_token = signing.loads(token, max_age=172800)  # max ages em segundos (2 dias)
        except signing.BadSignature:
            return fail_response(400, u'{"type": "token", "object": "Token expirado."}')
        try:
            loja = Loja.objects.get(token_login=token)
        except Loja.DoesNotExist:
            return fail_response(400, u'{"type": "token", "object": "Token inválido."}')
        apps = Apps.objects.filter(loja=loja.id)
        modulos_contratados = None
        for modulo in apps:
            if modulo.app == 'indoor':
                if modulos_contratados is None:
                    modulos_contratados = u''
                else:
                    modulos_contratados += u', '
                modulos_contratados += u'Atendimento'
            elif modulo.app == 'delivery':
                if modulos_contratados is None:
                    modulos_contratados = u''
                else:
                    modulos_contratados += u', '
                modulos_contratados += u'Delivery'
            elif modulo.app == 'demoEmail':
                if modulos_contratados is None:
                    modulos_contratados = u''
                else:
                    modulos_contratados += u', '
                modulos_contratados += u'Demo E-mail'
            elif modulo.app == 'demoSMS':
                if modulos_contratados is None:
                    modulos_contratados = u''
                else:
                    modulos_contratados += u', '
                modulos_contratados += u'Demo SMS'
        if modulos_contratados is None:
            return fail_response(400, u'{"type": "mod", "object": "Não foi possível definir o produto contratado."}')
        senha = request.data.get('senha')
        confirma_senha = request.data.get('confirma_senha')
        if senha != confirma_senha:
            return fail_response(400, u'{"type": "pass2", "object": "A senha de confirmação não confere com a senha '
                                      u'digitada."}')
        if valida_senha(senha) is False:
            return fail_response(400, u'{"type": "pass1", "object": "Para sua segurança sua senha deve possuir pelo '
                                      u'menos 6 caracteres, dentre eles, 1 caractere especial, 1 número, 1 letra '
                                      u'minúscula e 1 letra maiúscula."}')
        body = u'<h2>Informações do Estabelecimento</h2><br>' \
               u'<strong>Nome:</strong> ' + loja.nome_estabelecimento + u'<br><br>' \
               u'<strong>Telefone:</strong> ' + loja.telefone1 + u'<br><br>' \
               u'<strong>CNPJ:</strong> ' + loja.cnpj + u'<br><br>' \
               u'<strong>CEP:</strong> ' + loja.cep + u'<br><br>' \
               u'<strong>Endereço:</strong> ' + loja.endereco + u'<br><br>' \
               u'<strong>Complemento:</strong> ' + loja.complemento + u'<br><br>' \
               u'<strong>Bairro:</strong> ' + loja.bairro + u'<br><br>' \
               u'<strong>Estado:</strong> ' + loja.estado + u'<br><br>' \
               u'<strong>Cidade:</strong> ' + loja.cidade + u'<br><br>' \
               u'<strong>Módulo(s):</strong> ' + modulos_contratados + u'<br><br>' \
               u'<h2>Informações do Usuário</h2><br>' \
               u'<strong>Etapa:</strong> Criação senha<br><br>' \
               u'<strong>Nome:</strong> ' + loja.nome_contato + u'<br><br>' \
               u'<strong>Email:</strong> ' + loja.email + u'<br><br>' \
               u'<strong>Telefone:</strong> ' + loja.telefone2 + u'<br><br>'
        with transaction.atomic():
            while True:
                user, created = User.objects.get_or_create(username=''.join(random.choice(
                    string.ascii_letters + string.digits + '@._+-') for x in range(30)))
                if created:
                    break
        user.first_name = decoded_token[0]
        user.last_name = decoded_token[1]
        user.email = loja.email
        user.set_password(senha)
        user.is_active = True
        user.profile.telefone = loja.telefone2
        user.save()
        grupo = Group(name=loja.nome)
        grupo.save()
        grupo.user_set.add(user)
        grupo.save()
        loja.group = grupo
        loja.token_login = signing.dumps('licenca_valida', compress=True)
        loja.save()
        for loja_app in apps:
            loja_app.ativa = True
            loja_app.save()
        # envio de email para o cliente sobre sua nova aquisicao, FALTOU FALAR DA COBRANCA
        with codecs.open(os.path.join(os.path.join(os.path.join(os.path.join(settings.BASE_DIR, 'marviin'),
                                                                'templates'),
                                                   'acesso'), 'email-inscricao.html'),
                         encoding='utf-8') as email_inscricao:
            body_incompleto = email_inscricao.read().replace('\n', '')
        body_template = Template(body_incompleto)
        body_inscricao = body_template.substitute(arg1=user.first_name)
        enviar_email(u'Obrigado por contratar o módulo de ' + modulos_contratados + u' Marviin', body_inscricao,
                     [user.email])
        # envio de email para o comercial sobre solicitacao de acesso.
        enviar_email(u'[Solicitação de Acesso] Dados da solicitação', body, ['comercial@marviin.com.br'])
        return Response({"success": True, "message": u'Tudo pronto, fácil assim, você já pode começar a '
                                                     u'utilizar seu novo produto. Acesse sua caixa postal '
                                                     u'eletrônica, pois enviamos um e-mail com informações '
                                                     u'importantes.'})


class CriaSenha2View(views.APIView):
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        token = request.data.get('token')
        if token is None:
            return fail_response(400, u'{"type": "token", "object": "Token inválido."}')
        token = ''.join(token.split(' '))
        logger.debug('===---=-=--=--=-=-= token validacao::: ' + token)
        try:
            signing.loads(token, max_age=172800)  # max ages em segundos (2 dias)
        except signing.BadSignature:
            return fail_response(400, u'{"type": "token", "object": "Token expirado."}')
        try:
            user_profile = Profile.objects.get(token_senha=token)
        except Profile.DoesNotExist:
            return fail_response(400, u'{"type": "token", "object": "Token inválido."}')
        senha = request.data.get('senha')
        confirma_senha = request.data.get('confirma_senha')
        if senha != confirma_senha:
            return fail_response(400, u'{"type": "pass2", "object": "A senha de confirmação não confere com a senha '
                                      u'digitada."}')
        if valida_senha(senha) is False:
            return fail_response(400, u'{"type": "pass1", "object": "Para sua segurança sua senha deve possuir pelo '
                                      u'menos 6 caracteres, dentre eles, 1 caractere especial, 1 número, 1 letra '
                                      u'minúscula e 1 letra maiúscula."}')
        user = user_profile.user
        user.profile.token_senha = None
        user.set_password(senha)
        user.save()
        return Response({"success": True, "message": 'Senha alterada com sucesso.'})


class EsqueciSenhaView(views.APIView):
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        email_usuario = request.data.get('email')
        if len(email_usuario) == 0:
            return fail_response(400, u'{"type": "msg", "object": "Não foi possível validar os dados '
                                      u'enviados."}')
        user = User.objects.filter(email=email_usuario).select_related('profile').first()
        if user is None:
            return fail_response(400, u'{"type": "msg", "object": "E-mail não encontrado."}')
        user.profile.token_senha = signing.dumps(['esqueci senha'], compress=True)
        user.save()
        response = Response({"success": True, "message": u'Siga as instruções, no e-mail que enviamos à você, para '
                                                         u'cadastrar uma nova senha.'})
        # envio de email para cliente poder cadastrar sua senha.
        with codecs.open(os.path.join(os.path.join(os.path.join(os.path.join(settings.BASE_DIR, 'marviin'),
                                                                'templates'),
                                                   'acesso'), 'email-senha2.html'), encoding='utf-8') as email_senha:
            body_incompleto = email_senha.read().replace('\n', '')
        body_template = Template(body_incompleto)
        body_senha = body_template.substitute(arg1=user.first_name,
                                              arg2='https://acesso.marviin.com.br/confirmacao.html?'
                                                   'token2=' + user.profile.token_senha)
        enviar_email(u'Cadastre uma nova senha no Marviin', body_senha, [email_usuario])
        return response


def enviar_email(titulo, body, email_to, email_from='Marviin <contato@marviin.com.br>'):
    msg = EmailMessage(
        titulo,
        body,
        email_from,
        email_to
    )
    msg.content_subtype = "html"
    msg.send()

'''
class AcessoBotView(views.APIView):
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        page_id = request.data.get('pid')
        try:
            Fb_acesso.objects.get(page_id=page_id)
            return fail_response(400, u'Página já utiliza o Marviin.')
        except Fb_acesso.DoesNotExist:
            pass
        user_access_token = request.data.get('uac')
        fb_service_long_lived_token = Template('https://graph.facebook.com/oauth/access_token?'
                                               'client_id=$arg1&'
                                               'client_secret=$arg2&'
                                               'grant_type=fb_exchange_token&'
                                               'fb_exchange_token=$arg3')
        url_long_lived_user_token = fb_service_long_lived_token.substitute(arg1=settings.FB_APP_ID,
                                                                           arg2=settings.FB_APP_SECRET,
                                                                           arg3=user_access_token)
        response = fb_request(fb_url=url_long_lived_user_token)
        if response is None:
            return fail_response(500, u'Cód. 1: Não foi possível completar a solicitação. '
                                      u'Por favor, tente em instantes.')
        logger.debug('-=-=-=- url_long_lived_user_token text ' + repr(response.text))
        user_access_token = response.text.split('=')[1]
        url_user_accounts = 'https://graph.facebook.com/v2.7/me/accounts?access_token='+user_access_token
        response = fb_request(fb_url=url_user_accounts)
        if response is None:
            return fail_response(500, u'Cód. 2: Não foi possível completar a solicitação. '
                                      u'Por favor, tente em instantes.')
        logger.debug('-=-=-=- url_user_accounts json ' + repr(response.json()))
        user_pages = response.json()
        if 'data' not in user_pages:
            return fail_response(500, u'Nenhuma página encontrada para o usuário.')
        page_access_token = None
        for user_page in user_pages['data']:
            if page_id == user_page['id']:
                page_access_token = user_page['access_token']
                break
        if page_access_token is None:
            return fail_response(500, u'Cód. 3: Não foi possível completar a solicitação. '
                                      u'Por favor, tente em instantes.')
        logger.debug('-=-=-=- page_access_token ' + page_access_token)
        response = fb_subscribe(page_id, page_access_token)
        if response.status_code == 200:
            nome_loja = request.data.get('nome_loja')
            loja = Loja()
            loja.nome = nome_loja
            loja.id_loja_facebook = page_id
            loja.save()
        return response
'''


def fb_subscribe(page_id, page_access_token, app_scoped_user_id=None, modulo='548897018630774'):
    config_problem = None
    response = fb_subscribe_page(page_id, page_access_token)
    if response is None:
        logger.error(page_id + u' :: Cód. SUBS1: Não foi possível completar a solicitação.')
        return fail_response(500, u'{"type": "subs", "object": "Cód. SUBS1: Não foi possível completar a solicitação. '
                                  u'Por favor, tente em instantes."}'), None
    subscribe = response.json()
    if 'success' in subscribe and subscribe['success'] == True:
        response = fb_persistent_menu(page_access_token, modulo=modulo)
        if response is None:
            config_problem = u'Cód. SUBS2: Não foi possível criar o menu hamburguer.'
            logger.error(page_id + u' :: Cód. SUBS2: Não foi possível criar o menu hamburguer.')
        else:
            persistent_menu = response.json()
            if 'Success' not in persistent_menu['result']:
                config_problem = u'Cód. SUBS3: Não foi possível criar o menu hamburguer.'
                logger.error(page_id + u' :: Cód. SUBS3: Não foi possível criar o menu hamburguer.')
        fb_greeting_text(page_access_token, modulo=modulo)
        response = fb_get_started(page_access_token)
        if response is None:
            config_problem = u'Cód. SUBS4: Não foi possível adicionar o botão iniciar.'
            logger.error(page_id + u' :: Cód. SUBS4: Não foi possível adicionar o botão iniciar.')
        else:
            get_started = response.json()
            if 'Success' not in get_started['result']:
                config_problem = u'Cód. SUBS5: Não foi possível adicionar o botão iniciar.'
                logger.error(page_id + u' :: Cód. SUBS5: Não foi possível adicionar o botão iniciar.')
        response = fb_whitelist_domain(page_access_token)
        if response is None:
            response = fb_subscribe_page(page_id, page_access_token, method='DELETE')
            if response is None:
                logger.error(page_id + u' :: Cód. SUBS6: Não foi possível remover associação com app.')
            else:
                unsubscribe = response.json()
                if 'success' not in unsubscribe or unsubscribe['success'] == False:
                    logger.error(page_id + u' :: Cód. SUBS7: Não foi possível remover associação com app.')
            logger.error(page_id + u' :: Cód. SUBS8: Não foi possível adicionar whitelist domain.')
            return fail_response(500,
                                 u'{"type": "subs", "object": "Cód. SUBS8: Não foi possível completar a solicitação. '
                                 u'Por favor, tente em instantes."}'), None
        else:
            whitelist_domain = response.json()
            if 'Success' not in whitelist_domain['result']:
                response = fb_subscribe_page(page_id, page_access_token, method='DELETE')
                if response is None:
                    logger.error(page_id + u' :: Cód. SUBS9: Não foi possível remover associação com app.')
                else:
                    unsubscribe = response.json()
                    if 'success' not in unsubscribe or unsubscribe['success'] == False:
                        logger.error(page_id + u' :: Cód. SUBS10: Não foi possível remover associação com app.')
                logger.error(page_id + u' :: Cód. SUBS11: Não foi possível adicionar whitelist domain.')
                return fail_response(500,
                                     u'{"type": "subs", "object": "Cód. SUBS11: Não foi possível completar a '
                                     u'solicitação. Por favor, tente em instantes."}'), None
        fb_acesso = Fb_acesso()
        fb_acesso.page_id = page_id
        fb_acesso.page_access_token = page_access_token
        if app_scoped_user_id:
            fb_acesso.app_scoped_user_id = app_scoped_user_id
        fb_acesso.save()
        return Response({"success": True, "message": u'Tudo pronto, fácil assim, você já pode começar a utilizar seu '
                                                     u'novo produto. Acesse sua caixa postal eletrônica, pois enviamos '
                                                     u'um e-mail com informações importantes.'}), config_problem
    else:
        return fail_response(500, u'{"type": "subs", "object": "Cód. SUBS6: Não foi possível completar a solicitação. '
                                  u'Por favor, tente em instantes."}'), None


def fb_request(method=None, fb_url=None, json=None):
    try:
        return requests.request(method or "GET", fb_url, json=json)
    except requests.RequestException as e:
        response = json.loads(e.read())
        logger.error('!!!ERROR!!! ' + repr(response))
        return None


def fb_subscribe_page(pid, pac, method='POST'):
    fb_service_subscribe_app_to_page = Template('https://graph.facebook.com/$arg1/subscribed_apps?'
                                                'access_token=$arg2')
    url_subscribe_app_to_page = fb_service_subscribe_app_to_page.substitute(arg1=pid, arg2=pac)
    return fb_request(method=method, fb_url=url_subscribe_app_to_page)


def fb_persistent_menu(pac, modulo='548897018630774'):
    call_to_actions = []
    pass
    call_to_actions.append(
        {
            "type": "postback",
            "title": "Novo pedido",
            "payload": "menu_novo_pedido"
        })
    call_to_actions.append(
        {
            "type": "postback",
            "title": u"Pedir cardápio" if modulo == '548897018630774' else u"Visualizar cardápio",
            "payload": "pedir_cardapio"
        })
    if modulo == '548897018630774':
        call_to_actions.append(
            {
                "type": "postback",
                "title": "Chamar garçom",
                "payload": "chamar_garcom"
            })
    call_to_actions.append(
        {
            "type": "postback",
            "title": "Definir mesa" if modulo == '548897018630774' else u"Definir endereço",
            "payload": "menu_trocar_mesa"
        })
    if modulo == '548897018630774':
        call_to_actions.append(
            {
                "type": "postback",
                "title": "Pedir a conta",
                "payload": "pedir_conta"
            })

    persistent_menu = {
        "setting_type": "call_to_actions",
        "thread_state": "existing_thread",
        "call_to_actions": call_to_actions
    }
    url_persistent_menu = 'https://graph.facebook.com/v2.7/me/thread_settings?access_token='+pac
    return fb_request(method='POST', fb_url=url_persistent_menu, json=persistent_menu)


def fb_greeting_text(pac, modulo='548897018630774'):
    greeting_text = {
      "setting_type": "greeting",
      "greeting": {
        "text": u"Olá {{user_first_name}}, muito prazer, me chamo Marviin. Seja bem-vindo(a) a uma nova forma de "
                u"atendimento. Clique no botão abaixo ou digite início."
      }
    }
    url_greeting_text = 'https://graph.facebook.com/v2.7/me/thread_settings?access_token=' + pac
    return fb_request(method='POST', fb_url=url_greeting_text, json=greeting_text)


def fb_get_started(pac):
    get_started = {
      "setting_type": "call_to_actions",
      "thread_state": "new_thread",
      "call_to_actions": [
        {
          "payload": "menu_get_started"
        }
      ]
    }
    url_get_started = 'https://graph.facebook.com/v2.7/me/thread_settings?access_token=' + pac
    return fb_request(method='POST', fb_url=url_get_started, json=get_started)


def fb_whitelist_domain(pac):
    whitelist_domain = {
      "setting_type": "domain_whitelisting",
      "whitelisted_domains": ["https://sistema.marviin.com.br"],
      "domain_action_type": "add"
    }
    url_whitelist_domain = 'https://graph.facebook.com/v2.7/me/thread_settings?access_token=' + pac
    return fb_request(method='POST', fb_url=url_whitelist_domain, json=whitelist_domain)


class PageAccessTokenView(views.APIView):
    authentication_classes = (BasicAuthentication,)
    permission_classes = (IsAdminUser,)

    def get(self, request, *args, **kwargs):
        nao_valido = valida_chamada_interna(request)
        if nao_valido:
            return nao_valido
        try:
            fb_acesso = Fb_acesso.objects.get(pk=request.GET['page_id'])
            logger.debug('===---=-=--=--=-=-= access token::: ' + fb_acesso.page_access_token)
            return Response({"success": True, "access_token": fb_acesso.page_access_token})
        except Fb_acesso.DoesNotExist:
            logger.error('-=-=-=-=-=-=-=- facebook page_id inexistente: ' +
                         repr(request.data.get('page_id')))
            return Response({"success": False})


class CardapioView(views.APIView):
    authentication_classes = (BasicAuthentication,)
    permission_classes = (IsAdminUser,)

    def get(self, request, *args, **kwargs):
        nao_valido = valida_chamada_interna(request)
        if nao_valido:
            return nao_valido
        try:
            loja = Loja.objects.get(pk=request.GET['id_loja'])
        except Loja.DoesNotExist:
            logger.error('-=-=-=-=-=-=-=- loja inexistente para id: ' +
                         repr(request.GET['id_loja']))
            return Response({"success": False})
        cardapios = Cardapio.objects.filter(loja=loja.id).order_by('pagina')
        cardapio_payload = ['https://sistema.marviin.com.br' + cardapio.caminho for cardapio in cardapios]
        return Response({'success': True, 'cardapio': cardapio_payload})


class FormularioInteresseView(views.APIView):
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        dados = json.loads(request.data.get('formulario_dados'))
        logger.debug('===---=-=--=--=-=-= dados fomrulario::: ' + repr(dados))
        loja = Loja()
        loja.nome = dados['nome']
        loja.nome_contato = dados['contato']
        loja.tipo_loja = dados['tipo_estabelecimento']
        loja.email = dados['email']
        loja.telefone1 = dados['telefone']
        loja.cep = dados['cep']
        loja.save()
        questionario = Questionario()
        questionario.loja = loja
        questionario.descr_problemas = dados['descricao_problemas']
        questionario.problemas = dados['ordem_campos']
        questionario.save()

        body = u'<h2>Informações fornecidas</h2><br>' \
               u'<strong>Nome do estabelecimento:</strong> ' + loja.nome + u'<br><br>' \
               u'<strong>Nome do contato:</strong> ' + loja.nome_contato + u'<br><br>' \
               u'<strong>Tipo de estabelecimento:</strong> ' + loja.tipo_loja + u'<br><br>' \
               u'<strong>Email:</strong> ' + loja.email + u'<br><br>' \
               u'<strong>Telefone:</strong> ' + loja.telefone1 + u'<br><br>' \
               u'<strong>CEP:</strong> ' + loja.cep + u'<br><br>' \
               u'<strong>Descrição problemas:</strong> ' + questionario.descr_problemas + u'<br><br>' \
               u'<strong>Ordem dos principais problemas:</strong><br><ol>'
        for problema in questionario.problemas:
            body += u'<li>' + problema + u'</li>'
        body += u'</ol>'

        enviar_email(u'[Site] Formulário de interesse', body, ['contato@marviin.com.br'])

        return Response({'success': True})


class FaleConoscoView(views.APIView):
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        dados = json.loads(request.data.get('formulario_dados'))
        body = u'<h2>Dados</h2><br>' \
               u'<strong>Nome:</strong> ' + dados['name'] + u'<br><br>' \
               u'<strong>Email:</strong> ' + dados['email'] + u'<br><br>' \
               u'<strong>Mensagem:</strong><br> ' + dados['message']

        enviar_email(u'[Site] Fale Conosco', body, ['contato@marviin.com.br'])

        return Response({'success': True})


class FormularioIndicacaoView(views.APIView):
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        dados = json.loads(request.data.get('formulario_dados'))
        logger.debug('===---=-=--=--=-=-= dados fomrulario::: ' + repr(dados))
        body = u'<h2>Informações fornecidas</h2><br>' \
               u'<strong>Nome do estabelecimento:</strong> ' + dados['nome'] + u'<br><br>' \
               u'<strong>Cidade do estabelecimento:</strong> ' + dados['cidade'] + u'<br><br>' \
               u'<strong>Telefone do estabelecimento:</strong> ' + dados['telefone'] + u'<br><br>' \
               u'<strong>Email de quem indicou:</strong> ' + dados['email']

        enviar_email(u'[Site] Formulário de indicação de estabelecimento', body, ['contato@marviin.com.br'])

        return Response({'success': True})


class EstadosView(views.APIView):
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        estados = Estado.objects.order_by('nome_uf')
        estados_payload = [{'id': estado.sigla_uf, 'nome': estado.sigla_uf} for estado in estados]
        logger.info(repr(estados_payload))
        return Response({'success': True, 'estados': estados_payload})


class CidadesView(views.APIView):
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        estado = request.GET['estado']
        try:
            cidades = Cidade.objects.filter(uf__sigla_uf=estado).order_by('nome_cidade')
        except Cidade.DoesNotExist:
            logger.error('-=-=-=-=-=-=-=- estado inexistente: ' + repr(estado))
            return Response({"success": False})
        cidades_payload = [{'id': cidade.nome_cidade, 'nome': cidade.nome_cidade} for cidade in cidades]
        return Response({'success': True, 'cidades': cidades_payload})
