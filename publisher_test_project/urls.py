from django.conf.urls import include, url
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin

import debug_toolbar

from publisher_test_project.publisher_test_app.views import PublisherTestDetailView

urlpatterns = [
    url(r'^test/(?P<pk>[0-9]+)/$', PublisherTestDetailView.as_view(), name='test-detail'),
]


urlpatterns += i18n_patterns(
    url(r'^admin/', include(admin.site.urls)),
    url(r'^__debug__/', include(debug_toolbar.urls)),
    url(r'^', include('cms.urls')),
)
