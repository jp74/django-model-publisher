# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django_tools.permissions
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0016_auto_20160608_1535'),
    ]

    operations = [
        migrations.CreateModel(
            name='PageProxyModel',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('publisher_is_draft', models.BooleanField(db_index=True, editable=False, default=True)),
                ('publisher_modified_at', models.DateTimeField(editable=False, default=django.utils.timezone.now)),
                ('publisher_published_at', models.DateTimeField(editable=False, null=True)),
                ('publication_start_date', models.DateTimeField(db_index=True, verbose_name='publication start date', help_text='Published content will only be visible from this point in time. Leave blank if always visible.', null=True, blank=True)),
                ('publication_end_date', models.DateTimeField(db_index=True, verbose_name='publication end date', help_text='When to expire the published version. Leave empty to never expire.', null=True, blank=True)),
                ('page', models.OneToOneField(to='cms.Page', related_name='+')),
                ('publisher_linked', models.OneToOneField(on_delete=django.db.models.deletion.SET_NULL, editable=False, null=True, related_name='publisher_draft', to='publisher_cms.PageProxyModel')),
            ],
            options={
                'permissions': (('can_publish', 'Can publish'),),
                'abstract': False,
            },
            bases=(django_tools.permissions.ModelPermissionMixin, models.Model),
        ),
    ]
