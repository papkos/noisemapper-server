# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2016-11-08 12:32
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('noisemapper', '0002_recording'),
    ]

    operations = [
        migrations.AddField(
            model_name='recording',
            name='lat',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='recording',
            name='lon',
            field=models.FloatField(blank=True, null=True),
        ),
    ]