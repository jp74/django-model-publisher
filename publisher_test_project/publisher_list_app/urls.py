
"""
    created 2017 by Jens Diemer <ya-publisher@jensdiemer.de>
"""

from django.conf.urls import url

from publisher_test_project.publisher_list_app.views import PublisherItemListView, PublisherItemDetailView

urlpatterns = [
    url(r'^$', PublisherItemListView.as_view(), name='publisher-list'),
    url(r'^(?P<slug>\w[-_\w]*)/$', PublisherItemDetailView.as_view(), name='publisher-detail'),
]
