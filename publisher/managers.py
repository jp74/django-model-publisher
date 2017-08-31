from django.db import models


from .signals import publisher_pre_delete
from .middleware import get_draft_status


class PublisherQuerySet(models.QuerySet):
    def drafts(self):
        from .models import PublisherModelBase
        return self.filter(publisher_is_draft=PublisherModelBase.STATE_DRAFT)

    def published(self):
        from .models import PublisherModelBase
        return self.filter(publisher_is_draft=PublisherModelBase.STATE_PUBLISHED)


class PublisherManager(models.Manager):
    def get_queryset(self):
        return PublisherQuerySet(self.model, using=self._db)

    def contribute_to_class(self, model, name):
        super(PublisherManager, self).contribute_to_class(model, name)
        models.signals.pre_delete.connect(publisher_pre_delete, model)

    def drafts(self):
        return self.all().drafts()

    def published(self):
        return self.all().published()

    def current(self):
        if get_draft_status():
            return self.drafts()
        return self.published()

try:
    from parler.managers import TranslatableManager, TranslatableQuerySet
except ImportError:
    pass
else:
    class PublisherParlerQuerySet(PublisherQuerySet, TranslatableQuerySet):
        pass

    class PublisherParlerManager(PublisherManager, TranslatableManager):
        def get_queryset(self):
            return PublisherParlerQuerySet(self.model, using=self._db)
