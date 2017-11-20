import logging

from django.db import models
from django.db.models import Q
from django.utils import timezone
from publisher import constants

from .middleware import get_draft_status
from .signal_handlers import publisher_post_save, publisher_pre_delete

log = logging.getLogger(__name__)


class PublisherQuerySet(models.QuerySet):
    def drafts(self):
        from .models import PublisherModelBase
        return self.filter(publisher_is_draft=PublisherModelBase.STATE_DRAFT)

    def published(self):
        """
        Note: will ignore start/end date!
        Use self.visible() to get all publicly accessible entries.
        """
        from .models import PublisherModelBase
        return self.filter(
            publisher_is_draft=PublisherModelBase.STATE_PUBLISHED,
        )

    def visible(self):
        """
        Filter all publicly accessible entries.
        """
        from .models import PublisherModelBase
        return self.filter(
            Q(publication_start_date__isnull=True) | Q(publication_start_date__lte=timezone.now()),
            Q(publication_end_date__isnull=True) | Q(publication_end_date__gt=timezone.now()),
            publisher_is_draft=PublisherModelBase.STATE_PUBLISHED,
        )


class BasePublisherManager(models.Manager):
    def get_queryset(self):
        return PublisherQuerySet(self.model, using=self._db)

    def contribute_to_class(self, model, name):
        super(BasePublisherManager, self).contribute_to_class(model, name)

        log.debug("Add 'publisher_pre_delete' signal handler to %s", repr(model))
        models.signals.pre_delete.connect(publisher_pre_delete, model)

        # log.debug("Add 'publisher_post_save' signal handler to %s", repr(model))
        # models.signals.post_save.connect(publisher_post_save, model)


    def current(self):
        if get_draft_status():
            return self.drafts()
        return self.published()


PublisherManager = BasePublisherManager.from_queryset(PublisherQuerySet)

try:
    from parler.managers import TranslatableManager, TranslatableQuerySet
except ImportError:
    pass
else:
    class PublisherParlerQuerySet(PublisherQuerySet, TranslatableQuerySet):
        pass

    class BasePublisherParlerManager(PublisherManager, TranslatableManager):
        def get_queryset(self):
            return PublisherParlerQuerySet(self.model, using=self._db)

    PublisherParlerManager = BasePublisherParlerManager.from_queryset(PublisherParlerQuerySet)



class PublisherChangeQuerySet(models.QuerySet):
    def filter_open(self):
        return self.filter(state=self.model.STATE_REQUEST)

    def filter_closed(self):
        return self.exclude(state=self.model.STATE_REQUEST)


class PublisherChangeManager(models.Manager):

    def get_queryset(self):
        return PublisherChangeQuerySet(self.model, using=self._db)

    def get_state(self, publisher_instance):
        queryset = self.all()
        queryset = queryset.filter(publisher_instance=publisher_instance)
        instance = queryset.latest()
        return instance

    ############################################################################
    # request methods:

    def _create_request(self, action, user, publisher_instance, note):
        assert action in (constants.ACTION_PUBLISH, constants.ACTION_UNPUBLISH)

        state_instance = self.model()
        state_instance.action = action
        state_instance.state = constants.STATE_REQUEST
        state_instance.publisher_instance = publisher_instance
        state_instance.request_user = user
        state_instance.request_note = note
        state_instance.save()

        return state_instance

    def request_publishing(self, user, publisher_instance, note=None):
        self.model.has_ask_request_permission(user, raise_exception=True)

        assert publisher_instance.is_dirty

        state_instance = self._create_request(
            constants.ACTION_PUBLISH,
            user, publisher_instance, note
        )

        # TODO: fire signal: e.g.: handler to mail user

        return state_instance

    def request_unpublishing(self, user, publisher_instance, note=None):
        self.model.has_ask_request_permission(user, raise_exception=True)

        assert publisher_instance.is_published

        state_instance = self._create_request(
            constants.ACTION_UNPUBLISH,
            user, publisher_instance, note
        )

        # TODO: fire signal: e.g.: handler to mail user

        return state_instance


