

from django.core.management import BaseCommand

from publisher_test_project.fixtures import create_test_data


class Command(BaseCommand):
    help = "Create publisher test app data"
    def handle(self, *args, **options):
        create_test_data()
