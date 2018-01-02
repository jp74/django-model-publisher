# coding: utf-8


import sys

import django

import mock

from publisher.models import PublisherStateModel
from publisher_test_project.publisher_test_app.models import PublisherTestModel
from publisher_tests.base import ClientBaseTestCase


class AdminLoggedinTests(ClientBaseTestCase):
    """
    Some basics test with the django admin
    """
    def test_superuser_admin_index(self):
        self.login_superuser()
        response = self.client.get('/en/admin/', HTTP_ACCEPT_LANGUAGE='en')
        self.assertResponse(response,
            must_contain=(
                'Django administration',
                'superuser',
                'Site administration',
                '/admin/auth/group/add/',
                '/admin/auth/user/add/',
                'href="/en/admin/publisher/publisherstatemodel/"',
                'href="/en/admin/publisher_test_app/publishertestmodel/"',
            ),
            must_not_contain=('error', 'traceback'),
            template_name='admin/index.html',
        )

    def test_superuser_publishertestmodel_index(self):
        self.login_superuser()
        response = self.client.get('/en/admin/publisher_test_app/publishertestmodel/', HTTP_ACCEPT_LANGUAGE='en')
        self.assertResponse(response,
            must_contain=(
                'Django administration',
                'superuser',
                'Select Publisher Test Model to change',
                '4 Publisher Test Model',
            ),
            must_not_contain=('error', 'traceback'),
            template_name='admin/change_list.html',
        )

    def test_superuser_publishertestmodel_add(self):
        self.login_superuser()
        response = self.client.get('/en/admin/publisher_test_app/publishertestmodel/add/', HTTP_ACCEPT_LANGUAGE='en')
        self.assertResponse(response,
            must_contain=(
                'Django administration',
                'superuser',
                'Add Publisher Test Model',
                'Title:',
                'Publication start date:',
                'Publication end date:',
                # 'XXX'
            ),
            must_not_contain=('error', 'traceback'),
            template_name='publisher/change_form.html',
        )

    def test_edit_pending_request(self):
        draft = PublisherTestModel.objects.create(no=1, title="foobar")

        ask_permission_user = self.login_reporter_user() # 'reporter' user can create un-/publish requests

        PublisherStateModel.objects.request_publishing(
            user=ask_permission_user,
            publisher_instance=draft,
        )

        if django.VERSION < (1, 11):
            url = "/en/admin/publisher_test_app/publishertestmodel/%s/" % draft.pk
        else:
            url = "/en/admin/publisher_test_app/publishertestmodel/%s/change/" % draft.pk

        def raise_error(*args, **kwargs):
            tb = sys.exc_info()[2]
            raise AssertionError().with_traceback(tb)

        # django/conf/urls/__init__.py - handler404
        with mock.patch('django.views.defaults.page_not_found', new=raise_error):
            response = self.client.get(url, HTTP_ACCEPT_LANGUAGE='en')

        self.assertRedirects(response,
            expected_url="/en/admin/publisher_test_app/publishertestmodel/"
        )
        self.assertMessages(response,
            ["You can't edit this, because a publish request is pending!"]
        )
