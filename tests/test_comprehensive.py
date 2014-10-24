# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from django.test import TestCase, Client
from django.conf import settings

from .helpers import *

from datetime import datetime, timedelta
from dateutil.tz import tzutc


def make_request(path='/', post_data=None, header_dict=None,
                 response_msg_type=None, st=None, sd_keys=None, expected_code=200):
    """
    Makes a TAXII Request. Allows for a lot of munging of the request to test various aspects of the message

    :param path:
    :param post_data:
    :param header_dict:
    :param response_msg_type: Expected Response message type (e.g., MSG_STATUS_MESSAGE)
    :param st: Expected status type (e.g., ST_SUCCESS). Only applies if response_msg_type == MSG_STATUS_MESSAGE
    :param sd_keys: Expected status details (e.g., SD_ITEM). Only applies if response_msg_type == MSG_STATUS_MESSSAGE
    :param expected_code: Expected HTTP response code (defaults to 200)
    :return: A TAXII Message
    """
    c = Client()

    if not header_dict:
        # Use TAXII 1.1 HTTP Headers
        header_dict = get_headers(VID_TAXII_SERVICES_11, is_secure=False)
        header_dict['Accept'] = 'application/xml'
        header_dict['X-TAXII-Accept'] = VID_TAXII_XML_11

    if post_data:  # Make a POST
        resp = c.post(path, data=post_data, content_type='application/xml', **header_dict)
    else:  # Make a GET
        resp = c.get(path, **header_dict)

    if resp.status_code != expected_code:
        msg = resp.content
        raise ValueError("Response code was not %s. Was: %s.\r\n%s" %
                         (str(expected_code), str(resp.status_code), msg))

    msg = get_message_from_client_response(resp, '0')
    msg_xml = msg.to_xml(pretty_print=True)
    if len(msg_xml) > 4096:
        msg_xml = "MESSAGE WAS TOO BIG TO PRINT: %s" % len(msg_xml)

    if (response_msg_type and
        msg.message_type != response_msg_type):
        raise ValueError("Incorrect message type sent in response. Expected: %s. Got: %s.\r\n%s" %
                         (response_msg_type, msg.message_type, msg_xml))

    if st:
        if msg.status_type != st:
            raise ValueError("Incorrect status type. Expected %s got %s)\r\n%s" %
                             (st, msg.status_type, msg_xml))

    if sd_keys:
        for key in sd_keys:
            if key not in msg.status_detail:
                raise ValueError("SD Key not present: %s\r\n%s" %
                                 (key, msg_xml))

    return msg


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


class ProtocolTests(TestCase):
    """
    Tests the implementation of the protocol side,
    making sure failure scenarios fail and
    success cases succeed.
    """

    def setUp(self):
        settings.DEBUG = True
        add_basics()
        add_discovery_service()

    def test_01(self):
        """
        Sends an Inbox Message to an invalid URL.
        Should get back a 404
        """
        inbox_message = tm11.InboxMessage(generate_message_id())
        make_request(post_data=inbox_message.to_xml(), path='/Services/PathThatShouldNotWork/', expected_code=404)

    def test_02(self):
        """
        Tests sending a GET request to the server. Should result in a BAD MESSAGE
        """
        # Lack of post_data makes it a GET request
        make_request(path=DISCOVERY_PATH)

    def test_03(self):
        """
        Send an XML fragment to the server
        """
        make_request(path=DISCOVERY_PATH,
                     post_data='<XML_that_is_not_well_formed>',
                     response_msg_type=MSG_STATUS_MESSAGE)

    def test_04(self):
        """
        Send schema-invalid XML
        """
        make_request(path=DISCOVERY_PATH,
                     post_data='<well_formed_schema_invalid_xml/>',
                     response_msg_type=MSG_STATUS_MESSAGE)

    # The next few tests test headers presence/absence
    # and unsupported values

    def test_05(self):
        """
        For each set of TAXII Headers, test the following:
        - One header missing
        - A bad value for each header
        - Other permutations in the future?
        """

        # TODO: The responses could probably be checked better
        # TODO: This whole thing can probably be done better,
        # but it's probably sufficient for now

        # Tuples of services version / is_secure
        http = False
        https = True
        tuples = ((VID_TAXII_SERVICES_11, https),
                  (VID_TAXII_SERVICES_11, http),
                  (VID_TAXII_SERVICES_10, https),
                  (VID_TAXII_SERVICES_10, http))

        # Create a list of headers for mangling header values
        tmp_headers = get_headers(tuples[0][0], tuples[0][1])
        header_list = tmp_headers.keys()

        # Iterate over every TAXII Service version / is_secure value,
        # over every header, and try that header with a bad value
        # and not present
        for tuple_ in tuples:
            if tuple_[0] == VID_TAXII_SERVICES_11:
                disc_req_xml = tm11.DiscoveryRequest(generate_message_id()).to_xml()
            else:
                disc_req_xml = tm10.DiscoveryRequest(generate_message_id()).to_xml()
            for header in header_list:
                expected_code = 200 if header != 'HTTP_ACCEPT' else 406
                r_msg = MSG_STATUS_MESSAGE
                request_headers = get_headers(tuple_[0], tuple_[1])

                # Try the bad header value
                request_headers[header] = 'THIS_IS_A_BAD_VALUE'

                make_request(post_data=disc_req_xml,
                             path=DISCOVERY_PATH,
                             response_msg_type=r_msg,
                             header_dict=request_headers,
                             expected_code=expected_code)

                # Now try without the header
                if header in ('HTTP_ACCEPT', 'HTTP_X_TAXII_ACCEPT'):  # These headers can be missing
                    expected_code = 200
                    r_msg = MSG_DISCOVERY_RESPONSE
                del request_headers[header]
                make_request(post_data=disc_req_xml,
                             path=DISCOVERY_PATH,
                             response_msg_type=r_msg,
                             header_dict=request_headers,
                             expected_code=expected_code)
                # everything OK, now on to the next one!
        pass

    def test_06(self):
        """
        Send a discovery message mismatched with the message binding ID
        """
        # TODO: Write this
        pass

    def test_07(self):
        """
        Send a request mismatched with the protocol binding ID
        """
        # TODO: Write this
        pass

    def test_08(self):
        """
        Send a request mismatched with the services version
        """
        # TODO: Write this
        pass

    def test_09(self):
        """
        Send a TAXII 1.0 message with an X-TAXII-Accept value of TAXII 1.1
        """
        # TODO: Write this
        pass

    def test_10(self):
        """
        Send a TAXII 1.1 message with an X-TAXII-Accept value of TAXII 1.0
        """
        # TODO: Write this
        pass


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


class PollFulfillmentTests11(TestCase):
    pass


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


class SubscriptionTests11(TestCase):
    # Make sure to test query in here
    pass


class SubscriptionTests10(TestCase):
    pass


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
