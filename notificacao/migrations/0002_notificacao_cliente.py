# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-09-18 18:35
from __future__ import unicode_literals

from django.db import migrations
import django.db.models.deletion
import utils.bigint


class Migration(migrations.Migration):

    dependencies = [
        ('cliente', '0005_auto_20160918_1306'),
        ('notificacao', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificacao',
            name='cliente',
            field=utils.bigint.BigForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='cliente.Cliente'),
        ),
    ]