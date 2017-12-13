

# https://github.com/jedie/django-tools
from django.conf import settings
from django.test import Client
from django.utils import translation

from django_tools.unittest_utils.unittest_base import BaseTestCase
from django_tools.unittest_utils.user import TestUserMixin, create_user, get_super_user


class ClientBaseTestCase(TestUserMixin, BaseTestCase):
    """ Main base class for all TestCases that used the Client() """

    maxDiff = 20000

    def setUp(self):
        super(ClientBaseTestCase, self).setUp()
        self.client = Client()
        translation.activate(settings.LANGUAGE_CODE)
