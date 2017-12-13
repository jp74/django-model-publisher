# coding: utf-8

from __future__ import absolute_import, print_function, unicode_literals

import pytest

from publisher_tests.base import ClientBaseTestCase


@pytest.mark.django_db
class AdminLoggedinTests(ClientBaseTestCase):
    """
    Some basics test with the django admin
    """
    def test_superuser_publisherstatemodel_index(self):
        self.login(usertype='superuser')
        response = self.client.get('/en/admin/publisher/publisherstatemodel/', HTTP_ACCEPT_LANGUAGE='en')
        self.assertResponse(response,
            must_contain=(
                'Django administration',
                'superuser',
                'Select Publisher State to change',
                '0 Publisher States',
            ),
            must_not_contain=('error', 'traceback'),
            template_name='admin/change_list.html',
        )

    def test_superuser_publisherstatemodel_add(self):
        self.login(usertype='superuser')
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
