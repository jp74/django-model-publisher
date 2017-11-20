
from django.contrib import admin

from publisher_test_project.myapp.models import PublisherTestModel


class PublisherStateAdminMixin:
    pass


@admin.register(PublisherTestModel)
class PublisherTestModelAdmin(PublisherStateAdminMixin, admin.ModelAdmin):
    pass


