from django.views.generic import ListView
from django.views.generic.detail import DetailView

from .middleware import get_draft_status


class PublisherViewMixin(object):

    class Meta:
        abstract = True

    def get_queryset(self):
        return self.model.objects.filter(publisher_is_draft=get_draft_status()).all()


class PublisherDetailView(PublisherViewMixin, DetailView):
    pass


class PublisherListView(PublisherViewMixin, ListView):
    pass
