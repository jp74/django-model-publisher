.PHONY: clean-pyc clean-build docs

help:
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "lint - check style with flake8"
	@echo "test - run tests quickly with the default Python"
	@echo "testall - run tests on every Python version with tox"
	@echo "coverage - check code coverage quickly with the default Python"
	@echo "docs - generate Sphinx HTML documentation, including API docs"
	@echo "release - package and upload a release"
	@echo "sdist - package"

clean: clean-build clean-pyc

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info

clean-pyc:
	find . -type d -name "__pycache__" | xargs --no-run-if-empty rm -Rf
	find . -type f -name "*.py[co]" -delete
	find . -name '*~' -exec rm -f {} +

lint:
	flake8 django-ya-model-publisher tests

test:
	python setup.py test

test-all:
	python setup.py tox

dev_install: clean
	pip install -U pip
	pip install -r requirements/dev.txt
	pip install -e .

coverage:
	coverage run --source django-ya-model-publisher setup.py test
	coverage report -m
	coverage html
	open htmlcov/index.html

docs:
	rm -f docs/django-ya-model-publisher.rst
	rm -f docs/modules.rst
	sphinx-apidoc -o docs/ django-ya-model-publisher
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
	open docs/_build/html/index.html

publish: clean
	python setup.py publish

sdist: clean
	python setup.py sdist
	ls -l dist
