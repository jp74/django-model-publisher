from django.core.urlresolvers import reverse
from django.db import models

from publisher_cms.cms_toolbars import PublisherPageToolbar

from publisher.managers import PublisherManager
from publisher.models import PublisherModel


try:
    import parler
except ImportError:
    parler=None


try:
    import aldryn_translation_tools
except ImportError as err:
    aldryn_translation_tools=None


class PublisherTestModel(PublisherModel):
    title = models.CharField(max_length=100)
    objects = PublisherManager()

    def get_absolute_url(self):
        return reverse("test-detail", kwargs={"pk": self.pk})

    def __str__(self):
        return "<PublisherTestModel pk:%r is_draft:%r title:%r>" % (self.pk, self.publisher_is_draft, self.title)

    class Meta(PublisherModel.Meta):
        verbose_name = "Publisher Test Model"
        verbose_name_plural = "Publisher Test Model"


if parler is not None:
    from parler.models import TranslatedFields
    from publisher.models import PublisherParlerModel

    class PublisherParlerTestModel(PublisherParlerModel):
        translations = TranslatedFields(
            title=models.CharField(max_length=100)
        )


if aldryn_translation_tools is not None:
    from publisher.models import PublisherParlerAutoSlugifyModel

    class PublisherParlerAutoSlugifyTestModel(PublisherParlerAutoSlugifyModel):
        slug_source_field_name = "title" # TranslatedAutoSlugifyMixin options

        translations = TranslatedFields(
            title=models.CharField(max_length=100),
            slug=models.SlugField(max_length=255, db_index=True, blank=True),
        )


PublisherPageToolbar.replace_toolbar()
