# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-08-08 00:41
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pedido', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pedido',
            name='status',
            field=models.CharField(blank=True, choices=[(b'solicitado', b'Solicitado'), (b'cancelado', b'Cancelado'), (b'entregue', b'Entregue'), (b'emprocessamento', b'Em Processamento'), (b'concluido', b'Conclu\xc3\xaddo')], max_length=20, null=True),
        ),
    ]
