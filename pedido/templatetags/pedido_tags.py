# -*- coding: utf-8 -*-

from django import template
from django.utils import timezone

import datetime
import time
import logging
import pytz

logger = logging.getLogger('django')

register = template.Library()


@register.simple_tag
def minutos_passados(data, hora):
    data_hora = datetime.datetime.combine(data, hora)
    logger.debug('-=-=-=-=-=-=-=- data_hora.timetuple(): ' + repr(data_hora.timetuple()))
    logger.debug('-=-=-=-=-=-=-=- datetime.datetime.now().timetuple(): ' + repr(datetime.datetime.now().timetuple()))
    d1_ts = time.mktime(data_hora.timetuple())
    d2_ts = time.mktime(datetime.datetime.now().timetuple())
    minutos = int(d2_ts-d1_ts) / 60
    return minutos


@register.simple_tag
def pedido_uid(data, numero):
    return data.strftime('%Y%m%d') + repr(int(numero))


@register.simple_tag
def hora_notificacao(data):
    return data.replace(tzinfo=pytz.UTC).astimezone(timezone.get_current_timezone()).strftime('%H:%M')


@register.simple_tag
def paginacao_inicial(total_paginas, pagina, itens_visiveis):
    if pagina - itens_visiveis < 1:
        return 2
    elif (total_paginas - pagina) >= itens_visiveis:
        return pagina - ((pagina % 3) + 1)
    else:
        return total_paginas - itens_visiveis


@register.simple_tag
def paginacao_range(total_paginas, itens_visiveis):
    if total_paginas <= (itens_visiveis + 1):
        return 'x' * (total_paginas - 2)
    else:
        return 'x' * itens_visiveis


@register.simple_tag
def paginacao_pagina_equal(pagina, pagina_inicial, cont):
    return pagina == (pagina_inicial + cont)
