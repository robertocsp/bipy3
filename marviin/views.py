# -*- coding: utf-8 -*-

from marviin.forms import *
from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponseRedirect
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect
from django.core import signing

from loja.models import Loja
from marviin.cliente_marviin.models import ClienteMarviin

import logging

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
    redirect_uri = request.data.get('redirect_uri', None)
    account_linking_token = request.data.get('account_linking_token', None)
    logger.info('-=-=-=- redirect_uri -=-=-=-' + redirect_uri)
    logger.info('-=-=-=- account_linking_token -=-=-=-' + account_linking_token)
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid() and redirect_uri is not None and account_linking_token is not None:
            username = form.username
            senha = form.senha
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
                user.cliente_marviin.authorization_code = signing.dumps('autorizado', compress=True)
                user.cliente_marviin.authorization_code.save()
                redirect('{0}?account_linking_token={1}&authorization_code={2}'.format(
                    redirect_uri, account_linking_token, user.cliente_marviin.authorization_code))
            else:
                redirect('{0}?account_linking_token={1}'.format(redirect_uri, account_linking_token))
        else:
            redirect('{0}?account_linking_token={1}'.format(redirect_uri, account_linking_token))
    else:
        form = LoginForm()
        return render(request, 'fb_authorize.html', {'form': form, 'redirect_uri': redirect_uri,
                                                     'account_linking_token': account_linking_token})
