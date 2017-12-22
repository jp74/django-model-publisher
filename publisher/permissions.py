import logging

from django.contrib.auth import get_permission_codename
from django_tools.permissions import check_permission
from publisher import constants

log = logging.getLogger(__name__)


def has_object_permission(user, obj, action, raise_exception=True):
    """
    Check user permissions
    TODO: Add to django-tools ;)
    """
    opts = obj._meta
    codename = get_permission_codename(action, opts)
    perm_name = "%s.%s" % (
        opts.app_label,
        codename
    )
    return check_permission(user, perm_name, raise_exception)


def can_publish_object(user, obj, raise_exception=True):
    """
    Check if user has "<app_name>.can_publish_<model_name>"
    """
    opts = obj._meta
    codename = get_permission_codename(constants.PERMISSION_CAN_PUBLISH, opts)
    perm_name = "%s.%s" % (
        opts.app_label,
        codename
    )
    return check_permission(user, perm_name, raise_exception)
