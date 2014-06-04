class NotDraftException(Exception):
    pass


def assert_draft(method):
    def decorated(self, *args, **kwargs):
        if not self.is_draft:
            raise NotDraftException()

        return method(self, *args, **kwargs)
    return decorated
