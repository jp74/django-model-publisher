#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

from setuptools import setup

import publisher

version = publisher.__version__

if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    print("You probably want to also tag the version now:")
    print("  git tag -a %s -m 'version %s'" % (version, version))
    print("  git push --tags")
    sys.exit()

readme = open('README.rst').read()

setup(
    name='django-model-publisher-ai',
    version=version,
    description="""Handy mixin/abstract class for providing a "publisher workflow" to arbitrary Django models.""",
    long_description=readme,
    author='JP74',
    author_email='opensource@jp74.com',
    url='https://github.com/andersinno/django-model-publisher-ai',
    packages=[
        'publisher',
    ],
    include_package_data=True,
    license="BSD",
    zip_safe=False,
    keywords='django-model-publisher',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ],
)
