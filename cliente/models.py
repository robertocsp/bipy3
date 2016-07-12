# -*- coding: utf-8 -*-
from django.db import models
# Create your models here.

class Cliente(models.Model):
    nome = models.CharField('nome', max_length=200, null=True, blank=True)
    telefone = models.CharField('telefone', max_length=20, unique=True, null=True, blank=True)

    def __unicode__(self):
        return self.nome

