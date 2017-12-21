from publisher.models import PublisherStateModel


def debug_info(request):
    user = request.user
    return {
        "has_ask_request_permission": PublisherStateModel.has_ask_request_permission(
            user, raise_exception=False
        ),
        "has_reply_request_permission": PublisherStateModel.has_reply_request_permission(
            user, raise_exception=False
        ),

        "cms_publish_page": user.has_perms("cms.publish_page"),
    }
