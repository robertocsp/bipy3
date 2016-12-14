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
from django.db import transaction

from loja.models import Loja
from marviin.cliente_marviin.models import ClienteMarviin, Facebook, FacebookTemp

from string import Template

import requests
import logging
import uuid

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


def fb_endereco(request):
    if request.method == 'GET':
        return render(request, 'fb_endereco.html')


def fb_criarconta(request):
    if request.method == 'GET':
        return render(request, 'fb_criarconta.html')
    elif request.method == 'POST':
        psid = request.POST['psid']
        nome = request.POST['nome']
        cpf = request.POST['cpf']
        telefone = request.POST['telefone']
        email = request.POST['email']
        termos = request.POST['termos']
        mailmkt = request.POST['mailmkt']


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
        fb_login_redirect = Template('https://www.facebook.com/v2.8/dialog/oauth?'
                                     'client_id=1147337505373379&'
                                     'redirect_uri=https://sistema.marviin.com.br/fb_login&'
                                     'state=$arg1&'
                                     'scope=public_profile,email,user_birthday&'
                                     'auth_type=reauthenticate&'
                                     'response_type=code%20token')
        logger.info('-=-=-=-1 redirect_uri -=-=-=-' + redirect_uri)
        logger.info('-=-=-=-1 account_linking_token -=-=-=-' + account_linking_token)
        logger.info('-=-=-=-1 state -=-=-=-' + state)
        return redirect(fb_login_redirect.substitute(arg1=state))
    elif 'code' in request.GET and 'state' in request.GET and 'token' in request.GET:
        user_code = request.GET['code']
        user_state = request.GET['state']
        user_token = request.GET['token']
        logger.info('-=-=-=-2 code -=-=-=-' + user_code)
        logger.info('-=-=-=-2 state -=-=-=-' + user_state)
        logger.info('-=-=-=-2 token -=-=-=-' + user_token)
        try:
            user_temp = FacebookTemp.objects.get(id=state)
            FacebookTemp.objects.filter(id=state).delete()
        except FacebookTemp.DoesNotExist:
            return fail_response(400, u'{"type": "msg", "object": "Cód. 1: Estado inválido."}')
        fb_code_to_token = Template('https://graph.facebook.com/v2.8/oauth/access_token?'
                                    'client_id=1147337505373379&'
                                    'client_secret=$arg1&'
                                    'code=$arg2&'
                                    'redirect_uri=https://acesso.marviin.com.br/')
        url_code_to_token = fb_code_to_token.substitute(arg1=settings.FB_APPS['1147337505373379'],
                                                        arg2=user_code)
        response = fb_request(fb_url=url_code_to_token)
        if response is None:
            return fail_response(500, u'{"type": "msg", "object": "Cód. 1: Falha na verificação do código FB."}')
        code_to_token = response.json()
        logger.info('-=-=-=-2 code_to_token json ' + repr(code_to_token))
        if 'access_token' not in code_to_token:
            return fail_response(500, u'{"type": "msg", "object": "Cód. 2: Falha na verificação do código FB."}')
        access_token = code_to_token['access_token']
        fb_check_token = Template('https://graph.facebook.com/debug_token?input_token=$arg1&'
                                  'access_token=1147337505373379|$arg2')
        url_check_token = fb_check_token.substitute(arg1=access_token,
                                                    arg2=settings.FB_APPS['1147337505373379'])
        response = fb_request(fb_url=url_check_token)
        if response is None:
            return fail_response(500, u'{"type": "msg", "object": "Cód. 3: Falha na verificação do token FB."}')
        token_info = response.json()
        logger.info('-=-=-=-2 check_token json ' + repr(token_info))
        if 'data' not in token_info:
            return fail_response(500, u'{"type": "msg", "object": "Cód. 4: Falha na verificação do token FB."}')
        if token_info['data']['app_id'] != '1147337505373379':
            return fail_response(500, u'{"type": "msg", "object": "Cód. 5: Falha na verificação do token FB."}')
        user_id = token_info['data']['user_id']
        fb_user_info = Template('https://graph.facebook.com/v2.8/$arg1?access_token=$arg2')
        url_user_info = fb_user_info.substitute(arg1=user_id,
                                                arg2=access_token)
        response = fb_request(fb_url=url_user_info)
        if response is None:
            return fail_response(500, u'{"type": "msg", "object": "Cód. 6: Falha ao validar usuário FB."}')
        user_info = response.json()
        logger.info('-=-=-=- user_info json ' + repr(user_info))
        if 'name' not in user_info:
            return fail_response(500, u'{"type": "msg", "object": "Cód. 7: Falha ao validar usuário FB."}')
        fb_user_permissions = Template('https://graph.facebook.com/v2.8/$arg1/permissions?access_token=$arg2')
        url_user_permissions = fb_user_permissions.substitute(arg1=user_id,
                                                              arg2=access_token)
        response = fb_request(fb_url=url_user_permissions)
        if response is None:
            return fail_response(500, u'{"type": "msg", "object": "Cód. 8: Falha ao validar permissões FB."}')
        user_permissions = response.json()
        logger.info('-=-=-=- user_permissions json ' + repr(user_permissions))
        if 'data' not in user_permissions:
            return fail_response(500, u'{"type": "msg", "object": "Cód. 9: Falha ao validar permissões FB."}')
        not_granted = []
        for user_permission in user_permissions['data']:
            if user_permission['status'] != 'granted':
                not_granted.append(user_permission['permission'])
        if len(not_granted) > 0:
            pass
        else:
            # TODO tratamento de erros e salvar usuario
            user = Facebook()
            raw_auth_code = str(uuid.uuid4())
            user.authorization_code = signing.dumps(raw_auth_code, compress=True) + '#' + raw_auth_code
            logger.info('-=-=-=- user logged in ' + repr(user.authorization_code))
            return redirect('{0}&authorization_code={1}'.format(user_temp.redirect_uri,
                                                                user.authorization_code))


def fb_request(method=None, fb_url=None, json=None):
    try:
        return requests.request(method or "GET", fb_url, json=json)
    except requests.RequestException as e:
        response = json.loads(e.read())
        logger.error('!!!ERROR!!! ' + repr(response))
        return None


def fail_response(status_code, message):
    return {"success": False, "type": status_code, "message": message}
