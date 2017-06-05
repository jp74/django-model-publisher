import sys

from django.core.management.base import BaseCommand
from optparse import make_option


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--list', action='store_true', dest='show_list', default=False,
                    help='List model items waiting to be published (limited to 100)'),
    )

    args = '[modelname] [pk] [--list]'
    help = 'Publish a specific model or models within app'
    usage_str = 'Usage: ./manage.py publish_model app.models.Blog'

    def error(self, message, code=1):
        """
        Print error and stop command
        """
        print(message)
        sys.exit(code)

    def handle(self, model_name=None, pk=None, show_list=None, *args, **options):
        if not model_name:
            self.error('You must provide an app to publish.\n' + self.usage_str)

        module = self.get_model(model_name)

        # TODO: Validate model is a publisher instance

        qs = module.objects.filter(publisher_is_draft=True).filter(publisher_linked_id=None)

        if pk:
            qs = qs.filter(pk=pk)

        if qs.count() < 1:
            self.error('No model(s) found to publish')

        if show_list:
            for model in qs.all():
                print("%s doesn't have published version yet" % model)
            return

        for model in qs.all():
            model.publish()
            print('Successfully published %s' % model)

    def get_model(self, model_name):
        """
        TODO: Need to validate model name has 2x '.' chars
        """
        klass = None
        try:
            module_name, class_name = model_name.rsplit('.', 1)
            mod = __import__(module_name, fromlist=[class_name])
            klass = getattr(mod, class_name)
        except ImportError as e:
            self.error('Cannot find app %s %s' % (model_name, e))

        return klass
