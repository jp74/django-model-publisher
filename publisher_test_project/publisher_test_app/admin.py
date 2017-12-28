
from django.contrib import admin

from publisher.admin import PublisherAdmin, PublisherPublishedFilter
from publisher.utils import parler_exists
from publisher_test_project.publisher_test_app.models import PublisherTestModel


@admin.register(PublisherTestModel)
class PublisherTestModelAdmin(PublisherAdmin):
    fieldsets = (
        (None, {
            "fields": (
                "no", "title",
            )
        }),
        ("visibility", {
            "classes": ("collapse",),
            "fields": (
                ("publication_start_date", "publication_end_date"),
            )
        }),
    )
    list_filter = (
        PublisherPublishedFilter,
    )


if parler_exists:
    from publisher_test_project.publisher_test_app.models import PublisherParlerTestModel
    from publisher.admin import PublisherParlerAdmin

    @admin.register(PublisherParlerTestModel)
    class PublisherParlerTestModelAdmin(PublisherParlerAdmin):
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
