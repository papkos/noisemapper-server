# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-03-21 15:32
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('noisemapper', '0006_auto_20170125_1629'),
    ]

    operations = [
        migrations.AddField(
            model_name='recording',
            name='with_headset',
            field=models.BooleanField(default=False),
        ),
    ]
