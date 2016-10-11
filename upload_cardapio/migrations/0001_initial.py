# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-10-08 02:17
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('loja', '0004_loja_id_loja_facebook'),
    ]

    operations = [
        migrations.CreateModel(
            name='Cardapio',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('chave', models.CharField(max_length=32)),
                ('nome', models.CharField(max_length=100)),
                ('tamanho', models.FloatField(verbose_name=b'tamanho')),
                ('caminho', models.CharField(max_length=200)),
                ('loja', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='loja.Loja')),
            ],
        ),
    ]