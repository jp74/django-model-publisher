# coding: utf-8

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
