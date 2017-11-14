==================
Handling relations
==================


django-ya-model-publisher does not provide any mechanism to publish related models, as it can be quite specific. Implementing classes wishing to do so will have to override the ``clone_relations()`` method from ``PublisherModelBase``, which takes two arguments: ``src_obj`` (the draft instance), and ``dst_obj`` (the published instance).

Here's a simple example which maintains the relations with a many to many model::

    def clone_relations(self, src_obj, dst_obj):
        dst_obj.sites.add(*src_obj.sites.all())

