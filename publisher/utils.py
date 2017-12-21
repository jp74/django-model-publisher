
from pkgutil import find_loader

##############################################################################
# Some bools that indicate if python packages exists without to import them.
# Needed for activate code parts depents on modul existing.
#
# e.g.: importing django-parler in settings will raise into a error, because
#       of import loops
#
parler_exists = find_loader("parler") is not None # django-parler
hvad_exists = find_loader("hvad") is not None # django-hvad
django_cms_exists = find_loader("cms") is not None # django-cms
aldryn_translation_tools_exists = find_loader("aldryn_translation_tools") is not None # aldryn-translation-tools


##############################################################################


class NotDraftException(Exception):
    pass


def assert_draft(method):
    def decorated(self, *args, **kwargs):
        if not self.publisher_is_draft:
            raise NotDraftException()

        return method(self, *args, **kwargs)
    return decorated
