# -*- coding: utf-8 -*-

import os
import sys

sys.path.insert(0, "..")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")


def runtests():
    from django.core.management import execute_from_command_line
    args = sys.argv

    args.insert(1, "test")

    execute_from_command_line(args)


if __name__ == "__main__":
    runtests()
