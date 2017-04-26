import datetime

from django import test
from django.utils import timezone

from mock import MagicMock

from publisher.utils import NotDraftException
from publisher.signals import publisher_post_publish, publisher_post_unpublish
from publisher.middleware import PublisherMiddleware, get_draft_status

from myapp.models import PublisherTestModel


class PublisherTest(test.TestCase):

    def test_creating_model_creates_only_one_record(self):
        PublisherTestModel.publisher_manager.create(title='Test model')
        count = PublisherTestModel.publisher_manager.count()
        self.assertEqual(count, 1)

    def test_new_models_are_draft(self):
        instance = PublisherTestModel(title='Test model')
        self.assertTrue(instance.is_draft)

    def test_editing_a_record_does_not_create_a_duplicate(self):
        instance = PublisherTestModel.publisher_manager.create(title='Test model')
        instance.title = 'Updated test model'
        instance.save()
        count = PublisherTestModel.publisher_manager.count()
        self.assertEqual(count, 1)

    def test_editing_a_draft_does_not_update_published_record(self):
        title = 'Test model'
        instance = PublisherTestModel.publisher_manager.create(title=title)
        instance.publish()
        instance.title = 'Updated test model'
        instance.save()
        published_instance = PublisherTestModel.publisher_manager.published().get()
        self.assertEqual(published_instance.title, title)

    def test_publishing_creates_new_record(self):
        instance = PublisherTestModel.publisher_manager.create(title='Test model')
        instance.publish()

        published = PublisherTestModel.publisher_manager.published().count()
        drafts = PublisherTestModel.publisher_manager.drafts().count()

        self.assertEqual(published, 1)
        self.assertEqual(drafts, 1)

    def test_unpublishing_deletes_published_record(self):
        instance = PublisherTestModel.publisher_manager.create(title='Test model')
        instance.publish()
        instance.unpublish()

        published = PublisherTestModel.publisher_manager.published().count()
        drafts = PublisherTestModel.publisher_manager.drafts().count()

        self.assertEqual(published, 0)
        self.assertEqual(drafts, 1)

    def test_unpublished_record_can_be_republished(self):
        instance = PublisherTestModel.publisher_manager.create(title='Test model')
        instance.publish()
        instance.unpublish()
        instance.publish()

        published = PublisherTestModel.publisher_manager.published().count()
        drafts = PublisherTestModel.publisher_manager.drafts().count()

        self.assertEqual(published, 1)
        self.assertEqual(drafts, 1)

    def test_published_date_is_set_to_none_for_new_records(self):
        draft = PublisherTestModel(title='Test model')
        self.assertEqual(draft.publisher_published_at, None)

    def test_published_date_is_updated_when_publishing(self):
        now = timezone.now()
        draft = PublisherTestModel.publisher_manager.create(title='Test model')
        draft.publish()
        draft = PublisherTestModel.publisher_manager.drafts().get()
        published = PublisherTestModel.publisher_manager.drafts().get()

        self.assertGreaterEqual(draft.publisher_published_at, now)
        self.assertGreaterEqual(published.publisher_published_at, now)
        self.assertEqual(draft.publisher_published_at, published.publisher_published_at)

    def test_published_date_is_not_changed_when_publishing_twice(self):
        published_date = datetime.datetime(1970, 1, 1, 0, 0, tzinfo=timezone.utc)
        draft = PublisherTestModel.publisher_manager.create(title='Test model')
        draft.publish()
        published = PublisherTestModel.publisher_manager.drafts().get()
        draft.publisher_published_at = published_date
        draft.save()
        published.publisher_published_at = published_date
        published.save()

        draft.publish()
        draft = PublisherTestModel.publisher_manager.drafts().get()
        published = PublisherTestModel.publisher_manager.drafts().get()
        self.assertEqual(draft.publisher_published_at, published_date)
        self.assertEqual(published.publisher_published_at, published_date)

    def test_published_date_is_set_to_none_when_unpublished(self):
        draft = PublisherTestModel.publisher_manager.create(title='Test model')
        draft.publish()
        draft.unpublish()
        self.assertIsNone(draft.publisher_published_at)

    def test_published_date_is_set_when_republished(self):
        now = timezone.now()
        draft = PublisherTestModel.publisher_manager.create(title='Test model')
        draft.publish()
        draft.unpublish()
        draft.publish()
        self.assertGreaterEqual(draft.publisher_published_at, now)

    def test_deleting_draft_also_deletes_published_record(self):
        instance = PublisherTestModel.publisher_manager.create(title='Test model')
        instance.publish()
        instance.delete()

        published = PublisherTestModel.publisher_manager.published().count()
        drafts = PublisherTestModel.publisher_manager.drafts().count()

        self.assertEqual(published, 0)
        self.assertEqual(drafts, 0)

    def test_delete_published_does_not_delete_draft(self):
        obj = PublisherTestModel.publisher_manager.create(title='Test model')
        obj.publish()

        published = PublisherTestModel.publisher_manager.published().get()
        published.delete()

        published = PublisherTestModel.publisher_manager.published().count()
        drafts = PublisherTestModel.publisher_manager.drafts().count()

        self.assertEqual(published, 0)
        self.assertEqual(drafts, 1)

    def test_reverting_reverts_draft_from_published_record(self):
        title = 'Test model'
        instance = PublisherTestModel.publisher_manager.create(title=title)
        instance.publish()
        instance.title = 'Updated test model'
        instance.save()
        revert_instance = instance.revert_to_public()
        self.assertEqual(title, revert_instance.title)

    def test_only_draft_records_can_be_published_or_reverted(self):
        draft = PublisherTestModel.publisher_manager.create(title='Test model')
        draft.publish()

        published = PublisherTestModel.publisher_manager.published().get()
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
        instance = PublisherTestModel.publisher_manager.create(title='Test model')
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
        instance = PublisherTestModel.publisher_manager.create(title='Test model')
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
        instance = PublisherTestModel.publisher_manager.create(title='Test model')
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
