# Copyright (c) 2015, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from django.conf import settings
from django.test import TestCase

from .helpers import add_basics, make_request


class DJTTestCase(TestCase):
    """A base class for django-taxii-services test cases."""

    def setUp(self):
        settings.DEBUG = True
        add_basics()

    def make_request(self, **kwargs):
        make_request(**kwargs)
