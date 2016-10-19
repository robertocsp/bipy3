# -*- coding: utf-8 -*-

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from cliente.models import Cliente
from django.utils import timezone
from django.db.models import Q

import datetime
import logging

logger = logging.getLogger('django')


@login_required
def relacionamento(request):
    data_hora_filtro = timezone.now() - datetime.timedelta(days=1)
    clientes = Cliente.objects.filter(Q(data_interacao__gt=data_hora_filtro) | Q(data_interacao__lt=data_hora_filtro,
                                                                                 mensagens=0))
    if clientes:
        for cliente in clientes:
            logger.debug(cliente.mensagens)
    return render(request, 'relacionamento.html')
