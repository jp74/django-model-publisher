import datetime

from django import test
from django.utils import timezone

from publisher.utils import NotDraftException

from ..signals import publisher_post_publish, publisher_post_unpublish
from .models import PublisherTestModel
from .utils import create_models_from_app


class PublisherTest(test.TestCase):

    def setUp(self):
        create_models_from_app('publisher.tests')

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
