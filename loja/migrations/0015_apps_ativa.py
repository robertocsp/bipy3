# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2017-01-12 11:53
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('loja', '0014_auto_20170112_0018'),
    ]

    operations = [
        migrations.AddField(
            model_name='apps',
            name='ativa',
            field=models.BooleanField(default=False),
        ),
    ]
