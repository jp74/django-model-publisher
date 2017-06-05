import json

from django.contrib.admin import ModelAdmin, SimpleListFilter
from django.contrib import messages
from django.conf.urls import url
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.utils.encoding import force_text
from django.utils.html import escape
from django.utils.translation import ugettext_lazy as _
from django import forms
from django.template import loader, Context


def make_published(modeladmin, request, queryset):
    for row in queryset.all():
        row.publish()


make_published.short_description = _('Publish')


def make_unpublished(modeladmin, request, queryset):
    for row in queryset.all():
        row.unpublish()


make_unpublished.short_description = _('Unpublish')


def http_json_response(data):
    return HttpResponse(json.dumps(data), content_type='application/json')


class PublisherForm(forms.ModelForm):
    def clean(self):
        data = super(PublisherForm, self).clean()
        cleaned_data = self.cleaned_data
        instance = self.instance

        # work out which fields are unique_together
        unique_fields_set = instance.get_unique_together()

        if not unique_fields_set:
            return data

        for unique_fields in unique_fields_set:
            unique_filter = {}
            for unique_field in unique_fields:
                field = instance.get_field(unique_field)

                # Get value from the form or the model
                if field.editable:
                    unique_filter[unique_field] = cleaned_data[unique_field]
                else:
                    unique_filter[unique_field] = getattr(instance, unique_field)

            # try to find if any models already exist in the db;
            # I find all models and then exclude those matching the current model.
            existing_instances = type(instance).objects \
                                               .filter(**unique_filter) \
                                               .exclude(pk=instance.pk)

            if instance.publisher_linked:
                existing_instances = existing_instances.exclude(pk=instance.publisher_linked.pk)

            if existing_instances:
                for unique_field in unique_fields:
                    self._errors[unique_field] = self.error_class(
                        [_('This value must be unique.')])

        return data


class PublisherAdmin(ModelAdmin):
    form = PublisherForm
    change_form_template = 'publisher/change_form.html'
    # publish or unpublish actions sometime makes the plugins disappear from page
    # so we disable it for now, until we can investigate it further.
    # actions = (make_published, make_unpublished, )
    list_display = ('publisher_object_title', 'publisher_publish', 'publisher_status', )
    url_name_prefix = None

    class Media:
        js = (
            'publisher/publisher.js',
        )
        css = {
            'all': ('publisher/publisher.css', ),
        }

    def __init__(self, model, admin_site):
        super(PublisherAdmin, self).__init__(model, admin_site)
        self.request = None
        self.url_name_prefix = '%(app_label)s_%(module_name)s_' % {
            'app_label': self.model._meta.app_label,
            'module_name': self.model._meta.model_name,
        }

        # Reverse URL strings used in multiple places..
        self.publish_reverse = '%s:%spublish' % (
            self.admin_site.name,
            self.url_name_prefix, )
        self.unpublish_reverse = '%s:%sunpublish' % (
            self.admin_site.name,
            self.url_name_prefix, )
        self.revert_reverse = '%s:%srevert' % (
            self.admin_site.name,
            self.url_name_prefix, )
        self.changelist_reverse = '%s:%schangelist' % (
            self.admin_site.name,
            self.url_name_prefix, )

    def has_publish_permission(self, request, obj=None):
        opts = self.opts
        return request.user.has_perm('%s.can_publish' % opts.app_label)

    def publisher_object_title(self, obj):
        return u'%s' % obj
    publisher_object_title.short_description = 'Title'

    def publisher_status(self, obj):
        if not self.has_publish_permission(self.request, obj):
            return ''

        template_name = 'publisher/change_list_publish_status.html'

        publish_btn = None
        if obj.is_dirty:
            publish_btn = reverse(self.publish_reverse, args=(obj.pk, ))

        t = loader.get_template(template_name)
        c = Context({
            'publish_btn': publish_btn,
        })
        return t.render(c)
    publisher_status.short_description = 'Last Changes'
    publisher_status.allow_tags = True

    def publisher_publish(self, obj):
        template_name = 'publisher/change_list_publish.html'

        is_published = False
        if obj.publisher_linked and obj.is_draft:
            is_published = True

        t = loader.get_template(template_name)
        c = Context({
            'object': obj,
            'is_published': is_published,
            'has_publish_permission': self.has_publish_permission(self.request, obj),
            'publish_url': reverse(self.publish_reverse, args=(obj.pk, )),
            'unpublish_url': reverse(self.unpublish_reverse, args=(obj.pk, )),
        })
        return t.render(c)
    publisher_publish.short_description = 'Published'
    publisher_publish.allow_tags = True

    def get_queryset(self, request):
        # hack! We need request.user to check user publish perms
        self.request = request
        qs = self.model.publisher_manager.drafts()
        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs

    queryset = get_queryset

    def get_urls(self):
        urls = super(PublisherAdmin, self).get_urls()

        publish_name = '%spublish' % (self.url_name_prefix, )
        unpublish_name = '%sunpublish' % (self.url_name_prefix, )
        revert_name = '%srevert' % (self.url_name_prefix, )
        publish_urls = [
            url(r'^(?P<object_id>\d+)/publish/$', self.publish_view, name=publish_name),
            url(r'^(?P<object_id>\d+)/unpublish/$', self.unpublish_view, name=unpublish_name),
            url(r'^(?P<object_id>\d+)/revert/$', self.revert_view, name=revert_name),
        ]

        return publish_urls + urls

    def get_model_object(self, request, object_id):
        obj = self.model.objects.get(pk=object_id)

        if not self.has_change_permission(request, obj):
            raise PermissionDenied

        if obj is None:
            raise Http404(_('%s object with primary key %s does not exist.') % (
                force_text(self.model._meta.verbose_name),
                escape(object_id)
            ))

        if not self.has_change_permission(request) and not self.has_add_permission(request):
            raise PermissionDenied

        return obj

    def revert_view(self, request, object_id):
        obj = self.get_model_object(request, object_id)

        if not self.has_publish_permission(request, obj):
            raise PermissionDenied

        obj.revert_to_public()

        if not request.is_ajax():
            messages.success(request, _('Draft has been revert to the public version.'))
            return HttpResponseRedirect(reverse(self.changelist_reverse))

        return http_json_response({'success': True})

    def unpublish_view(self, request, object_id):
        obj = self.get_model_object(request, object_id)

        if not self.has_publish_permission(request, obj):
            raise PermissionDenied

        obj.unpublish()

        if not request.is_ajax():
            messages.success(request, _('Published version has been deleted.'))
            return HttpResponseRedirect(reverse(self.changelist_reverse))

        return http_json_response({'success': True})

    def publish_view(self, request, object_id):
        obj = self.get_model_object(request, object_id)

        if not self.has_publish_permission(request, obj):
            raise PermissionDenied

        obj.publish()

        if not request.is_ajax():
            messages.success(request, _('Draft version has been published.'))
            return HttpResponseRedirect(reverse(self.changelist_reverse))

        return http_json_response({'success': True})

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        obj = context.get('original', None)
        if not obj:
            return super(PublisherAdmin, self).render_change_form(
                request, context, add, change, form_url, obj=None)

        if not self.has_publish_permission(request, obj):
            context['has_publish_permission'] = False
        else:
            context['has_publish_permission'] = True

            publish_btn = None
            if obj.is_dirty:
                publish_btn = reverse(self.publish_reverse, args=(obj.pk, ))

            preview_draft_btn = None
            if callable(getattr(obj, 'get_absolute_url', None)):
                preview_draft_btn = True

            unpublish_btn = None
            if obj.is_draft and obj.publisher_linked:
                unpublish_btn = reverse(self.unpublish_reverse, args=(obj.pk, ))

            revert_btn = None
            if obj.is_dirty and obj.publisher_linked:
                revert_btn = reverse(self.revert_reverse, args=(obj.pk, ))

            context.update({
                'publish_btn_live': publish_btn,
                'preview_draft_btn': preview_draft_btn,
                'unpublish_btn': unpublish_btn,
                'revert_btn': revert_btn,
            })

        return super(PublisherAdmin, self).render_change_form(
            request, context, add, change, form_url, obj=None)


