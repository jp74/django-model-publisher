
import unittest

from django import test
from django.core.cache import cache

from publisher.utils import aldryn_translation_tools_exists, parler_exists

if parler_exists:
    from parler.managers import TranslatableQuerySet

    from publisher_test_project.publisher_test_app.models import PublisherParlerTestModel

    if aldryn_translation_tools_exists:
        from publisher_test_project.publisher_test_app.models import PublisherParlerAutoSlugifyTestModel


@unittest.skipIf(parler_exists != True, 'Django-Parler is not installed')
class PublisherParlerTest(test.TestCase):

    def test_queryset_subclass(self):
        queryset = PublisherParlerTestModel.objects.all()
        self.assertTrue(issubclass(queryset.__class__, TranslatableQuerySet))

    def test_creation(self):
        x = PublisherParlerTestModel.objects.create(title='english title')
        x.create_translation('de', title='deutsche Titel')
        self.assertEqual(sorted(x.get_available_languages()), ['de', 'en'])

    def test_creating_instance(self):
        instance = PublisherParlerTestModel()
        instance.set_current_language('en')
        instance.title = 'The english title'
        instance.save()
        instance.set_current_language('de')
        instance.title = 'Der deutsche Titel'
        instance.save()

        instance = PublisherParlerTestModel.objects.get(pk=instance.pk)

        self.assertEqual(sorted(instance.get_available_languages()), ['de', 'en'])

        count = PublisherParlerTestModel.objects.count()
        self.assertEqual(count, 1)

        count = PublisherParlerTestModel.objects.drafts().count()
        self.assertEqual(count, 1)

        count = PublisherParlerTestModel.objects.published().count()
        self.assertEqual(count, 0)

        count = PublisherParlerTestModel.objects.visible().count()
        self.assertEqual(count, 0)

        count = PublisherParlerTestModel.objects.language(language_code='en').count()
        self.assertEqual(count, 1)

        queryset = PublisherParlerTestModel.objects.active_translations('en')
        queryset = queryset.drafts()
        count = queryset.count()
        self.assertEqual(count, 1)

        queryset = PublisherParlerTestModel.objects.active_translations('en')
        queryset = queryset.published()
        count = queryset.count()
        self.assertEqual(count, 0)

        queryset = PublisherParlerTestModel.objects.active_translations('de')
        queryset = queryset.drafts()
        count = queryset.count()
        self.assertEqual(count, 1)

    def test_publish(self):
        instance = PublisherParlerTestModel.objects.create()
        instance.publish()

        count = PublisherParlerTestModel.objects.drafts().count()
        self.assertEqual(count, 1)

        count = PublisherParlerTestModel.objects.published().count()
        self.assertEqual(count, 1)

        count = PublisherParlerTestModel.objects.visible().count()
        self.assertEqual(count, 1)



