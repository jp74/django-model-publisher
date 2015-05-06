from threading import current_thread


class PublisherMiddleware(object):
    _draft_status = {}

    @staticmethod
    def is_draft(request):
        authenticated = request.user.is_authenticated() and request.user.is_staff
        is_draft = 'edit' in request.GET and authenticated
        return is_draft

    def process_request(self, request):
        PublisherMiddleware._draft_status[current_thread()] = self.is_draft(request)

    @staticmethod
    def process_response(request, response):
        try:
            del PublisherMiddleware._draft_status[current_thread()]
        except KeyError:
            pass
        return response

    @staticmethod
    def get_draft_status():
        try:
            return PublisherMiddleware._draft_status[current_thread()]
        except KeyError:
            return False


def get_draft_status():
    return PublisherMiddleware.get_draft_status()
