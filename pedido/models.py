# -*- coding: utf-8 -*-
from loja.models import *
from cliente.models import *
from jsonfield import JSONField
from utils import BigForeignKey

import datetime
import logging

logger = logging.getLogger('django')


class Pedido(models.Model):
    id = BigAutoField(primary_key=True, editable=False)
    numero = models.IntegerField('numero', default=0)
    valor = models.FloatField('valor', blank=True, null=True)
    FORMAPAGAMENTO = (
        ("credito", "Crédito"),
        ("debito", "Débito"),
        ("dinheiro", "Dinheiro"),
        ("cheque", "Cheque"),
    )
    formapagamento = models.CharField(max_length=20, choices=FORMAPAGAMENTO, blank=True, null=True)
    historico = JSONField()
    STATUS = (
        ("solicitado", "Solicitado"),
        ("cancelado", "Cancelado"),
        ("entregue", "Entregue"),
        ("emprocessamento", "Em Processamento"),
        ("concluido", "Concluído"),
    )
    status = models.CharField(max_length=20, choices=STATUS, blank=True, null=True)
    data = models.DateField(editable=False)
    hora = models.TimeField(editable=False, null=True)
    modificado = models.DateTimeField(null=True)
    ORIGEM = (
        ("telegram", "Telegram"),
        ("fbmessenger", "Facebook Messenger"),
    )
    origem = models.CharField(max_length=20, choices=ORIGEM, blank=True, null=True)
    mesa = models.CharField(max_length=50, blank=True, null=True)
    loja = models.ForeignKey(Loja, null=True, blank=True)
    cliente = BigForeignKey(Cliente, null=True, blank=True)

    def save(self, *args, **kwargs):
        ''' On save, update timestamps '''
        self.modificado = datetime.datetime.today()
        if not self.id:
            self.data = self.modificado
            self.hora = self.data.time()
        logger.debug('-=-=-=-=-=-=-=- modificado 2: ' + repr(self.modificado))
        # banco armazena a DateTimeField como UTC, a data e hora separada é armazenada no timezone corrente.
        return super(Pedido, self).save(*args, **kwargs)
        '''
Make sure you read Django's timezone documentation. The approach is succinctly stated in the very first sentence:

When support for time zones is enabled, Django stores datetime information in UTC in the database, uses
time-zone-aware datetime objects internally, and translates them to the end user’s time zone in templates and forms.
So, yes, it is normal that you see the return value from the database in UTC.

As for why, the documentation states:

Even if your Web site is available in only one time zone, it’s still good practice to store data in UTC in your
database. The main reason is Daylight Saving Time (DST). Many countries have a system of DST, where clocks are
moved forward in spring and backward in autumn. If you’re working in local time, you’re likely to encounter errors
twice a year, when the transitions happen.
It also links to a more detailed description in the pytz documentation.
        '''

    def __unicode__(self):
        return repr(self.numero) + ';' + repr(self.data) + ';' + repr(self.status)


class ItemPedido(models.Model):
    id = BigAutoField(primary_key=True, editable=False)
    pedido = BigForeignKey(Pedido, null=True, blank=True, related_name='itens', on_delete=models.CASCADE)
    produto = models.CharField('produto', max_length=100, blank=True, null=True)
    valor = models.FloatField('valor', blank=True, null=True)
    quantidade = models.IntegerField('quantidade', blank=True, null=True)
