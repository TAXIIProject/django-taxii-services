# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from django.test import TestCase


class BasicsTests(TestCase):

    def test_01(self):
        """
        Attempts to import all parts of taxii_services
        """
        import taxii_services
        import taxii_services.admin
        import taxii_services.base_taxii_handlers
        import taxii_services.exceptions
        import taxii_services.handlers
        import taxii_services.management
        import taxii_services.middleware
        import taxii_services.models
        import taxii_services.taxii_handlers
        import taxii_services.urls
        import taxii_services.views
