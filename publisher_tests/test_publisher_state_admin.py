# coding: utf-8
import sys

import mock

from django.contrib.auth import get_user_model
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
            must_contain=(
                'Django administration',
                'superuser',
                'Add Publisher State',
            ),
            must_not_contain=('error', 'traceback'),
            template_name='admin/change_form.html',
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
