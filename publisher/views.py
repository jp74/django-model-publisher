from django.views.generic import ListView
from django.views.generic.detail import DetailView


class PublisherViewMixin(object):

    class Meta:
        abstract = True

    def get_queryset(self):
        return self.model.objects.filter(publisher_is_draft=self.is_draft()).all()

    def is_draft(self):
        if self.request.user.is_authenticated() and self.request.user.is_staff:
            if self.request.GET and 'edit' in self.request.GET:
                return True
        return False


class PublisherDetailView(PublisherViewMixin, DetailView):
    pass


class PublisherListView(PublisherViewMixin, ListView):
    pass
