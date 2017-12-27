


"""
    created 2017 by Jens Diemer <ya-publisher@jensdiemer.de>


"""



import logging

from django.core.urlresolvers import reverse, NoReverseMatch
from django.utils.translation import ugettext_lazy as _

from cms.toolbar_pool import toolbar_pool
from cms.toolbar_base import CMSToolbar
from cms.utils.urlutils import admin_reverse

from publisher_test_project.publisher_list_app.models import PublisherItem


log = logging.getLogger(__name__)


class PublisherItemToolbar(CMSToolbar):
    watch_models = [PublisherItem]

    def populate(self):
        menu = self.toolbar.get_or_create_menu('list_item-app', _('PublisherItems'))

        try:
            url=reverse('list_item:publisher-list')
        except NoReverseMatch as err:
            log.debug("No app page created? (Error: %s)", err)
        else:
            menu.add_link_item(
                name=_('View on page'),
                url=url
            )
            menu.add_break()

        user = self.request.user

        add_model_perm = PublisherItem.has_add_permission(user, raise_exception=False)
        change_model_perm = PublisherItem.has_change_permission(user, raise_exception=False)
        delete_model_perm = PublisherItem.has_delete_permission(user, raise_exception=False)

        log.debug(
            "User %s 'PublisherItem' permissions: add:%r, change:%r, delete:%r",
            user, add_model_perm, change_model_perm, delete_model_perm
        )

        if change_model_perm:
            menu.add_sideframe_item(
                name=_('PublisherItem list'),
                url=admin_reverse('publisher_list_app_publisheritem_changelist'),
            )

        if add_model_perm:
            menu.add_modal_item(
                name=_('Add new list_item'),
                url=admin_reverse('publisher_list_app_publisheritem_add'),
            )

toolbar_pool.register(PublisherItemToolbar)
