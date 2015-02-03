# Copyright (C) 2015 - The MITRE Corporation
# For license information, see the LICENSE.txt file

import os, sys

import django
from django.conf import settings
from django.test.utils import get_runner


def runtests():
    os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.test_settings'
    django.setup()

    TestRunner = get_runner(settings)
    test_runner = TestRunner()

    failures = test_runner.run_tests(['tests',])
    if failures:
        sys.exit(failures)


if __name__ == '__main__':
    runtests()
