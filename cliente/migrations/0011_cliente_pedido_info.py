# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-12-10 15:09
from __future__ import unicode_literals

from django.db import migrations
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('cliente', '0010_cliente_cliente_marviin'),
    ]

    operations = [
        migrations.AddField(
            model_name='cliente',
            name='pedido_info',
            field=jsonfield.fields.JSONField(blank=True, null=True),
        ),
    ]
