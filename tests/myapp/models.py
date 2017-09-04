from django.db import models

from publisher.managers import PublisherManager
from publisher.models import PublisherModel


try:
    import parler
except ImportError:
    PARLER_INSTALLED=False
else:
    PARLER_INSTALLED = True


try:
    import aldryn_translation_tools
except ImportError as err:
    TRANSLATION_TOOLS_INSTALLED=False
else:
    TRANSLATION_TOOLS_INSTALLED = True


class PublisherTestModel(PublisherModel):
    title = models.CharField(max_length=100)
    objects = PublisherManager()


if PARLER_INSTALLED:
    from parler.models import TranslatedFields
    from publisher.models import PublisherParlerModel

    class PublisherParlerTestModel(PublisherParlerModel):
        translations = TranslatedFields(
            title=models.CharField(max_length=100)
        )


if TRANSLATION_TOOLS_INSTALLED:
    from publisher.models import PublisherParlerAutoSlugifyModel

    class PublisherParlerAutoSlugifyTestModel(PublisherParlerAutoSlugifyModel):
        slug_source_field_name = "title" # TranslatedAutoSlugifyMixin options

        translations = TranslatedFields(
            title=models.CharField(max_length=100),
            slug=models.SlugField(max_length=255, db_index=True, blank=True),
        )
