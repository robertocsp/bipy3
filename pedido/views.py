# -*- coding: utf-8 -*-

from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.db.models import Q
from django.utils import timezone

from pedido.models import Pedido
from notificacao.models import Notificacao

import datetime
import logging

logger = logging.getLogger('django')


@login_required(login_url='/')
def pedidos(request):
    nome_cliente_filtro = None
    num_pedido_filtro = None
    data_hora_filtro = datetime.datetime.today() - datetime.timedelta(days=1)
    valor_data_filtro = data_hora_filtro.date()
    valor_hora_filtro = data_hora_filtro.time()
    # data_hora2 = datetime.datetime.today().replace(tzinfo=timezone.get_default_timezone())
    logger.debug('-=-=-=-=-=-=-=- data e hora: ' + repr(valor_data_filtro) + ' - ' + repr(valor_hora_filtro))
    # logger.debug('-=-=-=-=-=-=-=- data2 e hora2: ' + repr(data_hora2.date()) + ' - ' + repr(data_hora2.time()))
    if 'nome_cliente_filtro' in request.POST and request.POST['nome_cliente_filtro']:
        nome_cliente_filtro = request.POST['nome_cliente_filtro']
    if 'num_pedido_filtro' in request.POST and request.POST['num_pedido_filtro']:
        num_pedido_filtro = request.POST['num_pedido_filtro']
        valor_data_pedido_filtro = datetime.datetime.strptime(num_pedido_filtro[:8], '%Y%m%d').date()
        valor_id_pedido_filtro = int(num_pedido_filtro[8:])
    id_loja = request.session['id_loja']
    if nome_cliente_filtro and num_pedido_filtro:
        pedidos_resultado = Pedido.objects.filter(
            Q(loja=id_loja, numero=valor_id_pedido_filtro, cliente__nome__icontains=nome_cliente_filtro),
            Q(data__gt=valor_data_filtro) | Q(data=valor_data_filtro, hora__gte=valor_hora_filtro)) \
            .order_by('status', 'data', 'hora').select_related('cliente')
    elif nome_cliente_filtro:
        pedidos_resultado = Pedido.objects.filter(
            Q(loja=id_loja, cliente__nome__icontains=nome_cliente_filtro),
            Q(data__gt=valor_data_filtro) | Q(data=valor_data_filtro, hora__gte=valor_hora_filtro)) \
            .order_by('status', 'data', 'hora').select_related('cliente')
    elif num_pedido_filtro:
        pedidos_resultado = Pedido.objects.filter(
            loja=id_loja, numero=valor_id_pedido_filtro, data=valor_data_pedido_filtro)\
            .order_by('status', 'data', 'hora').select_related('cliente')
    else:
        pedidos_resultado = Pedido.objects.filter(
            Q(loja=id_loja), Q(data__gt=valor_data_filtro) | Q(data=valor_data_filtro, hora__gte=valor_hora_filtro)) \
            .order_by('status', 'data', 'hora')\
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
    notificacoes = Notificacao.objects.filter(loja=id_loja, dt_visto__isnull=True).order_by('dt_criado')
    return render_to_response('pedidos.html', {'solicitado': solicitado, 'em_processamento': em_processamento,
                                               'concluido': concluido, 'entregue': entregue, 'cancelado': cancelado,
                                               'filtros': {'nome_cliente_filtro': nome_cliente_filtro,
                                                           'num_pedido_filtro': num_pedido_filtro},
                                               'notificacoes': notificacoes},
                              context_instance=RequestContext(request))
