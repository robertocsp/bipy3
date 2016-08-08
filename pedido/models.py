# -*- coding: utf-8 -*-
from django.db import models
from loja.models import *
from cliente.models import *
from jsonfield import JSONField
# Create your models here.pip

class Pedido(models.Model):
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
    data = models.DateField(auto_now=True, auto_now_add=False)
    hora = models.TimeField(auto_now=True, auto_now_add=False, null=True)
    ORIGEM = (
        ("telegram", "Telegram"),
        ("fbmessenger", "Facebook Messenger"),
    )
    origem = models.CharField(max_length=20, choices=ORIGEM, blank=True, null=True)

    loja = models.ForeignKey(Loja, null=True, blank=True)
    cliente = models.ForeignKey(Cliente, null=True, blank=True)

    def __unicode__(self):
        return repr(self.numero) + ';' + repr(self.data) + ';' + repr(self.status)


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, null=True, blank=True)
    produto = models.CharField('produto', max_length=100, blank=True, null=True)
    valor = models.FloatField('valor', blank=True, null=True)
    quantidade = models.IntegerField('quantidade', blank=True, null=True)
