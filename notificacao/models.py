# -*- coding: utf-8 -*-
from jsonfield import JSONField
from loja.models import *
from cliente.models import *
from utils import BigAutoField, BigForeignKey

import datetime
import uuid
import logging

logger = logging.getLogger('django')


class Notificacao(models.Model):
    id = BigAutoField(primary_key=True, editable=False)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    loja = models.ForeignKey(Loja, null=False, blank=False)
    info = JSONField()
    dt_criado = models.DateTimeField(null=False)
    dt_visto = models.DateTimeField(null=True)
    cliente = BigForeignKey(Cliente, null=True, blank=False)

    def save(self, *args, **kwargs):
        ''' On save, update timestamps '''
        if not self.id:
            self.dt_criado = datetime.datetime.today()
        # banco armazena a DateTimeField como UTC
        return super(Notificacao, self).save(*args, **kwargs)
