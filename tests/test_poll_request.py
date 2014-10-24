# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from django.test import TestCase
from django.conf import settings

from .helpers import *

from datetime import datetime, timedelta
from dateutil.tz import tzutc

def create_poll_w_query(relationship, params, target, collection='default'):

    test = tdq.Test(capability_id=CM_CORE,
                    relationship=relationship,
                    parameters=params)

    criterion = tdq.Criterion(target=target, test=test)
    criteria = tdq.Criteria(OP_AND, criterion=[criterion])
    q = tdq.DefaultQuery(CB_STIX_XML_111, criteria)
    pp = tm11.PollParameters(query=q)
    pr = tm11.PollRequest(message_id=generate_message_id(),
                          collection_name=collection,
                          poll_parameters=pp)

    return pr


class PollRequestTests11(TestCase):

    # Make sure query tests are in here

    def setUp(self):
        settings.DEBUG = True
        add_basics()
        add_poll_service()
        add_test_content(collection='default')

    def test_01(self):
        """
        Test an invalid collection name
        """
        pp = tm11.PollParameters()
        pr = tm11.PollRequest(message_id=generate_message_id(),
                              collection_name='INVALID_COLLECTION_NAME_13820198320',
                              poll_parameters=pp)

        make_request('/test_poll_1/',
                     pr.to_xml(),
                     get_headers(VID_TAXII_SERVICES_11, False),
                     MSG_STATUS_MESSAGE,
                     st=ST_NOT_FOUND,
                     sd_keys=[SD_ITEM])

    def test_02(self):
        """
        Test a begin TS later than an end TS.
        """
        begin_ts = datetime.now(tzutc())
        end_ts = begin_ts - timedelta(days=7)

        pp = tm11.PollParameters()
        pr = tm11.PollRequest(message_id=generate_message_id(),
                              collection_name='default',
                              poll_parameters=pp,
                              exclusive_begin_timestamp_label=begin_ts,
                              inclusive_end_timestamp_label=end_ts)
        make_request('/test_poll_1/',
                     pr.to_xml(),
                     get_headers(VID_TAXII_SERVICES_11, False),
                     MSG_STATUS_MESSAGE)

    def test_03(self):
        """
        Test an invalid subscription ID
        """
        pr = tm11.PollRequest(message_id=generate_message_id(),
                              collection_name='default',
                              subscription_id='IdThatWontWork')
        make_request('/test_poll_1/',
                     pr.to_xml(),
                     get_headers(VID_TAXII_SERVICES_11, False),
                     MSG_STATUS_MESSAGE,
                     st=ST_NOT_FOUND,
                     sd_keys=[SD_ITEM])

    def test_04(self):
        """
        Test a Content Binding ID not supported by the server
        """
        pp = tm11.PollParameters(content_bindings=[tm11.ContentBinding('some_random_binding')])
        pr = tm11.PollRequest(message_id=generate_message_id(),
                              collection_name='default',
                              poll_parameters=pp)
        make_request('/test_poll_1/',
                     pr.to_xml(),
                     get_headers(VID_TAXII_SERVICES_11, False),
                     MSG_STATUS_MESSAGE,
                     st=ST_UNSUPPORTED_CONTENT_BINDING,
                     sd_keys=[SD_SUPPORTED_CONTENT])

    def test_05(self):
        """
        Test a supported Content Binding ID with an unsupported subtype
        """
        pp = tm11.PollParameters(content_bindings=[tm11.ContentBinding(CB_STIX_XML_111, subtype_ids=['FakeSubtype'])])
        pr = tm11.PollRequest(message_id=generate_message_id(),
                              collection_name='default',
                              poll_parameters=pp)
        make_request('/test_poll_1/',
                     pr.to_xml(),
                     get_headers(VID_TAXII_SERVICES_11, False),
                     MSG_STATUS_MESSAGE,
                     st=ST_UNSUPPORTED_CONTENT_BINDING,
                     sd_keys=[SD_SUPPORTED_CONTENT])

    # This test case currently fails and will not be able to pass until either django-taxii-services
    # changes or libtaxii changes.
    # def test_06(self):
        # """
        # Test an unsupported query format
        # """
        # pp = tm11.PollParameters(query=tm11.Query(format_id='unsupported_format_id'))
        # pr = tm11.PollRequest(
        # message_id = generate_message_id(),
        # collection_name = 'default',
        # poll_parameters = pp)
        # msg = self.send_poll_request('/test_poll_1/',
        # VID_TAXII_XML_11, pr, status_type=ST_UNSUPPORTED_QUERY, sd_keys=[SD_SUPPORTED_QUERY])

    # This test won't be valid until Delivery Params are implemented
    # def test_07(self):
        # """
        # Test unsupported delivery parameters - protocol
        # """
        # dp = tm11.DeliveryParameters('protocol_x', 'http://example.com/whatever/', VID_TAXII_XML_11)
        # pp = tm11.PollParameters(delivery_parameters=dp)
        # pr = tm11.PollRequest(
                # message_id = generate_message_id(),
                # collection_name = 'default',
                # poll_parameters = pp)
        # msg = self.send_poll_request('/test_poll_1/',
        # VID_TAXII_XML_11, pr, status_type=ST_UNSUPPORTED_PROTOCOL, sd_keys=[SD_SUPPORTED_PROTOCOL])

    # This test won't be valid until Delivery Params are implemented
    # def test_08(self):
        # """
        # Test unsupported delivery parameters - message_binding
        # """
        # dp = tm11.DeliveryParameters(VID_TAXII_HTTPS_11, 'http://example.com/whatever/', 'message_binding_x')
        # pp = tm11.PollParameters(delivery_parameters=dp)
        # pr = tm11.PollRequest(
                # message_id = generate_message_id(),
                # collection_name = 'default',
                # poll_parameters = pp)
        # msg = self.send_poll_request('/test_poll_1/',
        # VID_TAXII_XML_11, pr, status_tpe=ST_UNSUPPORTED_MESSAGE, sd_keys=[SD_SUPPORTED_MESSAGE])

    def test_09(self):
        """
        Tests that a single PollRequest succeeds.
        """
        pp = tm11.PollParameters()
        pr = tm11.PollRequest(message_id=generate_message_id(),
                              collection_name='default',
                              poll_parameters=pp)
        msg = make_request('/test_poll_1/',
                           pr.to_xml(),
                           get_headers(VID_TAXII_SERVICES_11, False),
                           MSG_POLL_RESPONSE)
        if len(msg.content_blocks) != 5:
            raise ValueError('Got %s CBs' % len(msg.content_blocks))

    def test_10(self):
        """
        Test a query with an unsupported Capability Module
        """
        test = tdq.Test(capability_id='hello',
                        relationship=R_EQUALS,
                        parameters={P_VALUE: 'x', P_MATCH_TYPE: 'case_sensitive_string'})
        tgt = '**'
        criterion = tdq.Criterion(target=tgt, test=test)
        criteria = tdq.Criteria(OP_AND, criterion=[criterion])
        q = tdq.DefaultQuery(CB_STIX_XML_111, criteria)
        pp = tm11.PollParameters(query=q)
        pr = tm11.PollRequest(message_id=generate_message_id(),
                              collection_name='default',
                              poll_parameters=pp)
        msg = make_request('/test_poll_1/',
                           pr.to_xml(),
                           get_headers(VID_TAXII_SERVICES_11, False),
                           MSG_STATUS_MESSAGE,
                           st=ST_UNSUPPORTED_CAPABILITY_MODULE,
                           sd_keys=[SD_CAPABILITY_MODULE])

    def test_12(self):
        """
        Test a query with an invalid target
        """
        test = tdq.Test(capability_id=CM_CORE,
                        relationship=R_EQUALS,
                        parameters={P_VALUE: 'x', P_MATCH_TYPE: 'case_insensitive_string'})
        tgt = 'STIX_Pakkage/**'
        criterion = tdq.Criterion(target=tgt, test=test)
        criteria = tdq.Criteria(OP_AND, criterion=[criterion])
        q = tdq.DefaultQuery(CB_STIX_XML_111, criteria)
        pp = tm11.PollParameters(query=q)
        pr = tm11.PollRequest(message_id=generate_message_id(),
                              collection_name='default',
                              poll_parameters=pp)
        msg = make_request('/test_poll_1/',
                           pr.to_xml(),
                           get_headers(VID_TAXII_SERVICES_11, False),
                           MSG_STATUS_MESSAGE,
                           st=ST_UNSUPPORTED_TARGETING_EXPRESSION)

    def test_13(self):
        """
        Test a query with an unsupported Targeting Expression Vocabulary
        """
        test = tdq.Test(capability_id=CM_CORE,
                        relationship=R_EQUALS,
                        parameters={P_VALUE: 'x', P_MATCH_TYPE: 'case_insensitive_string'})
        tgt = '**'
        criterion = tdq.Criterion(target=tgt, test=test)
        criteria = tdq.Criteria(OP_AND, criterion=[criterion])
        q = tdq.DefaultQuery('SOMETHING_UNSUPPORTED', criteria)
        pp = tm11.PollParameters(query=q)
        pr = tm11.PollRequest(message_id=generate_message_id(),
                              collection_name='default',
                              poll_parameters=pp)
        msg = make_request('/test_poll_1/',
                           pr.to_xml(),
                           get_headers(VID_TAXII_SERVICES_11, False),
                           MSG_STATUS_MESSAGE,
                           st=ST_UNSUPPORTED_TARGETING_EXPRESSION_ID,
                           sd_keys=[SD_TARGETING_EXPRESSION_ID])

    def test_14(self):
        """
        Test a query. Should match just the APT1 report.
        equals / case sensitive
        no wildcards
        """

        tgt = 'STIX_Package/Threat_Actors/Threat_Actor/Identity/' \
              'Specification/PartyName/OrganisationName/SubDivisionName'

        params = {P_VALUE: 'Unit 61398', P_MATCH_TYPE: 'case_sensitive_string'}

        pr = create_poll_w_query(R_EQUALS, params, tgt)

        msg = make_request('/test_poll_1/',
                           pr.to_xml(),
                           get_headers(VID_TAXII_SERVICES_11, False),
                           MSG_POLL_RESPONSE)
        if len(msg.content_blocks) != 1:
            raise ValueError('Got %s CBs' % len(msg.content_blocks))
        id_ = 'threat-actor-d5b62b58-df7c-46b1-a435-4d01945fe21d'
        if id_ not in msg.content_blocks[0].content:
            raise ValueError('string not found in result: ', id_)

    def test_15(self):
        """
        Query - test the equals / case_insensitive_string relationship
                and single-field wildcard
        """

        tgt = 'STIX_Package/STIX_Header/*'
        params = {P_VALUE: 'Example watchlist that contains IP information.',
                  P_MATCH_TYPE: 'case_insensitive_string'}

        pr = create_poll_w_query(R_EQUALS, params, tgt)

        msg = make_request('/test_poll_1/',
                           pr.to_xml(),
                           get_headers(VID_TAXII_SERVICES_11, False),
                           MSG_POLL_RESPONSE)

        if len(msg.content_blocks) != 1:
            raise ValueError('Got %s CBs' % len(msg.content_blocks))

    def test_16(self):
        """
        Query - test equals / number
        no wildcard
        """

        pass

    def test_17(self):
        """
        Query - equals / case_insensitive_string
        naked multi field WC
        """
        tgt = '**'
        value = '10.0.0.0##comma##10.0.0.1##comma##10.0.0.2'
        params = {P_VALUE: value,
                  P_MATCH_TYPE: 'case_insensitive_string'}
        pr = create_poll_w_query(R_EQUALS, params, tgt)
        msg = make_request('/test_poll_1/',
                           pr.to_xml(),
                           get_headers(VID_TAXII_SERVICES_11, False),
                           MSG_POLL_RESPONSE)

        if len(msg.content_blocks) != 1:
            raise ValueError('Got %s CBs' % len(msg.content_blocks))

        if value not in msg.content_blocks[0].content:
            raise ValueError('string not found in result: ', value)

    def test_18(self):
        """
        Query - Not equal case sensitive
        no wildcard
        """
        tgt = 'STIX_Package/STIX_Header/Title'
        value = 'example file watchlist'
        params = {P_VALUE: value,
                  P_MATCH_TYPE: 'case_sensitive_string'}
        pr = create_poll_w_query(R_NOT_EQUALS, params, tgt)
        msg = make_request('/test_poll_1/',
                           pr.to_xml(),
                           get_headers(VID_TAXII_SERVICES_11, False),
                           MSG_POLL_RESPONSE)

        if len(msg.content_blocks) != 5:
            raise ValueError("Incorrect number of content blocks!")

    def test_19(self):
        """
        Query - Not equals case insensitive
        no wildcard
        """
        tgt = 'STIX_Package/STIX_Header/Title'
        value = 'example file watchlist'
        params = {P_VALUE: value,
                  P_MATCH_TYPE: 'case_insensitive_string'}
        pr = create_poll_w_query(R_NOT_EQUALS, params, tgt)
        msg = make_request('/test_poll_1/',
                           pr.to_xml(),
                           get_headers(VID_TAXII_SERVICES_11, False),
                           MSG_POLL_RESPONSE)

        if len(msg.content_blocks) != 4:
            raise ValueError("Incorrect number of content blocks!")

    def test_20(self):
        """
        Query - not equals number
        leading multi-field wildcard
        """
        tgt = '**/@cybox_major_version'
        value = str(2)
        params = {P_VALUE: value,
                  P_MATCH_TYPE: 'number'}
        pr = create_poll_w_query(R_NOT_EQUALS, params, tgt)
        msg = make_request('/test_poll_1/',
                           pr.to_xml(),
                           get_headers(VID_TAXII_SERVICES_11, False),
                           MSG_POLL_RESPONSE)

        cb_len = len(msg.content_blocks)
        if cb_len != 0:
            raise ValueError("Incorrect number of content blocks!", cb_len)

    def test_21(self):
        """
        Query - greater than
        no wildcard
        """
        pass

    def test_22(self):
        """
        Query - greater than or equals
        no wildcard
        """
        pass

    def test_23(self):
        """
        Query - less than
        no wildcard
        """
        pass

    def test_24(self):
        """
        Query - less than or equals
        no wildcard
        """
        pass

    def test_25(self):
        """
        Query - exists
        no wildcard
        """
        pass

    def test_26(self):
        """
        Query - does not exist
        no wildcard
        """
        pass

    def test_27(self):
        """
        Query - begins with case sensitive
        no wildcard
        """
        pass

    def test_28(self):
        """
        Query - begins with case insensitive
        no wildcard
        """
        pass

    def test_29(self):
        """
        Query - contains case sensitive
        no wildcard
        """
        pass

    def test_30(self):
        """
        Query - contains case insensitive
        no wildcard
        """
        pass

    def test_31(self):
        """
        Query - ends with case sensitive
        no wildcard
        """
        pass

    def test_32(self):
        """
        Query - ends with case insensitive
        no wildcard
        """
        pass


class PollRequestTests10(TestCase):

    def setUp(self):
        settings.DEBUG = True
        add_basics()
        add_poll_service()
        add_test_content(collection='default')

    def test_01(self):
        """
        Test an invalid collection name
        """
        pr = tm10.PollRequest(message_id=generate_message_id(),
                              feed_name='INVALID_COLLECTION_NAME_13820198320')

        make_request('/test_poll_1/',
                     pr.to_xml(),
                     get_headers(VID_TAXII_SERVICES_10, False),
                     MSG_STATUS_MESSAGE,
                     st=ST_NOT_FOUND,
                     sd_keys=[SD_ITEM])

    def test_02(self):
        """
        Test a correct poll request
        """

        pr = tm10.PollRequest(message_id=generate_message_id(),
                              feed_name='default')
        msg = make_request('/test_poll_1/',
                           pr.to_xml(),
                           get_headers(VID_TAXII_SERVICES_10, False),
                           MSG_POLL_RESPONSE)

        if len(msg.content_blocks) != 5:
            raise ValueError("Expected 5 content blocks, got %s" % len(msg.content_blocks))