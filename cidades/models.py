from __future__ import unicode_literals

from django.db import models
from estados.models import Estado


class Cidade(models.Model):
    uf = models.ForeignKey(Estado, null=False, blank=False)
    nome_cidade = models.CharField('nome_cidade', max_length=30, null=False, blank=False)
