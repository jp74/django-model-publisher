

"""
    created 2017 by Jens Diemer <ya-publisher@jensdiemer.de>

"""


import logging

from django.conf import settings
from django.core.urlresolvers import NoReverseMatch, reverse
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from cms.models import CMSPlugin, PlaceholderField
from cms.utils.i18n import force_language

from parler.models import TranslatedFields
from publisher.models import PublisherParlerAutoSlugifyModel

# https://github.com/jedie/django-cms-tools
from django_cms_tools.permissions import EditModeAndChangePermissionMixin
from publisher_test_project.publisher_list_app import constants

log = logging.getLogger(__name__)


class PublisherItem(EditModeAndChangePermissionMixin, PublisherParlerAutoSlugifyModel):
    # TranslatedAutoSlugifyMixin options
    slug_source_field_name = "text"

    translations = TranslatedFields(
        text=models.CharField(max_length=255),
        slug=models.SlugField(max_length=255, db_index=True, blank=True),
    )
    content = PlaceholderField(slotname="item_content")

    #--------------------------------------------------------------------------

    def get_absolute_url(self, language=None):
        language = language or self.get_current_language()
        slug = self.safe_translation_getter('slug', language_code=language)

        with force_language(language):
            if not slug:
                return reverse('%s:publisher-list' % constants.LIST_APPHOOK_NAMESPACE)
            else:
                return reverse(
                    '%s:publisher-detail' % constants.LIST_APPHOOK_NAMESPACE,
                    kwargs={"slug": slug},
                )

    def __str__(self):
        """
        str() used in relation choice fields, wo we used the
        published fields, if available
        """
        if self.publisher_linked is None:
            obj = self
        else:
            obj = self.publisher_linked

        text = obj.safe_translation_getter(field="text", any_language=True) or "none"

        if self.publisher_is_draft:
            info = "draft,"
            if self.publisher_linked is None:
                info += "not published"
            else:
                info += "is published"
        else:
            info = "published"

        return "%s (pk:%r, %s)" % (text, self.pk, info)


class PublisherItemCMSPlugin(CMSPlugin):
    item=models.ForeignKey(
        PublisherItem,
        limit_choices_to={
            # Limit selection to drafts that are published
            "publisher_is_draft": True,
            "publisher_linked__isnull": False,
        },
    )

    def __str__(self):
        return "%s" % self.item
