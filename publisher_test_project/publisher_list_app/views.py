
"""
    created 2017 by Jens Diemer <ya-publisher@jensdiemer.de>
"""

import logging

from parler.views import TranslatableSlugMixin

from publisher.views import PublisherCmsListView, PublisherCmsDetailView
from publisher_test_project.publisher_list_app.models import PublisherItem

log = logging.getLogger(__name__)


class PublisherItemListView(PublisherCmsListView):
    model = PublisherItem
    template_name = 'list_app/list.html'


class PublisherItemDetailView(TranslatableSlugMixin, PublisherCmsDetailView):
    model = PublisherItem
    template_name = 'list_app/detail.html'

