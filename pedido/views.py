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
    if 'data_filtro' in request.GET and request.GET['data_filtro']:
        data_filtro = request.GET['data_filtro']
        if 'hora_filtro' in request.GET and request.GET['hora_filtro']:
            hora_filtro = request.GET['hora_filtro']
    logger.debug('-=-=-=-=-=-=-=- data e hora: ' + repr(data_filtro) + ' - ' + repr(hora_filtro))
    if data_filtro:
        valor_data_filtro = datetime.datetime.strptime(data_filtro, '%d/%m/%Y').date()
        valor_hora_filtro = datetime.datetime.strptime(hora_filtro, '%H:%M').time()
        logger.debug('-=-=-=-=-=-=-=- data2 e hora2: ' + repr(valor_data_filtro) + ' - ' + repr(valor_hora_filtro))
        pedidos_resultado = Pedido.objects.filter(
            Q(loja=1),
            Q(data__gt=valor_data_filtro) | Q(data=valor_data_filtro, hora__gte=hora_filtro))\
            .order_by('status', 'data', 'hora').select_related('cliente')
    else:
        pedidos_resultado = Pedido.objects.filter(loja=1).order_by('status', 'data', 'hora').select_related('cliente')
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
                                               'filtros': {'data_filtro': data_filtro, 'hora_filtro': hora_filtro}},
                              context_instance=RequestContext(request))
