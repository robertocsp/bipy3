# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-11-10 11:30
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import utils.bigint


class Migration(migrations.Migration):

    dependencies = [
        ('loja', '0008_bigint_20161110_0004'),
    ]

    operations = [
        migrations.AlterField(
            model_name='questionario',
            name='loja',
            field=utils.bigint.BigForeignKey(on_delete=django.db.models.deletion.CASCADE, to='loja.Loja'),
        ),
    ]
