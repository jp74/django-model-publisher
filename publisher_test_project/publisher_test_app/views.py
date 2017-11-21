from django.http import Http404
from django.utils.translation import ugettext_lazy as _
from django.views.generic import DetailView

from publisher_test_project.publisher_test_app.models import PublisherTestModel


class PublisherTestDetailView(DetailView):
    model=PublisherTestModel
    queryset = PublisherTestModel.objects.all()

    def get_object(self, queryset=None):
        obj = super(PublisherTestDetailView, self).get_object(queryset=queryset)
        if not obj.is_visible:
            raise Http404(_("Object pk:%i is not visible! Publish first ;)") % obj.pk)
        return obj
