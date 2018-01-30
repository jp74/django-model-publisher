
import json
import logging
from collections import OrderedDict

from django.conf import settings
from django.conf.urls import url
from django.contrib import admin, messages
from django.contrib.admin import ModelAdmin, SimpleListFilter
from django.contrib.admin.templatetags.admin_static import static
from django.contrib.auth import get_permission_codename
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, SuspiciousOperation, ValidationError
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.template import loader
from django.utils.encoding import force_text
from django.utils.html import escape, format_html
from django.utils.translation import ugettext_lazy as _

from django_tools.permissions import check_permission

from publisher import constants
from publisher.forms import PublisherForm, PublisherNoteForm, PublisherParlerForm
from publisher.models import PublisherStateModel
from publisher.permissions import can_publish_object, has_object_permission
from publisher.utils import django_cms_exists, hvad_exists, parler_exists

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


class PendingPublishRequest(PermissionDenied):
    """
    User without publish permission will edit a object with open publish requests
    """
    pass


class VisibilityMixin:
    """
    for PublisherAdmin:
        list_display = (..., "visibility", ...)
    """
    def visibility(self, obj):
        is_dirty = obj.is_dirty
        if obj.publisher_linked:
            obj = obj.publisher_linked

        if obj.is_visible:
            if is_dirty:
                alt_text = _("Changed!")
                title = _("Changes not yet published. Older version is online.")
                icon_filename = "icon_alert.gif"
            else:
                alt_text = _("is public")
                title = _("Is public.")
                icon_filename = "icon-yes.gif"
        elif not obj.is_published:
            alt_text = _("not public")
            title = _("Not published, yet")
            icon_filename = "icon-no.gif"
        else:
            alt_text = _("hidden")
            icon_filename = "icon_alert.gif"
            if obj.hidden_by_end_date and obj.hidden_by_start_date:
                title = _("Published, but hidden by start/end date.")
            elif obj.hidden_by_start_date:
                title = _("Published, but hidden by start date.")
            elif obj.hidden_by_end_date:
                title = _("Published, but hidden by end date.")
            else:
                log.error("Unknown why hidden?!?")
                title = _("Published, but hidden.")

        icon_url = static("admin/img/%s" % icon_filename)
        return format_html(
            '<img src="{}" alt="{}" title="{}" />', icon_url, alt_text, title
        )

    visibility.short_description = _("Visibility")
    visibility.allow_tags = True


