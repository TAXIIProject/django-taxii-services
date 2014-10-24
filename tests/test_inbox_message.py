# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from django.test import TestCase
from django.conf import settings

from .helpers import *


class InboxTests11(TestCase):
    """
    Test various aspects of the
    taxii_handlers.InboxMessage11Handler
    """

    def setUp(self):
        settings.DEBUG = True
        add_basics()
        add_inbox_service()

    def test_01(self):
        """
        Send a message to test_inbox_1 with a valid destination collection name
        """
        inbox = tm11.InboxMessage(generate_message_id(), destination_collection_names=['default'])
        make_request('/test_inbox_1/', inbox.to_xml(), get_headers(VID_TAXII_SERVICES_11, False), MSG_STATUS_MESSAGE, ST_SUCCESS)

    def test_02(self):
        """
        Send a message to test_inbox_1 with an invalid destination collection name
        """
        inbox = tm11.InboxMessage(generate_message_id(), destination_collection_names=['default_INVALID'])
        make_request('/test_inbox_1/', inbox.to_xml(), get_headers(VID_TAXII_SERVICES_11, False), MSG_STATUS_MESSAGE, ST_NOT_FOUND, sd_keys=[SD_ITEM])

    def test_03(self):
        """
        Send a message to test_inbox_1 without a destination collection name
        """
        inbox = tm11.InboxMessage(generate_message_id())
        make_request('/test_inbox_1/',
                     inbox.to_xml(),
                     get_headers(VID_TAXII_SERVICES_11, False),
                     MSG_STATUS_MESSAGE,
                     st=ST_DESTINATION_COLLECTION_ERROR,
                     sd_keys=[SD_ACCEPTABLE_DESTINATION])

    def test_04(self):
        """
        Send a message to test_inbox_2 with a valid destination collection name
        """
        inbox = tm11.InboxMessage(generate_message_id(), destination_collection_names=['default'])
        make_request('/test_inbox_2/',
                     inbox.to_xml(),
                     get_headers(VID_TAXII_SERVICES_11, False),
                     MSG_STATUS_MESSAGE,
                     st=ST_SUCCESS)

    def test_05(self):
        """
        Send a message to test_inbox_2 with an invalid destination collection name
        """
        inbox = tm11.InboxMessage(generate_message_id(), destination_collection_names=['default_INVALID'])
        make_request('/test_inbox_2/',
                     inbox.to_xml(),
                     get_headers(VID_TAXII_SERVICES_11, False),
                     MSG_STATUS_MESSAGE,
                     st=ST_NOT_FOUND,
                     sd_keys=[SD_ITEM])

    def test_06(self):
        """
        Send a message to test_inbox_2 without a destination collection name
        """
        inbox = tm11.InboxMessage(generate_message_id())
        make_request('/test_inbox_2/',
                     inbox.to_xml(),
                     get_headers(VID_TAXII_SERVICES_11, False),
                     MSG_STATUS_MESSAGE,
                     st=ST_SUCCESS)

    def test_08(self):
        """
        Send a message to test_inbox_3 with a destination collection name
        """
        inbox = tm11.InboxMessage(generate_message_id(), destination_collection_names=['default'])
        make_request('/test_inbox_3/',
                     inbox.to_xml(),
                     get_headers(VID_TAXII_SERVICES_11, False),
                     MSG_STATUS_MESSAGE,
                     st=ST_DESTINATION_COLLECTION_ERROR)

    def test_09(self):
        """
        Send a message to test_inbox_3 without a destination collection name
        """
        inbox = tm11.InboxMessage(generate_message_id())
        make_request('/test_inbox_3/',
                     inbox.to_xml(),
                     get_headers(VID_TAXII_SERVICES_11, False),
                     MSG_STATUS_MESSAGE,
                     st=ST_SUCCESS)

    def test_10(self):
        """
        Send an Inbox message with a Record Count
        """
        inbox = tm11.InboxMessage(generate_message_id(), destination_collection_names=['default'])
        inbox.record_count = tm11.RecordCount(0, True)
        make_request('/test_inbox_1/',
                     inbox.to_xml(),
                     get_headers(VID_TAXII_SERVICES_11, False),
                     MSG_STATUS_MESSAGE,
                     st=ST_SUCCESS)

    def test_11(self):
        """
        Replicate the InboxClientScript
        """
        from libtaxii.scripts.inbox_client import InboxClient11Script
        stix_xml = InboxClient11Script.stix_watchlist

        cb = tm11.ContentBlock(tm11.ContentBinding(CB_STIX_XML_111), stix_xml)

        inbox = tm11.InboxMessage(message_id=generate_message_id(),
                                  destination_collection_names=['default'],
                                  content_blocks=[cb])

        make_request('/test_inbox_1/',
                     inbox.to_xml(),
                     get_headers(VID_TAXII_SERVICES_11, False),
                     MSG_STATUS_MESSAGE,
                     st=ST_SUCCESS)


class InboxTests10(TestCase):

    def setUp(self):
        settings.DEBUG = True
        add_basics()
        add_inbox_service()

    def test_01(self):
        """
        Send a TAXII 1.0 Inbox Message to /test_inbox_1/. Will always
        fail because /test_inbox_1/ requires a DCN and TAXII 1.0 cannot specify that.
        """
        inbox = tm10.InboxMessage(generate_message_id())
        make_request('/test_inbox_1/',
                     inbox.to_xml(),
                     get_headers(VID_TAXII_SERVICES_10, False),
                     MSG_STATUS_MESSAGE,
                     st=ST_DESTINATION_COLLECTION_ERROR)  # TODO: Is this the right behavior? it's kind of a TAXII 1.1 error for a TAXII 1.0 request but not really

    def test_02(self):
        """
        Send a TAXII 1.0 Inbox Message to /test_inbox_2/
        """
        inbox = tm10.InboxMessage(generate_message_id())
        make_request('/test_inbox_2/',
                     inbox.to_xml(),
                     get_headers(VID_TAXII_SERVICES_10, False),
                     MSG_STATUS_MESSAGE,
                     st=ST_SUCCESS)

    def test_03(self):
        """
        Send a TAXII 1.0 Inbox Message to /test_inbox_3/
        """
        inbox = tm10.InboxMessage(generate_message_id())
        make_request('/test_inbox_3/',
                     inbox.to_xml(),
                     get_headers(VID_TAXII_SERVICES_10, False),
                     MSG_STATUS_MESSAGE,
                     st=ST_SUCCESS)

    def test_04(self):
        """
        Send a TAXII 1.0 Inbox Message to /test_inbox_3/ with two content blocks
        """
        cb1 = tm10.ContentBlock(content_binding=CB_STIX_XML_111, content=stix_watchlist_111)
        cb2 = tm10.ContentBlock(content_binding=CB_STIX_XML_111, content=stix_watchlist_111)

        inbox = tm10.InboxMessage(message_id=generate_message_id(),
                                  content_blocks=[cb1, cb2])
        make_request('/test_inbox_3/',
                     inbox.to_xml(),
                     get_headers(VID_TAXII_SERVICES_10, False),
                     MSG_STATUS_MESSAGE,
                     st=ST_SUCCESS)
