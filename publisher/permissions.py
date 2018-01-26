import logging

from django.contrib.auth import get_permission_codename
from django.core.exceptions import PermissionDenied

from django_tools.permissions import check_permission, get_permission_by_string

from publisher import constants

log = logging.getLogger(__name__)


def has_object_permission(user, opts, action, raise_exception=True):
    """
    Check if user has "<app_name>.<action>_<model_name>"

    opts is <model_instance>._meta
    """
    codename = get_permission_codename(action, opts)

    if codename == "can_publish_page":
        # FIXME: Django CMS code name doesn't has the prefix "can_" !
        # TODO: Remove "can_" from own permissions to unify it.
        # see also: publisher.models.PublisherStateModel#object_permission_name
        # https://github.com/wearehoods/django-ya-model-publisher/issues/8
        codename = "publish_page"

    perm_name = "%s.%s" % (
        opts.app_label,
        codename
    )

    try:
        has_permission = check_permission(user, perm_name, raise_exception)
    except PermissionDenied:
        # get_permission() will raise helpfull errors if format is wrong
        # or if the permission doesn't exists
        get_permission_by_string(perm_name)
        raise

    if not has_permission:
        get_permission_by_string(perm_name)

    return has_permission


def can_publish_object(user, opts, raise_exception=True):
    """
    Check if user has "<app_name>.can_publish_<model_name>"

    opts is <model_instance>._meta
    """
    return has_object_permission(user, opts,
        action=constants.PERMISSION_CAN_PUBLISH,
        raise_exception=raise_exception
    )
