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

    def test_publish(self):
        """
        Create a draft object then publish. One of each type should exist.
        """
        obj = PublisherTestModel.objects.create(title='dog')
        obj.publish()

        published = PublisherTestModel.objects.published().filter(title='dog').count()
        drafts = PublisherTestModel.objects.drafts().filter(title='dog').count()

        self.assertEqual(published, 1)
        self.assertEqual(drafts, 1)

    def test_unpublish(self):
        obj = PublisherTestModel.objects.create(title='donkey')
        obj.publish()
        obj.unpublish()

        published = PublisherTestModel.objects.published().filter(title='donkey').count()
        drafts = PublisherTestModel.objects.drafts().filter(title='donkey').count()

        self.assertEqual(published, 0)
        self.assertEqual(drafts, 1)

        # Republish the object to ensure moving back and forth works as intended.
        obj.publish()

        published = PublisherTestModel.objects.published().filter(title='donkey').count()
        drafts = PublisherTestModel.objects.drafts().filter(title='donkey').count()

        self.assertEqual(published, 1)
        self.assertEqual(drafts, 1)

    def test_published_at_publish(self):
        now = timezone.now()

        # Check that the published_at is set to None when the object is created.
        draft = PublisherTestModel.objects.create(title='hawk')
        draft.save()
        self.assertEqual(draft.publisher_published_at, None)

        # Check that the values are correct when published.
        draft.publish()
        draft = PublisherTestModel.objects.drafts().get(title='hawk')
        published = PublisherTestModel.objects.drafts().get(title='hawk')

        self.assertGreaterEqual(draft.publisher_published_at, now)
        self.assertGreaterEqual(published.publisher_published_at, now)
        self.assertEqual(draft.publisher_published_at, published.publisher_published_at)

        # Check that the value is not changed when re-published.
        draft = PublisherTestModel.objects.drafts().get(title='hawk')
        dt = draft.publisher_published_at
        draft.publish()
        draft = PublisherTestModel.objects.drafts().get(title='hawk')
        published = PublisherTestModel.objects.drafts().get(title='hawk')
        self.assertEqual(draft.publisher_published_at, dt)
        self.assertEqual(published.publisher_published_at, dt)

        # Check that the published_at is set to None when unpublished.
        draft = PublisherTestModel.objects.drafts().get(title='hawk')
        draft.unpublish()
        draft = PublisherTestModel.objects.drafts().get(title='hawk')
        self.assertIsNone(draft.publisher_published_at)

        # Check that the published_at is set to when unpublished and re-published.
        draft = PublisherTestModel.objects.drafts().get(title='hawk')
        draft.publish()
        draft.unpublish()
        draft.publish()
        self.assertGreaterEqual(draft.publisher_published_at, now)

    def test_delete(self):
        """
        Testing if deleting a draft object also removes the published object.
        """
        obj = PublisherTestModel.objects.create(title='fish')
        obj.publish()
        obj.delete()

        published = PublisherTestModel.objects.published().filter(title='fish').count()
        drafts = PublisherTestModel.objects.drafts().filter(title='fish').count()

        self.assertEqual(published, 0)
        self.assertEqual(drafts, 0)

    def test_delete_published(self):
        """
        Deleting a published object should not delete the draft version.
        """
        obj = PublisherTestModel.objects.create(title='sheep')
        obj.publish()

        published = PublisherTestModel.objects.published().get(title='sheep')
        published.delete()

        published = PublisherTestModel.objects.published().filter(title='sheep').count()
        drafts = PublisherTestModel.objects.drafts().filter(title='sheep').count()

        self.assertEqual(published, 0)
        self.assertEqual(drafts, 1)

    def test_revert(self):
        """
        Create an object, publish, amend the draft... Then revert it to published version which
        should discard the changes.
        """
        test_str = 'wolf'
        new_str = 'white wolf'

        obj = PublisherTestModel.objects.create(title=test_str)
        obj.publish()
        obj.title = new_str
        obj.save()

        revert_obj = obj.revert_to_public()
        self.assertEqual(test_str, revert_obj.title)

    def test_actions_on_published(self):
        """
        Only draft records can be published or reverted.
        Expected exceptions to be raised.
        """
        draft = PublisherTestModel.objects.create(title='frog')
        draft.publish()

        published = PublisherTestModel.objects.published().get(title='frog')
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
        obj = PublisherTestModel.objects.create(title='gentoo penguin')
        obj.publish()

        self.assertTrue(self.got_signal)
        self.assertEqual(self.signal_sender, PublisherTestModel)
        self.assertEqual(self.signal_instance, obj)

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
        obj = PublisherTestModel.objects.create(title='emperor penguin')
        obj.publish()
        obj.unpublish()

        self.assertTrue(self.got_signal)
        self.assertEqual(self.signal_sender, PublisherTestModel)
        self.assertEqual(self.signal_instance, obj)