try:
    from hvad.admin import TranslatableAdmin
    from hvad.manager import FALLBACK_LANGUAGES
except ImportError:
    pass
else:
    class PublisherHvadAdmin(TranslatableAdmin, PublisherAdmin):
        change_form_template = 'publisher/hvad/change_form.html'

        def queryset(self, request):
            # hack! We need request.user to check user publish perms
            self.request = request
            language = self._language(request)
            languages = [language]
            for lang in FALLBACK_LANGUAGES:
                if lang not in languages:
                    languages.append(lang)
            qs = self.model._default_manager.untranslated().use_fallbacks(*languages)
            qs = qs.filter(publisher_is_draft=True)
            ordering = getattr(self, 'ordering', None) or ()
            if ordering:
                qs = qs.order_by(*ordering)
            return qs


try:
    from parler.admin import TranslatableAdmin as PTranslatableAdmin
except ImportError:
    pass
else:
    class PublisherParlerAdmin(PTranslatableAdmin, PublisherAdmin):
        change_form_template = 'publisher/parler/change_form.html'

        def queryset(self, request):
            # hack! We need request.user to check user publish perms
            self.request = request
            qs = self.model.objects
            qs_language = self.get_queryset_language(request)
            if qs_language:
                qs = qs.language(qs_language)
            qs = qs.filter(publisher_is_draft=True)
            ordering = getattr(self, 'ordering', None) or ()
            if ordering:
                qs = qs.order_by(*ordering)
            return qs


class PublisherPublishedFilter(SimpleListFilter):
    title = _('Published')
    parameter_name = 'published'

    def lookups(self, request, model_admin):
        return (
            ('1', _('Yes')),
            ('0', _('No'))
        )

    def queryset(self, request, queryset):
        try:
            value = int(self.value())
        except TypeError:
            return queryset

        isnull = not value
        return queryset.filter(publisher_linked__isnull=isnull)
