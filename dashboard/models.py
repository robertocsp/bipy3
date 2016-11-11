# -*- coding: utf-8 -*-
from django.db import models
from loja.models import *
import utils.bigint
# Create your models here.


class Dashboard(models.Model):
    nome = models.CharField('nome', max_length=100, null=True, blank=True)
    loja = utils.bigint.BigForeignKey(Loja, null=True, blank=True)

    def __unicode__(self):
        return self.nome

