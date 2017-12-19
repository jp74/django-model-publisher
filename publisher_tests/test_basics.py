
import os

from django.core.management import call_command
from django.test import TestCase

import publisher_test_project
from django_tools.unittest_utils.django_command import DjangoCommandMixin
from django_tools.unittest_utils.stdout_redirect import StdoutStderrBuffer

MANAGE_DIR = os.path.abspath(os.path.dirname(publisher_test_project.__file__))


class ManageCommandTests(DjangoCommandMixin, TestCase):
    def call_manage_py(self, cmd, **kwargs):
        self.assertTrue(os.path.isfile(os.path.join(MANAGE_DIR, 'manage.py')))
        return super(ManageCommandTests, self).call_manage_py(cmd, manage_dir=MANAGE_DIR, **kwargs)

    def test_help(self):
        """
        Run './manage.py --help' via subprocess and check output.
        """
        output = self.call_manage_py(['--help'])

        self.assertNotIn('ERROR', output)
        self.assertIn('[django]', output)
        self.assertIn('Type \'manage.py help <subcommand>\' for help on a specific subcommand.', output)

    def test_missing_migrations(self):
        output = self.call_manage_py(["makemigrations", "--dry-run"])
        print(output)
        self.assertIn("No changes detected", output)
        self.assertNotIn("Migrations for", output) # output like: """Migrations for 'appname':"""
        self.assertNotIn("SystemCheckError", output)
        self.assertNotIn("ERRORS", output)


class ManageCheckTests(TestCase):

    def test_django_check(self):
        """
        call './manage.py check' directly via 'call_command'
        """
        with StdoutStderrBuffer() as buff:
            call_command('check')
        output = buff.get_output()
        self.assertIn('System check identified no issues (0 silenced).', output)

    def test_django_cms_check(self):
        """
        call './manage.py cms check' directly via 'call_command'
        """
        with StdoutStderrBuffer() as buff:
            call_command('cms', 'check')
        output = buff.get_output()
        print(output)
        self.assertIn('Installation okay', output)
        self.assertNotIn('ERROR', output)
