# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.auth.models import Group
from jsonfield import JSONField
from utils import BigAutoField, BigForeignKey, BigOneToOneField

# Create your models here.


class Loja(models.Model):
    id = BigAutoField(primary_key=True, editable=False)
    id_loja_facebook = models.CharField('id_loja_facebook', max_length=128, unique=True, null=True, blank=True)
    nome = models.CharField('nome', max_length=100)
    nome_estabelecimento = models.CharField('nome_estabelecimento', max_length=100, null=True, blank=True)
    cnpj = models.CharField('cnpj', max_length=14, null=True, blank=True)
    endereco = models.CharField('endereco', max_length=200, null=True, blank=True)
    complemento = models.CharField('complemento', max_length=100, null=True, blank=True)
    bairro = models.CharField('bairro', max_length=100, null=True, blank=True)
    cep = models.CharField('cep', max_length=15, null=True, blank=True)
    estado = models.CharField('estado', max_length=2, null=True, blank=True)
    cidade = models.CharField('cidade', max_length=100, null=True, blank=True)
    telefone1 = models.CharField('telefone1', max_length=30, null=True, blank=True)
    telefone2 = models.CharField('telefone2', max_length=30, null=True, blank=True)
    email = models.CharField('email', max_length=100, null=True, blank=True)
    nome_contato = models.CharField('nome_contato', max_length=100, null=True, blank=True)
    group = models.ForeignKey(Group, null=True, blank=True)
    TIPOS_ESTABELECIMENTO = (
        ("bar", "Bar"),
        ("restaurante", "Restaurante"),
        ("lanchonete", "Lanchonete"),
        ("hotel", "Hotel"),
        ("padaria", "Padaria"),
        ("outro", "Outro"),
    )
    tipo_loja = models.CharField(max_length=20, choices=TIPOS_ESTABELECIMENTO, blank=True, null=True)
    outro_tipo_loja = models.CharField('outro_tipo_loja', max_length=100, null=True, blank=True)
    token_login = models.CharField('token_login', max_length=200, null=True, blank=True)

    def __unicode__(self):
        return self.nome


class Apps(models.Model):
    id = BigAutoField(primary_key=True, editable=False)
    loja = BigForeignKey(Loja)
    app = models.CharField(max_length=30, blank=False, null=False)
    ativa = models.BooleanField(default=False, blank=False, null=False)


class Questionario(models.Model):
    id = BigAutoField(primary_key=True, editable=False)
    loja = BigForeignKey(Loja, null=False, blank=False)
    descr_problemas = models.TextField('descr_problemas', null=True, blank=True)
    problemas = JSONField('problemas', null=True, blank=True)


class DemoSms(models.Model):
    loja = BigOneToOneField(Loja, primary_key=True, on_delete=models.CASCADE)
    quantidade = models.IntegerField(blank=True, null=True)


class DemoEmail(models.Model):
    loja = BigOneToOneField(Loja, primary_key=True, on_delete=models.CASCADE)
    quantidade = models.IntegerField(blank=True, null=True)
