import datetime
import logging

import time
import unittest

import pytest

from django import test
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from django_tools.permissions import add_permissions, create_permission, get_admin_permissions, log_user_permissions
from django_tools.unittest_utils.user import create_user
from mock import MagicMock
from myapp.models import PublisherTestModel

from publisher import constants
from publisher.middleware import PublisherMiddleware, get_draft_status
from publisher.models import PublisherStateModel
from publisher.signals import publisher_post_publish, publisher_post_unpublish
from publisher.utils import NotDraftException

try:
    import parler
    from parler.managers import TranslatableQuerySet
except ImportError:
    PARLER_INSTALLED=False
else:
    PARLER_INSTALLED = True
    from myapp.models import PublisherParlerTestModel


TRANSLATION_TOOLS_INSTALLED=False
if PARLER_INSTALLED:
    try:
        import aldryn_translation_tools
    except ImportError as err:
        pass
    else:
        TRANSLATION_TOOLS_INSTALLED = True
        from myapp.models import PublisherParlerAutoSlugifyTestModel


log = logging.getLogger(__name__)
User = get_user_model()


class PublisherTest(test.TestCase):

    def test_creating_model_creates_only_one_record(self):
        PublisherTestModel.objects.create(title='Test model')
        count = PublisherTestModel.objects.count()
        self.assertEqual(count, 1)

    def test_new_models_are_draft(self):
        instance = PublisherTestModel(title='Test model')
        self.assertTrue(instance.is_draft)

    def test_editing_a_record_does_not_create_a_duplicate(self):
        instance = PublisherTestModel.objects.create(title='Test model')
        instance.title = 'Updated test model'
        instance.save()
        count = PublisherTestModel.objects.count()
        self.assertEqual(count, 1)

    def test_editing_a_draft_does_not_update_published_record(self):
        title = 'Test model'
        instance = PublisherTestModel.objects.create(title=title)
        instance.publish()
        instance.title = 'Updated test model'
        instance.save()
        published_instance = PublisherTestModel.objects.published().get()
        self.assertEqual(published_instance.title, title)

    def test_publishing_creates_new_record(self):
        instance = PublisherTestModel.objects.create(title='Test model')
        instance.publish()

        published = PublisherTestModel.objects.published().count()
        drafts = PublisherTestModel.objects.drafts().count()

        self.assertEqual(published, 1)
        self.assertEqual(drafts, 1)

    def test_unpublishing_deletes_published_record(self):
        instance = PublisherTestModel.objects.create(title='Test model')
        instance.publish()
        instance.unpublish()

        published = PublisherTestModel.objects.published().count()
        drafts = PublisherTestModel.objects.drafts().count()

        self.assertEqual(published, 0)
        self.assertEqual(drafts, 1)

    def test_unpublished_record_can_be_republished(self):
        instance = PublisherTestModel.objects.create(title='Test model')
        instance.publish()
        instance.unpublish()
        instance.publish()

        published = PublisherTestModel.objects.published().count()
        drafts = PublisherTestModel.objects.drafts().count()

        self.assertEqual(published, 1)
        self.assertEqual(drafts, 1)

    def test_published_date_is_set_to_none_for_new_records(self):
        draft = PublisherTestModel(title='Test model')
        self.assertEqual(draft.publisher_published_at, None)

    def test_published_date_is_updated_when_publishing(self):
        now = timezone.now()
        draft = PublisherTestModel.objects.create(title='Test model')
        draft.publish()
        draft = PublisherTestModel.objects.drafts().get()
        published = PublisherTestModel.objects.drafts().get()

        self.assertGreaterEqual(draft.publisher_published_at, now)
        self.assertGreaterEqual(published.publisher_published_at, now)
        self.assertEqual(draft.publisher_published_at, published.publisher_published_at)

    def test_published_date_is_not_changed_when_publishing_twice(self):
        published_date = datetime.datetime(1970, 1, 1, 0, 0, tzinfo=timezone.utc)
        draft = PublisherTestModel.objects.create(title='Test model')
        draft.publish()
        published = PublisherTestModel.objects.drafts().get()
        draft.publisher_published_at = published_date
        draft.save()
        published.publisher_published_at = published_date
        published.save()

        draft.publish()
        draft = PublisherTestModel.objects.drafts().get()
        published = PublisherTestModel.objects.drafts().get()
        self.assertEqual(draft.publisher_published_at, published_date)
        self.assertEqual(published.publisher_published_at, published_date)

    def test_published_date_is_set_to_none_when_unpublished(self):
        draft = PublisherTestModel.objects.create(title='Test model')
        draft.publish()
        draft.unpublish()
        self.assertIsNone(draft.publisher_published_at)

    def test_published_date_is_set_when_republished(self):
        now = timezone.now()
        draft = PublisherTestModel.objects.create(title='Test model')
        draft.publish()
        draft.unpublish()
        draft.publish()
        self.assertGreaterEqual(draft.publisher_published_at, now)

    def test_deleting_draft_also_deletes_published_record(self):
        instance = PublisherTestModel.objects.create(title='Test model')
        instance.publish()
        instance.delete()

        published = PublisherTestModel.objects.published().count()
        drafts = PublisherTestModel.objects.drafts().count()

        self.assertEqual(published, 0)
        self.assertEqual(drafts, 0)

    def test_delete_published_does_not_delete_draft(self):
        obj = PublisherTestModel.objects.create(title='Test model')
        obj.publish()

        published = PublisherTestModel.objects.published().get()
        published.delete()

        published = PublisherTestModel.objects.published().count()
        drafts = PublisherTestModel.objects.drafts().count()

        self.assertEqual(published, 0)
        self.assertEqual(drafts, 1)

    def test_reverting_reverts_draft_from_published_record(self):
        title = 'Test model'
        instance = PublisherTestModel.objects.create(title=title)
        instance.publish()
        instance.title = 'Updated test model'
        instance.save()
        revert_instance = instance.revert_to_public()
        self.assertEqual(title, revert_instance.title)

    def test_only_draft_records_can_be_published_or_reverted(self):
        draft = PublisherTestModel.objects.create(title='Test model')
        draft.publish()

        published = PublisherTestModel.objects.published().get()
        self.assertRaises(NotDraftException, published.publish)
        self.assertRaises(NotDraftException, published.unpublish)
        self.assertRaises(NotDraftException, published.revert_to_public)

    def test_published_signal(self):
        # Check the signal was sent. These get lost if they don't reference self.
        self.got_signal = False
        self.signal_sender = None
        self.signal_instance = None

        def handle_signal(sender, instance, **kwargs):
            self.got_signal = True
            self.signal_sender = sender
            self.signal_instance = instance

        publisher_post_publish.connect(handle_signal)

        # call the function
        instance = PublisherTestModel.objects.create(title='Test model')
        instance.publish()

        self.assertTrue(self.got_signal)
        self.assertEqual(self.signal_sender, PublisherTestModel)
        self.assertEqual(self.signal_instance, instance)

    def test_unpublished_signal(self):
        # Check the signal was sent. These get lost if they don't reference self.
        self.got_signal = False
        self.signal_sender = None
        self.signal_instance = None

        def handle_signal(sender, instance, **kwargs):
            self.got_signal = True
            self.signal_sender = sender
            self.signal_instance = instance

        publisher_post_unpublish.connect(handle_signal)

        # Call the function.
        instance = PublisherTestModel.objects.create(title='Test model')
        instance.publish()
        instance.unpublish()

        self.assertTrue(self.got_signal)
        self.assertEqual(self.signal_sender, PublisherTestModel)
        self.assertEqual(self.signal_instance, instance)

    def test_unpublished_signal_is_sent_when_deleting(self):
        self.got_signal = False
        self.signal_sender = None
        self.signal_instance = None

        def handle_signal(sender, instance, **kwargs):
            self.got_signal = True
            self.signal_sender = sender
            self.signal_instance = instance

        publisher_post_unpublish.connect(handle_signal)

        # Call the function.
        instance = PublisherTestModel.objects.create(title='Test model')
        instance.publish()
        instance.delete()

        self.assertTrue(self.got_signal)
        self.assertEqual(self.signal_sender, PublisherTestModel)
        self.assertEqual(self.signal_instance, instance)

    def test_middleware_detects_published_when_logged_out(self):

        class MockUser(object):
            is_staff = False

            def is_authenticated(self):
                return False

        class MockRequest(object):
            user = MockUser()
            GET = {'edit': '1'}

        mock_request = MockRequest()
        self.assertFalse(PublisherMiddleware.is_draft(mock_request))

    def test_middleware_detects_published_when_user_edit_parameter_is_missing(self):

        class MockUser(object):
            is_staff = True

            def is_authenticated(self):
                return True

        class MockRequest(object):
            user = MockUser()
            GET = {}

        mock_request = MockRequest()
        self.assertFalse(PublisherMiddleware.is_draft(mock_request))

    def test_middleware_detects_published_when_user_is_not_staff(self):

        class MockUser(object):
            is_staff = False

            def is_authenticated(self):
                return True

        class MockRequest(object):
            user = MockUser()
            GET = {'edit': '1'}

        mock_request = MockRequest()
        self.assertFalse(PublisherMiddleware.is_draft(mock_request))

    def test_middleware_detects_draft_when_user_is_staff_and_edit_parameter_is_present(self):

        class MockUser(object):
            is_staff = True

            def is_authenticated(self):
                return True

        class MockRequest(object):
            user = MockUser()
            GET = {'edit': '1'}

        mock_request = MockRequest()
        self.assertTrue(PublisherMiddleware.is_draft(mock_request))

    def test_middleware_get_draft_status_shortcut_defaults_to_false(self):
        self.assertFalse(get_draft_status())

    def test_middleware_get_draft_status_shortcut_returns_true_in_draft_mode(self):
        # Mock the request process to initialise the middleware, but force the middleware to go in
        # draft mode.
        middleware = PublisherMiddleware()
        middleware.is_draft = MagicMock(return_value=True)
        middleware.process_request(None)
        draft_status = get_draft_status()
        PublisherMiddleware.process_response(None, None)

        self.assertTrue(draft_status)

    def test_middleware_get_draft_status_shortcut_does_not_change_draft_status(self):
        # The get_draft_status() shortcut shouldn't change the value returned by
        # PublisherMiddleware.get_draft_status().
        middleware = PublisherMiddleware()
        middleware.is_draft = MagicMock(return_value=True)
        middleware.process_request(None)
        expected_draft_status = PublisherMiddleware.get_draft_status()
        draft_status = get_draft_status()
        PublisherMiddleware.process_response(None, None)

        self.assertTrue(expected_draft_status, draft_status)

    def test_middleware_forgets_current_draft_status_after_request(self):
        middleware = PublisherMiddleware()
        middleware.is_draft = MagicMock(return_value=True)
        middleware.process_request(None)
        PublisherMiddleware.process_response(None, None)

        self.assertFalse(get_draft_status())

    def test_model_properties(self):
        draft_obj = PublisherTestModel.objects.create(title="one")

        self.assertEqual(draft_obj.is_draft, True)
        self.assertEqual(draft_obj.is_published, False)
        self.assertEqual(draft_obj.is_dirty, True)
        self.assertEqual(draft_obj.get_draft_object(), draft_obj)
        self.assertEqual(draft_obj.get_public_object(), None)

        publish_obj = draft_obj.publish()

        self.assertEqual(publish_obj.title, "one")
        self.assertEqual(publish_obj.is_draft, False)
        self.assertEqual(publish_obj.is_published, True)
        self.assertEqual(publish_obj.is_dirty, False)
        self.assertEqual(publish_obj.get_draft_object(), draft_obj)
        self.assertEqual(publish_obj.get_public_object(), publish_obj)

        self.assertEqual(draft_obj.get_draft_object(), draft_obj)
        self.assertEqual(draft_obj.get_public_object(), publish_obj)

        self.assertEqual(draft_obj.title, "one")
        self.assertEqual(draft_obj.is_draft, True)
        self.assertEqual(draft_obj.is_published, False) # FIXME: Should this not be True ?!?
        self.assertEqual(draft_obj.is_dirty, False)

        draft_obj.title="two"
        draft_obj.save()

        self.assertEqual(publish_obj.title, "one")
        self.assertEqual(publish_obj.is_draft, False)
        self.assertEqual(publish_obj.is_published, True)
        self.assertEqual(publish_obj.is_dirty, False) # FIXME: Should this not be True ?!?

        self.assertEqual(draft_obj.title, "two")
        self.assertEqual(draft_obj.is_draft, True)
        self.assertEqual(draft_obj.is_published, False) # FIXME: Should this not be True ?!?
        self.assertEqual(draft_obj.is_dirty, True)

        publish_obj = draft_obj.publish()

        self.assertEqual(publish_obj.title, "two")
        self.assertEqual(publish_obj.is_draft, False)
        self.assertEqual(publish_obj.is_published, True)
        self.assertEqual(publish_obj.is_dirty, False)

        self.assertEqual(draft_obj.title, "two")
        self.assertEqual(draft_obj.is_draft, True)
        self.assertEqual(draft_obj.is_published, False) # FIXME: Should this not be True ?!?
        self.assertEqual(draft_obj.is_dirty, False)

    def test_publication_start_date(self):
        yesterday = timezone.now() - datetime.timedelta(days=1)
        tomorrow = timezone.now() + datetime.timedelta(days=1)

        instance = PublisherTestModel.objects.create(title='Test model')
        instance.publish()

        # No publication_start_date set:

        published = PublisherTestModel.objects.published()
        self.assertEqual(published.count(), 1)
        # Check model instance
        obj = published[0]
        self.assertEqual(obj.publication_start_date, None)
        self.assertEqual(obj.publication_end_date, None)
        self.assertEqual(obj.is_published, True)
        self.assertEqual(obj.hidden_by_end_date, False)
        self.assertEqual(obj.hidden_by_start_date, False)
        self.assertEqual(obj.is_visible, True)

        # Hidden, because publication_start_date is in the future:

        instance.publication_start_date = tomorrow
        instance.save()
        instance.publish()

        published = PublisherTestModel.objects.published()
        self.assertEqual(published.count(), 1)

        visible = PublisherTestModel.objects.visible()
        self.assertEqual(visible.count(), 0)

        count = PublisherTestModel.objects.all().count()
        self.assertEqual(count, 2) # draft + published

        draft = PublisherTestModel.objects.drafts()[0]
        self.assertEqual(draft.publication_start_date, tomorrow)

        # Check model instance
        obj = PublisherTestModel.objects.filter(publisher_is_draft=PublisherTestModel.STATE_PUBLISHED)[0]
        self.assertEqual(obj.publication_start_date, tomorrow)
        self.assertEqual(obj.publication_end_date, None)
        self.assertEqual(obj.is_published, True)
        self.assertEqual(obj.hidden_by_end_date, False)
        self.assertEqual(obj.hidden_by_start_date, True)
        self.assertEqual(obj.is_visible, False)

        # Visible, because publication_start_date is in the past:

        instance.publication_start_date = yesterday
        instance.save()
        instance.publish()

        published = PublisherTestModel.objects.published()
        self.assertEqual(published.count(), 1)

        visible = PublisherTestModel.objects.visible()
        self.assertEqual(visible.count(), 1)

        # Check model instance
        obj = published[0]
        self.assertEqual(obj.publication_start_date, yesterday)
        self.assertEqual(obj.publication_end_date, None)
        self.assertEqual(obj.is_published, True)
        self.assertEqual(obj.hidden_by_end_date, False)
        self.assertEqual(obj.hidden_by_start_date, False)
        self.assertEqual(obj.is_visible, True)

    def test_publication_end_date(self):
        yesterday = timezone.now() - datetime.timedelta(days=1)
        tomorrow = timezone.now() + datetime.timedelta(days=1)

        instance = PublisherTestModel.objects.create(title='Test model')
        instance.publish()

        # No publication_end_date set:
        published = PublisherTestModel.objects.published()
        self.assertEqual(published.count(), 1)

        visible = PublisherTestModel.objects.visible()
        self.assertEqual(visible.count(), 1)

        # Check model instance
        obj = published[0]
        self.assertEqual(obj.publication_start_date, None)
        self.assertEqual(obj.publication_end_date, None)
        self.assertEqual(obj.is_published, True)
        self.assertEqual(obj.hidden_by_end_date, False)
        self.assertEqual(obj.hidden_by_start_date, False)
        self.assertEqual(obj.is_visible, True)

        # Hidden, because publication_end_date is in the past:
        instance.publication_end_date = yesterday
        instance.save()
        instance.publish()

        published = PublisherTestModel.objects.published()
        self.assertEqual(published.count(), 1)

        visible = PublisherTestModel.objects.visible()
        self.assertEqual(visible.count(), 0)

        count = PublisherTestModel.objects.all().count()
        self.assertEqual(count, 2) # draft + published

        draft = PublisherTestModel.objects.drafts()[0]
        self.assertEqual(draft.publication_start_date, None)
        self.assertEqual(draft.publication_end_date, yesterday)

        # Check model instance
        obj = PublisherTestModel.objects.filter(publisher_is_draft=PublisherTestModel.STATE_PUBLISHED)[0]
        self.assertEqual(obj.publication_start_date, None)
        self.assertEqual(obj.publication_end_date, yesterday)
        self.assertEqual(obj.is_published, True)
        self.assertEqual(obj.hidden_by_end_date, True)
        self.assertEqual(obj.hidden_by_start_date, False)
        self.assertEqual(obj.is_visible, False)

        # Visible, because publication_end_date is in the future:
        instance.publication_end_date = tomorrow
        instance.save()
        instance.publish()

        published = PublisherTestModel.objects.published()
        self.assertEqual(published.count(), 1)

        visible = PublisherTestModel.objects.visible()
        self.assertEqual(visible.count(), 1)

        # Check model instance
        obj = published[0]
        self.assertEqual(obj.publication_start_date, None)
        self.assertEqual(obj.publication_end_date, tomorrow)
        self.assertEqual(obj.is_published, True)
        self.assertEqual(obj.hidden_by_end_date, False)
        self.assertEqual(obj.hidden_by_start_date, False)
        self.assertEqual(obj.is_visible, True)


