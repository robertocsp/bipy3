# -*- coding: utf-8 -*-
from django.db import models
# Create your models here.

class Cliente(models.Model):
    nome = models.CharField('nome', max_length=200, null=True, blank=True)
    telefone = models.CharField('telefone', max_length=20, unique=True, null=True, blank=True)
    chave_telegram = models.CharField('chave_telegram', max_length=20, unique=True, null=True, blank=True)
    #cheguei a este tamanho a partir deste post: http://stackoverflow.com/questions/7566672/whats-the-max-length-of-a-facebook-uid
    chave_facebook = models.CharField('chave_facebook', max_length=128, unique=True, null=True, blank=True)

    def __unicode__(self):
        return self.nome

