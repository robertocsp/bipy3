# -*- coding: utf-8 -*-

from django.shortcuts import render, render_to_response

def login(request):
    return render(request, 'login.html')

def home(request):
    return render(request, 'index.html')

def upload(request):
    return render(request, 'upload.html')

def pedidos(request):
    return render(request, 'pedidos.html')

def historico_pedidos(request):
    return render(request, 'historico.html')

def cadastro(request):
    return render(request, 'cadastro.html')