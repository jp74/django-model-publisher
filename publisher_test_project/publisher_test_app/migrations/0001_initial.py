# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import aldryn_translation_tools.models
import django.db.models.deletion
import parler.models
import django_tools.permissions
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0016_auto_20160608_1535'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlainTextPluginModel',
            fields=[
                ('cmsplugin_ptr', models.OneToOneField(serialize=False, auto_created=True, related_name='publisher_test_app_plaintextpluginmodel', parent_link=True, to='cms.CMSPlugin', primary_key=True)),
                ('text', models.TextField()),
            ],
            options={
                'abstract': False,
            },
            bases=('cms.cmsplugin',),
        ),
        migrations.CreateModel(
            name='PublisherParlerAutoSlugifyTestModel',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
                ('publisher_is_draft', models.BooleanField(editable=False, default=True, db_index=True)),
                ('publisher_modified_at', models.DateTimeField(editable=False, default=django.utils.timezone.now)),
                ('publisher_published_at', models.DateTimeField(editable=False, null=True)),
                ('publication_start_date', models.DateTimeField(help_text='Published content will only be visible from this point in time. Leave blank if always visible.', db_index=True, null=True, blank=True, verbose_name='publication start date')),
                ('publication_end_date', models.DateTimeField(help_text='When to expire the published version. Leave empty to never expire.', db_index=True, null=True, blank=True, verbose_name='publication end date')),
                ('publisher_linked', models.OneToOneField(editable=False, related_name='publisher_draft', null=True, to='publisher_test_app.PublisherParlerAutoSlugifyTestModel', on_delete=django.db.models.deletion.SET_NULL)),
            ],
            options={
                'default_permissions': ('add', 'change', 'delete', 'can_publish'),
                'abstract': False,
            },
            bases=(aldryn_translation_tools.models.TranslatedAutoSlugifyMixin, parler.models.TranslatableModelMixin, django_tools.permissions.ModelPermissionMixin, models.Model),
        ),
        migrations.CreateModel(
            name='PublisherParlerAutoSlugifyTestModelTranslation',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
                ('language_code', models.CharField(max_length=15, db_index=True, verbose_name='Language')),
                ('title', models.CharField(max_length=100)),
                ('slug', models.SlugField(max_length=255, blank=True)),
                ('master', models.ForeignKey(editable=False, related_name='translations', null=True, to='publisher_test_app.PublisherParlerAutoSlugifyTestModel')),
            ],
            options={
                'db_tablespace': '',
                'managed': True,
                'db_table': 'publisher_test_app_publisherparlerautoslugifytestmodel_translation',
                'verbose_name': 'publisher parler auto slugify test model Translation',
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='PublisherParlerTestModel',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
                ('publisher_is_draft', models.BooleanField(editable=False, default=True, db_index=True)),
                ('publisher_modified_at', models.DateTimeField(editable=False, default=django.utils.timezone.now)),
                ('publisher_published_at', models.DateTimeField(editable=False, null=True)),
                ('publication_start_date', models.DateTimeField(help_text='Published content will only be visible from this point in time. Leave blank if always visible.', db_index=True, null=True, blank=True, verbose_name='publication start date')),
                ('publication_end_date', models.DateTimeField(help_text='When to expire the published version. Leave empty to never expire.', db_index=True, null=True, blank=True, verbose_name='publication end date')),
                ('publisher_linked', models.OneToOneField(editable=False, related_name='publisher_draft', null=True, to='publisher_test_app.PublisherParlerTestModel', on_delete=django.db.models.deletion.SET_NULL)),
            ],
            options={
                'default_permissions': ('add', 'change', 'delete', 'can_publish'),
                'abstract': False,
            },
            bases=(parler.models.TranslatableModelMixin, django_tools.permissions.ModelPermissionMixin, models.Model),
        ),
        migrations.CreateModel(
            name='PublisherParlerTestModelTranslation',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
                ('language_code', models.CharField(max_length=15, db_index=True, verbose_name='Language')),
                ('title', models.CharField(max_length=100)),
                ('master', models.ForeignKey(editable=False, related_name='translations', null=True, to='publisher_test_app.PublisherParlerTestModel')),
            ],
            options={
                'db_tablespace': '',
                'managed': True,
                'db_table': 'publisher_test_app_publisherparlertestmodel_translation',
                'verbose_name': 'publisher parler test model Translation',
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='PublisherTestModel',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
                ('publisher_is_draft', models.BooleanField(editable=False, default=True, db_index=True)),
                ('publisher_modified_at', models.DateTimeField(editable=False, default=django.utils.timezone.now)),
                ('publisher_published_at', models.DateTimeField(editable=False, null=True)),
                ('publication_start_date', models.DateTimeField(help_text='Published content will only be visible from this point in time. Leave blank if always visible.', db_index=True, null=True, blank=True, verbose_name='publication start date')),
                ('publication_end_date', models.DateTimeField(help_text='When to expire the published version. Leave empty to never expire.', db_index=True, null=True, blank=True, verbose_name='publication end date')),
                ('no', models.PositiveSmallIntegerField()),
                ('title', models.CharField(max_length=100)),
                ('publisher_linked', models.OneToOneField(editable=False, related_name='publisher_draft', null=True, to='publisher_test_app.PublisherTestModel', on_delete=django.db.models.deletion.SET_NULL)),
            ],
            options={
                'abstract': False,
                'verbose_name': 'Publisher Test Model',
                'verbose_name_plural': 'Publisher Test Model',
                'default_permissions': ('add', 'change', 'delete', 'can_publish'),
            },
            bases=(django_tools.permissions.ModelPermissionMixin, models.Model),
        ),
        migrations.AlterUniqueTogether(
            name='publishertestmodel',
            unique_together=set([('publisher_is_draft', 'no', 'title')]),
        ),
        migrations.AlterUniqueTogether(
            name='publisherparlertestmodeltranslation',
            unique_together=set([('language_code', 'master')]),
        ),
        migrations.AlterUniqueTogether(
            name='publisherparlerautoslugifytestmodeltranslation',
            unique_together=set([('language_code', 'master')]),
        ),
    ]
