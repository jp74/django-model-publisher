#!/usr/bin/env python3

import os
import sys

print("sys.real_prefix:", getattr(sys, "real_prefix", "-"))
print("sys.prefix:", sys.prefix)

if __name__ == "__main__":
    if "VIRTUAL_ENV" not in os.environ:
        raise RuntimeError(" *** ERROR: Virtual env not activated! *** ")

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
