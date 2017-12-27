
"""
    created 2017 by Jens Diemer <ya-publisher@jensdiemer.de>
"""


from django.core.management import BaseCommand

from publisher_test_project.publisher_list_app.fixtures import list_item_fixtures


class Command(BaseCommand):
    def handle(self, *args, **options):
        list_item_fixtures()
