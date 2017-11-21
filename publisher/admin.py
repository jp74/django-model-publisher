
import json
import logging

from django.contrib.admin.utils import quote

from django.conf.urls import url
from django.contrib import admin, messages
from django.contrib.admin import ModelAdmin, SimpleListFilter
from django.core.exceptions import PermissionDenied, ValidationError, FieldError
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.template import loader
from django.utils.encoding import force_text
from django.utils.html import escape
from django.utils.translation import ugettext_lazy as _

from publisher import constants
from publisher.forms import PublisherForm
from publisher.models import PublisherStateModel

log = logging.getLogger(__name__)


def make_published(modeladmin, request, queryset):
    for row in queryset.all():
        row.publish()


make_published.short_description = _("Publish")


def make_unpublished(modeladmin, request, queryset):
    for row in queryset.all():
        row.unpublish()


make_unpublished.short_description = _("Unpublish")


def http_json_response(data):
    return HttpResponse(json.dumps(data), content_type="application/json")


class PublisherAdmin(ModelAdmin):
    form = PublisherForm
    change_form_template = "publisher/change_form.html"
    # publish or unpublish actions sometime makes the plugins disappear from page
    # so we disable it for now, until we can investigate it further.
    # actions = (make_published, make_unpublished, )
    list_display = (
        "publisher_object_title",
        "is_dirty", "is_draft",
        "publisher_publish", "publisher_status",
    )
    url_name_prefix = None

    class Media:
        js = (
            "publisher/publisher.js",
        )
        css = {
            "all": ("publisher/publisher.css", ),
        }

    def __init__(self, model, admin_site):
        super(PublisherAdmin, self).__init__(model, admin_site)
        self.request = None
        self.url_name_prefix = "%(app_label)s_%(module_name)s_" % {
            "app_label": self.model._meta.app_label,
            "module_name": self.model._meta.model_name,
        }

        # Reverse URL strings used in multiple places:
        self.publish_reverse = "%s:%spublish" % (
            self.admin_site.name,
            self.url_name_prefix
        )
        self.unpublish_reverse = "%s:%sunpublish" % (
            self.admin_site.name,
            self.url_name_prefix
        )
        self.revert_reverse = "%s:%srevert" % (
            self.admin_site.name,
            self.url_name_prefix
        )
        self.changelist_reverse = "%s:%schangelist" % (
            self.admin_site.name,
            self.url_name_prefix
        )

    def has_publish_permission(self, request, obj=None):
        opts = self.opts
        return request.user.has_perm(
            "%s.%s" % (
                opts.app_label,
                constants.PERMISSION_MODEL_CAN_PUBLISH
            )
        )

    def has_ask_request_permission(self, request, obj=None):
        """
        has the current user permission to create a publish/unpublish request?
        """
        user = request.user
        has_ask_request_permission = PublisherStateModel.has_ask_request_permission(user, raise_exception=False)
        if not has_ask_request_permission:
            log.debug("Hide 'ask publish request' because current user has not the permission for it!")
        return has_ask_request_permission

    def has_reply_request_permission(self, request, obj=None):
        """
        has the current user permission to accept/reject a publish/unpublish request?
        """
        user = request.user
        has_reply_request_permission = PublisherStateModel.has_reply_request_permission(user, raise_exception=False)
        if not has_reply_request_permission:
            log.debug("Hide 'reply publish request' because current user has not the permission for it!")
        return has_reply_request_permission

    def publisher_object_title(self, obj):
        return u"%s" % obj
    publisher_object_title.short_description = "Title"

    def publisher_status(self, obj):
        if not self.has_publish_permission(self.request, obj):
            return ""

        template_name = "publisher/change_list_publish_status.html"

        publish_btn = None
        if obj.is_dirty:
            publish_btn = reverse(self.publish_reverse, args=(obj.pk, ))

        t = loader.get_template(template_name)
        context = {
            "publish_btn": publish_btn,
        }
        return t.render(context)
    publisher_status.short_description = "Last Changes"
    publisher_status.allow_tags = True

    def publisher_publish(self, obj):
        template_name = "publisher/change_list_publish.html"

        is_published = False
        if obj.publisher_linked and obj.is_draft:
            is_published = True

        t = loader.get_template(template_name)
        context = {
            "object": obj,
            "is_published": is_published,
            "has_publish_permission": self.has_publish_permission(self.request, obj),
            "publish_url": reverse(self.publish_reverse, args=(obj.pk, )),
            "unpublish_url": reverse(self.unpublish_reverse, args=(obj.pk, )),
        }
        return t.render(context)
    publisher_publish.short_description = "Published"
    publisher_publish.allow_tags = True

    def get_queryset(self, request):
        # hack! We need request.user to check user publish perms
        self.request = request
        qs = self.model.objects.drafts()
        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs

    queryset = get_queryset

    def get_urls(self):
        urls = super(PublisherAdmin, self).get_urls()

        publish_name = "%spublish" % (self.url_name_prefix, )
        unpublish_name = "%sunpublish" % (self.url_name_prefix, )
        revert_name = "%srevert" % (self.url_name_prefix, )
        publish_urls = [
            url(r"^(?P<object_id>\d+)/publish/$", self.publish_view, name=publish_name),
            url(r"^(?P<object_id>\d+)/unpublish/$", self.unpublish_view, name=unpublish_name),
            url(r"^(?P<object_id>\d+)/revert/$", self.revert_view, name=revert_name),
        ]

        return publish_urls + urls

    def get_model_object(self, request, object_id):
        obj = self.model.objects.get(pk=object_id)

        if not self.has_change_permission(request, obj):
            raise PermissionDenied

        if obj is None:
            raise Http404(_("%s object with primary key %s does not exist.") % (
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
            messages.success(request, _("Draft has been revert to the public version."))
            return HttpResponseRedirect(reverse(self.changelist_reverse))

        return http_json_response({"success": True})

    def unpublish_view(self, request, object_id):
        obj = self.get_model_object(request, object_id)

        if not self.has_publish_permission(request, obj):
            raise PermissionDenied

        obj.unpublish()

        if not request.is_ajax():
            messages.success(request, _("Published version has been deleted."))
            return HttpResponseRedirect(reverse(self.changelist_reverse))

        return http_json_response({"success": True})

    def publish_view(self, request, object_id):
        obj = self.get_model_object(request, object_id)

        if not self.has_publish_permission(request, obj):
            raise PermissionDenied

        obj.publish()

        if not request.is_ajax():
            messages.success(request, _("Draft version has been published."))
            return HttpResponseRedirect(reverse(self.changelist_reverse))

        return http_json_response({"success": True})

    def _add_ask_publish_request(self, request, obj):

        if obj is not None:
            queryset = PublisherStateModel.objects.all()
            obj_qs = queryset.filter_by_instance(obj)
            publish_request_qs = obj_qs.filter_open()
            if publish_request_qs.count() != 0:
                messages.info(request, _("An open request already exists"))

        return self.has_ask_request_permission(request, obj)

    def _add_reply_publish_request(self, request, obj):

        if obj is not None:
            queryset = PublisherStateModel.objects.all()
            obj_qs = queryset.filter_by_instance(obj)
            publish_request_qs = obj_qs.filter_open()
            if publish_request_qs.count() == 0:
                log.debug("Hide 'reply publish request' because there is no request!")
                return False

        return self.has_reply_request_permission(request, obj)

    def post_ask_publish(self, request, obj, form):
        if not obj.is_dirty:
            # FIXME: Will never happen, because obj.save() always sets the dirty flag, no matter if something"s changed :(
            messages.warning(request, _("Don't create publish request, because it's not dirty!"))
            return False

        note = form.cleaned_data["note"]
        state_instance = PublisherStateModel.objects.request_publishing(
            user=request.user,
            publisher_instance=obj,
            note=note,
        )
        log.debug("Create: %s", state_instance)
        messages.success(request, _("Publish request has been created."))

    def post_reply_reject(self, request, obj, form):
        note = form.cleaned_data["note"]
        current_state = PublisherStateModel.objects.get_current_request(obj)
        current_state.reject(
            response_user=request.user,
            response_note=note,
        )
        log.debug("reject: %s", current_state)
        messages.success(request, _("Publish request has been rejected."))

    def post_reply_accept(self, request, obj, form):
        note = form.cleaned_data["note"]
        current_state = PublisherStateModel.objects.get_current_request(obj)
        current_state.accept(
            response_user=request.user,
            response_note=note,
        )
        log.debug("accept: %s", current_state)
        messages.success(request, _("Publish request has been accepted."))

    def save_model(self, request, obj, form, change):
        super(PublisherAdmin, self).save_model(request, obj, form, change)

        if constants.POST_ASK_PUBLISH_KEY in request.POST:
            self.post_ask_publish(request, obj, form)
        elif constants.POST_REPLY_REJECT_KEY in request.POST:
            self.post_reply_reject(request, obj, form)
        elif constants.POST_REPLY_ACCEPT_KEY in request.POST:
            self.post_reply_accept(request, obj, form)

    def get_fieldsets(self, request, obj=None):
        fieldsets = super(PublisherAdmin, self).get_fieldsets(request, obj=obj)

        add_ask = self._add_ask_publish_request(request, obj)
        add_reply = self._add_reply_publish_request(request, obj)

        fieldset_name = None
        if add_reply:
            fieldset_name = _("reply publishing request")
        elif add_ask:
            fieldset_name = _("request publishing")

        if fieldset_name is not None:
            # made the "note" field visible
            fieldsets += (
                (fieldset_name, {"fields": ("note",)}),
            )

        return fieldsets

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        obj = context.get("original", None)
        if not obj:
            return super(PublisherAdmin, self).render_change_form(
                request, context, add, change, form_url, obj=None)

        has_publish_permission=self.has_publish_permission(request, obj)
        context["has_publish_permission"] = has_publish_permission

        if has_publish_permission:
            publish_btn = None
            if obj.is_dirty:
                publish_btn = reverse(self.publish_reverse, args=(obj.pk, ))

            preview_draft_btn = None
            if callable(getattr(obj, "get_absolute_url", None)):
                preview_draft_btn = True

            unpublish_btn = None
            if obj.is_draft and obj.publisher_linked:
                unpublish_btn = reverse(self.unpublish_reverse, args=(obj.pk, ))

            revert_btn = None
            if obj.is_dirty and obj.publisher_linked:
                revert_btn = reverse(self.revert_reverse, args=(obj.pk, ))

            context.update({
                "publish_btn_live": publish_btn,
                "preview_draft_btn": preview_draft_btn,
                "unpublish_btn": unpublish_btn,
                "revert_btn": revert_btn,
            })

        context["original"] = obj

        publisher_states = PublisherStateModel.objects.all().filter_by_instance(
            publisher_instance=obj
        )
        context["publisher_states"] = publisher_states

        add_reply = self._add_reply_publish_request(request, obj)

        if add_reply:
            has_reply_request_permission = self.has_reply_request_permission(request, obj)
            context["has_reply_request_permission"] = has_reply_request_permission
            context["POST_REPLY_ACCEPT_KEY"] = constants.POST_REPLY_ACCEPT_KEY
            context["POST_REPLY_REJECT_KEY"] = constants.POST_REPLY_REJECT_KEY
            current_request = PublisherStateModel.objects.get_current_request(obj)
            context["current_request"] = current_request
        else:
            add_ask = self._add_ask_publish_request(request, obj)
            if add_ask:
                has_ask_request_permission = self.has_ask_request_permission(request, obj)
                context["has_ask_request_permission"] = has_ask_request_permission
                context["POST_ASK_PUBLISH_KEY"] = constants.POST_ASK_PUBLISH_KEY

        return super(PublisherAdmin, self).render_change_form(
            request, context, add, change, form_url, obj=None)


try:
    from hvad.admin import TranslatableAdmin
    from hvad.manager import FALLBACK_LANGUAGES
except ImportError:
    pass
else:
    class PublisherHvadAdmin(TranslatableAdmin, PublisherAdmin):
        change_form_template = "publisher/hvad/change_form.html"

        def get_queryset(self, request):
            # hack! We need request.user to check user publish perms
            self.request = request
            language = self._language(request)
            languages = [language]
            for lang in FALLBACK_LANGUAGES:
                if lang not in languages:
                    languages.append(lang)
            qs = self.model._default_manager.untranslated().use_fallbacks(*languages)
            qs = qs.filter(publisher_is_draft=True)
            ordering = getattr(self, "ordering", None) or ()
            if ordering:
                qs = qs.order_by(*ordering)
            return qs


try:
    from parler.admin import TranslatableAdmin as PTranslatableAdmin
except ImportError:
    pass
else:
    class PublisherParlerAdmin(PTranslatableAdmin, PublisherAdmin):
        change_form_template = "publisher/parler/change_form.html"

        def get_queryset(self, request):
            # hack! We need request.user to check user publish perms
            self.request = request
            qs = self.model.objects
            qs_language = self.get_queryset_language(request)
            if qs_language:
                qs = qs.language(qs_language)
            qs = qs.filter(publisher_is_draft=True)
            ordering = getattr(self, "ordering", None) or ()
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



class StatusListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _('open/closed')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'active'

    CLOSED = 'closed'
    ALL = 'all'

    def lookups(self, request, model_admin):
        """ Returns a list of tuples for URL query. """
        return (
            (self.CLOSED, _('Closed')),
            (self.ALL, _('All')),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        choice = self.value()
        if choice is None:
            # The default: Display only requests
            queryset = queryset.filter_open()
        elif choice == self.CLOSED:
            # Display only closed entries by exclude 'requests'
            queryset = queryset.filter_closed()
        elif choice == self.ALL:
            # Display all items
            return queryset
        else:
            raise ValidationError("Unknown choice: %r" % choice)

        return queryset

    def choices(self, cl):
        """
        Change the choice list text in the right admin sidebar
        """
        choices = super(StatusListFilter, self).choices(cl)
        for item in choices:
            query_string = item["query_string"]
            if query_string == "?":
                # Change the default 'All' to 'Active'
                item["display"] = _("Active")
            yield item


@admin.register(PublisherStateModel)
class PublisherStateModelAdmin(admin.ModelAdmin):
    def view_on_page_link(self, obj):
        publisher_instance = obj.publisher_instance
        url = publisher_instance.get_absolute_url()
        html = '<a href="{url}">{url}</a>'.format(url=url)
        return html
    view_on_page_link.allow_tags = True
    view_on_page_link.short_description = _("view on page")

    def change_link(self, obj):
        if not obj.is_open:
            return "-"
        else:
            publisher_instance = obj.publisher_instance
            pk_value = publisher_instance.pk
            opts = publisher_instance._meta
            url = reverse('admin:%s_%s_change' % (
                opts.app_label, opts.model_name),
                args=(quote(pk_value),),
                current_app=self.admin_site.name
            )
            html = '<a href="{url}">{txt}</a>'.format(
                url=url,
                txt=_("Reply Request"),
            )
            return html
    change_link.allow_tags = True
    change_link.short_description = _("Reply Link")

    list_display = (
        "request_timestamp",
        "change_link",
        "request_user", "action_name",
        "response_user", "state_name",
        "publisher_instance", "view_on_page_link",
    )
    list_filter = (
        StatusListFilter,
        "action", "state",
    )

