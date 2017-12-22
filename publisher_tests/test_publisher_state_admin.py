# coding: utf-8
import sys

import mock

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
                    '0 Publisher States',
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
