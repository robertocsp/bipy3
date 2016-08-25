# -*- coding: utf-8 -*-

from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.template import RequestContext

from pedido.models import Pedido

import datetime
import logging

logger = logging.getLogger('django')


@login_required(login_url='/')
def pedidos(request):
    data_pedido = datetime.date.today()
    # pedidos = Pedido.objects.filter(loja=1, data=data_pedido).order_by('status').select_related('cliente')
    pedidos = Pedido.objects.filter(loja=1).order_by('status', 'data', 'hora').select_related('cliente')
    if pedidos:
        solicitado = [pedido for pedido in pedidos if pedido.status == 'solicitado']
        em_processamento = [pedido for pedido in pedidos if pedido.status == 'emprocessamento']
        concluido = [pedido for pedido in pedidos if pedido.status == 'concluido']
        entregue = [pedido for pedido in pedidos if pedido.status == 'entregue']
        cancelado = [pedido for pedido in pedidos if pedido.status == 'cancelado']
    else:
        solicitado = []
        em_processamento = []
        concluido = []
        entregue = []
        cancelado = []
    logger.debug('-=-=-=-=-=-=-=- pedidos solicitados: ' + repr(solicitado))
    logger.debug('-=-=-=-=-=-=-=- pedidos em_processamento: ' + repr(em_processamento))
    logger.debug('-=-=-=-=-=-=-=- pedidos concluido: ' + repr(concluido))
    logger.debug('-=-=-=-=-=-=-=- pedidos entregue: ' + repr(entregue))
    logger.debug('-=-=-=-=-=-=-=- pedidos cancelado: ' + repr(cancelado))
    return render_to_response('pedidos.html', {'solicitado': solicitado, 'em_processamento': em_processamento,
                                               'concluido': concluido, 'entregue': entregue, 'cancelado': cancelado},
                              context_instance=RequestContext(request))
