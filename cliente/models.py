# -*- coding: utf-8 -*-
from django.db import models
from utils import BigAutoField, BigForeignKey
from marviin.cliente_marviin.models import Facebook
from loja.models import Loja
from jsonfield import JSONField

import datetime


class Cliente(models.Model):
    id = BigAutoField(primary_key=True, editable=False)
    nome = models.CharField('nome', max_length=200, null=True, blank=True)
    telefone = models.CharField('telefone', max_length=20, null=True, blank=True)
    chave_telegram = models.CharField('chave_telegram', max_length=20, unique=True, null=True, blank=True)
    # cheguei a este tamanho a partir deste post:
    # http://stackoverflow.com/questions/7566672/whats-the-max-length-of-a-facebook-uid
    chave_facebook = models.CharField('chave_facebook', max_length=128, unique=True, null=True, blank=True)
    foto = models.CharField('foto', max_length=255, null=True, blank=True)
    data_interacao = models.DateTimeField(null=True)
    mensagens = models.IntegerField('numero', default=0)
    genero = models.CharField('genero', max_length=20, null=True, blank=True)
    # loja = BigForeignKey(Loja, null=True, blank=True)
    id_loja_facebook = models.CharField('id_loja_facebook', max_length=128, null=True, blank=True)
    cliente_marviin = models.ForeignKey(Facebook, null=True, blank=True)
    pedido_info = JSONField(null=True, blank=True)

    def save(self, *args, **kwargs):
        ''' On save, update timestamps '''
        self.data_interacao = datetime.datetime.today()
        # banco armazena a DateTimeField como UTC, a data e hora separada é armazenada no timezone corrente.
        return super(Cliente, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.nome

