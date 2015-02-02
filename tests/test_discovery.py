# Copyright (c) 2015, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from django.test import TestCase
from django.conf import settings

from libtaxii.constants import VID_TAXII_SERVICES_10, VID_TAXII_SERVICES_11
from libtaxii.constants import ST_BAD_MESSAGE
import libtaxii.messages_10 as tm10
import libtaxii.messages_11 as tm11

from .base import DJTTestCase
from .constants import DISCOVERY_PATH
from .helpers import add_discovery_service


class DiscoveryTests11(DJTTestCase):

    def setUp(self):
        super(DiscoveryTests11, self).setUp()
        add_discovery_service()

    def test_discovery_exchange(self):
        """Send a discovery request, look to get a discovery response back."""
        req = tm11.DiscoveryRequest(tm11.generate_message_id())
        response = self.post(DISCOVERY_PATH, req.to_xml())

        self.assertDiscoveryResponse(response)

    def test_discovery_message_get(self):
        """Ensure you get a BAD_MESSAGE when issuing a GET request."""

        response = self.get(DISCOVERY_PATH)
        self.assertStatusMessage(response, ST_BAD_MESSAGE)

    def test_discovery_message_post_empty(self):
        """Ensure you get a BAD_MESSAGE when issuing an empty POST request."""

        response = self.post(DISCOVERY_PATH, "")
        self.assertStatusMessage(response, ST_BAD_MESSAGE)


class DiscoveryTests10(DJTTestCase):

    taxii_version = VID_TAXII_SERVICES_10

    def setUp(self):
        super(DiscoveryTests10, self).setUp()
        add_discovery_service()

    def test_discovery_exchange(self):
        """Send a discovery request, look to get a discovery response back."""
        req = tm10.DiscoveryRequest(tm10.generate_message_id())
        response = self.post(DISCOVERY_PATH, req.to_xml())

        self.assertDiscoveryResponse(response)
