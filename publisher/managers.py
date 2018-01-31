import logging

from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Q
from django.utils import timezone

from cms.models import Page

from publisher import constants
from publisher.permissions import has_object_permission
from publisher.utils import parler_exists

from .signal_handlers import publisher_post_save, publisher_pre_delete

log = logging.getLogger(__name__)


class PublisherQuerySet(models.QuerySet):
    def drafts(self):
        return self.filter(publisher_is_draft=True)

    def published(self):
        """
        Note: will ignore start/end date!
        Use self.visible() to get all publicly accessible entries.
        """
        return self.filter(
            publisher_is_draft=False,
        )

    def visible(self):
        """
        Filter all publicly accessible entries.
        """
        now = timezone.now()
        return self.filter(
            Q(publication_start_date__isnull=True) | Q(publication_start_date__lte=now),
            Q(publication_end_date__isnull=True) | Q(publication_end_date__gt=now),
            publisher_is_draft=False,
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


PublisherManager = BasePublisherManager.from_queryset(PublisherQuerySet)

if parler_exists:
    from parler.managers import TranslatableManager, TranslatableQuerySet

    class PublisherParlerQuerySet(PublisherQuerySet, TranslatableQuerySet):
        pass

    class BasePublisherParlerManager(PublisherManager, TranslatableManager):
        def get_queryset(self):
            return PublisherParlerQuerySet(self.model, using=self._db)

    PublisherParlerManager = BasePublisherParlerManager.from_queryset(PublisherParlerQuerySet)



class PublisherStateQuerySet(models.QuerySet):
    """
    FIXME: We can't filter open/close with e.g.: publisher_instance__isnull=False
    because GenericForeignKey 'publisher_instance' does not generate an automatic reverse relation
    """
    def filter_open(self):
        return self.filter(state=constants.STATE_REQUEST)

    def filter_closed(self):
        return self.exclude(state=constants.STATE_REQUEST)

    def filter_by_state(self, publisher_state):
        queryset = self.filter(
            content_type=publisher_state.content_type,
            object_id=publisher_state.object_id,
        )
        return queryset

    def filter_by_instance(self, publisher_instance):
        assert publisher_instance.publisher_is_draft

        content_type = ContentType.objects.get_for_model(publisher_instance)

        queryset = self.filter(
            content_type=content_type,
            object_id=publisher_instance.pk
        )
        return queryset


class BasePublisherStateManager(models.Manager):

    def get_queryset(self):
        return PublisherStateQuerySet(self.model, using=self._db)

    def get_open_requests(self, publisher_instance):
        return self.all().filter_open().filter_by_instance(
            publisher_instance=publisher_instance
        )

    def has_open_requests(self, publisher_instance):
        return self.get_open_requests(publisher_instance).exists()

    def get_current_request(self, publisher_instance):
        qs = self.get_open_requests(publisher_instance)
        current_request = qs.latest()
        return current_request

    def _create_request(self, action, user, publisher_instance, note):
        assert action in (constants.ACTION_PUBLISH, constants.ACTION_UNPUBLISH)

        assert not self.has_open_requests(publisher_instance), \
            "Can't create new request, because there are pending requests!"

        state_instance = self.model()
        state_instance.action = action
        state_instance.state = constants.STATE_REQUEST
        state_instance.publisher_instance = publisher_instance
        state_instance.request_user = user
        state_instance.request_note = note
        state_instance.save()

        return state_instance

    def _assert_permissions(self, user, publisher_instance):
        # raise PermissionDenied if user can't change object
        has_object_permission(user,
            opts=publisher_instance._meta,
            action="change",
            raise_exception=True
        )

        # raise PermissionDenied if user can't change PublisherStateModel
        self.model.has_change_permission(
            user,
            raise_exception=True
        )

    def request_publishing(self, user, publisher_instance, note=None):
        self._assert_permissions(user, publisher_instance)

        assert publisher_instance.publisher_is_draft
        assert publisher_instance.is_dirty

        state_instance = self._create_request(
            constants.ACTION_PUBLISH,
            user, publisher_instance, note
        )

        # TODO: fire signal: e.g.: handler to mail user

        return state_instance

    def request_unpublishing(self, user, publisher_instance, note=None):
        self._assert_permissions(user, publisher_instance)

        draft = publisher_instance.get_draft_object()
        if isinstance(draft, Page):
            # It's a Django CMS Page
            assert publisher_instance.get_public_url(language=None, fallback=True), \
                "Can't unpublish a not published instance!"
        else:
            # It's a PublisherModel:
            assert draft.publisher_linked is not None, \
                "Can't unpublish a not published instance!"

        state_instance = self._create_request(
            constants.ACTION_UNPUBLISH,
            user, draft, note
        )

        # TODO: fire signal: e.g.: handler to mail user

        return state_instance

    def _admin_url(self, obj, viewname):
        object_id = obj.pk
        content_type = ContentType.objects.get_for_model(obj)
        content_type_id = content_type.pk
        url = reverse(viewname,
            kwargs={
                "content_type_id": content_type_id,
                "object_id": object_id,
            }
        )
        return url

    def admin_request_publish_url(self, obj):
        return self._admin_url(obj=obj,
            # publisher.admin.PublisherStateModelAdmin.get_urls()
            viewname="admin:publisher_publisherstatemodel_request_publish",
        )

    def admin_request_unpublish_url(self, obj):
        return self._admin_url(obj=obj,
            # publisher.admin.PublisherStateModelAdmin.get_urls()
            viewname="admin:publisher_publisherstatemodel_request_unpublish",
        )

PublisherStateManager = BasePublisherStateManager.from_queryset(PublisherStateQuerySet)
