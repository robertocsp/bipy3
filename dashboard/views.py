# -*- coding: utf-8 -*-

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

import logging

logger = logging.getLogger('django')


@login_required
def dashboard(request):
    # exemplo
    variaveis = 0
    return render(request, 'dashboard.html', {'variaveis': variaveis})


@login_required
def login(request):
    return render(request, 'login.html')


@login_required
def home(request):
    return render(request, 'index.html')


@login_required
def cadastro(request):
    return render(request, 'cadastro.html')


@login_required
def termos(request):
    return render(request, 'termos.html')

@login_required
def cadastraCardapio(request):
    return render(request, 'cad-cardapio.html')

@login_required
def pedidos_delivery(request):
    return render(request, 'pedido-delivery.html')

@login_required
def pagamento(request):
    return render(request, 'pagamento.html')