@unittest.skipIf(PARLER_INSTALLED != True, 'Django-Parler is not installed')
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



@unittest.skipIf(TRANSLATION_TOOLS_INSTALLED != True, 'aldryn_translation_tools is not installed')
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

        self.assertEqual(draft_obj.is_draft, True)
        self.assertEqual(draft_obj.is_published, False)
        self.assertEqual(draft_obj.is_visible, False)
        self.assertEqual(draft_obj.is_dirty, True)

        publish_obj = draft_obj.publish()

        self.assertEqual(publish_obj.title, "one")
        self.assertEqual(publish_obj.is_draft, False)
        self.assertEqual(publish_obj.is_published, True)
        self.assertEqual(publish_obj.is_visible, True)
        self.assertEqual(publish_obj.is_dirty, False)

        self.assertEqual(draft_obj.title, "one")
        self.assertEqual(draft_obj.is_draft, True)
        self.assertEqual(draft_obj.is_published, False) # FIXME: Should this not be True ?!?
        self.assertEqual(draft_obj.is_visible, False) # FIXME: Should this not be True ?!?
        self.assertEqual(draft_obj.is_dirty, False)

        draft_obj.title="two"
        draft_obj.save()

        self.assertEqual(publish_obj.title, "one")
        self.assertEqual(publish_obj.is_draft, False)
        self.assertEqual(publish_obj.is_published, True)
        self.assertEqual(publish_obj.is_visible, True)
        self.assertEqual(publish_obj.is_dirty, False) # FIXME: Should this not be True ?!?

        self.assertEqual(draft_obj.title, "two")
        self.assertEqual(draft_obj.is_draft, True)
        self.assertEqual(draft_obj.is_published, False) # FIXME: Should this not be True ?!?
        self.assertEqual(draft_obj.is_visible, False) # FIXME: Should this not be True ?!?
        self.assertEqual(draft_obj.is_dirty, True)

        publish_obj = draft_obj.publish()

        self.assertEqual(publish_obj.title, "two")
        self.assertEqual(publish_obj.is_draft, False)
        self.assertEqual(publish_obj.is_published, True)
        self.assertEqual(publish_obj.is_visible, True)
        self.assertEqual(publish_obj.is_dirty, False)

        self.assertEqual(draft_obj.title, "two")
        self.assertEqual(draft_obj.is_draft, True)
        self.assertEqual(draft_obj.is_published, False) # FIXME: Should this not be True ?!?
        self.assertEqual(draft_obj.is_visible, False) # FIXME: Should this not be True ?!?
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