class PublisherAdmin(VisibilityMixin, ModelAdmin):
    form = PublisherForm
    change_form_template = "publisher/change_form.html"
    # publish or unpublish actions sometime makes the plugins disappear from page
    # so we disable it for now, until we can investigate it further.
    # actions = (make_published, make_unpublished, )
    list_display = (
        "publisher_object_title",
        "is_dirty",
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

    def get_form(self, request, obj=None, **kwargs):
        """
        Use get_form() as an early executed hook where we can collect
        information about the current object, used in:
         * self.get_fieldsets()
         * self.render_change_form()
        """
        # Current user can direct publish the current object:
        self.user_can_publish = self.has_publish_permission(request, obj=obj, raise_exception=False)

        self.current_request = None # Open PublisherStateModel instance, if exists.
        self.publisher_states = None # PublisherStateModel entries for current object, if exists.

        if obj is not None:
            self.publisher_states = PublisherStateModel.objects.all().filter_by_instance(
                publisher_instance=obj
            )
            try:
                self.current_request = self.publisher_states.latest()
            except PublisherStateModel.DoesNotExist:
                pass
            else:
                if self.current_request.state==constants.STATE_REQUEST:
                    raise PendingPublishRequest

        return super(PublisherAdmin, self).get_form(request, obj=obj, **kwargs)

    def changeform_view(self, request, *args, **kwargs):
        try:
            return super(PublisherAdmin, self).changeform_view(request, *args, **kwargs)
        except PendingPublishRequest:
            messages.error(request, _("You can't edit this, because a publish request is pending!"))
            return HttpResponseRedirect(reverse(self.changelist_reverse))

    def has_publish_permission(self, request, obj=None, raise_exception=True):
        if obj is None:
            opts = self.opts
        else:
            opts = obj._meta

        return can_publish_object(request.user, opts, raise_exception=False)

    def has_ask_request_permission(self, request, obj=None):
        """
        has the current user permission to create a (un-)publish request?
        """
        return PublisherStateModel.has_change_permission(request.user, raise_exception=False)

    def has_delete_permission(self, request, obj=None):
        has_delete_permission = super(PublisherAdmin, self).has_delete_permission(request, obj=obj)
        if has_delete_permission:
            if not self.has_publish_permission(request, obj=obj, raise_exception=False):
                # If a user can't publish -> he should not delete the object!
                has_delete_permission = False

        return has_delete_permission

    def publisher_object_title(self, obj):
        return u"%s" % obj
    publisher_object_title.short_description = "Title"

    def publisher_status(self, obj):
        if not self.has_publish_permission(self.request, obj, raise_exception=False):
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
        if obj.publisher_linked and obj.publisher_is_draft:
            is_published = True

        t = loader.get_template(template_name)
        context = {
            "object": obj,
            "is_published": is_published,
            "has_publish_permission": self.has_publish_permission(self.request, obj, raise_exception=False),
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
        if obj is None:
            raise Http404(_("%s object with primary key %s does not exist.") % (
                force_text(self.model._meta.verbose_name),
                escape(object_id)
            ))

        if not self.has_change_permission(request, obj) or not self.has_add_permission(request):
            raise PermissionDenied

        return obj

    def revert_view(self, request, object_id):
        obj = self.get_model_object(request, object_id)

        self.has_publish_permission(request, obj, raise_exception=True)

        obj.revert_to_public()

        if not request.is_ajax():
            messages.success(request, _("Draft has been revert to the public version."))
            return HttpResponseRedirect(reverse(self.changelist_reverse))

        return http_json_response({"success": True})

    def unpublish_view(self, request, object_id):
        obj = self.get_model_object(request, object_id)

        self.has_publish_permission(request, obj, raise_exception=True)

        obj.unpublish()

        if not request.is_ajax():
            messages.success(request, _("Published version has been deleted."))
            return HttpResponseRedirect(reverse(self.changelist_reverse))

        return http_json_response({"success": True})

    def publish_view(self, request, object_id):
        obj = self.get_model_object(request, object_id)

        self.has_publish_permission(request, obj, raise_exception=True)

        obj.publish()

        if not request.is_ajax():
            messages.success(request, _("Draft version has been published."))
            return HttpResponseRedirect(reverse(self.changelist_reverse))

        return http_json_response({"success": True})

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

    def post_ask_unpublish(self, request, obj, form):
        note = form.cleaned_data["note"]
        state_instance = PublisherStateModel.objects.request_unpublishing(
            user=request.user,
            publisher_instance=obj,
            note=note,
        )
        log.debug("Create: %s", state_instance)
        messages.success(request, _("Unpublish request has been created."))

    def post_reply_reject(self, request, obj, form):
        note = form.cleaned_data["note"]
        current_state = PublisherStateModel.objects.get_current_publisher_request(obj)
        current_state.reject(
            response_user=request.user,
            response_note=note,
        )
        log.debug("reject: %s", current_state)
        messages.success(request, _("Publish request has been rejected."))

    def post_reply_accept(self, request, obj, form):
        note = form.cleaned_data["note"]
        current_state = PublisherStateModel.objects.get_current_publisher_request(obj)
        current_state.accept(
            response_user=request.user,
            response_note=note,
        )
        log.debug("accept: %s", current_state)
        messages.success(request, _("Publish request has been accepted."))

    def post_save_and_publish(self, request, obj, form):
        self.has_publish_permission(request, obj, raise_exception=True)

        obj.publish()

        if not request.is_ajax():
            messages.success(request, _("Draft version has been published."))
            return HttpResponseRedirect(reverse(self.changelist_reverse))

        return http_json_response({"success": True})

    def save_model(self, request, obj, form, change):
        super(PublisherAdmin, self).save_model(request, obj, form, change)

        if constants.POST_ASK_PUBLISH_KEY in request.POST:
            self.post_ask_publish(request, obj, form)
        elif constants.POST_ASK_UNPUBLISH_KEY in request.POST:
            self.post_ask_unpublish(request, obj, form)
        elif constants.POST_REPLY_REJECT_KEY in request.POST:
            self.post_reply_reject(request, obj, form)
        elif constants.POST_REPLY_ACCEPT_KEY in request.POST:
            self.post_reply_accept(request, obj, form)
        elif constants.POST_SAVE_AND_PUBLISH_KEY in request.POST:
            self.post_save_and_publish(request, obj, form)

    def get_fieldsets(self, request, obj=None):
        """
        Add 'node' fieldset.
        """
        fieldsets = super(PublisherAdmin, self).get_fieldsets(request, obj=obj)

        fieldset_name = None

        if self.user_can_publish:
            if self.current_request is not None:
                fieldset_name = _("reply open publish request")
        else:
            fieldset_name = _("send publish request")

        if fieldset_name is not None:
            log.debug("made the 'note' fieldset visible as %s", fieldset_name)
            fieldsets += (
                (fieldset_name, {"fields": ("note",)}),
            )
        else:
            log.debug("Don't display 'note' fieldset.")

        return fieldsets

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        obj = context.get("original", None)

        current_request = None

        if obj is None:
            add_publish = False
            add_unpublish = False
            add_revert = False
        else:
            add_publish = obj.is_dirty
            add_unpublish = obj.publisher_is_draft and obj.publisher_linked
            add_revert = obj.is_dirty and obj.publisher_linked

            context["add_current_request_info"] = True
            if self.publisher_states is not None:
                context["publisher_states"] = self.publisher_states
                context["current_request"] = self.current_request
                if obj.is_dirty and callable(getattr(obj, "get_absolute_url", None)):
                    context["preview_draft_btn"] = True

        if self.user_can_publish:
            if current_request is None:
                context["POST_SAVE_AND_PUBLISH_KEY"] = constants.POST_SAVE_AND_PUBLISH_KEY
            else:

                context["action"]= current_request.action
                context["POST_REPLY_ACCEPT_KEY"] = constants.POST_REPLY_ACCEPT_KEY
                context["POST_REPLY_REJECT_KEY"] = constants.POST_REPLY_REJECT_KEY

            if add_publish:
                context["publish_btn"] = reverse(self.publish_reverse, args=(obj.pk, ))

            if add_unpublish:
                context["unpublish_btn"] = reverse(self.unpublish_reverse, args=(obj.pk, ))

            if add_revert:
                context["revert_btn"] = reverse(self.revert_reverse, args=(obj.pk, ))
        else:
            # User can't publish
            if current_request is not None:
                raise SuspiciousOperation("Pending request!")

            context["POST_ASK_PUBLISH_KEY"] = constants.POST_ASK_PUBLISH_KEY
            if add_unpublish:
                context["POST_ASK_UNPUBLISH_KEY"] = constants.POST_ASK_UNPUBLISH_KEY

        return super(PublisherAdmin, self).render_change_form(
            request, context, add, change, form_url, obj=None)


if hvad_exists:
    from hvad.admin import TranslatableAdmin
    from hvad.manager import FALLBACK_LANGUAGES

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


if parler_exists:
    from parler.admin import TranslatableAdmin as PTranslatableAdmin

    class PublisherParlerAdmin(PTranslatableAdmin, PublisherAdmin):
        form = PublisherParlerForm
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

    request_publish_page_template = "publisher/publisher_requests.html"

    def get_urls(self):
        info = "%s_%s" % (self.model._meta.app_label, self.model._meta.model_name) # => "publisher_publisherstatemodel"

        pat = lambda regex, fn: url(regex, self.admin_site.admin_view(fn), name='%s_%s' % (info, fn.__name__))

        url_patterns = [
            # "publisher_publisherstatemodel_reply_request"
            pat(r'^(?P<pk>[0-9]+)/reply_request/$', self.reply_request),

            # "publisher_publisherstatemodel_close_deleted"
            pat(r'^(?P<pk>[0-9]+)/close_deleted/$', self.close_deleted),

            # "publisher_publisherstatemodel_request_publish"
            pat(r'^(?P<content_type_id>[0-9]+)/(?P<object_id>[0-9]+)/request_publish/$', self.request_publish),

            # "publisher_publisherstatemodel_request_unpublish"
            pat(r'^(?P<content_type_id>[0-9]+)/(?P<object_id>[0-9]+)/request_unpublish/$', self.request_unpublish),
        ]
        url_patterns += super(PublisherStateModelAdmin, self).get_urls()
        return url_patterns

    def reply_request(self, request, pk):
        user = request.user
        PublisherStateModel.has_change_permission(user, raise_exception=True)

        current_request = get_object_or_404(
            PublisherStateModel,
            pk=pk,
            state=constants.STATE_REQUEST # only open requests
        )
        publisher_instance = current_request.publisher_instance
        assert publisher_instance is not None, "Publisher instance was deleted!"

        # raise PermissionDenied if user has no publish permissions:
        opts = publisher_instance._meta
        can_publish_object(user, opts, raise_exception=True)

        if request.method == "POST":
            form = PublisherNoteForm(request.POST)
            if form.is_valid():
                note = form.cleaned_data["note"]

                # opts = self.model._meta
                # url = reverse('admin:%s_%s_changelist' % (
                #     opts.app_label, opts.model_name),
                #     current_app=self.admin_site.name
                # )
                url = publisher_instance.get_absolute_url()

                if constants.POST_REPLY_REJECT_KEY in request.POST:
                    current_request.reject(
                        response_user=request.user,
                        response_note=note,
                    )
                    log.debug("reject: %s", current_request)
                    messages.success(request, _("%s has been rejected.") % current_request)

                elif constants.POST_REPLY_ACCEPT_KEY in request.POST:
                    current_request.accept(
                        response_user=request.user,
                        response_note=note,
                    )
                    log.debug("accept: %s", current_request)
                    messages.success(request, _("%s has been accept.") % current_request)

                    if current_request.action == constants.ACTION_UNPUBLISH:
                        # We should not redirect to a unpublished page/object ;)
                        # otherwise we get a 404
                        # see: https://github.com/wearehoods/django-ya-model-publisher/issues/9
                        # merge with self.redirect_to_parent() ?
                        if django_cms_exists:
                            # turn on Django CMS edit mode
                            url += "?edit"
                        else:
                            url = "/" # FIXME

                else:
                    raise SuspiciousOperation

                return redirect(url)
        else:
            form = PublisherNoteForm()

        publisher_states = PublisherStateModel.objects.all().filter_by_instance(
            publisher_instance=publisher_instance
        )

        context = {
            "form": form,
            "original": publisher_instance,
            # "original": current_state,
            "publisher_states": publisher_states,

            "add_publisher_submit": True, # Add publisher submit buttons
            "add_current_request_info": True,
            "current_request": current_request,

            "action": current_request.action,

            "POST_REPLY_ACCEPT_KEY": constants.POST_REPLY_ACCEPT_KEY,
            "POST_REPLY_REJECT_KEY": constants.POST_REPLY_REJECT_KEY,

            # For origin django admin templates:
            "opts": self.opts,
        }
        request.current_app = self.admin_site.name
        return render(request,
            template_name=self.request_publish_page_template,
            context=context
        )

    def close_deleted(self, request, pk):
        """
        mark a request for a deleted instance as 'closed'
        """
        user = request.user
        PublisherStateModel.has_change_permission(
            user,
            raise_exception=True
        )

        current_request = get_object_or_404(
            PublisherStateModel,
            pk=pk,
            state=constants.STATE_REQUEST # only open requests
        )
        assert current_request.publisher_instance is None, "The instance was not deleted!"

        current_request.close_deleted(response_user=user)
        messages.success(request, _("Entry with deleted instance was closed."))
        url = reverse("admin:publisher_publisherstatemodel_changelist")
        return redirect(url)

    def redirect_to_parent(self, publisher_instance):
        # url = publisher_instance.get_absolute_url()
        # url = "%s?edit_off" % url

        # TODO: redirect to the first publish parent
        # See: https://github.com/wearehoods/django-ya-model-publisher/issues/9
        # But how to get this url ?!?

        # Update test, too:
        # publisher_tests.test_publisher_cms_page.CmsPagePublisherWorkflowTests#test_reporter_create_publish_request_on_new_page

        url = "/"
        if django_cms_exists:
            # turn off Django CMS edit mode
            url += "?edit_off"
        return redirect(url)

    def _publisher_request(self, request, content_type_id, object_id, action):
        assert action in PublisherStateModel.ACTION_DICT

        user = request.user
        has_change_permission = PublisherStateModel.has_change_permission(
            user,
            raise_exception=True
        )
        content_type = get_object_or_404(ContentType, pk=content_type_id)
        publisher_instance = content_type.get_object_for_this_type(pk=object_id)

        # raise PermissionDenied if user can't change object
        has_object_permission(user,
            opts=publisher_instance._meta,
            action="change",
            raise_exception=True
        )

        has_open_requests = PublisherStateModel.objects.has_open_requests(publisher_instance)
        if has_open_requests:
            messages.error(request, _("Can't create new request, because there are pending requests!"))
            return self.redirect_to_parent(publisher_instance)

        if request.method != 'POST':
            form = PublisherNoteForm()
        else:
            form = PublisherNoteForm(request.POST)
            if form.is_valid():
                note = form.cleaned_data["note"]

                if action == constants.ACTION_PUBLISH:
                    action_func = PublisherStateModel.objects.request_publishing

                elif action == constants.ACTION_UNPUBLISH:
                    action_func = PublisherStateModel.objects.request_unpublishing
                else:
                    raise RuntimeError

                state_instance = action_func(
                    user=user,
                    publisher_instance=publisher_instance,
                    note=note
                )

                messages.info(request, _("%(action)s %(state)s created.") % {
                    "action": state_instance.action_name,
                    "state": state_instance.state_name,
                })
                return self.redirect_to_parent(publisher_instance)

        publisher_states = PublisherStateModel.objects.all().filter_by_instance(
            publisher_instance=publisher_instance
        )

        context = {
            "form": form,
            "original": publisher_instance,
            # "original": current_state,

            "add_publisher_submit": True, # Add publisher submit buttons

            "publisher_states": publisher_states,

            "action": action,
            "has_ask_request_permission": has_change_permission,

            # For origin django admin templates:
            "opts": self.opts,
        }

        if action == constants.ACTION_PUBLISH:
            context["POST_ASK_PUBLISH_KEY"] = constants.POST_ASK_PUBLISH_KEY
        elif action == constants.ACTION_UNPUBLISH:
            context["POST_ASK_UNPUBLISH_KEY"] = constants.POST_ASK_UNPUBLISH_KEY
        else:
            raise RuntimeError

        request.current_app = self.admin_site.name
        return render(request,
            template_name=self.request_publish_page_template,
            context=context
        )

    def request_publish(self, request, content_type_id, object_id):
        return self._publisher_request(request, content_type_id, object_id,
            action=constants.ACTION_PUBLISH
        )

    def request_unpublish(self, request, content_type_id, object_id):
        return self._publisher_request(request, content_type_id, object_id,
            action=constants.ACTION_UNPUBLISH
        )

    def changeform_view(self, request, *args, **kwargs):
        """
        Only the superuser should be able to use the "raw" change view
        """
        user = request.user
        if not user.is_superuser:
            log.error("Only superuser can use the 'raw' change view!")
            raise PermissionDenied
        return super(PublisherStateModelAdmin, self).changeform_view(request, *args, **kwargs)

    ###########################################################################
    # Change List stuff:

    def has_add_permission(self, request):
        """ Hide 'add' links/views """
        return False

    def get_changelist(self, request, **kwargs):
        """
        Make 'request' object available in list_display methods e.g.: self.change_link()
        """
        self.request = request
        return super(PublisherStateModelAdmin, self).get_changelist(request, **kwargs)

    def view_on_page_link(self, obj):
        publisher_instance = obj.publisher_instance
        if publisher_instance is None:
            txt = "Deleted '%s' (old pk:%r)" % (obj.content_type, obj.object_id)
            html = "<i>%s</i>" % txt
        else:
            txt = str(publisher_instance)
            try:
                url = publisher_instance.get_absolute_url()
            except AttributeError as err:
                log.error("Can't add 'view on page' link: %s", err)
                if settings.DEBUG:
                    return '<span title="{err}">{txt}</span>'.format(err=err, txt=txt)
                else:
                    return "-"
            html = '<a href="{url}?edit">{txt}</a>'.format(url=url, txt=txt)
        return html
    view_on_page_link.allow_tags = True
    view_on_page_link.short_description = _("view on page")

    def change_link(self, obj):
        user = self.request.user # self.request set in self.get_changelist()
        has_publish_permissions = obj.check_object_publish_permission(user, raise_exception=False)
        if not has_publish_permissions:
            html = '<span title="%s">-</span>' % (
                _("You have no reply permissions.")
            )
            return html

        if not obj.is_open:
            if obj.publisher_instance is None:
                # instance was delete -> display 'close' link
                url = obj.admin_close_deleted_url()
                txt=_("close deleted request")
            else:
                return "-"
        else:
            url = obj.admin_reply_url()
            if obj.action == constants.ACTION_PUBLISH:
                txt=_("reply publish request")
            elif obj.action == constants.ACTION_UNPUBLISH:
                txt=_("reply unpublish request")
            else:
                raise RuntimeError

        html = '<a href="{url}">{txt}</a>'.format(url=url, txt=txt)
        return html
    change_link.allow_tags = True
    change_link.short_description = _("Reply Link")

    def get_list_display_links(self, request, list_display):
        user = request.user
        if user.is_superuser:
            # Only superuser can use the "raw" change view:
            return super(PublisherStateModelAdmin, self).get_list_display_links(request, list_display)
        else:
            # Hide change view link for all non-superusers:
            return None

    def get_actions(self, request):
        user = request.user
        if user.is_superuser:
            # Only superuser can use the admin actions:
            return super(PublisherStateModelAdmin, self).get_actions(request)
        else:
            # Hide admin actions for all non-superusers:
            return OrderedDict()

    list_display = (
        "request_timestamp",
        "change_link",
        "request_user",
        # "action_name", "response_user", "state_name",
        "view_on_page_link",
    )
    list_filter = (
        StatusListFilter,
        "action", "state",
    )
