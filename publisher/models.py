import logging

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.urlresolvers import reverse
from django.db import models
from django.template.defaultfilters import truncatewords
from django.utils import six, timezone
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

# https://github.com/jedie/django-tools
from django_tools.permissions import ModelPermissionMixin, check_permission

from publisher.permissions import can_publish_object

from . import constants
from .managers import PublisherManager, PublisherStateManager
from .signals import (publisher_post_publish, publisher_post_unpublish, publisher_pre_publish, publisher_pre_unpublish,
                      publisher_publish_pre_save_draft)
from .utils import aldryn_translation_tools_exists, assert_draft, django_cms_exists, parler_exists

log = logging.getLogger(__name__)

if django_cms_exists:
    from cms.models import Page
    from cms.models.placeholdermodel import Placeholder
    from cms.models.fields import PlaceholderField
    from cms.utils.copy_plugins import copy_plugins_to


class PublisherModelBase(ModelPermissionMixin, models.Model):
    publisher_linked = models.OneToOneField(
        'self',
        related_name='publisher_draft',
        null=True,
        editable=False,
        on_delete=models.SET_NULL)
    publisher_is_draft = models.BooleanField(default=True, editable=False, db_index=True)

    publisher_modified_at = models.DateTimeField(default=timezone.now, editable=False)
    publisher_published_at = models.DateTimeField(null=True, editable=False)

    publication_start_date = models.DateTimeField(
        _("publication start date"),
        null=True, blank=True, db_index=True,
        help_text=_(
            "Published content will only be visible from this point in time."
            " Leave blank if always visible."
        )
    )
    publication_end_date = models.DateTimeField(
        _("publication end date"),
        null=True, blank=True, db_index=True,
        help_text=_(
            "When to expire the published version."
            " Leave empty to never expire."
        ),
    )

    publisher_fields = (
        'publisher_linked',
        'publisher_is_draft',
        'publisher_modified_at',
        'publisher_draft',
    )
    publisher_ignore_fields = publisher_fields + (
        'pk',
        'id',
        'publisher_linked',
    )
    publisher_publish_empty_fields = (
        'pk',
        'id',
    )

    class Meta:
        abstract = True

    def get_draft_object(self):
        if not self.publisher_is_draft == True:
            return self.publisher_draft
        return self

    def get_public_object(self):
        if self.publisher_is_draft == False:
            return self
        return self.publisher_linked

    @property
    def is_published(self):
        """
        return True if this instance is the published version.

        Note:
            * It doesn't mean that this draft version has been published!
            * It will ignore start/end date!

        Use self.is_visible() if you want to know if this entry should be publicly accessible.
        """
        return self.publisher_is_draft == False

    @property
    def hidden_by_end_date(self):
        if not self.publication_end_date:
            return False
        return self.publication_end_date <= timezone.now()

    @property
    def hidden_by_start_date(self):
        if not self.publication_start_date:
            return False
        return self.publication_start_date >= timezone.now()

    @property
    def is_visible(self):
        """
        Is this entry publicly available?
        """
        if self.publisher_linked:
            # This is the draft: return visible bool from the published version
            return self.publisher_linked.is_visible

        return self.is_published and (not self.hidden_by_end_date) and (not self.hidden_by_start_date)

    @property
    def is_dirty(self):
        if self.publisher_is_draft == False: # published versions are never dirty
            return False

        # If the record has not been published assume dirty
        if not self.publisher_linked:
            return True

        if self.publisher_modified_at > self.publisher_linked.publisher_modified_at:
            return True

        # Get all placeholders + their plugins to find their modified date
        for placeholder_field in self.get_placeholder_fields():
            placeholder = getattr(self, placeholder_field)
            for plugin in placeholder.get_plugins_list():
                if plugin.changed_date > self.publisher_linked.publisher_modified_at:
                    return True

        return False

    @assert_draft
    def publish(self):
        if self.publisher_is_draft == False:
            log.info("Don't publish %s because it's not the daft version!", self)
            return self

        if not self.is_dirty:
            log.info("Don't publish %s because it's not dirty!", self)
            return self

        publisher_pre_publish.send(sender=self.__class__, instance=self)

        # Reference self for readability
        draft_obj = self

        # Set the published date if this is the first time the page has been published
        if not draft_obj.publisher_linked:
            draft_obj.publisher_published_at = timezone.now()

        if draft_obj.publisher_linked:
            # Duplicate placeholder patch to prevent plugins from being deleted
            # In some random cases a placeholder has been shared between the draft and published
            # version of the page
            self.patch_placeholders(draft_obj)

            # Remove the current published record
            draft_obj.publisher_linked.delete()

        # Duplicate the draft object and set to published
        publish_obj = self.__class__.objects.get(pk=self.pk)
        for fld in self.publisher_publish_empty_fields:
            setattr(publish_obj, fld, None)
        publish_obj.publisher_is_draft = False
        publish_obj.publisher_published_at = draft_obj.publisher_published_at

        # Link the published obj to the draft version
        # publish_obj.publisher_linked = draft_obj
        publish_obj.save()

        # Check for translations, if so duplicate the object
        self.clone_translations(draft_obj, publish_obj)

        # Clone any placeholder fields into the new published object
        self.clone_placeholder(draft_obj, publish_obj)

        # Clone relationships
        self.clone_relations(draft_obj, publish_obj)

        # Link the draft obj to the current published version
        draft_obj.publisher_linked = publish_obj

        publisher_publish_pre_save_draft.send(sender=draft_obj.__class__, instance=draft_obj)

        self._suppress_modified=True # Don't update self.publisher_modified_at
        draft_obj.save()
        self._suppress_modified=False

        publisher_post_publish.send(sender=draft_obj.__class__, instance=draft_obj)

        return publish_obj

    @assert_draft
    def patch_placeholders(self, draft_obj):
        if not django_cms_exists:
            return

        published_obj = draft_obj.publisher_linked

        for field in self.get_placeholder_fields(draft_obj):
            draft_placeholder = getattr(draft_obj, field)
            published_placeholder = getattr(published_obj, field)

            if draft_placeholder.pk == published_placeholder.pk:
                published_placeholder.pk = None
                published_placeholder.save()

    @assert_draft
    def unpublish(self):
        if self.publisher_is_draft == False or not self.publisher_linked:
            return

        publisher_pre_unpublish.send(sender=self.__class__, instance=self)
        self.publisher_linked.delete()
        self.publisher_linked = None
        self.publisher_published_at = None
        self.save()
        publisher_post_unpublish.send(sender=self.__class__, instance=self)

    @assert_draft
    def revert_to_public(self):
        """
        @todo Relook at this method. It would be nice if the draft pk did not have to change
        @toavoid Updates self to a alternative instance
        @toavoid self.__class__ = draft_obj.__class__
        @toavoid self.__dict__ = draft_obj.__dict__
        """
        if not self.publisher_linked:
            return

        # Get published obj and delete the draft
        draft_obj = self
        publish_obj = self.publisher_linked

        draft_obj.publisher_linked = None
        draft_obj.save()
        draft_obj.delete()

        # Mark the published object as a draft
        draft_obj = publish_obj
        publish_obj = None

        draft_obj.publisher_is_draft = True
        draft_obj.save()
        draft_obj.publish()

        return draft_obj

    @staticmethod
    def clone_translations(src_obj, dst_obj):
        if hasattr(src_obj, 'translations'):
            for translation in src_obj.translations.all():
                translation.pk = None
                translation.master = dst_obj
                translation.save()

    def clone_placeholder(self, src_obj, dst_obj):
        if not django_cms_exists:
            return

        for field in self.get_placeholder_fields(src_obj):
            src_placeholder = getattr(src_obj, field)
            dst_placeholder = getattr(dst_obj, field)

            dst_placeholder.pk = None
            dst_placeholder.save()

            setattr(dst_obj, field, dst_placeholder)
            dst_obj.save()

            src_plugins = src_placeholder.get_plugins_list()

            # CMS automatically generates a new Placeholder ID
            copy_plugins_to(src_plugins, dst_placeholder)

    def clone_relations(self, src_obj, dst_obj):
        """
        Since copying relations is so complex, leave this to the implementing class
        """
        pass

    def get_placeholder_fields(self, obj=None):
        if not django_cms_exists:
            return []

        placeholder_fields = []

        if obj is None:
            obj = self

        model_fields = obj.__class__._meta.get_fields()
        for field in model_fields:
            if field.name in self.publisher_ignore_fields:
                continue

            try:
                if isinstance(field, (Placeholder, PlaceholderField)):
                    placeholder_fields.append(field.name)
            except (ObjectDoesNotExist, AttributeError) as err:
                continue

        return placeholder_fields

    _suppress_modified=False

    def save(self, **kwargs):
        if self._suppress_modified is False:
            # FIXME: Will always sets the dirty flag, no matter if really something's changed :(
            self.publisher_modified_at = timezone.now()

        super(PublisherModelBase, self).save(**kwargs)


