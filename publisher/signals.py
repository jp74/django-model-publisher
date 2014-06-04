from django.dispatch import Signal


def publisher_pre_delete(sender, **kwargs):
    from publisher.models import PublisherModelBase

    instance = kwargs.get('instance', None)
    if not instance:
        return

    # If the draft record is deleted, the published object should be as well
    if (instance.publisher_is_draft == PublisherModelBase.STATE_DRAFT and
            instance.publisher_linked):
        instance.publisher_linked.delete()


# Sent when a model is being published, before the draft is saved (the draft is sent)
publisher_publish_pre_save_draft = Signal(providing_args=['instance'])


# Sent when a model is published (the draft is sent)
publisher_post_publish = Signal(providing_args=['instance'])


# Sent when a model about to be unpublished (the draft is sent)
publisher_pre_unpublish = Signal(providing_args=['instance'])


# Sent when a model is unpublished (the draft is sent)
publisher_post_unpublish = Signal(providing_args=['instance'])
