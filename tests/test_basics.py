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

        """
        Test import of default message handlers.
        """
        import taxii_services.message_handlers.base_handlers
        import taxii_services.message_handlers.discovery_request_handlers
        import taxii_services.message_handlers.collection_information_request_handlers
        import taxii_services.message_handlers.inbox_message_handlers
        import taxii_services.message_handlers.poll_fulifllment_request_handlers
        import taxii_services.message_handlers.poll_request_handlers
        import taxii_services.message_handlers.subscription_request_handlers