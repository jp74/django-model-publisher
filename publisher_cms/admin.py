import logging

from django.conf.urls import url
from django.contrib import admin, messages
from django.core.exceptions import SuspiciousOperation
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import ugettext_lazy as _

from cms.admin.pageadmin import PageAdmin
from cms.models import Page, Title

from publisher import constants
from publisher.admin import PublisherAdmin
from publisher.forms import PublisherNoteForm
from publisher.models import PublisherStateModel
from publisher_cms.forms import PageProxyForm
from publisher_cms.models import PageProxyModel

log = logging.getLogger(__name__)


@admin.register(PageProxyModel)
class PageProxyModelAdmin(PublisherAdmin):
    form = PageProxyForm
    fieldsets = (
        (None, {
            "fields": (
                "page",
            )
        }),
    )

class PublisherPageAdmin(PageAdmin):
    """
    Add publisher workflow to django-cms page admin

    usage e.g.:
        from publisher_cms.admin import PublisherPageAdmin

        PublisherPageAdmin.replace_page_admin()
    """
    # request_publish_page_template = "admin/publisher_cms/publisher_requests.html"
    #
    # def get_urls(self):
    #     """Get the admin urls
    #     """
    #     info = "%s_%s" % (self.model._meta.app_label, self.model._meta.model_name) # => 'cms_page'
    #     print("info:", info)
    #     pat = lambda regex, fn: url(regex, self.admin_site.admin_view(fn), name='%s_%s' % (info, fn.__name__))
    #
    #     url_patterns = [
    #         pat(r'^([0-9]+)/([a-z\-]+)/request_publish_page/$', self.request_publish_page), # "cms_page_request_publish_page"
    #         pat(r'^([0-9]+)/([a-z\-]+)/request_unpublish_page/$', self.request_unpublish_page), # "cms_page_request_unpublish_page"
    #     ]
    #     print(url_patterns)
    #
    #     url_patterns += super(PublisherPageAdmin, self).get_urls()
    #     return url_patterns
    #
    # def get_page_and_title(self, page_id, language):
    #     page = get_object_or_404(Page, pk=page_id, publisher_is_draft=True, title_set__language=language)
    #     title = get_object_or_404(Title, page_id=page_id, language=language, publisher_is_draft=True)
    #     return page, title
    #
    # def render(self, request, context, template):
    #     request.current_app = self.admin_site.name
    #     return render(request, template, context)
    #
    # def request_publish_page(self, request, page_id, language):
    #     user = request.user
    #     has_ask_request_permission = PublisherStateModel.has_ask_request_permission(
    #         user,
    #         raise_exception=True
    #     )
    #     page, title = self.get_page_and_title(page_id, language)
    #     if request.method != 'POST':
    #         form = PublisherNoteForm()
    #     else:
    #         form = PublisherNoteForm(request.POST)
    #         if form.is_valid():
    #             note = form.cleaned_data["note"]
    #             state_instance = PublisherStateModel.objects.request_publishing(
    #                 user=user,
    #                 publisher_instance=page,
    #                 note=note
    #             )
    #             return redirect(title.page.get_absolute_url(language, fallback=True))
    #
    #     publisher_states = PublisherStateModel.objects.all().filter_by_instance(
    #         publisher_instance=page
    #     )
    #
    #     context = {
    #         "form": form,
    #         "page": page,
    #         "title": title,
    #         "original": title,
    #         "publisher_states": publisher_states,
    #
    #         "has_ask_request_permission": has_ask_request_permission,
    #         "POST_ASK_PUBLISH_KEY": constants.POST_ASK_PUBLISH_KEY,
    #
    #         # For origin django admin templates:
    #         "opts": self.opts,
    #     }
    #     return self.render(request, context=context, template=self.request_publish_page_template)

    def request_unpublish_page(self, request, page_id, language):
        raise NotImplemented

    def publish_page(self, request, page_id, language):
        """
        overwrite PageAdmin.publish_page():
        """
        user = request.user

        # User with "reply" permission can publish CMS Pages directly.
        has_reply_request_permission = PublisherStateModel.has_reply_request_permission(user, raise_exception=False)
        if not has_reply_request_permission:
            # raise permission error if user doesn't have "ask" permission:
            PublisherStateModel.has_ask_request_permission(user, raise_exception=True)

            page, title = self.get_page_and_title(page_id, language)

            state_instance = PublisherStateModel.objects.request_publishing(
                user=user,
                publisher_instance=page,
                # note=note # TODO: get the user note somewhere ;)
            )

            # state_instance = PageProxyModel.objects.request_publishing(user=user, page=page)
            log.debug("Create: %s", state_instance)
            messages.success(request, _("Publish request has been created."))

            return redirect(title.page.get_absolute_url(language, fallback=True))

        return super(PublisherPageAdmin, self).publish_page(request, page_id, language)

    @classmethod
    def replace_page_admin(cls):
        if admin.site.is_registered(Page):
            log.debug("Unregister cms.Page from Admin")
            admin.site.unregister(Page)

        log.debug("Register %s for cms.PageAdmin", cls)
        admin.site.register(Page, cls)
