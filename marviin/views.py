# -*- coding: utf-8 -*-

from marviin.forms import *
from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponseRedirect
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect
from django.core import signing
from django.conf import settings
from django.db import IntegrityError, transaction
from django.template import RequestContext

from loja.models import Loja
from cliente.models import Cliente
from marviin.cliente_marviin.models import ClienteMarviin, Facebook, FacebookTemp
from utils.aescipher import AESCipher

from string import Template

import requests
import logging
import uuid
import unicodedata

logger = logging.getLogger('django')


def login_geral(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            if 'loja' not in request.POST or len(request.POST['loja'].strip()) == 0:
                return render(request, 'login.html',
                              {"form": form, "success": False, "type": 400, "message": u'Loja é obrigatório.'})
            id_loja = request.POST['loja'].strip()
            try:
                loja = Loja.objects.get(pk=id_loja)
            except Loja.DoesNotExist:
                return render(request, 'login.html',
                              {"form": form, "success": False, "type": 400,
                               "message": u'Loja não encontrada. Entre em contato com o administrador do sistema.'})
            username = request.POST['username']
            senha = request.POST['senha']
            try:
                user_login = User.objects.get(email=username)
                if user_login.is_active:
                    user = authenticate(username=user_login.username, password=senha)
                else:
                    return render(request, 'login.html',
                                  {"form": form, "success": False, "type": 403,
                                   "message": u'Usuário desabilitado.'})
            except User.DoesNotExist:
                user = None
            if user is not None:
                login(request, user)
                request.session['id_loja'] = loja.id
                request.session['id_fb_loja'] = loja.id_loja_facebook
                request.session['nome_loja'] = loja.nome
                if 'next' in request.GET:
                    next = request.GET['next']
                    return HttpResponseRedirect(next)
                else:
                    return HttpResponseRedirect('/pedidos/')
            else:
                return render(request, 'login.html',
                              {"form": form, "success": False, "type": 403,
                               "message": u'Usuário e/ou senha inválido(s).'})
        error_message = u'Usuário e senha são campos obrigatórios.'
        if 'loja' not in request.POST or len(request.POST['loja'].strip()) == 0:
            error_message = u'Usuário, senha e loja são campos obrigatórios.'
        return render(request, 'login.html',
                      {"form": form, "success": False, "type": 400, "message": error_message})
    else:
        form = LoginForm()
        return render(request, 'login.html', {'form': form, 'error': False})


def logout_geral(request):
    logout(request)
    return HttpResponseRedirect('/')


def fb_authorize(request):
    if 'redirect_uri' in request.POST and 'account_linking_token' in request.POST:
        redirect_uri = request.POST['redirect_uri']
        account_linking_token = request.POST['account_linking_token']
    elif 'redirect_uri' in request.GET and 'account_linking_token' in request.GET:
        redirect_uri = request.GET['redirect_uri']
        account_linking_token = request.GET['account_linking_token']
    else:
        return render(request, 'fb_authorize_fail.html')
    if account_linking_token not in redirect_uri:
        redirect(redirect_uri)
    logger.info('-=-=-=- redirect_uri -=-=-=-' + redirect_uri)
    logger.info('-=-=-=- account_linking_token -=-=-=-' + account_linking_token)
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            senha = form.cleaned_data['senha']
            try:
                user_login = User.objects.get(email=username)
                if user_login.is_active:
                    user = authenticate(username=user_login.username, password=senha)
                else:
                    user = None
            except User.DoesNotExist:
                user = None
            if user is not None:
                try:
                    user.cliente_marviin
                except ObjectDoesNotExist:
                    ClienteMarviin.objects.create(user=user)
                raw_auth_code = str(uuid.uuid4())
                user.cliente_marviin.authorization_code = signing.dumps(raw_auth_code, compress=True)+'#'+raw_auth_code
                user.cliente_marviin.save()
                return redirect('{0}&authorization_code={1}'.format(redirect_uri,
                                                                    user.cliente_marviin.authorization_code))
            else:
                return redirect(redirect_uri)
        else:
            return redirect(redirect_uri)
    else:
        form = LoginForm()
        return render(request, 'fb_authorize.html', {'form': form, 'redirect_uri': redirect_uri,
                                                     'account_linking_token': account_linking_token})


def fb_endereco(request, psid=None):
    if request.method == 'GET':
        render_data = {'close': False, 'psid': psid, 'error': None}
        return render(request, 'fb_endereco.html', render_data, context_instance=RequestContext(request))
    elif request.method == 'POST':
        endereco = request.POST['endereco_entrega']
        if psid is None and 'psid' not in request.POST:
            logger.error('-=-=-=-=-=-=-=- parametro psid nao encontrado.')
            render_data = {'close': False, 'psid': None, 'error': u'Desculpe, mas não foi possível completar sua ação '
                                                                  u'de escolher o endereço. Por favor, tente '
                                                                  u'novamente.'}
            return render(request, 'fb_endereco.html', render_data, context_instance=RequestContext(request))
        if psid is None:
            psid = request.POST['psid']
        else:
            logger.debug('-=-=-=-=-=-=-=- key before :: ' + settings.SECRET_KEY[:32])
            key32 = '{: <32}'.format(settings.SECRET_KEY[:32]).encode("utf-8")
            logger.debug('-=-=-=-=-=-=-=- key after :: ' + key32)
            logger.debug('-=-=-=-=-=-=-=- enc psid :: ' + psid)
            psid = unicodedata.normalize('NFKD', psid).encode('ascii', 'ignore')
            cipher = AESCipher(key=key32)
            psid = cipher.decrypt(psid)
        try:
            cliente = Cliente.objects.get(chave_facebook=psid)
        except Cliente.DoesNotExist:
            logger.error('-=-=-=-=-=-=-=- usuario nao encontrado.')
            render_data = {'close': False, 'psid': None, 'error': u'Desculpe, mas não foi possível completar sua ação '
                                                                  u'de escolher o endereço. Por favor, tente '
                                                                  u'novamente.'}
            return render(request, 'fb_endereco.html', render_data, context_instance=RequestContext(request))
        cliente.pedido_info = {'endereco': endereco}
        cliente.save()
        render_data = {'close': True, 'psid': psid, 'error': None}
        return render(request, 'fb_endereco.html', render_data, context_instance=RequestContext(request))


def fb_cad_endereco(request):
    if request.method == 'GET':
        return render(request, 'fb_cad_endereco.html')
    elif request.method == 'POST':
        pass


def fb_login(request):
    state = None
    if 'redirect_uri' in request.GET and 'account_linking_token' in request.GET:
        redirect_uri = request.GET['redirect_uri']
        account_linking_token = request.GET['account_linking_token']
        if account_linking_token not in redirect_uri:
            return redirect(redirect_uri)
        with transaction.atomic():
            while True:
                state = str(uuid.uuid4())
                user_temp, created = FacebookTemp.objects.get_or_create(id=state)
                if created:
                    break
        user_temp.redirect_uri = redirect_uri
        user_temp.account_linking_token = account_linking_token
        user_temp.save()
    if state is not None and 'code' not in request.GET and 'state' not in request.GET and 'token' not in request.GET:
        if 'perm' not in request.GET and request.session.get('not_granted_step', False):
            fb_login_redirect = Template('https://www.facebook.com/v2.8/dialog/oauth?'
                                         'client_id=1147337505373379&'
                                         'redirect_uri=https://sistema.marviin.com.br/fb_login/&'
                                         'state=$arg1&'
                                         'response_type=code')
            del request.session['not_granted_step']
            request.session['skip_perm'] = True
            return redirect(fb_login_redirect.substitute(arg1=state))
        else:
            fb_login_redirect = Template('https://www.facebook.com/v2.8/dialog/oauth?'
                                         'client_id=1147337505373379&'
                                         'redirect_uri=https://sistema.marviin.com.br/fb_login/&'
                                         'state=$arg1&'
                                         'scope=$arg2&'
                                         'auth_type=$arg3&'
                                         'response_type=code')
        if 'perm' not in request.GET:
            arg2 = 'public_profile,email,user_birthday'
            arg3 = 'reauthenticate'
        else:
            arg2 = request.GET['perm']
            arg3 = 'rerequest'
        return redirect(fb_login_redirect.substitute(arg1=state, arg2=arg2, arg3=arg3))
    if 'code' in request.GET and 'state' in request.GET:
        user_code = request.GET['code']
        user_state = request.GET['state']
        try:
            user_temp = FacebookTemp.objects.get(id=user_state)
            FacebookTemp.objects.filter(id=user_state).delete()
        except FacebookTemp.DoesNotExist:
            logger.error('-=-=-=- FacebookTemp.DoesNotExist -=-=-=-')
            return render(request, 'fb_login_fail.html',
                          {'message': u'Não é possível prosseguir com seu login, pois foi detectada uma falha de '
                                      u'segurança. Certifique-se que você esteja em uma rede segura e tente seu login '
                                      u'novamente. Obrigado.'})
        fb_code_to_token = Template('https://graph.facebook.com/v2.8/oauth/access_token?'
                                    'client_id=1147337505373379&'
                                    'client_secret=$arg1&'
                                    'code=$arg2&'
                                    'redirect_uri=https://sistema.marviin.com.br/fb_login/')
        url_code_to_token = fb_code_to_token.substitute(arg1=settings.FB_APPS['1147337505373379'],
                                                        arg2=user_code)
        response = fb_request(fb_url=url_code_to_token)
        if response is None:
            logger.error('-=-=-=- Nao houve resposta a chamada url_code_to_token -=-=-=-')
            return render(request, 'fb_authorize_fail.html',
                          {'type': 500, 'message': u'Foi detectada uma falha no seu processo de Login. '
                                                   u'Por favor, tente novamente clicando no botão abaixo. Obrigado.',
                           'redirect_uri': user_temp.redirect_uri,
                           'account_linking_token': user_temp.account_linking_token})
        code_to_token = response.json()
        if 'access_token' not in code_to_token:
            logger.error('-=-=-=- access_token nao encontrado na resposta de url_code_to_token -=-=-=- ' +
                         repr(code_to_token))
            return render(request, 'fb_authorize_fail.html',
                          {'type': 500, 'message': u'Foi detectada uma falha no seu processo de Login. '
                                                   u'Por favor, tente novamente clicando no botão abaixo. Obrigado.',
                           'redirect_uri': user_temp.redirect_uri,
                           'account_linking_token': user_temp.account_linking_token})
        access_token = code_to_token['access_token']
        fb_check_token = Template('https://graph.facebook.com/debug_token?input_token=$arg1&'
                                  'access_token=1147337505373379|$arg2')
        url_check_token = fb_check_token.substitute(arg1=access_token,
                                                    arg2=settings.FB_APPS['1147337505373379'])
        response = fb_request(fb_url=url_check_token)
        if response is None:
            logger.error('-=-=-=- Nao houve resposta a chamada url_check_token -=-=-=-')
            return render(request, 'fb_authorize_fail.html',
                          {'type': 500, 'message': u'Foi detectada uma falha no seu processo de Login. '
                                                   u'Por favor, tente novamente clicando no botão abaixo. Obrigado.',
                           'redirect_uri': user_temp.redirect_uri,
                           'account_linking_token': user_temp.account_linking_token})
        token_info = response.json()
        if 'data' not in token_info:
            logger.error('-=-=-=- data nao encontrado na resposta de url_check_token -=-=-=- ' + repr(token_info))
            return render(request, 'fb_authorize_fail.html',
                          {'type': 500, 'message': u'Foi detectada uma falha no seu processo de Login. '
                                                   u'Por favor, tente novamente clicando no botão abaixo. Obrigado.',
                           'redirect_uri': user_temp.redirect_uri,
                           'account_linking_token': user_temp.account_linking_token})
        if token_info['data']['app_id'] != '1147337505373379':
            logger.error('-=-=-=- app_id nao confere -=-=-=- ' + repr(token_info))
            return render(request, 'fb_authorize_fail.html',
                          {'type': 500, 'message': u'Foi detectada uma falha no seu processo de Login. '
                                                   u'Por favor, tente novamente clicando no botão abaixo. Obrigado.',
                           'redirect_uri': user_temp.redirect_uri,
                           'account_linking_token': user_temp.account_linking_token})
        user_id = token_info['data']['user_id']
        fb_user_info = Template('https://graph.facebook.com/v2.8/$arg1?access_token=$arg2')
        url_user_info = fb_user_info.substitute(arg1=user_id,
                                                arg2=access_token)
        response = fb_request(fb_url=url_user_info)
        if response is None:
            logger.error('-=-=-=- Nao houve resposta a chamada url_user_info -=-=-=-')
            return render(request, 'fb_authorize_fail.html',
                          {'type': 500, 'message': u'Foi detectada uma falha no seu processo de Login. '
                                                   u'Por favor, tente novamente clicando no botão abaixo. Obrigado.',
                           'redirect_uri': user_temp.redirect_uri,
                           'account_linking_token': user_temp.account_linking_token})
        user_info = response.json()
        if 'name' not in user_info:
            logger.error('-=-=-=- name nao encontrado para user_id:: ' + user_id + ' -=-=-=- ' + repr(user_info))
            return render(request, 'fb_authorize_fail.html',
                          {'type': 500, 'message': u'Foi detectada uma falha no seu processo de Login. '
                                                   u'Por favor, tente novamente clicando no botão abaixo. Obrigado.',
                           'redirect_uri': user_temp.redirect_uri,
                           'account_linking_token': user_temp.account_linking_token})
        fb_user_permissions = Template('https://graph.facebook.com/v2.8/$arg1/permissions?access_token=$arg2')
        url_user_permissions = fb_user_permissions.substitute(arg1=user_id,
                                                              arg2=access_token)
        response = fb_request(fb_url=url_user_permissions)
        if response is None:
            logger.error('-=-=-=- Nao houve resposta a chamada url_user_permissions -=-=-=-')
            return render(request, 'fb_authorize_fail.html',
                          {'type': 500, 'message': u'Foi detectada uma falha no seu processo de Login. '
                                                   u'Por favor, tente novamente clicando no botão abaixo. '
                                                   u'Obrigado.',
                           'redirect_uri': user_temp.redirect_uri,
                           'account_linking_token': user_temp.account_linking_token})
        user_permissions = response.json()
        if 'data' not in user_permissions:
            logger.error('-=-=-=- data nao encontrado na resposta de url_user_permissions -=-=-=- ' +
                         repr(user_permissions))
            return render(request, 'fb_authorize_fail.html',
                          {'type': 500, 'message': u'Foi detectada uma falha no seu processo de Login. '
                                                   u'Por favor, tente novamente clicando no botão abaixo. '
                                                   u'Obrigado.',
                           'redirect_uri': user_temp.redirect_uri,
                           'account_linking_token': user_temp.account_linking_token})
        not_granted = []
        for user_permission in user_permissions['data']:
            if user_permission['status'] != 'granted':
                not_granted.append(user_permission['permission'])
        try:
            user = Facebook.objects.get(user_id=user_id)
        except Facebook.DoesNotExist:
            pass
        if not request.session.get('skip_perm', False) and (user is None or not user.skip_perm):
            if len(not_granted) > 0:
                logger.error('-=-=-=- permissoes nao dadas -=-=-=- ' + repr(not_granted))
                if not request.session.session_key:
                    request.session.create()
                    request.session.set_expiry(300)  # 5 minutos
                request.session['not_granted_step'] = True
                return render(request, 'fb_authorize_fail.html',
                              {'type': 400, 'message': u'Olá {0}, notei que você não gostaria de compartilhar algumas '
                                                       u'das informações que lhe pedi permissão. Estas informações '
                                                       u'servem somente para uma melhor experiência conosco. Caso mude '
                                                       u'de idéia, clique no botão do Facebook abaixo, ou clique em '
                                                       u'continuar para finalizar o processo de login. Você também '
                                                       u'poderá dar estas permissões mais tarde, acessando sua área '
                                                       u'privada através do nosso site '
                                                       u'<A DEFINIR>'.format(user_info['name']),
                               'redirect_uri': user_temp.redirect_uri,
                               'account_linking_token': user_temp.account_linking_token, 'perm': not_granted})
        else:
            if user is None:
                while True:
                    try:
                        with transaction.atomic():
                            user = Facebook.objects.create(id=str(uuid.uuid4()))
                        break
                    except IntegrityError:
                        continue
            user.user_id = user_id
            if len(not_granted) > 0:
                user.perm_not_granted = ','.join(not_granted)
            if request.session.get('skip_perm', False):
                user.skip_perm = request.session.get('skip_perm', False)
            raw_auth_code = str(uuid.uuid4())
            signed_auth_code = signing.dumps(raw_auth_code, compress=True)
            user.authorization_code = signed_auth_code + '#' + raw_auth_code
            user.save()
            return redirect('{0}&authorization_code={1}'.format(user_temp.redirect_uri,
                                                                signed_auth_code))
    else:
        logger.error('-=-=-=- Acesso inválido ao login -=-=-=-')
        return render(request, 'fb_login_fail.html',
                      {'message': u'Não é possível prosseguir com seu login. Este acesso só pode ser feito a partir '
                                  u'do Messenger. Obrigado.'})


def fb_request(method=None, fb_url=None, json=None):
    try:
        return requests.request(method or "GET", fb_url, json=json)
    except requests.RequestException as e:
        response = json.loads(e.read())
        logger.error('!!!ERROR!!! ' + repr(response))
        return None


def fail_response(status_code, message):
    return {"success": False, "type": status_code, "message": message}
