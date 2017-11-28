import logging

from cms.models import CMSPlugin

log = logging.getLogger(__name__)


def publisher_pre_delete(sender, **kwargs):
    instance = kwargs.get('instance', None)
    if not instance:
        return

    # If the draft record is deleted, the published object should be as well
    if instance.publisher_is_draft and instance.publisher_linked:
        instance.unpublish()


def publisher_post_save(sender, **kwargs):
    """
    Work-a-round for:
    https://github.com/wearehoods/django-ya-model-publisher/issues/4

    The problem:
    If you only change the content of the PlaceholderField(): .save() is not executed.
    So the publisher model will not marked as dirty.

    see also:
    https://groups.google.com/d/msg/django-cms/sH6D7Sg7QhU/w5l2hza_AQAJ
    """
    instance = kwargs.get("instance", None)
    if instance is None:
        log.debug("Skip: No instance.")
        return

    if not isinstance(instance, CMSPlugin):
        log.debug("Skip: %s instance %s is no CMSPlugin", instance.__class__.__name__, repr(instance))
        return

    placeholder = instance.placeholder # cms.models.placeholdermodel.Placeholder instance

    # FIXME: How to get all relation sets?!?
    for name in dir(placeholder):
        if name.startswith("_") or not name.endswith("_set"):
            continue

        func = getattr(placeholder, name)
        for publisher_instance in func.all():
            from publisher.models import PublisherModelBase
            if not isinstance(publisher_instance, PublisherModelBase):
                continue

            if not publisher_instance.publisher_is_draft:
                # log.debug("Skip: not draft")
                continue

            log.debug("+++ save PublisherModel instance %s to mark it as dirty", repr(publisher_instance))
            # mark PublisherModel instance as dirty and update publisher_modified_at timestamp:
            publisher_instance.save()

            assert publisher_instance.is_dirty, "%s is not dirty!" % publisher_instance
