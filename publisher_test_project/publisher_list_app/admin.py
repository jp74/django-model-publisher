
"""
    created 2017 by Jens Diemer <ya-publisher@jensdiemer.de>
"""


import logging

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from cms.admin.placeholderadmin import PlaceholderAdminMixin

from publisher.admin import PublisherParlerAdmin, PublisherPublishedFilter
from publisher_test_project.publisher_list_app.models import PublisherItem

log = logging.getLogger(__name__)


@admin.register(PublisherItem)
class PublisherItemAdmin(PlaceholderAdminMixin, PublisherParlerAdmin):
    fieldsets = (
        ("content", {
            "fields": (
                ("text", "slug"),
            )
        }),
        ("visibility", {
            "fields": (
                ("publication_start_date", "publication_end_date"),
            )
        }),
    )
    list_display = ("text", "visibility")
    list_display_links = ("text",)
    list_filter = (
        PublisherPublishedFilter,
    )

