# -*- coding: utf-8 -*-

from marviin.forms import *
from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponseRedirect
from django.contrib.auth.models import User

from loja.models import Loja


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
