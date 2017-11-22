# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('publisher', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='publisherstatemodel',
            options={'verbose_name': 'Publisher State', 'get_latest_by': 'request_timestamp', 'permissions': (('direct_publisher', 'publish/unpublish a object directly'), ('ask_publisher_request', 'create a publish/unpublish request'), ('reply_publisher_request', 'accept/reject a publish/unpublish request')), 'ordering': ['-request_timestamp'], 'verbose_name_plural': 'Publisher States'},
        ),
    ]
