# -*- coding: utf-8 -*-

from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.db.models import Q

from pedido.models import Pedido

import datetime
import logging

logger = logging.getLogger('django')


@login_required(login_url='/')
def pedidos(request):
    data_filtro = None
    hora_filtro = None
    nome_cliente_filtro = None
    num_pedido_filtro = None
    if 'data_filtro' in request.POST and request.POST['data_filtro']:
        data_filtro = request.POST['data_filtro']
        hora_filtro = request.POST['hora_filtro']
        valor_data_filtro = datetime.datetime.strptime(data_filtro, '%d/%m/%Y').date()
        valor_hora_filtro = datetime.datetime.strptime(hora_filtro, '%H:%M').time()
        logger.debug('-=-=-=-=-=-=-=- data2 e hora2: ' + repr(valor_data_filtro) + ' - ' + repr(valor_hora_filtro))
    if 'nome_cliente_filtro' in request.POST and request.POST['nome_cliente_filtro']:
        nome_cliente_filtro = request.POST['nome_cliente_filtro']
    if 'num_pedido_filtro' in request.POST and request.POST['num_pedido_filtro']:
        num_pedido_filtro = request.POST['num_pedido_filtro']
        valor_data_pedido_filtro = datetime.datetime.strptime(num_pedido_filtro[:8], '%Y%m%d').date()
        valor_id_pedido_filtro = int(num_pedido_filtro[8:])
    id_loja = request.session['id_loja']
    if data_filtro and nome_cliente_filtro and num_pedido_filtro:
        if valor_data_filtro <= valor_data_pedido_filtro:
            pedidos_resultado = Pedido.objects.filter(
                Q(loja=id_loja, numero=valor_id_pedido_filtro, cliente__nome__icontains=nome_cliente_filtro),
                Q(data__gt=valor_data_filtro) | Q(data=valor_data_filtro, hora__gte=hora_filtro))\
                .order_by('status', 'data', 'hora').select_related('cliente')
        else:
            pedidos_resultado = None
    elif data_filtro and nome_cliente_filtro:
        pedidos_resultado = Pedido.objects.filter(
            Q(loja=id_loja, cliente__nome__icontains=nome_cliente_filtro),
            Q(data__gt=valor_data_filtro) | Q(data=valor_data_filtro, hora__gte=hora_filtro)) \
            .order_by('status', 'data', 'hora').select_related('cliente')
    elif data_filtro and num_pedido_filtro:
        if valor_data_filtro <= valor_data_pedido_filtro:
            pedidos_resultado = Pedido.objects.filter(
                Q(loja=id_loja, numero=valor_id_pedido_filtro),
                Q(data__gt=valor_data_filtro) | Q(data=valor_data_filtro, hora__gte=hora_filtro))\
                .order_by('status', 'data', 'hora').select_related('cliente')
        else:
            pedidos_resultado = None
    elif nome_cliente_filtro and num_pedido_filtro:
        pedidos_resultado = Pedido.objects.filter(
            loja=id_loja, numero=valor_id_pedido_filtro, cliente__nome__icontains=nome_cliente_filtro,
            data=valor_data_pedido_filtro).order_by('status', 'data', 'hora').select_related('cliente')
    elif nome_cliente_filtro:
        pedidos_resultado = Pedido.objects.filter(
            loja=id_loja, cliente__nome__icontains=nome_cliente_filtro)\
            .order_by('status', 'data', 'hora').select_related('cliente')
    elif num_pedido_filtro:
        pedidos_resultado = Pedido.objects.filter(
            loja=id_loja, numero=valor_id_pedido_filtro, data=valor_data_pedido_filtro)\
            .order_by('status', 'data', 'hora').select_related('cliente')
    elif data_filtro:
        pedidos_resultado = Pedido.objects.filter(
            Q(loja=id_loja),
            Q(data__gt=valor_data_filtro) | Q(data=valor_data_filtro, hora__gte=hora_filtro))\
            .order_by('status', 'data', 'hora').select_related('cliente')
    else:
        pedidos_resultado = Pedido.objects.filter(loja=id_loja).order_by('status', 'data', 'hora')\
            .select_related('cliente')
    if pedidos_resultado:
        solicitado = [pedido for pedido in pedidos_resultado if pedido.status == 'solicitado']
        em_processamento = [pedido for pedido in pedidos_resultado if pedido.status == 'emprocessamento']
        concluido = [pedido for pedido in pedidos_resultado if pedido.status == 'concluido']
        entregue = [pedido for pedido in pedidos_resultado if pedido.status == 'entregue']
        cancelado = [pedido for pedido in pedidos_resultado if pedido.status == 'cancelado']
    else:
        solicitado = []
        em_processamento = []
        concluido = []
        entregue = []
        cancelado = []
    return render_to_response('pedidos.html', {'solicitado': solicitado, 'em_processamento': em_processamento,
                                               'concluido': concluido, 'entregue': entregue, 'cancelado': cancelado,
                                               'filtros': {'data_filtro': data_filtro, 'hora_filtro': hora_filtro,
                                                           'nome_cliente_filtro': nome_cliente_filtro,
                                                           'num_pedido_filtro': num_pedido_filtro}},
                              context_instance=RequestContext(request))
