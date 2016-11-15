# -*- coding: utf-8 -*-
from loja.models import *
from cliente.models import *
from utils.bigint import BigForeignKey

import logging

logger = logging.getLogger('django')


class Cardapio(models.Model):
    chave = models.CharField(max_length=32, blank=False, null=False)
    nome = models.CharField(max_length=100, blank=False, null=False)
    tamanho = models.FloatField('tamanho', blank=False, null=False)
    caminho = models.CharField(max_length=200, blank=False, null=False)
    loja = BigForeignKey(Loja, null=True, blank=True)
    pagina = models.IntegerField(blank=False, null=False, default=0)

    def as_dict(self):
        return {
            'chave': self.chave,
            'nome': self.nome,
            'tamanho': self.tamanho,
            'caminho': self.caminho,
            'pagina': self.pagina
        }
