# Copyright (c) 2015, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from django.test import TestCase

from .base import DJTTestCase


class BasicsTests(TestCase):

    def test_imports(self):
        """
        Ensure all taxii_services modules can be imported.
        """
        import taxii_services
        import taxii_services.admin
        import taxii_services.exceptions
        import taxii_services.handlers
        import taxii_services.management
        import taxii_services.middleware
        import taxii_services.models
        import taxii_services.urls
        import taxii_services.views
