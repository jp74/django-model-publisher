# coding: utf-8

from __future__ import absolute_import, print_function, unicode_literals

import pytest

# https://github.com/jedie/django-tools
from django_tools.unittest_utils.unittest_base import BaseTestCase


@pytest.mark.django_db
class AdminLoggedinTests(BaseTestCase):
    """
    Some basics test with the django admin
    """
    def setUp(self):
        super(AdminLoggedinTests, self).setUp()
        self.create_testusers()

    def test_superuser_admin_index(self):
        self.login(usertype='superuser')
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
        self.login(usertype='superuser')
        response = self.client.get('/en/admin/publisher_test_app/publishertestmodel/', HTTP_ACCEPT_LANGUAGE='en')
        self.assertResponse(response,
            must_contain=(
                'Django administration',
                'superuser',
                'Select Publisher Test Model to change',
                '0 Publisher Test Model',
            ),
            must_not_contain=('error', 'traceback'),
            template_name='admin/change_list.html',
        )

    def test_superuser_publishertestmodel_add(self):
        self.login(usertype='superuser')
        response = self.client.get('/en/admin/publisher_test_app/publishertestmodel/add/', HTTP_ACCEPT_LANGUAGE='en')
        self.assertResponse(response,
            must_contain=(
                'Django administration',
                'superuser',
                'Add Publisher Test Model',
                'Title:',
                'Publication start date:',
                'Publication end date:',
            ),
            must_not_contain=('error', 'traceback'),
            template_name='publisher/change_form.html',
        )
