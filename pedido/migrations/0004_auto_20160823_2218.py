# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-08-24 01:18
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pedido', '0003_pedido_mesa'),
    ]

    operations = [
        migrations.AlterField(
            model_name='itempedido',
            name='pedido',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='itens', to='pedido.Pedido'),
        ),
    ]
