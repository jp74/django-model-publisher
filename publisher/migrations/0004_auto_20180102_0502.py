# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('publisher', '0003_auto_20171222_0706'),
    ]

    operations = [
        migrations.AlterField(
            model_name='publisherstatemodel',
            name='state',
            field=models.CharField(max_length=8, editable=False, choices=[('request', 'request'), ('rejected', 'rejected'), ('accepted', 'accepted'), ('done', 'done')]),
        ),
    ]
