
from django.contrib import admin

from publisher_test_project.publisher_test_app.models import PublisherTestModel

from publisher.admin import PublisherAdmin


class PublisherStateAdminMixin:
    pass


@admin.register(PublisherTestModel)
class PublisherTestModelAdmin(PublisherStateAdminMixin, PublisherAdmin):
    fieldsets = (
        (None, {
            "fields": (
                "title",
            )
        }),
        ("visibility", {
            "classes": ("collapse",),
            "fields": (
                ("publication_start_date", "publication_end_date"),
            )
        }),
    )
