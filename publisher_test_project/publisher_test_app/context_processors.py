
import django

def debug_info(request):
    user = request.user
    return {
        "django_version": django.__version__,
        "cms_change_page": user.has_perms("cms.change_page"),
        "cms_publish_page": user.has_perms("cms.publish_page"),
    }
