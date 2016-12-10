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


@receiver(post_save, sender=User)
def create_cliente_marviin(sender, instance, created, **kwargs):
    if created:
        ClienteMarviin.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_cliente_marviin(sender, instance, **kwargs):
    try:
        instance.cliente_marviin.save()
    except ObjectDoesNotExist:
        ClienteMarviin.objects.create(user=instance)


class Endereco(models.Model):
    id = BigAutoField(primary_key=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
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
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    nome_cartao = models.CharField('nome_cartao', max_length=100)
    bandeira = models.SmallIntegerField('bandeira')  # 1: visa / 2: master
