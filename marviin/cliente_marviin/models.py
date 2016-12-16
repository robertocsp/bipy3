from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User
from utils import BigAutoField
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist


class ClienteMarviin(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='cliente_marviin')
    cpf = models.CharField('cpf', max_length=11, null=True, blank=True)
    authorization_code = models.CharField('authorization_code', max_length=200, null=True, blank=True)
    mail_mkt = models.BooleanField()


class FacebookTemp(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    redirect_uri = models.CharField(max_length=700, blank=True, null=True)
    account_linking_token = models.CharField(max_length=500, blank=True, null=True)


class Facebook(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user_id = models.CharField(max_length=128)
    authorization_code = models.CharField(max_length=200)
    perm_not_granted = models.CharField(max_length=200, blank=True, null=True)
    skip_perm = models.BooleanField(default=False)
    cpf = models.CharField('cpf', max_length=11, null=True, blank=True)


class Endereco(models.Model):
    id = BigAutoField(primary_key=True, editable=False)
    user = models.ForeignKey(Facebook, on_delete=models.CASCADE)
    endereco = models.CharField('endereco', max_length=200)
    complemento = models.CharField('complemento', max_length=100)
    bairro = models.CharField('bairro', max_length=100)
    cep = models.CharField('cep', max_length=15)
    estado = models.CharField('estado', max_length=2)
    cidade = models.CharField('cidade', max_length=100)
    tipo = models.SmallIntegerField('tipo')  # 1: entrega / 2: cobranca / 3: 1 e 2
    padrao = models.BooleanField()


class Cartao(models.Model):
    id = BigAutoField(primary_key=True, editable=False)
    user = models.ForeignKey(Facebook, on_delete=models.CASCADE)
    nome_cartao = models.CharField('nome_cartao', max_length=100)
    bandeira = models.SmallIntegerField('bandeira')  # 1: visa / 2: master
