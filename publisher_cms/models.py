import logging

from django.db import models
from django.utils.translation import ugettext_lazy as _
from publisher_cms.managers import PageProxyManager

from publisher.models import PublisherModel

log = logging.getLogger(__name__)


class PageProxyModel(PublisherModel):
    page = models.OneToOneField("cms.Page", related_name="+", on_delete=models.CASCADE)
    objects = PageProxyManager()

    def get_absolute_url(self, *args, **kwargs):
        return self.page.get_absolute_url(*args, **kwargs)

    def __str__(self):
        return str(self.page)

    class Meta:
        verbose_name = _("Publisher CMS-Page State")
        verbose_name_plural = _("Publisher CMS-Page States")
