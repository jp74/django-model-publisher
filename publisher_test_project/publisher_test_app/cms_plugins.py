from django.utils.translation import ugettext_lazy as _

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from publisher_test_project.publisher_test_app.models import PlainTextPluginModel


@plugin_pool.register_plugin
class PlainTextPlugin(CMSPluginBase):
    model = PlainTextPluginModel
    name = _("Plain Text Plugin")
    render_template = "plain_text_plugin.html"
    cache = False
