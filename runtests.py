# Copyright (C) 2015 - The MITRE Corporation
# For license information, see the LICENSE.txt file

import os
import sys

import django
from django.conf import settings
from django.test.utils import get_runner


def runtests():
    os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.test_settings'
    django.setup()

    TestRunner = get_runner(settings)
    test_runner = TestRunner()

    # By default, run all of the tests
    tests = ['tests']

    # Allow running a subset of tests via the command line.
    if len(sys.argv) > 1:
        tests = sys.argv[1:]

    failures = test_runner.run_tests(tests, verbosity=3)
    if failures:
        sys.exit(failures)


if __name__ == '__main__':
    runtests()
