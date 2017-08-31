from django.db import models


from publisher.managers import PublisherManager
from publisher.models import PublisherModel


class PublisherTestModel(PublisherModel):
    title = models.CharField(max_length=100)

    publisher_manager = PublisherManager()


try:
    from parler.models import TranslatedFields
except ImportError:
    pass
else:
    from publisher.models import PublisherParlerModel

    class PublisherParlerTestModel(PublisherParlerModel):
        translations = TranslatedFields(
            title=models.CharField(max_length=100)
        )