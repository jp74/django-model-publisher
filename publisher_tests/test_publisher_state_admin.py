# coding: utf-8
import sys

import django
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse

import mock

from publisher.models import PublisherStateModel
from publisher_test_project.fixtures import REPORTER_USER
from publisher_test_project.publisher_test_app.models import PublisherTestModel
from publisher_tests.base import ClientBaseTestCase


class AdminLoggedinTests(ClientBaseTestCase):
    """
    Some basics test with the django admin
    """
    def assert_can_access_statemodel_index(self, username):
        def raise_error(*args, **kwargs):
            tb = sys.exc_info()[2]
            raise AssertionError().with_traceback(tb)

        # django/conf/urls/__init__.py:13 - handler400
        with mock.patch('django.views.defaults.bad_request', new=raise_error):
            response = self.client.get('/en/admin/publisher/publisherstatemodel/', HTTP_ACCEPT_LANGUAGE='en')
            self.assertResponse(response,
                must_contain=(
                    'Django administration',
                    username,
                    'Select Publisher State to change',
                    '0 Publisher State',
                ),
                must_not_contain=('error', 'traceback'),
                template_name='admin/change_list.html',
            )

    def test_superuser_publisherstatemodel_index(self):
        self.login_superuser()
        self.assert_can_access_statemodel_index("superuser")

    def test_reporter_publisherstatemodel_index(self):
        self.login_reporter_user() # 'reporter' user can create un-/publish requests
        self.assert_can_access_statemodel_index("reporter")

    def test_editor_publisherstatemodel_index(self):
        self.login_editor_user() # 'editor' user can accept/reject un-/publish requests
        self.assert_can_access_statemodel_index("editor")

    def test_superuser_publisherstatemodel_add(self):
        self.login_superuser()
        response = self.client.get('/en/admin/publisher/publisherstatemodel/add/', HTTP_ACCEPT_LANGUAGE='en')
        self.assertResponse(response,
            must_contain=('403 Forbidden',),
            must_not_contain=('error', 'traceback'),
            status_code=403
        )

    def assert_cant_add_publisherstatemodel(self):
        response = self.client.get('/en/admin/publisher/publisherstatemodel/add/', HTTP_ACCEPT_LANGUAGE='en')
        self.assertResponse(response,
            must_contain=('403 Forbidden',),
            must_not_contain=('error', 'traceback'),
            status_code=403
        )

    def test_reporter_publisherstatemodel_add(self):
        self.login_reporter_user()
        self.assert_cant_add_publisherstatemodel()

    def test_editor_publisherstatemodel_add(self):
        self.login_editor_user()
        self.assert_cant_add_publisherstatemodel()

    def get_state_with_deleted_instance(self):
        draft = PublisherTestModel.objects.create(no=1, title="delete publisher test")
        draft_id = draft.pk

        User = get_user_model()
        ask_permission_user = User.objects.get(username=REPORTER_USER)
        state_instance = PublisherStateModel.objects.request_publishing(
            user=ask_permission_user,
            publisher_instance=draft,
        )
        draft.delete()

        state_instance = PublisherStateModel.objects.get(pk=state_instance.pk) # needed for django 1.8

        return state_instance, draft_id

    def test_delete_publisher_instance_index_view(self):
        state_instance, draft_id = self.get_state_with_deleted_instance()

        self.login_editor_user()

        response = self.client.get('/en/admin/publisher/publisherstatemodel/', HTTP_ACCEPT_LANGUAGE='en')
        self.assertResponse(response,
            must_contain=(
                'Django administration',
                'Select Publisher State to change',

                "Deleted 'Publisher Test Model' (old pk:%s)" % draft_id,
                "close deleted request",
                "/en/admin/publisher/publisherstatemodel/%s/close_deleted/" % state_instance.pk,

                '1 Publisher State',
            ),
            must_not_contain=('error', 'traceback'),
            template_name='admin/change_list.html',
        )

    def test_close_delete_publisher_instance(self):
        state_instance, draft_id = self.get_state_with_deleted_instance()
        close_url = "/en/admin/publisher/publisherstatemodel/%s/close_deleted/" % state_instance.pk

        self.login_editor_user()

        self.assertFalse(state_instance.is_open) # With delete instance are always closed
        self.assertEqual(str(state_instance),
            "Deleted 'Publisher Test Model' with pk:%s publish request from: reporter" % draft_id
        )

        # publisher.managers.PublisherStateQuerySet can't filter 'deleted' entries:
        self.assertEqual(PublisherStateModel.objects.filter_open().count(), 1)
        self.assertEqual(PublisherStateModel.objects.filter_closed().count(), 0)

        response = self.client.post(close_url, HTTP_ACCEPT_LANGUAGE='en')
        self.assertRedirects(response, expected_url="/en/admin/publisher/publisherstatemodel/")

        # Now the state updates to 'closed':
        self.assertEqual(PublisherStateModel.objects.filter_open().count(), 0)
        self.assertEqual(PublisherStateModel.objects.filter_closed().count(), 1)

        self.assertMessages(response, ["Entry with deleted instance was closed."])

    def test_permission_deny_on_admin_reply_request_view(self):
        ask_permission_user = self.login_reporter_user()
        self.assertFalse(ask_permission_user.has_perm("cms.publish_page"))

        draft = PublisherTestModel.objects.create(no=1, title="test_permission_deny_on_admin_reply_request_view")

        state_instance = PublisherStateModel.objects.request_publishing(
            user=ask_permission_user,
            publisher_instance=draft,
            note="test_permission_deny_on_admin_reply_request_view request",
        )
        self.assertEqual(PublisherStateModel.objects.all().count(), 1)

        reply_url = state_instance.admin_reply_url() # e.g.: /en/admin/publisher/publisherstatemodel/1/reply_request/
        print(reply_url)

        def raise_error(*args, **kwargs):
            tb = sys.exc_info()[2]
            raise AssertionError().with_traceback(tb)

        # django/conf/urls/__init__.py - handler404
        with mock.patch('django.views.defaults.page_not_found', new=raise_error):
            response = self.client.get(reply_url)
        self.assertResponse(response,
            must_contain=('403 Forbidden',),
            must_not_contain=('error', 'traceback'),
            status_code=403
        )

    def _create_request(self, title):
        draft = PublisherTestModel.objects.create(no=1, title=title)
        ask_permission_user = self.get_test_user(username=REPORTER_USER)
        state_instance = PublisherStateModel.objects.request_publishing(
            user=ask_permission_user,
            publisher_instance=draft,
            note="%s request" % title,
        )
        return state_instance

    def _get_change_url(self, state_instance):
        url = self.get_admin_change_url(obj=state_instance)
        if django.VERSION < (1, 11):
            self.assertEqual(url, "/en/admin/publisher/publisherstatemodel/%i/" % state_instance.pk)
        else:
            self.assertEqual(url, "/en/admin/publisher/publisherstatemodel/%i/change/" % state_instance.pk)
        return url

    def test_permission_deny_on_changeform_view(self):
        # create PublisherStateModel instance and returned the admin change link to it:
        state_instance = self._create_request(title="test_permission_deny_on_changeform_view")
        change_url = self._get_change_url(state_instance)

        self.login_editor_user()
        response = self.client.get(change_url)
        self.assertResponse(response,
            must_contain=('403 Forbidden',),
            must_not_contain=('error', 'traceback'),
            status_code=403
        )

    def test_superuser_can_use_changeform_view(self):
        # create PublisherStateModel instance and returned the admin change link to it:
        state_instance = self._create_request(title="test_superuser_can_use_changeform_view")
        change_url = self._get_change_url(state_instance)

        self.login_superuser()
        response = self.client.get(change_url, HTTP_ACCEPT_LANGUAGE='en')
        self.assertResponse(response,
            must_contain=(
                'Django administration',
                'Change Publisher State',

                "test_superuser_can_use_changeform_view request",
            ),
            must_not_contain=('error', 'traceback'),
            messages=[],
            template_name='admin/change_form.html',
        )

    def test_replay_view_on_closed_request(self):
        state_instance = self._create_request(title="test_replay_view_on_closed_request")
        reply_url = state_instance.admin_reply_url() # e.g.: /en/admin/publisher/publisherstatemodel/1/reply_request/

        editor = self.login_editor_user()
        state_instance.reject(response_user=editor, response_note="reject response")

        response = self.client.get(reply_url, HTTP_ACCEPT_LANGUAGE='en')
        self.assertRedirects(response, expected_url="/en/admin/publisher/publisherstatemodel/")
        self.assertMessages(response, messages=["This request has been closed!"])

    def test_replay_view_on_deleted_instance(self):
        state_instance = self._create_request(title="test_replay_view_on_deleted_instance")
        reply_url = state_instance.admin_reply_url() # e.g.: /en/admin/publisher/publisherstatemodel/1/reply_request/

        pk = state_instance.publisher_instance.pk
        state_instance.publisher_instance.delete()

        self.login_editor_user()
        response = self.client.get(reply_url, HTTP_ACCEPT_LANGUAGE='en')
        self.assertRedirects(response, expected_url="/en/admin/publisher/publisherstatemodel/")
        self.assertMessages(response, messages=[
            "Publisher instance 'Publisher Test Model' was deleted. (old pk:%i)" % pk
        ])

    def test_history_view_with_open_request(self):
        state_instance = self._create_request(title="test_history_view_with_open_request")
        history_url = state_instance.admin_history_url() # e.g.: /en/admin/publisher/publisherstatemodel/1/history/

        self.login_reporter_user()

        response = self.client.get(history_url, HTTP_ACCEPT_LANGUAGE='en')
        self.assertResponse(response,
            must_contain=(
                'Publisher History',

                "User reporter made a publish request at",
                "note:",
                "test_history_view_with_open_request request",

                "Publisher History for",
            ),
            must_not_contain=('error', 'traceback'),
            messages=[],
            template_name="publisher/publish_history.html",
        )

    def test_history_with_reject_request(self):
        state_instance = self._create_request(title="test_history_with_reject_request")

        editor = self.login_editor_user()
        state_instance.reject(response_user=editor, response_note="reject test_history_with_reject_request")

        history_url = state_instance.admin_history_url() # e.g.: /en/admin/publisher/publisherstatemodel/1/history/

        self.login_reporter_user()
        response = self.client.get(history_url, HTTP_ACCEPT_LANGUAGE='en')
        self.assertResponse(response,
            must_contain=(
                'Publisher History',

                "User reporter made a publish request at",
                "note:",
                "test_history_with_reject_request request",

                "User editor response at",
                "reject test_history_with_reject_request",

                "Publisher History for",
            ),
            must_not_contain=('error', 'traceback'),
            messages=[],
            template_name="publisher/publish_history.html",
        )

    def test_history_with_deleted_instance(self):
        state_instance = self._create_request(title="test_history_with_deleted_instance")

        history_url = state_instance.admin_history_url() # e.g.: /en/admin/publisher/publisherstatemodel/1/history/

        editor = self.login_editor_user()
        state_instance.reject(response_user=editor, response_note="reject test_history_with_deleted_instance")

        pk = state_instance.publisher_instance.pk
        state_instance.publisher_instance.delete()

        self.login_reporter_user()
        response = self.client.get(history_url, HTTP_ACCEPT_LANGUAGE='en')
        self.assertResponse(response,
            must_contain=(
                'Publisher History',

                "User reporter made a publish request at",
                "Publisher Test Model:", "(deleted, old ID: %i)" % pk,
                "note:",
                "test_history_with_deleted_instance request",

                "User editor response at",
                "reject test_history_with_deleted_instance",

                "Publisher History for",
            ),
            must_not_contain=('error', 'traceback'),
            messages=[],
            template_name="publisher/publish_history.html",
        )
