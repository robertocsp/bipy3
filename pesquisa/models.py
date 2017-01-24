# -*- coding: utf-8 -*-
from loja.models import *
from utils import BigForeignKey


class Recomendar(models.Model):
    id = BigAutoField(primary_key=True, editable=False)
    loja = BigForeignKey(Loja, null=False, blank=False)
    cliente = models.CharField('cliente_fb', max_length=128, null=False, blank=False)
    app = models.CharField(max_length=30, blank=False, null=False)
    resposta = models.CharField(max_length=500, null=False, blank=False)
    data_resposta = models.DateTimeField(
        auto_now_add=True
    )
