import sys

from django.conf import settings
import django

settings.configure(
    DEBUG=True,
    USE_TZ=True,
    DATABASES={
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
        }
    },
    ROOT_URLCONF='publisher.urls',
    INSTALLED_APPS=[
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sites',
        'publisher',
    ],
    SITE_ID=1,
    NOSE_ARGS=['-s'],
)

try:
    django.setup()
except AttributeError:
    pass


def run_tests(*test_args):
    from django_nose import NoseTestSuiteRunner
    if not test_args:
        test_args = ['publisher.tests.tests']
    test_runner = NoseTestSuiteRunner(verbosity=1)
    failures = test_runner.run_tests(test_args)
    if failures:
        sys.exit(failures)

if __name__ == '__main__':
    run_tests(*sys.argv[1:])
