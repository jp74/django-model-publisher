import pprint
import sys

import pytest

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from django_cms_tools.fixtures.pages import CmsPageCreator

# https://github.com/jedie/django-tools
from django_tools.permissions import get_filtered_permissions
from django_tools.unittest_utils.user import get_or_create_user_and_group

from publisher import constants
from publisher.models import PublisherStateModel
from publisher_test_project.publisher_test_app.models import PublisherTestModel

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
    placeholder_slots = () # Don't fill any Plugins

    def get_title(self, language_code, lang_name):
        return "Test page in %s" % lang_name

    def add_plugins(self, page, placeholder):
        pass # Don't add any plugins


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

    editor_user = get_or_create_user_and_group(
        username=EDITOR_USER,
        groupname=EDITOR_GROUP,
        permissions=get_filtered_permissions(
            exclude_app_labels=("auth", "sites"),
            exclude_models=(),
            exclude_codenames=("publish_page",), # cms.publish_page
            exclude_permissions=(
                (PublisherStateModel, constants.PERMISSION_ASK_REQUEST),
            ),
        ),
        encrypted_password=encrypted_password
    )

    reporter_user = get_or_create_user_and_group(
        username=REPORTER_USER,
        groupname=REPORTER_GROUP,

        permissions=get_filtered_permissions(
            exclude_app_labels=("auth", "sites"),
            exclude_models=(),
            exclude_codenames=("publish_page",), # cms.publish_page
            exclude_permissions=(
                (PublisherStateModel, constants.PERMISSION_DIRECT_PUBLISHER),
                (PublisherStateModel, constants.PERMISSION_REPLY_REQUEST),
            ),
        ),
        encrypted_password=encrypted_password
    )
    return reporter_user, editor_user


def create_test_page(delete_first=False):
    page, created = TestPageCreator(delete_first=delete_first).create()
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
            title="Test entry %i" % no,
            publisher_is_draft=True
        )
        if created:
            print("Test model entry: '%s'" % instance)
        else:
            print("Test model entry already exists: '%s'" % instance)
        instance.publish()


def create_test_data(delete_first=False):

    reporter_user, editor_user = create_test_user(delete_first=delete_first)

    create_test_page(delete_first=delete_first)

    create_test_model_entries(delete_first=delete_first)

    return reporter_user, editor_user
