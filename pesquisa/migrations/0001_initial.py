# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2017-01-24 10:28
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import utils.bigint


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('loja', '0015_apps_ativa'),
    ]

    operations = [
        migrations.CreateModel(
            name='Recomendar',
            fields=[
                ('id', utils.bigint.BigAutoField(editable=False, primary_key=True, serialize=False)),
                ('cliente', models.CharField(max_length=128, verbose_name=b'cliente_fb')),
                ('app', models.CharField(max_length=30)),
                ('resposta', models.CharField(max_length=500)),
                ('data_resposta', models.DateTimeField(auto_now_add=True)),
                ('loja', utils.bigint.BigForeignKey(on_delete=django.db.models.deletion.CASCADE, to='loja.Loja')),
            ],
        ),
    ]