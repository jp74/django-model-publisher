import pprint
import sys

from django.contrib.auth import get_user_model

from django_tools.unittest_utils.user import create_user

from django.contrib.auth.models import Permission, Group

import pytest
from django.contrib.contenttypes.models import ContentType
from publisher import constants
from publisher.models import PublisherStateModel


# can create un-/publish requests:
from publisher_test_project.publisher_test_app.models import PublisherTestModel

REPORTER_USER="reporter"
REPORTER_GROUP="reporters"

# can accept/reject un-/publish requests:
EDITOR_USER="editor"
EDITOR_GROUP="editors"


def create_test_user(username, groupname, permissions, encrypted_password):
    User=get_user_model()

    print("_"*79)
    print("Create test user '%s':" % username)

    group, created = Group.objects.get_or_create(name=groupname)
    if created:
        print("User group '%s' created." % groupname)
    else:
        print("Use existing user group '%s', ok." % groupname)

    for permission in permissions:
        print("Add permission '%s'" % permission)
        group.permissions.add(permission)

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = create_user(
            username=username,
            groups=(group,),
            is_staff=True,
            is_superuser=False,
            encrypted_password=encrypted_password,
        )
        print("\nTest user '%s' created with password from superuser!\n" % username)
    else:
        print("Test user '%s' already exists, ok." % username)

    return user


def get_permission(model, codename):
    content_type = ContentType.objects.get_for_model(model)
    permission = Permission.objects.get(content_type=content_type, codename=codename)
    return permission


@pytest.fixture(scope="session")
def create_test_data():
    User=get_user_model()

    all_permissions = [
        "%s.%s" % (entry.content_type, entry.codename)
        for entry in Permission.objects.all().order_by("content_type", "codename")
    ]
    pprint.pprint(all_permissions)


    superuser_qs = User.objects.all().filter(is_superuser=True, is_active=True)
    try:
        superuser = superuser_qs[0]
    except IndexError:
        print("\nERROR: No active superuser found!")
        print("Please create one and run again!\n")
        sys.exit(-1)

    print("Use password from Superuser:", superuser)
    encrypted_password = superuser.password

    reporter_user = create_test_user(
        username=REPORTER_USER,
        groupname=REPORTER_GROUP,
        permissions=(
            get_permission(model=PublisherTestModel, codename="add_publishertestmodel"),
            get_permission(model=PublisherTestModel, codename="change_publishertestmodel"),
            get_permission(model=PublisherStateModel, codename=constants.PERMISSION_ASK_REQUEST),
        ),
        encrypted_password=encrypted_password
    )
    editor_user = create_test_user(
        username=EDITOR_USER,
        groupname=EDITOR_GROUP,
        permissions=(
            get_permission(model=PublisherTestModel, codename="can_publish"),
            get_permission(model=PublisherTestModel, codename="add_publishertestmodel"),
            get_permission(model=PublisherTestModel, codename="change_publishertestmodel"),
            get_permission(model=PublisherTestModel, codename="delete_publishertestmodel"),
            get_permission(model=PublisherStateModel, codename=constants.PERMISSION_REPLY_REQUEST),
        ),
        encrypted_password=encrypted_password
    )
    return reporter_user, editor_user





