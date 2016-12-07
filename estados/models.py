from __future__ import unicode_literals

from django.db import models


class Estado(models.Model):
    nome_uf = models.CharField('nome_uf', max_length=30, null=False, blank=False)
    sigla_uf = models.CharField('sigla_uf', max_length=2, null=False, blank=False)
