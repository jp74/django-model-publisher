import logging

from django.utils import timezone
from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from .managers import PublisherManager
from .utils import assert_draft
from .signals import (
    publisher_publish_pre_save_draft,
    publisher_pre_publish,
    publisher_post_publish,
    publisher_pre_unpublish,
    publisher_post_unpublish,
)

log = logging.getLogger(__name__)


class PublisherModelBase(models.Model):
    STATE_PUBLISHED = False
    STATE_DRAFT = True

    publisher_linked = models.OneToOneField(
        'self',
        related_name='publisher_draft',
        null=True,
        editable=False,
        on_delete=models.SET_NULL)
    publisher_is_draft = models.BooleanField(
        default=STATE_DRAFT,
        editable=False,
        db_index=True)
    publisher_modified_at = models.DateTimeField(
        default=timezone.now,
        editable=False)

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

    @property
    def is_draft(self):
        return self.publisher_is_draft == self.STATE_DRAFT

    @property
    def is_published(self):
        """
        Note: will ignore start/end date!
        Use self.is_visible() if you want to know if this entry should be publicly accessible.
        """
        return self.publisher_is_draft == self.STATE_PUBLISHED

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
        return self.is_published and (not self.hidden_by_end_date) and (not self.hidden_by_start_date)

    @property
    def is_dirty(self):
        if not self.is_draft:
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
        if not self.is_draft:
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
        publish_obj.publisher_is_draft = self.STATE_PUBLISHED
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
        try:
            from cms.utils.copy_plugins import copy_plugins_to  # noqa
        except ImportError:
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
        if not self.is_draft or not self.publisher_linked:
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

        draft_obj.publisher_is_draft = draft_obj.STATE_DRAFT
        draft_obj.save()
        draft_obj.publish()

        return draft_obj

    def get_unique_together(self):
        return self._meta.unique_together

    def get_field(self, field_name):
        # return the actual field (not the db representation of the field)
        try:
            return self._meta.get_field_by_name(field_name)[0]
        except models.fields.FieldDoesNotExist:
            return None

    @staticmethod
    def clone_translations(src_obj, dst_obj):
        if hasattr(src_obj, 'translations'):
            for translation in src_obj.translations.all():
                translation.pk = None
                translation.master = dst_obj
                translation.save()

    def clone_placeholder(self, src_obj, dst_obj):
        try:
            from cms.utils.copy_plugins import copy_plugins_to
        except ImportError:
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
        placeholder_fields = []

        try:
            from cms.models.placeholdermodel import Placeholder
            from cms.models.fields import PlaceholderField
        except ImportError:
            return placeholder_fields

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
            self.publisher_modified_at = timezone.now()

        super(PublisherModelBase, self).save(**kwargs)


class PublisherModel(PublisherModelBase):
    objects = PublisherManager()

    class Meta:
        abstract = True
        permissions = (
            ('can_publish', 'Can publish'),
        )


try:
    from .managers import PublisherParlerManager
    from parler.models import TranslatableModelMixin
except ImportError:
    pass
else:
    class PublisherParlerModel(TranslatableModelMixin, PublisherModelBase):
        objects = PublisherParlerManager()

        class Meta(PublisherModel.Meta):
            abstract = True

    try:
        from aldryn_translation_tools.models import TranslatedAutoSlugifyMixin
    except ImportError:
        pass
    else:
        class PublisherParlerAutoSlugifyModel(TranslatedAutoSlugifyMixin, PublisherParlerModel):

            def _get_slug_queryset(self, *args, **kwargs):
                """
                The slug must be only unique for drafts
                """
                qs = super(PublisherParlerAutoSlugifyModel, self)._get_slug_queryset()
                qs = qs.filter(publisher_is_draft=PublisherModelBase.STATE_DRAFT)
                return qs

            def save(self, **kwargs):
                """
                Set new slug by TranslatedAutoSlugifyMixin only on drafts
                see also:
                https://github.com/andersinno/django-model-ya-publisher/issues/8
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
