============
Installation
============

Install django-model-publisher (using pip)::

    pip install django-model-publisher


Add it to installed apps in your settings::

    INSTALLED_APPS = (
        ...
        'publisher',
    )


Add the middleware::

    MIDDLEWARE_CLASSES = (
        ...
        'publisher.middleware.PublisherMiddleware',
    )


Making models publishable
-------------------------

#. Have your model inherit from PublisherModel and use the custom manager (or signals won't work)::

    from publisher.managers import PublisherManager
    from publisher.models import PublisherModel


    class Article(PublisherModel):
        publisher_manager = PublisherManager()


#. Update your database schema. If using South, you can run::

    python manage.py schemamigration --auto <app_name>
    python manage.py migrate <app_name>


The model records in the database will now be duplicated in a draft and a published version.

Django admin
------------

If using Django admin, you can use the provided PublisherAdmin. You can also import PublisherPublishedFilter to use in ``list_filter``::

    from django.contrib import admin

    from publisher.admin import PublisherAdmin

    from .models import Article


    class ArticleAdmin(PublisherAdmin):
        pass


    admin.site.register(Article, ArticleAdmin)


Setting up the views
--------------------

Use the provided views to serve either the draft or published version of your model. PublisherDetailView and PublisherListView are based on Django's DetailView and ListView respectively, but you can also use the PublisherViewMixin mixing in your custom views::

    from .models import Article

    from publisher.views import PublisherDetailView, PublisherListView


    class ArticleListView(PublisherListView):
        model = Article


    class ArticleView(PublisherDetailView):
        model = Article


Those views will only display the published version by default. To view the draft version, either follow the preview link from the admin, or append ``?edit`` at the end of the URL (note that you will need to be logged in).
