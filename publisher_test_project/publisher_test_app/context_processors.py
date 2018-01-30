
import django
from django.contrib.auth import get_user_model


def debug_info(request):
    User = get_user_model()
    usernames = User.objects.filter(is_staff=True, is_active=True).values_list("username", flat=True)

    user = request.user
    return {
        "django_version": django.__version__,
        "cms_change_page": user.has_perms("cms.change_page"),
        "cms_publish_page": user.has_perms("cms.publish_page"),
        "usernames": usernames,
    }