class PublisherStateTests(test.TestCase):

    @classmethod
    def setUpTestData(cls):
        super(PublisherStateTests, cls).setUpTestData()

        cls.draft = PublisherTestModel.objects.create(title="publisher test")

        cls.user_no_permissions = User.objects.create(username="user_with_no_permissions")

        def create_test_user(username, permission):
            content_type = ContentType.objects.get_for_model(PublisherStateModel)
            permission = Permission.objects.get(content_type=content_type, codename=permission)

            group = Group.objects.create(name="%s_group" % username)
            group.permissions.add(permission)

            user = create_user(
                username=username,
                password="unittest",
                groups=(group,),
            )
            return user

        cls.ask_permission_user = create_test_user(
            username="ask_permission_user",
            permission="ask_publisher_request",
        )
        cls.reply_permission_user = create_test_user(
            username="reply_permission_user",
            permission="reply_publisher_request",
        )

    def test_environment(self):
        all_permissions = [
            "%s.%s" % (entry.content_type, entry.codename)
            for entry in Permission.objects.all()
        ]
        self.assertIn("publisher test model.can_publish", all_permissions)

        self.assertIn("publisher state model.direct_publisher", all_permissions)
        self.assertIn("publisher state model.ask_publisher_request", all_permissions)
        self.assertIn("publisher state model.reply_publisher_request", all_permissions)

        self.assertTrue(
            self.ask_permission_user.has_perm("publisher.ask_publisher_request")
        )

        permissions = self.ask_permission_user.get_all_permissions()
        self.assertIn("publisher.ask_publisher_request", permissions)

    def test_no_ask_request_permission(self):
        self.assertRaises(
            PermissionDenied,
            PublisherStateModel.objects.request_publishing,
            user=self.user_no_permissions,
            publisher_instance=self.draft,
        )

    def assert_timestamp(self, timestamp, diff=1):
        now = timezone.now()
        self.assertGreaterEqual(timestamp, now - datetime.timedelta(seconds=diff))
        self.assertLessEqual(timestamp, now + datetime.timedelta(seconds=diff))

    def test_ask_request(self):
        self.draft.title = "test_ask_request"
        self.draft.save()
        self.assertTrue(self.draft.is_dirty)
        self.assertEqual(PublisherTestModel.objects.all().count(), 1)

        self.assertEqual(PublisherStateModel.objects.all().count(), 0)
        state_instance = PublisherStateModel.objects.request_publishing(
            user=self.ask_permission_user,
            publisher_instance=self.draft,
            note="test ask request",
        )
        self.assertEqual(PublisherStateModel.objects.all().count(), 1)
        self.assertIsInstance(state_instance, PublisherStateModel)

        state_instance = PublisherStateModel.objects.get(pk=state_instance.pk)

        self.assertEqual(str(state_instance.state_name), "request")
        self.assertEqual(str(state_instance.action_name), "publish")

        self.assertTrue(state_instance.is_open)

        self.assertEqual(state_instance.publisher_instance, self.draft)
        self.assertTrue(state_instance.publisher_instance.is_draft)

        self.assert_timestamp(state_instance.request_timestamp)
        self.assertEqual(state_instance.request_user, self.ask_permission_user)
        self.assertEqual(state_instance.request_note, "test ask request")

        self.assertEqual(state_instance.response_timestamp, None)
        self.assertEqual(state_instance.response_user, None)
        self.assertEqual(state_instance.response_note, None)

    def test_accept_publish_request(self):
        self.draft.title = "test_accept_publish_request"
        self.draft.save()
        self.assertTrue(self.draft.is_dirty)
        self.assertEqual(PublisherTestModel.objects.all().count(), 1)

        self.assertEqual(PublisherStateModel.objects.all().count(), 0)
        state_instance = PublisherStateModel.objects.request_publishing(
            user=self.ask_permission_user,
            publisher_instance=self.draft,
            note="test_accept_publish_request request",
        )
        self.assertEqual(PublisherStateModel.objects.all().count(), 1)

        time.sleep(0.01) # assert request timestamp < response timestamp ;)

        state_instance.accept(
            response_user=self.reply_permission_user,
            response_note="test_accept_publish_request response",
        )
        self.assertEqual(PublisherStateModel.objects.all().count(), 1)
        self.assertEqual(PublisherTestModel.objects.all().count(), 2)
        self.assertIsInstance(state_instance, PublisherStateModel)

        state_instance = PublisherStateModel.objects.get(pk=state_instance.pk)

        instance = state_instance.publisher_instance
        self.assertTrue(instance.is_published)

        draft = PublisherTestModel.objects.get(pk=self.draft.pk)
        self.assertEqual(instance, draft.publisher_linked)

        self.assertEqual(str(state_instance.state_name), "accepted")
        self.assertEqual(str(state_instance.action_name), "publish")

        self.assertFalse(state_instance.is_open)

        self.assert_timestamp(state_instance.request_timestamp)
        self.assertLessEqual(
            state_instance.request_timestamp,
            state_instance.response_timestamp,
        )
        self.assertEqual(state_instance.request_user, self.ask_permission_user)
        self.assertEqual(state_instance.request_note, "test_accept_publish_request request")

        self.assert_timestamp(state_instance.response_timestamp)
        self.assertEqual(state_instance.response_user, self.reply_permission_user)
        self.assertEqual(state_instance.response_note, "test_accept_publish_request response")

    def test_reject_request(self):
        self.draft.title = "test_reject_request"
        self.draft.save()
        self.assertTrue(self.draft.is_dirty)
        self.assertEqual(PublisherTestModel.objects.all().count(), 1)

        self.assertEqual(PublisherStateModel.objects.all().count(), 0)
        state_instance = PublisherStateModel.objects.request_publishing(
            user=self.ask_permission_user,
            publisher_instance=self.draft,
            note="test_reject_request request",
        )
        self.assertEqual(PublisherStateModel.objects.all().count(), 1)
        self.assertIsInstance(state_instance, PublisherStateModel)

        time.sleep(0.01) # assert request timestamp < response timestamp ;)

        print(state_instance.reject)
        state_instance.reject(
            response_user=self.reply_permission_user,
            response_note="test_reject_request response",
        )
        self.assertEqual(PublisherStateModel.objects.all().count(), 1)

        state_instance = PublisherStateModel.objects.get(pk=state_instance.pk)

        # assert was not published:
        self.assertEqual(PublisherTestModel.objects.all().count(), 1)
        self.assertFalse(state_instance.publisher_instance.is_published)

        draft = PublisherTestModel.objects.get(pk=self.draft.pk)
        self.assertEqual(state_instance.publisher_instance, draft)

        self.assertEqual(str(state_instance.state_name), "rejected")
        self.assertEqual(str(state_instance.action_name), "publish")

        self.assertFalse(state_instance.is_open)

        self.assert_timestamp(state_instance.request_timestamp)
        self.assertLessEqual(
            state_instance.request_timestamp,
            state_instance.response_timestamp,
        )
        self.assertEqual(state_instance.request_user, self.ask_permission_user)
        self.assertEqual(state_instance.request_note, "test_reject_request request")

        self.assert_timestamp(state_instance.response_timestamp)
        self.assertEqual(state_instance.response_user, self.reply_permission_user)
        self.assertEqual(state_instance.response_note, "test_reject_request response")

    def test_accept_unpublish_request(self):
        self.draft.title = "test_accept_unpublish_request"
        self.draft.save()
        publish_instance = self.draft.publish()
        self.assertTrue(publish_instance.is_published)
        self.assertFalse(publish_instance.is_dirty)
        self.assertFalse(self.draft.is_dirty)
        self.assertEqual(PublisherTestModel.objects.all().count(), 2)

        self.assertEqual(PublisherStateModel.objects.all().count(), 0)
        state_instance = PublisherStateModel.objects.request_unpublishing(
            user=self.ask_permission_user,
            publisher_instance=publish_instance,
            note="test_accept_unpublish_request request",
        )
        self.assertEqual(PublisherStateModel.objects.all().count(), 1)

        time.sleep(0.01) # assert request timestamp < response timestamp ;)

        state_instance.accept(
            response_user=self.reply_permission_user,
            response_note="test_accept_unpublish_request response",
        )
        self.assertEqual(PublisherStateModel.objects.all().count(), 1)
        self.assertEqual(PublisherTestModel.objects.all().count(), 1)
        self.assertIsInstance(state_instance, PublisherStateModel)

        state_instance = PublisherStateModel.objects.get(pk=state_instance.pk)

        instance = state_instance.publisher_instance
        self.assertTrue(instance.is_draft)

        draft = PublisherTestModel.objects.get(pk=self.draft.pk)
        self.assertEqual(draft.publisher_linked, None)

        self.assertEqual(str(state_instance.state_name), "accepted")
        self.assertEqual(str(state_instance.action_name), "unpublish")

        self.assertFalse(state_instance.is_open)

        self.assert_timestamp(state_instance.request_timestamp)
        self.assertLessEqual(
            state_instance.request_timestamp,
            state_instance.response_timestamp,
        )
        self.assertEqual(state_instance.request_user, self.ask_permission_user)
        self.assertEqual(state_instance.request_note, "test_accept_unpublish_request request")

        self.assert_timestamp(state_instance.response_timestamp)
        self.assertEqual(state_instance.response_user, self.reply_permission_user)
        self.assertEqual(state_instance.response_note, "test_accept_unpublish_request response")
