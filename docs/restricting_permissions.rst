===========
Permissions
===========

To restrict publish access to your model, add 'PublisherModel.Meta' to your models Meta class::

    class Article(PublisherModel):

        class Meta(PublisherModel.Meta):
               pass


Then run the following management command::

    python manage.py update_permissions


You should now have the "Can publish" permission available for your model.
