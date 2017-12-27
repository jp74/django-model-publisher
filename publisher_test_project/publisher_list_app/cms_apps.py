
"""
    created 2017 by Jens Diemer <ya-publisher@jensdiemer.de>
"""


import logging

from cms.apphook_pool import apphook_pool

from cms.app_base import CMSApp

from publisher_test_project.publisher_list_app.constants import LIST_APPHOOK_NAMESPACE


log = logging.getLogger(__name__)


class PublisherItemApp(CMSApp):
    app_name = 'list_item'
    name = LIST_APPHOOK_NAMESPACE

    def get_urls(self, page=None, language=None, **kwargs):
        urls = ['publisher_test_project.publisher_list_app.urls']
        return urls

apphook_pool.register(PublisherItemApp)
