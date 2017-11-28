from publisher.forms import PublisherForm


class PageProxyForm(PublisherForm):
    def __init__(self, *args, **kwargs):
        self.base_fields["page"].widget.attrs["readonly"] = "readonly"
        super(PageProxyForm, self).__init__(*args, **kwargs)
