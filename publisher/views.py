import logging

from django.views.generic import ListView
from django.views.generic.detail import DetailView
from publisher.utils import django_cms_exists

log = logging.getLogger(__name__)


class PublisherViewMixin:

    class Meta:
        abstract = True

    def get_queryset(self):
        return self.model.objects.visible()


class PublisherDetailView(PublisherViewMixin, DetailView):
    pass


class PublisherListView(PublisherViewMixin, ListView):
    pass


if django_cms_exists:
    class PublisherCmsViewMixin(PublisherViewMixin):
        def get_queryset(self):
            # django_cms_tools.permissions.EditModeAndChangePermissionMixin#edit_mode_and_change_permission
            if not self.model.edit_mode_and_change_permission(self.request):
                log.info("Not in edit mode or User has no change permission: Display only 'public' items.")
                return super(PublisherCmsViewMixin, self).get_queryset()
            else:
                log.info("edit mode is on and User has change permission: List only 'drafts' items.")
                return self.model.objects.drafts()

    class PublisherCmsDetailView(PublisherCmsViewMixin, DetailView):
        pass


    class PublisherCmsListView(PublisherCmsViewMixin, ListView):
        pass