@unittest.skipIf(aldryn_translation_tools_exists != True, 'aldryn_translation_tools is not installed')
class PublisherParlerAutoSlugifyTest(test.TestCase):
    def tearDown(self):
        # Parler cache must be cleared, otherwise some test failed.
        # Maybe a other way is to set PARLER_ENABLE_CACHING=False in settings
        cache.clear()

    def _create_draft(self):
        instance = PublisherParlerAutoSlugifyTestModel.objects.language('de').create(title='Der deutsche Titel')
        instance.set_current_language('en')
        instance.title = 'The english title'
        instance.save()
        instance = PublisherParlerAutoSlugifyTestModel.objects.get(pk=instance.pk)
        return instance

    def assert_instance(self, instance):
        instance.set_current_language('de')
        self.assertEqual(instance.title, 'Der deutsche Titel')
        self.assertEqual(instance.slug, "der-deutsche-titel")

        instance.set_current_language('en')
        self.assertEqual(instance.title, 'The english title')
        self.assertEqual(instance.slug, "the-english-title")

        # FIXME: Will fail in some cases:
        # self.assertEqual(sorted(instance.get_available_languages()), ['de', 'en'])

    def test_slug_creation(self):
        instance = self._create_draft()
        self.assert_instance(instance)

    def test_publish(self):
        instance = self._create_draft()
        self.assert_instance(instance)

        count = PublisherParlerAutoSlugifyTestModel.objects.drafts().count()
        self.assertEqual(count, 1)

        count = PublisherParlerAutoSlugifyTestModel.objects.published().count()
        self.assertEqual(count, 0)

        count = PublisherParlerAutoSlugifyTestModel.objects.visible().count()
        self.assertEqual(count, 0)

        instance.publish()

        count = PublisherParlerAutoSlugifyTestModel.objects.drafts().count()
        self.assertEqual(count, 1)

        count = PublisherParlerAutoSlugifyTestModel.objects.published().count()
        self.assertEqual(count, 1)

        count = PublisherParlerAutoSlugifyTestModel.objects.visible().count()
        self.assertEqual(count, 1)

        count = PublisherParlerAutoSlugifyTestModel.objects.count()
        self.assertEqual(count, 2)

    def test_model_properties(self):
        draft_obj = PublisherParlerAutoSlugifyTestModel.objects.create(title="one")

        self.assertEqual(draft_obj.publisher_is_draft, True)
        self.assertEqual(draft_obj.is_published, False)
        self.assertEqual(draft_obj.is_visible, False)
        self.assertEqual(draft_obj.is_dirty, True)

        publish_obj = draft_obj.publish()

        self.assertEqual(publish_obj.title, "one")
        self.assertEqual(publish_obj.publisher_is_draft, False)
        self.assertEqual(publish_obj.is_published, True)
        self.assertEqual(publish_obj.is_visible, True)
        self.assertEqual(publish_obj.is_dirty, False) # published versions are never dirty

        self.assertEqual(draft_obj.title, "one")
        self.assertEqual(draft_obj.publisher_is_draft, True)
        self.assertEqual(draft_obj.is_published, False) # It's the draft, not the published object!
        self.assertEqual(draft_obj.is_visible, True)
        self.assertEqual(draft_obj.is_dirty, False)

        draft_obj.title="two"
        draft_obj.save()

        self.assertEqual(publish_obj.title, "one")
        self.assertEqual(publish_obj.publisher_is_draft, False)
        self.assertEqual(publish_obj.is_published, True)
        self.assertEqual(publish_obj.is_visible, True)
        self.assertEqual(publish_obj.is_dirty, False) # published versions are never dirty

        self.assertEqual(draft_obj.title, "two")
        self.assertEqual(draft_obj.publisher_is_draft, True)
        self.assertEqual(draft_obj.is_published, False) # It's the draft, not the published object!
        self.assertEqual(draft_obj.is_visible, True)
        self.assertEqual(draft_obj.is_dirty, True)

        publish_obj = draft_obj.publish()

        self.assertEqual(publish_obj.title, "two")
        self.assertEqual(publish_obj.publisher_is_draft, False)
        self.assertEqual(publish_obj.is_published, True)
        self.assertEqual(publish_obj.is_visible, True)
        self.assertEqual(publish_obj.is_dirty, False) # published versions are never dirty

        self.assertEqual(draft_obj.title, "two")
        self.assertEqual(draft_obj.publisher_is_draft, True)
        self.assertEqual(draft_obj.is_published, False) # It's the draft, not the published object!
        self.assertEqual(draft_obj.is_visible, True)
        self.assertEqual(draft_obj.is_dirty, False)

    def test_delete(self):
        for no in range(10):
            title = "%i" % no
            instance = PublisherParlerAutoSlugifyTestModel.objects.create(title=title)
            instance.publish()

        count = PublisherParlerAutoSlugifyTestModel.objects.drafts().count()
        self.assertEqual(count, 10)

        count = PublisherParlerAutoSlugifyTestModel.objects.published().count()
        self.assertEqual(count, 10)

        count = PublisherParlerAutoSlugifyTestModel.objects.count()
        self.assertEqual(count, 20)

        PublisherParlerAutoSlugifyTestModel.objects.all().delete()
        count = PublisherParlerAutoSlugifyTestModel.objects.count()
        self.assertEqual(count, 0)
