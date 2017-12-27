


"""
    created 2017 by Jens Diemer <ya-publisher@jensdiemer.de>


"""


import logging

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from publisher_test_project.publisher_list_app.constants import LIST_PLUGIN_NAME
from publisher_test_project.publisher_list_app.models import PublisherItemCMSPlugin

log = logging.getLogger(__name__)


class PublisherItemPlugin(CMSPluginBase):
    model = PublisherItemCMSPlugin
    render_template = 'list_app/includes/item_detail.html'
    name = _("PublisherItem Plugin")
    allow_children = False
    cache = False

    def render(self, context, instance, placeholder):
        context['object'] = instance.list_item
        return context


plugin_pool.register_plugin(PublisherItemPlugin)
assert PublisherItemPlugin.__name__ == LIST_PLUGIN_NAME
