# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-12-13 01:13
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cliente_marviin', '0002_endereco_padrao'),
    ]

    operations = [
        migrations.AddField(
            model_name='clientemarviin',
            name='mail_mkt',
            field=models.BooleanField(default=False),
            preserve_default=False,
        ),
    ]