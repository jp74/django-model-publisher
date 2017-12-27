
import os

from django.core.management import call_command
from django.test import TestCase

from django_tools.unittest_utils.django_command import DjangoCommandMixin
from django_tools.unittest_utils.stdout_redirect import StdoutStderrBuffer

import publisher_test_project
from publisher_tests.base import ClientBaseTestCase

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


class PermissionTestCase(ClientBaseTestCase):
    def test_reporter_permissions(self):
        with StdoutStderrBuffer() as buff:
            call_command("permission_info", "reporter")
        output = buff.get_output()

        output = [line.strip(" \t_") for line in output.splitlines()]
        output = "\n".join([line for line in output if line])
        print(output)

        # 'reporter' user has not 'can_publish' -> can only create un-/publish requests:

        self.assertEqual_dedent(output, """
            Display effective user permissions in the same format as user.has_perm() argument: <appname>.<codename>
            All permissions for user 'reporter':
            is_active    : yes
            is_staff     : yes
            is_superuser : no
            [*] admin.add_logentry
            [*] admin.change_logentry
            [*] admin.delete_logentry
            [ ] auth.add_group
            [ ] auth.change_group
            [ ] auth.delete_group
            [ ] auth.add_permission
            [ ] auth.change_permission
            [ ] auth.delete_permission
            [ ] auth.add_user
            [ ] auth.change_user
            [ ] auth.delete_user
            [*] cms.add_aliaspluginmodel
            [*] cms.change_aliaspluginmodel
            [*] cms.delete_aliaspluginmodel
            [*] cms.add_cmsplugin
            [*] cms.change_cmsplugin
            [*] cms.delete_cmsplugin
            [*] cms.add_globalpagepermission
            [*] cms.change_globalpagepermission
            [*] cms.delete_globalpagepermission
            [*] cms.add_page
            [*] cms.change_page
            [ ] cms.delete_page
            [*] cms.edit_static_placeholder
            [ ] cms.publish_page
            [*] cms.view_page
            [ ] cms.add_pagepermission
            [ ] cms.change_pagepermission
            [ ] cms.delete_pagepermission
            [*] cms.add_pageuser
            [*] cms.change_pageuser
            [*] cms.delete_pageuser
            [*] cms.add_pageusergroup
            [*] cms.change_pageusergroup
            [*] cms.delete_pageusergroup
            [*] cms.add_placeholder
            [*] cms.change_placeholder
            [*] cms.delete_placeholder
            [*] cms.use_structure
            [*] cms.add_placeholderreference
            [*] cms.change_placeholderreference
            [*] cms.delete_placeholderreference
            [*] cms.add_staticplaceholder
            [*] cms.change_staticplaceholder
            [*] cms.delete_staticplaceholder
            [*] cms.add_title
            [*] cms.change_title
            [*] cms.delete_title
            [*] cms.add_urlconfrevision
            [*] cms.change_urlconfrevision
            [*] cms.delete_urlconfrevision
            [*] cms.add_usersettings
            [*] cms.change_usersettings
            [*] cms.delete_usersettings
            [*] contenttypes.add_contenttype
            [*] contenttypes.change_contenttype
            [*] contenttypes.delete_contenttype
            [*] menus.add_cachekey
            [*] menus.change_cachekey
            [*] menus.delete_cachekey
            [ ] publisher.add_publisherstatemodel
            [*] publisher.change_publisherstatemodel
            [ ] publisher.delete_publisherstatemodel
            [*] publisher_list_app.add_publisheritem
            [ ] publisher_list_app.can_publish_publisheritem
            [*] publisher_list_app.change_publisheritem
            [ ] publisher_list_app.delete_publisheritem
            [*] publisher_list_app.add_publisheritemcmsplugin
            [*] publisher_list_app.change_publisheritemcmsplugin
            [*] publisher_list_app.delete_publisheritemcmsplugin
            [*] publisher_test_app.add_plaintextpluginmodel
            [*] publisher_test_app.change_plaintextpluginmodel
            [*] publisher_test_app.delete_plaintextpluginmodel
            [*] publisher_test_app.add_publisherparlerautoslugifytestmodel
            [ ] publisher_test_app.can_publish_publisherparlerautoslugifytestmodel
            [*] publisher_test_app.change_publisherparlerautoslugifytestmodel
            [ ] publisher_test_app.delete_publisherparlerautoslugifytestmodel
            [*] publisher_test_app.add_publisherparlertestmodel
            [ ] publisher_test_app.can_publish_publisherparlertestmodel
            [*] publisher_test_app.change_publisherparlertestmodel
            [ ] publisher_test_app.delete_publisherparlertestmodel
            [*] publisher_test_app.add_publishertestmodel
            [ ] publisher_test_app.can_publish_publishertestmodel
            [*] publisher_test_app.change_publishertestmodel
            [ ] publisher_test_app.delete_publishertestmodel
            [*] sessions.add_session
            [*] sessions.change_session
            [*] sessions.delete_session
            [ ] sites.add_site
            [ ] sites.change_site
            [ ] sites.delete_site
        """)

    def test_editor_permissions(self):
        with StdoutStderrBuffer() as buff:
            call_command("permission_info", "editor")
        output = buff.get_output()

        output = [line.strip(" \t_") for line in output.splitlines()]
        output = "\n".join([line for line in output if line])
        print(output)

        # 'editor' user has 'can_publish' -> can publish and accept/reject un-/publish requests:

        self.assertEqual_dedent(output, """
            Display effective user permissions in the same format as user.has_perm() argument: <appname>.<codename>
            All permissions for user 'editor':
            is_active    : yes
            is_staff     : yes
            is_superuser : no
            [*] admin.add_logentry
            [*] admin.change_logentry
            [*] admin.delete_logentry
            [ ] auth.add_group
            [ ] auth.change_group
            [ ] auth.delete_group
            [ ] auth.add_permission
            [ ] auth.change_permission
            [ ] auth.delete_permission
            [ ] auth.add_user
            [ ] auth.change_user
            [ ] auth.delete_user
            [*] cms.add_aliaspluginmodel
            [*] cms.change_aliaspluginmodel
            [*] cms.delete_aliaspluginmodel
            [*] cms.add_cmsplugin
            [*] cms.change_cmsplugin
            [*] cms.delete_cmsplugin
            [*] cms.add_globalpagepermission
            [*] cms.change_globalpagepermission
            [*] cms.delete_globalpagepermission
            [*] cms.add_page
            [*] cms.change_page
            [*] cms.delete_page
            [*] cms.edit_static_placeholder
            [*] cms.publish_page
            [*] cms.view_page
            [ ] cms.add_pagepermission
            [ ] cms.change_pagepermission
            [ ] cms.delete_pagepermission
            [*] cms.add_pageuser
            [*] cms.change_pageuser
            [*] cms.delete_pageuser
            [*] cms.add_pageusergroup
            [*] cms.change_pageusergroup
            [*] cms.delete_pageusergroup
            [*] cms.add_placeholder
            [*] cms.change_placeholder
            [*] cms.delete_placeholder
            [*] cms.use_structure
            [*] cms.add_placeholderreference
            [*] cms.change_placeholderreference
            [*] cms.delete_placeholderreference
            [*] cms.add_staticplaceholder
            [*] cms.change_staticplaceholder
            [*] cms.delete_staticplaceholder
            [*] cms.add_title
            [*] cms.change_title
            [*] cms.delete_title
            [*] cms.add_urlconfrevision
            [*] cms.change_urlconfrevision
            [*] cms.delete_urlconfrevision
            [*] cms.add_usersettings
            [*] cms.change_usersettings
            [*] cms.delete_usersettings
            [*] contenttypes.add_contenttype
            [*] contenttypes.change_contenttype
            [*] contenttypes.delete_contenttype
            [*] menus.add_cachekey
            [*] menus.change_cachekey
            [*] menus.delete_cachekey
            [ ] publisher.add_publisherstatemodel
            [*] publisher.change_publisherstatemodel
            [ ] publisher.delete_publisherstatemodel
            [*] publisher_list_app.add_publisheritem
            [*] publisher_list_app.can_publish_publisheritem
            [*] publisher_list_app.change_publisheritem
            [*] publisher_list_app.delete_publisheritem
            [*] publisher_list_app.add_publisheritemcmsplugin
            [*] publisher_list_app.change_publisheritemcmsplugin
            [*] publisher_list_app.delete_publisheritemcmsplugin
            [*] publisher_test_app.add_plaintextpluginmodel
            [*] publisher_test_app.change_plaintextpluginmodel
            [*] publisher_test_app.delete_plaintextpluginmodel
            [*] publisher_test_app.add_publisherparlerautoslugifytestmodel
            [*] publisher_test_app.can_publish_publisherparlerautoslugifytestmodel
            [*] publisher_test_app.change_publisherparlerautoslugifytestmodel
            [*] publisher_test_app.delete_publisherparlerautoslugifytestmodel
            [*] publisher_test_app.add_publisherparlertestmodel
            [*] publisher_test_app.can_publish_publisherparlertestmodel
            [*] publisher_test_app.change_publisherparlertestmodel
            [*] publisher_test_app.delete_publisherparlertestmodel
            [*] publisher_test_app.add_publishertestmodel
            [*] publisher_test_app.can_publish_publishertestmodel
            [*] publisher_test_app.change_publishertestmodel
            [*] publisher_test_app.delete_publishertestmodel
            [*] sessions.add_session
            [*] sessions.change_session
            [*] sessions.delete_session
            [ ] sites.add_site
            [ ] sites.change_site
            [ ] sites.delete_site
        """)
