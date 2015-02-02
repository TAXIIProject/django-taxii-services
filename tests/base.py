# Copyright (c) 2015, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from django.conf import settings
from django.test import TestCase

from libtaxii.constants import VID_TAXII_SERVICES_10, VID_TAXII_SERVICES_11
import libtaxii.messages_10 as tm10
import libtaxii.messages_11 as tm11

from .constants import (TAXII_10_HTTP_Headers, TAXII_10_HTTPS_Headers,
                        TAXII_11_HTTP_Headers, TAXII_11_HTTPS_Headers)
from .helpers import add_basics, make_request, get_message_from_client_response


class DJTTestCase(TestCase):
    """A base class for django-taxii-services test cases."""

    # By default, use TAXII 1.1. Test case subclasses can override this.
    taxii_version = VID_TAXII_SERVICES_11

    def setUp(self):
        settings.DEBUG = True
        add_basics()

    # TODO: Remove this once everything uses get() and post()
    def make_request(self, **kwargs):
        make_request(**kwargs)

    def _get_headers(self, taxii_version, secure):
        """Get default headers for a TAXII version/protocol combination"""

        # NOTE: We use the TAXII Services version as a proxy for both the
        # services version and the message binding version.

        # TODO: Should we add tests for strange combinations of
        # Services/Messages versions?

        if not taxii_version:
            taxii_version = self.taxii_version

        # Creates a copy of the dictionary to return.
        if taxii_version == VID_TAXII_SERVICES_11:
            if secure:
                return dict(TAXII_11_HTTPS_Headers)
            else:
                return dict(TAXII_11_HTTP_Headers)

        elif taxii_version == VID_TAXII_SERVICES_10:
            if secure:
                return dict(TAXII_10_HTTPS_Headers)
            else:
                return dict(TAXII_10_HTTP_Headers)
        else:
            msg = "Unsupported TAXII Services Version: %s" % taxii_version
            raise ValueError(msg)

    def get(self, path, headers=None, taxii_version=None, secure=False):
        """Perform a GET request.

        If `headers` are not provided, default headers will be chosen based on
        the `taxii_version` and `secure` arguments.

        Args:
            path (str): the URL to GET
            headers (dict): HTTP headers
            taxii_version (str): VID_TAXII_XML_10 or VID_TAXII_XML_11
            secure (bool): Use HTTPS headers if True, otherwise use HTTP
                headers.

        Returns:
            Django test client Response object
        """
        if headers is None:
            headers = self._get_headers(taxii_version, secure)
        return self.client.get(path, **headers)

    def post(self, path, data, headers=None, taxii_version=None, secure=False):
        """Perform a POST request.

        If `headers` are not provided, default headers will be chosen based on
        the `taxii_version` and `secure` arguments.

        Args:
            path (str): the URL to GET
            data (str): the payload of the HTTP request
            headers (dict): HTTP headers
            taxii_version (str): VID_TAXII_XML_10 or VID_TAXII_XML_11
            secure (bool): Use HTTPS headers if True, otherwise use HTTP
                headers.

        Returns:
            Django test client Response object
        """
        if headers is None:
            headers = self._get_headers(taxii_version, secure)
        return self.client.post(path, data, content_type='application/xml',
                                **headers)

    def _parse_taxii_response(self, response):
        """Convert an HTTPResponse into a TAXII Message."""
        #TODO: Actually check the in_reponse_to.
        return get_message_from_client_response(response, '0')

    def assertStatusMessage(self, response, status=None):
        """Verify that the response contains a TAXII Status with the specified
        status.

        Args:
            response (Django TestClient Response):
            status (str): TAXII Status message
        """
        taxii_message = self._parse_taxii_response(response)
        # TODO: check the correct TAXII version of response based on the
        # request.
        status_message_classes = (tm11.StatusMessage, tm10.StatusMessage)
        self.assertIsInstance(taxii_message, status_message_classes)
        if status:
            self.assertEqual(status, taxii_message.status_type)

    def assertDiscoveryResponse(self, response):
        """Verify that the response contains a TAXII Discovery Response.

        Args:
            response (Django TestClient Response):
        """
        taxii_message = self._parse_taxii_response(response)
        # TODO: check the correct TAXII version of response based on the
        # request.
        discovery_response = (tm11.DiscoveryResponse, tm10.DiscoveryResponse)
        self.assertIsInstance(taxii_message, discovery_response)
