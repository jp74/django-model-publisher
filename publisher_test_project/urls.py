import django
from django.conf.urls import url
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.shortcuts import redirect

from publisher_test_project.publisher_test_app.views import PublisherTestDetailView

urlpatterns = [
    url(r'^test/(?P<pk>[0-9]+)/$', PublisherTestDetailView.as_view(), name='test-detail'),

    # redirect root view to admin page:
    url(r'^$', lambda x: redirect("admin:index")),
]


if django.VERSION >= (1, 9):
    urlpatterns += i18n_patterns(
        url(r'^admin/', admin.site.urls),
    )
else:
    from django.conf.urls import include
    urlpatterns += i18n_patterns(
        url(r'^admin/', include(admin.site.urls)),
    )
