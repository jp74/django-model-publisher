from django.db import models

from .signals import publisher_pre_delete
from .middleware import get_draft_status


class PublisherManager(models.Manager):

    def contribute_to_class(self, model, name):
        super(PublisherManager, self).contribute_to_class(model, name)
        models.signals.pre_delete.connect(publisher_pre_delete, model)

    def drafts(self):
        from .models import PublisherModelBase
        return self.filter(publisher_is_draft=PublisherModelBase.STATE_DRAFT)

    def published(self):
        from .models import PublisherModelBase
        return self.filter(publisher_is_draft=PublisherModelBase.STATE_PUBLISHED)

    def current(self):
        if get_draft_status():
            return self.drafts()
        return self.published()
