from django.db import models

from publisher.models import PublisherModel


class PublisherTestModel(PublisherModel):
    title = models.CharField(max_length=100)
