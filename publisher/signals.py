import logging

from django.db.models import signals
from django.dispatch import Signal

from cms.models import CMSPlugin

from publisher.models import PublisherModelBase


log = logging.getLogger(__name__)


def publisher_pre_delete(sender, **kwargs):
    instance = kwargs.get('instance', None)
    if not instance:
        return

    # If the draft record is deleted, the published object should be as well
    if instance.is_draft and instance.publisher_linked:
        instance.unpublish()


def placeholder_post_save_callback(sender, **kwargs):
    """
    Work-a-round for:
    https://github.com/wearehoods/django-ya-model-publisher/issues/4

    The problem:
    If you only change the content of the PlaceholderField(): .save() is not executed.
    So the publisher model will not marked as dirty.

    To activate this, put this in e.g. your models.py:

        signals.post_save.connect(placeholder_post_save_callback)

    see also:
    https://groups.google.com/d/msg/django-cms/sH6D7Sg7QhU/w5l2hza_AQAJ
    """
    instance = kwargs.get("instance", None)
    if instance is None:
        log.debug("Skip: No instance.")
        return

    if not isinstance(instance, CMSPlugin):
        return

    placeholder = instance.placeholder # cms.models.placeholdermodel.Placeholder instance

    # FIXME: How to get all relation sets?!?
    for name in dir(placeholder):
        if name.startswith("_") or not name.endswith("_set"):
            continue

        func = getattr(placeholder, name)
        for publisher_instance in func.all():
            if not isinstance(publisher_instance, PublisherModelBase):
                continue

            if not publisher_instance.is_draft:
                # log.debug("Skip: not draft")
                continue

            log.debug("save PublisherModel instance %s to mark it as dirty", repr(publisher_instance))
            # mark PublisherModel instance as dirty and update publisher_modified_at timestamp:
            publisher_instance.save()

            assert publisher_instance.is_dirty, "%s is not dirty!" % publisher_instance


# Sent when a model is about to be published (the draft is sent).
publisher_pre_publish = Signal(providing_args=['instance'])


# Sent when a model is being published, before the draft is saved (the draft is sent).
publisher_publish_pre_save_draft = Signal(providing_args=['instance'])


# Sent when a model is published (the draft is sent)
publisher_post_publish = Signal(providing_args=['instance'])


# Sent when a model is about to be unpublished (the draft is sent).
publisher_pre_unpublish = Signal(providing_args=['instance'])


# Sent when a model is unpublished (the draft is sent).
publisher_post_unpublish = Signal(providing_args=['instance'])
