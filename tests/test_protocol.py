# Copyright (c) 2015, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from libtaxii import messages_10 as tm10
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
        # TODO: Why do we actually need a payload to return a 404? Shouldn't an
        # empty message to a non-existent URL also return a 404?
        inbox_msg = tm11.InboxMessage(tm11.generate_message_id())
        path = '/Services/PathThatShouldNotWork/'

        response = self.post(path, inbox_msg.to_xml())
        self.assertEqual(404, response.status_code)
        # TODO: test the actual content of the 404

    def test_get_request(self):
        """
        Sending a GET request to the server should result in a BAD_MESSAGE.
        """
        response = self.get(DISCOVERY_PATH)
        self.assertStatusMessage(response, ST_BAD_MESSAGE)

    def test_malformed_xml(self):
        """
        Send an XML fragment to the server
        """
        body = '<malformed_xml>'  # No closing tag.

        response = self.post(DISCOVERY_PATH, body)
        self.assertStatusMessage(response, ST_BAD_MESSAGE)

    def test_schema_invalid_xml(self):
        """
        Send schema-invalid XML
        """
        body = '<valid_xml/>'  # well-formed, but schema-invalid.

        response = self.post(DISCOVERY_PATH, body)
        self.assertStatusMessage(response, ST_BAD_MESSAGE)

    # The next few tests test headers presence/absence
    # and unsupported values

    def test_missing_headers_taxii_11_https(self):
        self._test_missing_headers(VID_TAXII_SERVICES_10, is_secure=True)

    def test_missing_headers_taxii_11_http(self):
        self._test_missing_headers(VID_TAXII_SERVICES_11, is_secure=False)

    def test_missing_headers_taxii_10_https(self):
        self._test_missing_headers(VID_TAXII_SERVICES_10, is_secure=True)

    def test_missing_headers_taxii_10_http(self):
        self._test_missing_headers(VID_TAXII_SERVICES_10, is_secure=False)

    def _test_missing_headers(self, version, is_secure):
        """
        Test requests with:
        - One header missing
        - A bad value for each header
        """

        # TODO: The responses could probably be checked better
        # TODO: This whole thing can probably be done better,
        # but it's probably sufficient for now

        # Get a copy of the expected headers the version/is_secure combination.
        clean_headers = get_headers(version, is_secure)

        # Build a DiscoveryRequest for the correct TAXII version.
        if version == VID_TAXII_SERVICES_11:
            mod = tm11
        else:
            mod = tm10
        body = mod.DiscoveryRequest(mod.generate_message_id()).to_xml()

        # Loop through each of the TAXII headers.
        for header in clean_headers.keys():
            # Make a copy of the header dict (since we're going to modify it)
            headers = dict(clean_headers)

            # Try the bad header value
            headers[header] = 'THIS_IS_A_BAD_VALUE'
            response = self.post(DISCOVERY_PATH, body, headers)

            if header == 'HTTP_ACCEPT':
                self.assertEqual(406, response.status_code, header)
            else:
                self.assertEqual(200, response.status_code, header)

            if header == 'HTTP_X_TAXII_CONTENT_TYPE':
                self.assertStatusMessage(response, ST_BAD_MESSAGE)
            else:
                self.assertStatusMessage(response, ST_FAILURE)

            # TODO: Django will automatically add CONTENT_TYPE to POST
            # requests, so find a better way to test when this header is
            # missing.
            if header == 'CONTENT_TYPE':
                continue

            # Now try without the header
            del headers[header]
            response = self.post(DISCOVERY_PATH, body, headers)

            #TODO: When should these return something other than a 200?
            self.assertEqual(200, response.status_code, header)

            if header in ('HTTP_ACCEPT', 'HTTP_X_TAXII_ACCEPT'):
                self.assertDiscoveryResponse(response)
            elif header == 'HTTP_X_TAXII_CONTENT_TYPE':
                self.assertStatusMessage(response, ST_BAD_MESSAGE)
            else:
                self.assertStatusMessage(response, ST_FAILURE)
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
