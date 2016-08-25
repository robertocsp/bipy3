# -*- coding: utf-8 -*-

from django import template

import datetime
import time
import logging

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
