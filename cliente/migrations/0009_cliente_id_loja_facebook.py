# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-11-27 12:16
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cliente', '0008_cliente_genero'),
    ]

    operations = [
        migrations.AddField(
            model_name='cliente',
            name='id_loja_facebook',
            field=models.CharField(blank=True, max_length=128, null=True, unique=True, verbose_name=b'id_loja_facebook'),
        ),
    ]