# -*- coding: utf-8 -*-

from django.shortcuts import render, render_to_response
from django.contrib.auth.decorators import login_required


@login_required(login_url='/')
def dashboard(request):
    # exemplo
    variaveis = 0
    return render(request, 'dashboard.html', {'variaveis': variaveis})


@login_required(login_url='/')
def login(request):
    return render(request, 'login.html')


@login_required(login_url='/')
def home(request):
    return render(request, 'index.html')


@login_required(login_url='/')
def upload(request):
    return render(request, 'upload.html')


@login_required(login_url='/')
def historico_pedidos(request):
    return render(request, 'historico.html')


@login_required(login_url='/')
def cadastro(request):
    return render(request, 'cadastro.html')

@login_required(login_url='/')
def relacionamento(request):
    return render(request, 'relacionamento.html')