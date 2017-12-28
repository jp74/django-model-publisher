
import logging
import sys

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from cms.models import Page, PagePermission

from django_cms_tools.fixtures.pages import CmsPageCreator

# https://github.com/jedie/django-tools
from django_tools.permissions import get_filtered_permissions, pformat_permission
from django_tools.unittest_utils.user import get_or_create_user_and_group

from publisher import constants
from publisher.models import PublisherStateModel
from publisher_test_project.publisher_list_app.fixtures import list_item_fixtures
from publisher_test_project.publisher_list_app.models import PublisherItem
from publisher_test_project.publisher_test_app.models import (PublisherParlerAutoSlugifyTestModel,
                                                              PublisherParlerTestModel, PublisherTestModel)

log = logging.getLogger(__name__)


# 'reporter' user can create un-/publish requests:
REPORTER_USER="reporter"
REPORTER_GROUP="reporters"

# 'editor' user can accept/reject un-/publish requests:
EDITOR_USER="editor"
EDITOR_GROUP="editors"


def get_permission(model, codename):
    content_type = ContentType.objects.get_for_model(model)
    permission = Permission.objects.get(content_type=content_type, codename=codename)
    return permission


class TestPageCreator(CmsPageCreator):
    placeholder_slots = ("content",)
    dummy_text_count = 1

    def __init__(self, no, *args, **kwargs):
        self.no = no
        super(TestPageCreator, self).__init__(*args, **kwargs)

    def get_title(self, language_code, lang_name):
        return "Test page %i in %s" % (self.no, lang_name)

    def get_slug(self, language_code, lang_name):
        slug = super(TestPageCreator, self).get_slug(language_code, lang_name)
        log.debug("slug: %r (%r %s)", slug, language_code, lang_name)
        return slug

    def get_add_plugin_kwargs(self, page, no, placeholder, language_code, lang_name):
        """
        Return "content" for create the plugin.
        Called from self.add_plugins()
        """
        return {
            "plugin_type": "PlainTextPlugin", # publisher_test_app.cms_plugins.PlainTextPlugin
            "text": "Dummy plain text plugin no.%i" % self.no
        }


def create_test_user(delete_first=False):
    User=get_user_model()

    if delete_first:
        qs = User.objects.exclude(is_superuser=True, is_active=True)
        print("Delete %i users..." % qs.count())
        qs.delete()

        qs = Group.objects.all()
        print("Delete %i user groups..." % qs.count())
        qs.delete()

    # all_permissions = [
    #     "%s.%s" % (entry.content_type, entry.codename)
    #     for entry in Permission.objects.all().order_by("content_type", "codename")
    # ]
    # pprint.pprint(all_permissions)

    superuser_qs = User.objects.all().filter(is_superuser=True, is_active=True)
    try:
        superuser = superuser_qs[0]
    except IndexError:
        print("\nERROR: No active superuser found!")
        print("Please create one and run again!\n")
        sys.exit(-1)

    print("Use password from Superuser:", superuser)
    encrypted_password = superuser.password

    # 'reporter' user can create (un-)publish requests:

    reporter_user = get_or_create_user_and_group(
        username=REPORTER_USER,
        groupname=REPORTER_GROUP,

        permissions=get_filtered_permissions(
            exclude_app_labels=("auth", "sites"),
            exclude_models=(
                PagePermission,
            ),
            exclude_codenames=(
                "can_publish" # <app_name>.can_publish_<model_name>
                "delete" # <app_name>.delete_<model_name>
            ),
            exclude_permissions=(
                # Django CMS permissions:
                (Page, "publish_page"), # cms.publish_page
                (Page, "delete_page"), # cms.delete_page

                # Publisher permissions:
                (PublisherStateModel, "add_publisherstatemodel"),
                (PublisherStateModel, "delete_publisherstatemodel"),

                (PublisherParlerAutoSlugifyTestModel, "can_publish_publisherparlerautoslugifytestmodel"),
                (PublisherParlerAutoSlugifyTestModel, "delete_publisherparlerautoslugifytestmodel"),

                (PublisherItem, "can_publish_publisheritem"),
                (PublisherItem, "delete_publisheritem"),

                (PublisherParlerTestModel, "can_publish_publisherparlertestmodel"),
                (PublisherParlerTestModel, "delete_publisherparlertestmodel"),

                (PublisherTestModel, "can_publish_publishertestmodel"),
                (PublisherTestModel, "delete_publishertestmodel"),
            ),
        ),
        encrypted_password=encrypted_password
    )

    # 'editor' can direct (un-)publish & accept/reject a (un-)publish request

    editor_user = get_or_create_user_and_group(
        username=EDITOR_USER,
        groupname=EDITOR_GROUP,
        permissions=get_filtered_permissions(
            exclude_app_labels=("auth", "sites"),
            exclude_models=(
                PagePermission,
            ),
            exclude_codenames=(),
            exclude_permissions=(
                # Publisher permissions:
                (PublisherStateModel, "add_publisherstatemodel"),
                (PublisherStateModel, "delete_publisherstatemodel"),
            ),
        ),
        encrypted_password=encrypted_password
    )

    return reporter_user, editor_user


def create_test_page(delete_first=False):
    for no in range(1,5):
        page, created = TestPageCreator(no=no, delete_first=delete_first).create()
        if created:
            print("Test page created: '%s'" % page)
        else:
            print("Test page already exists: '%s'" % page)


def create_test_model_entries(delete_first=False):
    if delete_first:
        qs = PublisherTestModel.objects.all()
        print("Delete %i test model entries..." % qs.count())
        qs.delete()

    for no in range(1,5):
        instance, created = PublisherTestModel.objects.get_or_create(
            no = no,
            title="Test entry %i" % no,
            publisher_is_draft=True
        )
        if created:
            print("Test model entry: '%s'" % instance)
        else:
            print("Test model entry already exists: '%s'" % instance)
        instance.publish()


def create_test_data(delete_first=False):

    if delete_first:
        qs = Page.objects.all()
        log.debug("Delete %i CMS pages...", qs.count())
        qs.delete()

    reporter_user, editor_user = create_test_user(delete_first=delete_first)

    create_test_page(delete_first=delete_first)

    create_test_model_entries(delete_first=delete_first)

    list_item_fixtures()

    return reporter_user, editor_user