class PublisherModel(PublisherModelBase):
    objects = PublisherManager()

    class Meta:
        abstract = True

        # https://docs.djangoproject.com/en/1.11/ref/models/options/#default-permissions
        default_permissions = (
            # Django default permissions:
            'add', 'change', 'delete',

            # (un-)publish a object directly & accept/reject a (un-)publish request:
            constants.PERMISSION_CAN_PUBLISH,
        )


if parler_exists:
    from .managers import PublisherParlerManager
    from parler.models import TranslatableModelMixin

    class PublisherParlerModel(TranslatableModelMixin, PublisherModelBase):
        objects = PublisherParlerManager()

        class Meta(PublisherModel.Meta):
            abstract = True

    if aldryn_translation_tools_exists:
        from aldryn_translation_tools.models import TranslatedAutoSlugifyMixin

        class PublisherParlerAutoSlugifyModel(TranslatedAutoSlugifyMixin, PublisherParlerModel):

            def _get_slug_queryset(self, *args, **kwargs):
                """
                The slug must be only unique for drafts
                """
                qs = super(PublisherParlerAutoSlugifyModel, self)._get_slug_queryset()
                qs = qs.filter(publisher_is_draft=True)
                return qs

            def save(self, **kwargs):
                """
                Set new slug by TranslatedAutoSlugifyMixin only on drafts
                see also:
                https://github.com/andersinno/django-model-publisher-ai/issues/8
                """
                if self.publisher_is_draft:
                    # code from TranslatedAutoSlugifyMixin.save():
                    slug = self._get_existing_slug()
                    if not slug or self._slug_exists(slug):
                        slug = self.make_new_slug(slug=slug)
                        setattr(self, self.slug_field_name, slug)

                # NOTE: We call PublisherParlerModel.save() here:
                super(PublisherParlerModel, self).save(**kwargs)

            class Meta(PublisherParlerModel.Meta):
                abstract = True


