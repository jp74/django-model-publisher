#!/usr/bin/env bash

set -e
set -x

cd publisher_test_project

./manage.py run_test_project_dev_server $*
