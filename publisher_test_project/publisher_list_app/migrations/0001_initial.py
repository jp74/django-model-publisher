# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import cms.models.fields
import django_tools.permissions
import django.utils.timezone
import parler.models
import django.db.models.deletion
import django_cms_tools.permissions
import aldryn_translation_tools.models


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0016_auto_20160608_1535'),
    ]

    operations = [
        migrations.CreateModel(
            name='PublisherItem',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('publisher_is_draft', models.BooleanField(db_index=True, default=True, editable=False)),
                ('publisher_modified_at', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('publisher_published_at', models.DateTimeField(null=True, editable=False)),
                ('publication_start_date', models.DateTimeField(db_index=True, help_text='Published content will only be visible from this point in time. Leave blank if always visible.', verbose_name='publication start date', null=True, blank=True)),
                ('publication_end_date', models.DateTimeField(db_index=True, help_text='When to expire the published version. Leave empty to never expire.', verbose_name='publication end date', null=True, blank=True)),
                ('content', cms.models.fields.PlaceholderField(null=True, editable=False, slotname='item_content', to='cms.Placeholder')),
                ('publisher_linked', models.OneToOneField(null=True, editable=False, to='publisher_list_app.PublisherItem', related_name='publisher_draft', on_delete=django.db.models.deletion.SET_NULL)),
            ],
            options={
                'abstract': False,
                'default_permissions': ('add', 'change', 'delete', 'can_publish'),
            },
            bases=(django_cms_tools.permissions.EditModeAndChangePermissionMixin, aldryn_translation_tools.models.TranslatedAutoSlugifyMixin, parler.models.TranslatableModelMixin, django_tools.permissions.ModelPermissionMixin, models.Model),
        ),
        migrations.CreateModel(
            name='PublisherItemCMSPlugin',
            fields=[
                ('cmsplugin_ptr', models.OneToOneField(related_name='publisher_list_app_publisheritemcmsplugin', to='cms.CMSPlugin', auto_created=True, primary_key=True, parent_link=True, serialize=False)),
                ('item', models.ForeignKey(to='publisher_list_app.PublisherItem')),
            ],
            options={
                'abstract': False,
            },
            bases=('cms.cmsplugin',),
        ),
        migrations.CreateModel(
            name='PublisherItemTranslation',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('language_code', models.CharField(db_index=True, verbose_name='Language', max_length=15)),
                ('text', models.CharField(max_length=255)),
                ('slug', models.SlugField(blank=True, max_length=255)),
                ('master', models.ForeignKey(null=True, editable=False, related_name='translations', to='publisher_list_app.PublisherItem')),
            ],
            options={
                'managed': True,
                'db_tablespace': '',
                'db_table': 'publisher_list_app_publisheritem_translation',
                'verbose_name': 'publisher item Translation',
                'default_permissions': (),
            },
        ),
        migrations.AlterUniqueTogether(
            name='publisheritemtranslation',
            unique_together=set([('language_code', 'master')]),
        ),
    ]