class PublisherStateModel(ModelPermissionMixin, models.Model):
    """
    Save request/response actions for a publisher model.
    """
    objects = PublisherStateManager()

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()

    # Note: It's always the draft version!
    publisher_instance = GenericForeignKey('content_type', 'object_id')

    #-------------------------------------------------------------------------

    ACTION_CHOICES = (
        (constants.ACTION_PUBLISH, _('publish')),
        (constants.ACTION_UNPUBLISH,  _('unpublish')),
    )
    ACTION_DICT=dict(ACTION_CHOICES)

    action = models.CharField(max_length=9, choices=ACTION_CHOICES, editable=False)

    @property
    def action_name(self):
        return self.ACTION_DICT[self.action]

    #-------------------------------------------------------------------------

    STATE_CHOICES = (
        (constants.STATE_REQUEST, _('request')),
        (constants.STATE_REJECTED, _('rejected')),
        (constants.STATE_ACCEPTED, _('accepted')),
        (constants.STATE_DONE, _('done')), # e.g.: close a entry with deleted instance
    )
    STATE_DICT=dict(STATE_CHOICES)

    state = models.CharField(max_length=8, choices=STATE_CHOICES, editable=False)

    @property
    def state_name(self):
        return self.STATE_DICT[self.state]

    @cached_property
    def is_open(self):
        """
        return True if is not a 'closed' entry.
        Is self.publisher_instance is None: The instance was deleted.
        """
        return self.publisher_instance is not None and self.state == constants.STATE_REQUEST

    #-------------------------------------------------------------------------

    request_timestamp = models.DateTimeField(null=True, unique=True, editable=False)
    request_user = models.ForeignKey( # User that creates the request
        getattr(settings, 'AUTH_USER_MODEL', 'auth.User'),
        null=True, editable=False,
        related_name='%(app_label)s_%(class)s_request_user'
    )
    request_note = models.TextField(_('Request Note'),
        help_text=_('Why create this publish/delete request?'),
        blank=True, null=True
    )

    #-------------------------------------------------------------------------

    response_timestamp = models.DateTimeField(null=True, unique=True, editable=False)
    response_user = models.ForeignKey( # User that reject/accept the request
        getattr(settings, 'AUTH_USER_MODEL', 'auth.User'),
        null=True, editable=False,
        related_name='%(app_label)s_%(class)s_response_user'
    )
    response_note = models.TextField(_('Response Note'),
        help_text=_('Why accept or reject this publish/delete request?'),
        blank=True, null=True
    )

    #-------------------------------------------------------------------------

    def object_permission_name(self, action):
        """
        Built the permission name with self.content_type

        check permission against self.content_type and not agains self.publisher_instance
        works also, if the instance is deleted ;)
        """
        permission = "{app}.{action}_{model}".format(
            app=self.content_type.app_label,
            action=action,
            model=self.content_type.model # python model class name
        )
        if permission == "cms.can_publish_page":
            # FIXME: Django CMS code name doesn't has the prefix "can_" !
            # TODO: Remove "can_" from own permissions to unify it.
            # see also: publisher.permissions.has_object_permission
            # https://github.com/wearehoods/django-ya-model-publisher/issues/8
            permission = "cms.publish_page"
        return permission

    def check_object_permission(self, user, action, raise_exception=True):
        """
        e.g.: <app-label>.<action>_<model-name>

        TODO: Use only permission checks against self.content_type everywhere if possible!
        """
        permission_name = self.object_permission_name(action)
        return check_permission(user, permission_name, raise_exception)

    def check_object_publish_permission(self, user, raise_exception=True):
        """
        Check 'publish' permission with self.content_type, e.g.:
            <app-label>.publish_<model-name>
        """
        return self.check_object_permission(user,
            action=constants.PERMISSION_CAN_PUBLISH,
            raise_exception=raise_exception
        )

    @classmethod
    def has_can_publish_permission(cls, user, raise_exception=True):
        """
        user permission to:
         * (un-)publish a object directly
         * accept/reject a (un-)publish request
        """
        permission_name = cls.extra_permission_name(action=constants.PERMISSION_CAN_PUBLISH)
        return check_permission(user, permission_name, raise_exception)

    #-------------------------------------------------------------------------

    def save(self, *args, **kwargs):
        if self.publisher_instance is not None:
            instance = self.publisher_instance
            try:
                assert instance.publisher_is_draft == True
            except AttributeError as err:
                raise AssertionError("%s: %s (class: %r) is not a PublisherModel" % (
                        err, repr(instance), instance.__class__.__name__
                    )
                )

        # Update timestamps
        if self.state == constants.STATE_REQUEST:
            self.request_timestamp = timezone.now()
        else:
            self.response_timestamp = timezone.now()

        super(PublisherStateModel, self).save(*args, **kwargs)

    #-------------------------------------------------------------------------

    @cached_property
    def short_request_note(self, max_length=30):
        return truncatewords(self.request_note, max_length)

    @cached_property
    def short_response_note(self, max_length=30):
        return truncatewords(self.response_note, max_length)

    @cached_property
    def status_text(self):
        txt = [self.action_name, self.state_name]

        if self.is_open or self.publisher_instance is None:
            if self.request_user:
                txt.append(
                    _('from: %(user)s') % {'user': self.request_user}
                )
            if self.request_note:
                txt.append("(%s)" % self.short_request_note)
        else:
            txt.append(
                _('from: %(user)s') % {'user': self.response_user}
            )
            txt.append("(%s)" % self.short_response_note)

        return " ".join([six.text_type(s) for s in txt])

    def admin_reply_url(self):
        url = reverse(
            "admin:publisher_publisherstatemodel_reply_request",
            kwargs={'pk': self.pk}
        )
        return url

    def admin_close_deleted_url(self):
        """
        Link to 'close this deleted request'
        """
        url = reverse(
            "admin:publisher_publisherstatemodel_close_deleted",
            kwargs={'pk': self.pk}
        )
        return url

    ############################################################################
    # response methods:

    def accept(self, response_user, response_note=None):
        assert self.state == constants.STATE_REQUEST, "%r != %r" % (self.state, constants.STATE_REQUEST)
        assert self.publisher_instance is not None, "Publisher instance was deleted!"
        assert self.request_user is not None
        assert self.request_timestamp is not None

        opts = self.publisher_instance._meta
        can_publish_object(response_user, opts, raise_exception=True)

        self.response_user = response_user
        self.response_note = response_note
        self.state = constants.STATE_ACCEPTED

        if self.action == constants.ACTION_PUBLISH:
            # publish
            assert self.publisher_instance.publisher_is_draft==True
            assert self.publisher_instance.is_dirty

            if Page is not None and isinstance(self.publisher_instance, Page):
                log.debug("Publish cms page %s", self.publisher_instance)

                languages = self.publisher_instance.title_set.values_list("language", flat=True)
                for language in languages:
                    log.debug("Publish cms page in language %s", language)
                    self.publisher_instance.publish(language=language)
            else:
                self.publisher_instance.publish()

        elif self.action == constants.ACTION_UNPUBLISH:
            # unpublish

            if Page is not None and isinstance(self.publisher_instance, Page):
                log.debug("Unpublish cms page %s", self.publisher_instance)

                languages = self.publisher_instance.title_set.values_list("language", flat=True)
                for language in languages:
                    log.debug("Unpublish cms page in language %s", language)
                    self.publisher_instance.unpublish(language=language)
            else:

                published = self.publisher_instance.get_public_object()
                assert published is not None
                draft = self.publisher_instance.get_draft_object()
                draft.unpublish()
        else:
            raise ValidationError("Unknown action: %r !" % self.action)

        # TODO: fire signal: e.g.: handler to mail user

        log.info('Accept "%s" for "%s"', self.action, self.publisher_instance)
        self.save()

    def reject(self, response_user, response_note):
        assert self.state == constants.STATE_REQUEST, "%r != %r" % (self.state, constants.STATE_REQUEST)
        assert self.publisher_instance is not None, "Publisher instance was deleted!"
        assert self.request_user is not None
        assert self.request_timestamp is not None

        opts = self.publisher_instance._meta
        can_publish_object(response_user, opts, raise_exception=True)

        self.response_user = response_user
        self.response_note = response_note
        self.state = constants.STATE_REJECTED

        # TODO: fire signal: e.g.: handler to mail user

        log.info('Reject "%s" for "%s"', self.action, self.publisher_instance)
        self.save()

    def close_deleted(self, response_user):
        self.state = constants.STATE_DONE
        self.response_user = response_user
        log.info("Close state for deleted instance")
        self.save()

    def __str__(self):
        if self.publisher_instance is None:
            return "Deleted '%s' with pk:%r %s" % (self.content_type, self.object_id, self.status_text)

        txt = '"%s" %s' % (self.publisher_instance, self.status_text)
        if self.is_open:
            txt += ' (open)'
        return txt

    class Meta:
        verbose_name = _("Publisher State")
        verbose_name_plural = _("Publisher States")
        get_latest_by = 'request_timestamp'
        ordering = ['-request_timestamp']
