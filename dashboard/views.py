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
def relacionamento(request):
    return render(request, 'relacionamento.html')


@login_required
def termos(request):
    return render(request, 'termos.html')