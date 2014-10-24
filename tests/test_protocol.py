# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from django.test import TestCase
from django.conf import settings

from .helpers import *


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
