from django.conf.urls.i18n import i18n_patterns

import django
from django.conf.urls import url

from django.contrib import admin


urlpatterns = []

if django.VERSION >= (1, 9):
    urlpatterns += i18n_patterns(
        url(r'^admin/', admin.site.urls),
    )
else:
    from django.conf.urls import include
    urlpatterns += i18n_patterns(
        url(r'^admin/', include(admin.site.urls)),
    )
