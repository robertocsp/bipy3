# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2017-02-05 11:33
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Enviado',
            fields=[
                ('id', models.CharField(editable=False, max_length=50, primary_key=True, serialize=False)),
                ('celular', models.CharField(blank=True, max_length=30, null=True)),
                ('conteudo', models.CharField(blank=True, max_length=160, null=True)),
                ('data_hora_envio', models.DateTimeField(blank=True, null=True)),
                ('status', models.IntegerField(blank=True, null=True)),
                ('retorno_integracao', models.CharField(blank=True, max_length=200, null=True)),
            ],
        ),
    ]
