# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from django.test import TestCase
from django.conf import settings

from .helpers import *

class DiscoveryTests11(TestCase):
    def setUp(self):
        settings.DEBUG = True
        add_basics()
        add_discovery_service()

    def test_01(self):
        """
        Send a discovery request, look to get a discovery response back
        """

        dr = tm11.DiscoveryRequest(generate_message_id())
        make_request(DISCOVERY_PATH,
                     dr.to_xml(),
                     get_headers(VID_TAXII_SERVICES_11, False),
                     MSG_DISCOVERY_RESPONSE)


class DiscoveryTests10(TestCase):
    def setUp(self):
        settings.DEBUG = True
        add_basics()
        add_discovery_service()

    def test_01(self):
        """
        Send a discovery request, look to get a discovery response back
        """

        dr = tm10.DiscoveryRequest(generate_message_id())
        make_request(DISCOVERY_PATH,
                     dr.to_xml(),
                     get_headers(VID_TAXII_SERVICES_10, False),
                     MSG_DISCOVERY_RESPONSE)