
import datetime
import logging
import pprint
import time

from django import test
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from django_tools.unittest_utils.user import create_user
from publisher_test_project.publisher_test_app.models import PublisherTestModel

from publisher.models import PublisherStateModel
from publisher_tests.base import ClientBaseTestCase

from publisher_test_project.fixtures import REPORTER_USER, EDITOR_USER

log = logging.getLogger(__name__)



class PublisherStateTests(ClientBaseTestCase):

    @classmethod
    def setUpTestData(cls):
        super(PublisherStateTests, cls).setUpTestData()

        PublisherTestModel.objects.all().delete() # FIXME
        cls.draft = PublisherTestModel.objects.create(no=1, title="publisher test")

        User = get_user_model()
        cls.user_no_permissions = User.objects.create(username="user_with_no_permissions")

        cls.ask_permission_user = User.objects.get(username=REPORTER_USER)
        cls.reply_permission_user = User.objects.get(username=EDITOR_USER)

    def test_environment(self):
        qs = Permission.objects.all().order_by("content_type__app_label", "content_type__model", "codename")
        all_permissions = [
            "%s.%s" % (entry.content_type.app_label, entry.codename)
            for entry in qs
        ]
        pprint.pprint(all_permissions)
        self.assertIn("publisher_test_app.can_publish_publisherparlertestmodel", all_permissions)

        self.assertIn("publisher.change_publisherstatemodel", all_permissions)

        self.assertTrue(
            self.ask_permission_user.has_perm("publisher.change_publisherstatemodel")
        )
        self.assertTrue(
            self.reply_permission_user.has_perm("publisher_test_app.can_publish_publisherparlertestmodel")
        )

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

    def test_manager_filters(self):
        qs = PublisherStateModel.objects.all()
        qs = qs.filter_by_instance(publisher_instance=self.draft)
        self.assertEqual(qs.count(), 0)
        self.assertEqual(qs.filter_open().count(), 0)
        self.assertEqual(qs.filter_closed().count(), 0)

        state_instance1 = PublisherStateModel.objects.request_publishing(
            user=self.ask_permission_user,
            publisher_instance=self.draft,
        )
        state_instance1.accept(response_user=self.reply_permission_user)

        self.draft.save()
        self.assertTrue(self.draft.is_dirty)
        PublisherStateModel.objects.request_publishing(
            user=self.ask_permission_user,
            publisher_instance=self.draft,
        )

        qs = PublisherStateModel.objects.all()
        qs = qs.filter_by_instance(publisher_instance=self.draft)
        self.assertEqual(qs.count(), 2)
        self.assertEqual(qs.filter_open().count(), 1)
        self.assertEqual(qs.filter_closed().count(), 1)

        self.assertEqual(
            list(qs.values_list("action", "state").order_by("pk")),
            [('publish', 'accepted'), ('publish', 'request')]
        )

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
        self.assertTrue(state_instance.publisher_instance.publisher_is_draft)

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

        draft_version = state_instance.publisher_instance
        self.assertEqual(draft_version.pk, draft_version.pk)

        published_version = draft_version.get_public_object()
        self.assertTrue(published_version is not None, "Was not published!")

        draft = PublisherTestModel.objects.get(pk=self.draft.pk)
        self.assertEqual(published_version, draft.publisher_linked)

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
        self.assertTrue(instance.publisher_is_draft)

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

    def test_delete_publisher_instance(self):
        draft = PublisherTestModel.objects.create(no=1, title="delete publisher test")
        draft_id = draft.pk

        PublisherStateModel.objects.request_publishing(
            user=self.ask_permission_user,
            publisher_instance=draft,
        )

        draft.delete()

        qs = PublisherStateModel.objects.all()
        self.assertEqual(qs.count(), 1)

        # FIXME: 'deleted' entries are open, see also: publisher.managers.PublisherStateQuerySet
        self.assertEqual(PublisherStateModel.objects.filter_open().count(), 1)
        self.assertEqual(PublisherStateModel.objects.filter_closed().count(), 0)

        state_instance = qs[0]

        self.assertEqual(
            str(state_instance),
            "Deleted 'Publisher Test Model' with pk:%i publish request from: reporter" % draft_id
        )
        self.assertFalse(state_instance.is_open)

    def test_no_permission_to_accept_request(self):
        self.draft.title = "test_no_permission_to_accept_request"
        self.draft.save()

        self.assertEqual(PublisherStateModel.objects.all().count(), 0)
        state_instance = PublisherStateModel.objects.request_publishing(
            user=self.ask_permission_user,
            publisher_instance=self.draft,
            note="test_no_permission_to_accept_request request",
        )
        self.assertEqual(PublisherStateModel.objects.all().count(), 1)

        self.assertFalse(self.ask_permission_user.has_perm("cms.publish_page"))
        self.assertRaises(
            PermissionDenied,
            state_instance.accept,
            response_user=self.ask_permission_user,
            response_note="test_no_permission_to_accept_request response",
        )

    def test_no_permission_to_reject_request(self):
        self.draft.title = "test_no_permission_to_reject_request"
        self.draft.save()

        self.assertEqual(PublisherStateModel.objects.all().count(), 0)
        state_instance = PublisherStateModel.objects.request_publishing(
            user=self.ask_permission_user,
            publisher_instance=self.draft,
            note="test_no_permission_to_reject_request request",
        )
        self.assertEqual(PublisherStateModel.objects.all().count(), 1)

        self.assertFalse(self.ask_permission_user.has_perm("cms.publish_page"))
        self.assertRaises(
            PermissionDenied,
            state_instance.reject,
            response_user=self.ask_permission_user,
            response_note="test_no_permission_to_reject_request response",
        )
