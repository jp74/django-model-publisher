
import logging

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from cms.toolbar_base import CMSToolbar
from cms.toolbar_pool import toolbar_pool
from cms.utils.urlutils import admin_reverse

from publisher.models import PublisherStateModel

log = logging.getLogger(__name__)


@toolbar_pool.register
class PublisherStateToolbar(CMSToolbar):
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
                publisher_instance = state.publisher_instance
                try:
                    url = publisher_instance.get_absolute_url()
                except AttributeError as err:
                    log.error("Can't add 'view on page' link: %s", err)
                    if settings.DEBUG:
                        url = "#%s" % err
                    else:
                        url = "#"
                menu.add_link_item(
                    name="%s: %s" % (state.action_name, publisher_instance),
                    url=url,
                )

            menu.add_break()
            menu.add_sideframe_item(
                name=_("Publisher State list"),
                url=admin_reverse("publisher_publisherstatemodel_changelist"),
            )
