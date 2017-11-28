
import logging

from django.utils.translation import ugettext_lazy as _

from publisher.managers import PublisherManager
from publisher.models import PublisherStateModel

log = logging.getLogger(__name__)


class PageProxyManager(PublisherManager):
    # def get_open_requests(self, page):
    #     try:
    #         proxy_instance = self.get(page=page)
    #
    #     return self.filter(page=page)

    def request_publishing(self, user, page, note=None):
        assert page.publisher_is_draft==True

        # Should not appear: request page should be locked until a open request exists.
        assert self.filter(page=page).exists() == 0, "Request for this page already exists!"

        proxy_instance = self.model()
        proxy_instance.page = page
        proxy_instance.save()

        from publisher.models import PublisherStateModel
        state_instance = PublisherStateModel.objects.request_publishing(
            user=user,
            publisher_instance=proxy_instance,
            note=note
        )
        return state_instance

    def request_unpublishing(self, user, page, note=None):
        assert page.publisher_is_draft==True

        proxy_instance = self.model()
        proxy_instance.page = page
        proxy_instance.save()

        state_instance = PublisherStateModel.objects.request_unpublishing(
            user=user,
            publisher_instance=proxy_instance,
            note=note
        )
        return state_instance
