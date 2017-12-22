

# https://github.com/jedie/django-tools
from django.conf import settings
from django.test import Client
from django.utils import translation

from django_tools.unittest_utils.unittest_base import BaseTestCase
from django_tools.unittest_utils.user import TestUserMixin

from publisher_test_project.fixtures import create_test_data, REPORTER_USER, EDITOR_USER


class ClientBaseTestCase(TestUserMixin, BaseTestCase):
    """ Main base class for all TestCases that used the Client() """

    maxDiff = 20000

    def setUp(self):
        super(ClientBaseTestCase, self).setUp()
        self.client = Client()
        translation.activate(settings.LANGUAGE_CODE)

    @classmethod
    def setUpTestData(cls):
        super(ClientBaseTestCase, cls).setUpTestData() # create django-tools default test users
        create_test_data()

    def get_test_user(self, username):
        try:
            return self.UserModel.objects.get(username=username)
        except self.UserModel.DoesNotExist as err:
            print("ERROR: %s" % err)
            usernames = ",".join(
                self.UserModel.objects.values_list("username", flat=True).order_by("username")
            )
            print("Existing users are: %s" % usernames)
            raise

    def login_test_user(self, username):
        user = self.get_test_user(username)

        superuser_data = self.get_userdata(usertype="superuser")
        password = superuser_data["password"]
        ok = self.client.login(username=username, password=password)
        self.assertTrue(ok, 'Can\'t login test user "%s"!' % username)

        return user

    def login_superuser(self):
        return self.login_test_user(username="superuser")

    def login_reporter_user(self):
        """
        The 'reporter' user can create un-/publish requests
        """
        return self.login_test_user(username=REPORTER_USER)

    def login_editor_user(self):
        """
        The 'editor' user can accept/reject un-/publish requests
        """
        return self.login_test_user(username=EDITOR_USER)


class CmsBaseTestCase(ClientBaseTestCase):
    @classmethod
    def setUpTestData(cls):
        super(CmsBaseTestCase, cls).setUpTestData()
        create_test_data()
