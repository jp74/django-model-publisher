
from django.core.urlresolvers import reverse
from django.db import models

from cms.models.pluginmodel import CMSPlugin

from publisher.managers import PublisherManager
from publisher.models import PublisherModel
from publisher.utils import aldryn_translation_tools_exists, parler_exists
from publisher_cms.cms_toolbars import PublisherPageToolbar


class PublisherTestModel(PublisherModel):
    no = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=100)

    objects = PublisherManager()

    def get_absolute_url(self):
        return reverse("test-detail", kwargs={"pk": self.pk})

    def __str__(self):
        return "<PublisherTestModel pk:%r no:%r is_draft:%r title:%r>" % (self.pk, self.no, self.publisher_is_draft, self.title)

    class Meta(PublisherModel.Meta):
        verbose_name = "Publisher Test Model"
        verbose_name_plural = "Publisher Test Model"

        # Just to test code parts depend on unique_together:
        unique_together = (
            ("publisher_is_draft", "no", "title"),
        )


class PlainTextPluginModel(CMSPlugin):
    text = models.TextField()


if parler_exists:
    from parler.models import TranslatedFields
    from publisher.models import PublisherParlerModel

    class PublisherParlerTestModel(PublisherParlerModel):
        translations = TranslatedFields(
            title=models.CharField(max_length=100)
        )


if aldryn_translation_tools_exists:
    from publisher.models import PublisherParlerAutoSlugifyModel

    class PublisherParlerAutoSlugifyTestModel(PublisherParlerAutoSlugifyModel):
        slug_source_field_name = "title" # TranslatedAutoSlugifyMixin options

        translations = TranslatedFields(
            title=models.CharField(max_length=100),
            slug=models.SlugField(max_length=255, db_index=True, blank=True),
        )


PublisherPageToolbar.replace_toolbar()
