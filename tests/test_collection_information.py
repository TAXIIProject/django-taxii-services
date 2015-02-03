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

    def test_issue_28(self):
        """
        Tests issue 28. https://github.com/TAXIIProject/django-taxii-services/issues/28

        :return:
        """

        # Add a disabled Inbox Service
        add_inbox_service()
        for inbox in InboxService.objects.all():
            inbox.enabled = False
            inbox.save()

        cir = tm11.CollectionInformationRequest(generate_message_id())
        msg = make_request(COLLECTION_PATH,
                           cir.to_xml(),
                           get_headers(VID_TAXII_SERVICES_11, False),
                           MSG_COLLECTION_INFORMATION_RESPONSE)
        if len(msg.collection_informations) != 1:
            raise ValueError("Expected 1 collection in response, got %s" % len(msg.collection_informations))
        if len(msg.collection_informations[0].receiving_inbox_services) > 0:
            raise ValueError("Expected 0 Receiving Inbox Services, got %s" %
                             len(msg.collection_informations[0].receiving_inbox_services))
        #print msg.to_xml(pretty_print=True)


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
