
import logging

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import SuspiciousOperation
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _

from cms.api import get_page_draft
from cms.cms_toolbars import PageToolbar
from cms.toolbar.items import ButtonList
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
        if not PublisherStateModel.has_change_permission(user, raise_exception=False):
            return

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
        redirect to "?edit_off" if request is pending
        """
        response = super(PublisherPageToolbar, self).request_hook()

        user = self.request.user

        if user.is_superuser:
            log.debug("Don't modify cms toolbar for superusers")
            return response

        can_publish_page = user.has_perm("cms.publish_page")
        can_change_page = user.has_perm("cms.change_page")
        log.debug("User %r can publish: %r - can change: %r", user, can_publish_page, can_change_page)
        if not (can_publish_page or can_change_page):
            # e.g.: anonymous user should not see any messages
            log.debug("Don't modify cms toolbar for current user %s", self.request.user)
            return response

        self.current_request = None

        page = get_page_draft(self.request.current_page)
        if page is None:
            log.warning("No current page.")
            return response

        open_requests = PublisherStateModel.objects.get_open_requests(publisher_instance = page)
        if open_requests.count() == 0:
            log.debug("Current page has no open publishing requests.")
            # self.is_dirty = self.page.is_dirty(language=self.current_lang)
            # if not self.is_dirty:
            #     log.debug("Current page is dirty")
            #     return response
            # else:
            #     log.debug("Current page is not dirty")
            return response

        self.current_request = open_requests.latest()

        if not self.toolbar.edit_mode:
            return response
        else:
            # User should not edit a page with pending request
            messages.error(self.request, _("This page '%s' has pending publish request.") % page)
            url = "?%s" % self.toolbar.edit_mode_url_off
            log.debug("Redirect to 'edit off': '%s'" % url)
            return HttpResponseRedirect(url)

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

    def is_page_dirty(self):
        """
        Seems that's not easy to check if a cms page is dirty.
        Here is the same logic how django cms adds the 'Publish page changes' button.
        see: cms.cms_toolbars.PageToolbar#get_publish_button
        """
        dirty = self.has_dirty_objects()
        if dirty:
            log.debug("Current page has dirty objects")
            return True

        if self.dirty_statics or (self.page and self.page.is_published(self.current_lang)):
            log.debug("Current page is dirty.")
            return dirty

        log.debug("Current page is not dirty.")
        return False

    def add_publish_button(self, classes=('cms-btn-action', 'cms-btn-publish',)):
        log.debug("Edit mode: %r - has_publish_permission: %r",
            self.toolbar.edit_mode,
            self.has_publish_permission(),
        )

        if not self.toolbar.edit_mode:
            log.debug("Not in edit mode: don't add buttons, ok.")
            return

        button_list = None

        if self.has_publish_permission():
            log.debug("User %s has CMS publish permission: Add default CMS buttons", self.request.user)

            log.debug(
                (
                    "has_dirty_objects: %r"
                    " - dirty_statics: %r"
                    " - page.is_published: %r"
                ),
                self.has_dirty_objects(),
                self.dirty_statics,
                (self.page and self.page.is_published(self.current_lang))
            )

            button_list = self.get_publish_button(classes=classes)

        else:
            log.debug("User %s has not CMS publish permissions, ok.", self.request.user)

            if self.current_request is not None:
                # Should never happen, see: self.request_hook()
                raise SuspiciousOperation()

            button_list = self.create_button_list()
            if self.is_page_dirty():
                log.debug("Dirty: Add request button")
                self.add_button(button_list,
                    title=_("Request publishing"),
                    url = PublisherStateModel.objects.admin_request_publish_url(obj=self.page),
                    disabled=False
                )
            else:
                log.debug("Not dirty: Don't add request button")

            has_public_version = self.page.publisher_public is not None
            log.debug(
                "page.publisher_public: %r (has_public_version: %r)",
                self.page.publisher_public, has_public_version
            )
            if has_public_version:
                log.debug("has public version: Add request unpublish button")
                self.add_button(button_list,
                    title=_("Request unpublishing"),
                    url = PublisherStateModel.objects.admin_request_unpublish_url(obj=self.page),
                    disabled=False
                )
            else:
                log.debug("page hasn't public version: Don't add request unpublish button")

        if button_list is not None:
            self.toolbar.add_item(button_list)

    @classmethod
    def replace_toolbar(cls):
        name = "%s.%s" % (PageToolbar.__module__, PageToolbar.__name__)
        if name in toolbar_pool.toolbars.keys():
            log.debug("unregister cms toolbar '%s'", PageToolbar)
            toolbar_pool.unregister(PageToolbar)

        log.debug("Register cms toolbar '%s'", cls)
        toolbar_pool.register(cls)
