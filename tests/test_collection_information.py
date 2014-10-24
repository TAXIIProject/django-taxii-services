# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from django.test import TestCase
from django.conf import settings

from helpers import *

class CollectionInformationTests11(TestCase):

    def setUp(self):
        settings.DEBUG = True
        add_basics()
        add_collection_service()

    def test_01(self):
        """
        Send a collection information request, look to get a collection information response back
        """
        cir = tm11.CollectionInformationRequest(generate_message_id())
        make_request(COLLECTION_PATH,
                     cir.to_xml(),
                     get_headers(VID_TAXII_SERVICES_11, False),
                     MSG_COLLECTION_INFORMATION_RESPONSE)


class FeedInformationTests10(TestCase):

    def setUp(self):
        settings.DEBUG = True
        add_basics()
        add_collection_service()

    def test_01(self):
        """
        Send a feed information request, look to get a feed information response back
        """

        fir = tm10.FeedInformationRequest(generate_message_id())
        make_request(COLLECTION_PATH,
                     fir.to_xml(),
                     get_headers(VID_TAXII_SERVICES_10, False),
                     MSG_FEED_INFORMATION_RESPONSE)
