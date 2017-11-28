
import logging

from cms.toolbar.items import ButtonList
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import SuspiciousOperation
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _

from cms.cms_toolbars import PageToolbar
from cms.toolbar_base import CMSToolbar
from cms.toolbar_pool import toolbar_pool
from cms.utils.urlutils import admin_reverse

from publisher.models import PublisherStateModel

log = logging.getLogger(__name__)


@toolbar_pool.register
class PublisherStateToolbar(CMSToolbar):
    """
    Add "open requests" menu to the CMS tool bar
    """
    watch_models = [PublisherStateModel]

    def populate(self):
        user = self.request.user

        has_ask_request_permission = PublisherStateModel.has_ask_request_permission(user, raise_exception=False)
        has_reply_request_permission = PublisherStateModel.has_reply_request_permission(user, raise_exception=False)

        if has_ask_request_permission or has_reply_request_permission:
            menu = self.toolbar.get_or_create_menu(
                key="publisher-state",
                verbose_name=_("open requests"),
            )

            state_qs = PublisherStateModel.objects.all().filter_open() # All open entries
            for state in state_qs:
                url = state.admin_reply_url()

                publisher_instance = state.publisher_instance
                # try:
                #     url = publisher_instance.get_absolute_url()
                # except AttributeError as err:
                #     log.error("Can't add 'view on page' link: %s", err)
                #     if settings.DEBUG:
                #         url = "#%s" % err
                #     else:
                #         url = "#"

                menu.add_link_item(
                    name="%s: %s" % (state.action_name, publisher_instance),
                    url=url,
                )

            menu.add_break()
            menu.add_sideframe_item(
                name=_("Publisher State list"),
                url=admin_reverse("publisher_publisherstatemodel_changelist"),
            )


class PublisherPageToolbar(PageToolbar):
    """
    Modify cms.cms_toolbars.PageToolbar:

    Change the toolbar button Text 'Publish page changes' to 'Request publishing'.

    To activate this, put the following code into e.g.: models.py:

        from publisher_cms.cms_toolbars import PublisherPageToolbar
        PublisherPageToolbar.replace_toolbar()

    """
    def request_hook(self):
        """
        redirect to "?edit_off" if request is pending and user has only "ask publishing" permissions
        """
        print("request_hook()")
        response = super(PublisherPageToolbar, self).request_hook()

        request = self.request
        user = request.user

        self.has_direct_permission = PublisherStateModel.has_direct_permission(user, raise_exception=False)
        self.has_reply_request_permission = PublisherStateModel.has_reply_request_permission(user, raise_exception=False)
        self.has_ask_request_permission = PublisherStateModel.has_ask_request_permission(user, raise_exception=False)

        if not (self.has_direct_permission or self.has_reply_request_permission or self.has_ask_request_permission):
            # e.g.: anonymous user should not see any messages
            log.debug("Don't modify cms toolbar for current user.")
            return response

        self.current_request = None

        current_page = request.current_page # SimpleLazyObject
        # ATTENTION: Don't test against 'is None' because page is a SimpleLazyObject
        if hasattr(current_page, "get_draft_object"):
            self.draft_page = current_page.get_draft_object()
            open_requests = PublisherStateModel.objects.get_open_requests(publisher_instance = self.draft_page)
            if open_requests.count() > 0:
                self.current_request = open_requests.latest()
                messages.info(self.request, _("This page '%s' has pending publish request.") % current_page)
            else:
                log.debug("Current page has no open publishing requests.")

            # self.is_dirty = self.draft_page.is_dirty(language=self.current_lang)
            # if not self.is_dirty:
            #     log.debug("Current page is dirty")
            #     return response
            # else:
            #     log.debug("Current page is not dirty")
        else:
            log.warning("No current page!")

        if self.has_direct_permission:
            return response

        if user.is_superuser:
            return response

        if not self.toolbar.edit_mode:
            return response

        if self.current_request is None:
            return response

        # If user has only "ask publishing" permissions: redirect to "edit off" mode

        if self.has_reply_request_permission or self.has_ask_request_permission:
            # Users with only "ask publish" permission should not edit a page with pending requests
            url = "?%s" % self.toolbar.edit_mode_url_off
            log.debug("Redirect to 'edit off': '%s'" % url)
            return HttpResponseRedirect(url)
        else:
            raise RuntimeError

    def add_button(self, button_list, title, url, disabled=False):
        log.debug("add button txt:'%s', url:%r disabled:%r", title, url, disabled)
        button_list.add_button(
            title,
            url=url,
            disabled=disabled,
            extra_classes=["cms-btn-action"], # "Remove" CMS ajax request ;)
        )

    def create_button_list(self):
        button_list = ButtonList(side=self.toolbar.RIGHT)
        return button_list

    def make_button_list(self, **kwargs):
        button_list = self.create_button_list()
        self.add_button(button_list, **kwargs)
        return button_list

    def add_publish_button(self, *args, **kwargs):
        super(PublisherPageToolbar, self).add_publish_button(*args, **kwargs)

        if self.has_reply_request_permission and self.current_request is not None:
            button_list = self.make_button_list(
                title=_("reply open request"),
                url = self.current_request.admin_reply_url(), # publisher.models.PublisherStateModel.admin_reply_url(),
                disabled=False
            )
            self.toolbar.add_item(button_list)

    def get_publish_button(self, *args, **kwargs):
        """
        Replace 'Publish page changes' button text
        """
        print("get_publish_button()")
        if not self.has_direct_permission:

            if self.has_reply_request_permission:
                if self.current_request is not None:
                    log.error("User with reply permission tries to edit a pending page!")
                    raise SuspiciousOperation()

            elif self.has_ask_request_permission:
                if self.current_request is not None:
                    log.error("User with ask permission tries to edit a pending page!")
                    raise SuspiciousOperation()

                dirty = self.has_dirty_objects()
                has_public_version = self.draft_page.publisher_public is not None

                button_list = self.create_button_list()
                if dirty:
                    self.add_button(button_list,
                        title=_("Request publishing"),
                        url = PublisherStateModel.objects.admin_request_publish_url(obj=self.page),
                        disabled=False
                    )

                if has_public_version:
                    self.add_button(button_list,
                        title=_("Request unpublishing"),
                        url = PublisherStateModel.objects.admin_request_unpublish_url(obj=self.page),
                        disabled=False
                    )

                return button_list

        log.debug("Don't change publish button for user that has direct permissions")
        return super(PublisherPageToolbar, self).get_publish_button(*args, **kwargs)

    @classmethod
    def replace_toolbar(cls):
        name = "%s.%s" % (PageToolbar.__module__, PageToolbar.__name__)
        if name in toolbar_pool.toolbars.keys():
            log.debug("unregister cms toolbar '%s'", PageToolbar)
            toolbar_pool.unregister(PageToolbar)

        log.debug("Register cms toolbar '%s'", cls)
        toolbar_pool.register(cls)
