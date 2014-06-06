========
Usage
========

Getting started
---------------

Browse to your page with /?edit to view the draft version of your model.

Make changes to your model as you normally would. When you are happy with your changes, use the publish button to copy your model to its published instance.

Now when you view your live page you should see the updated version of your model.

Updating your model
-------------------

You can now go back to /?edit and make changes to your model. These changes will remain in a draft state until you hit publish again.

If you are unhappy with the new draft, use the revert button to discard your draft changes.

Permissions
-----------

To restrict publish access to your model, add 'PublisherModel.Meta' to your models Meta class::

    class Meta(PublisherModel.Meta):
       ...


Then run the following management command::

    python manage.py update_permissions


You should now have the 'Can publish' permission available for your model.

Model
-----
::

    from django.db import models
    from publisher.models import PublisherModel


    class Article(PublisherModel):
        title = models.CharField('Title', max_length=255)
        slug = models.CharField('Slug', max_length=255)
        copy = models.CharField('Copy', max_length=255)

        def __unicode__(self):
            return self.title


View
----
::

    from .models import Article

    from publisher.views import PublisherDetailView, PublisherListView


    class ArticleListView(PublisherListView):
        model = Article
        context_object_name = 'articles'


    class ArticleView(PublisherDetailView):
        model = Article
        context_object_name = 'article'


Admin
-----
::

    from django.contrib import admin

    from publisher.admin import PublisherAdmin, PublisherPublishedFilter

    from .models import Article


    class ArticleAdmin(PublisherAdmin):
        list_filter = (PublisherPublishedFilter,)
        list_display = ('__unicode__', 'publisher_publish', 'publisher_status', )


    admin.site.register(Article, ArticleAdmin)
