# Copyright (c) 2015, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from libtaxii import messages_11 as tm11

from .base import DJTTestCase
from .constants import *
from .helpers import add_discovery_service, get_headers, DISCOVERY_PATH


class ProtocolTests(DJTTestCase):
    """
    Tests the implementation of the protocol side,
    making sure failure scenarios fail and
    success cases succeed.
    """

    def setUp(self):
        super(ProtocolTests, self).setUp()
        add_discovery_service()

    def test_nonexistent_service_url(self):
        """
        Sends an Inbox Message to an invalid URL.
        Should get back a 404.
        """
        inbox_message = tm11.InboxMessage(tm11.generate_message_id())
        self.make_request(post_data=inbox_message.to_xml(),
                          path='/Services/PathThatShouldNotWork/',
                          expected_code=404)

    def test_get_request(self):
        """
        Tests sending a GET request to the server. Should result in a BAD MESSAGE
        """
        # Lack of post_data makes it a GET request
        self.make_request(path=DISCOVERY_PATH)

    def test_malformed_xml(self):
        """
        Send an XML fragment to the server
        """
        self.make_request(path=DISCOVERY_PATH,
                          post_data='<XML_that_is_not_well_formed>',
                          response_msg_type=MSG_STATUS_MESSAGE)

    def test_schema_invalid_xml(self):
        """
        Send schema-invalid XML
        """
        self.make_request(path=DISCOVERY_PATH,
                          post_data='<well_formed_schema_invalid_xml/>',
                          response_msg_type=MSG_STATUS_MESSAGE)

    # The next few tests test headers presence/absence
    # and unsupported values

    def test_missing_headers(self):
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
                disc_req_xml = tm11.DiscoveryRequest(tm11.generate_message_id()).to_xml()
            else:
                disc_req_xml = tm10.DiscoveryRequest(tm10.generate_message_id()).to_xml()
            for header in header_list:
                expected_code = 200 if header != 'HTTP_ACCEPT' else 406
                r_msg = MSG_STATUS_MESSAGE
                request_headers = get_headers(tuple_[0], tuple_[1])

                # Try the bad header value
                request_headers[header] = 'THIS_IS_A_BAD_VALUE'

                self.make_request(post_data=disc_req_xml,
                                  path=DISCOVERY_PATH,
                                  response_msg_type=r_msg,
                                  header_dict=request_headers,
                                  expected_code=expected_code)

                # Now try without the header
                if header in ('HTTP_ACCEPT', 'HTTP_X_TAXII_ACCEPT'):  # These headers can be missing
                    expected_code = 200
                    r_msg = MSG_DISCOVERY_RESPONSE
                del request_headers[header]
                self.make_request(post_data=disc_req_xml,
                                  path=DISCOVERY_PATH,
                                  response_msg_type=r_msg,
                                  header_dict=request_headers,
                                  expected_code=expected_code)
                # everything OK, now on to the next one!

    def test_mismatched_message_binding_id(self):
        """
        Send a discovery message mismatched with the message binding ID
        """
        # TODO: Write this
        pass

    def test_mismatched_protocol_binding_id(self):
        """
        Send a request mismatched with the protocol binding ID
        """
        # TODO: Write this
        pass

    def test_mismatched_services_version(self):
        """
        Send a request mismatched with the services version
        """
        # TODO: Write this
        pass

    def test_mismatched_taxii_version(self):
        """
        Send a TAXII 1.0 message with an X-TAXII-Accept value of TAXII 1.1
        """
        # TODO: Write this
        pass

    def test_mismatched_taxii_version2(self):
        """
        Send a TAXII 1.1 message with an X-TAXII-Accept value of TAXII 1.0
        """
        # TODO: Write this
        pass
