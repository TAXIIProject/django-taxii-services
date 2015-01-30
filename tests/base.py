# Copyright (c) 2015, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from django.conf import settings
from django.test import TestCase
import libtaxii.messages_10 as tm10
import libtaxii.messages_11 as tm11

from .constants import TAXII_11_HTTP_Headers
from .helpers import add_basics, make_request, get_message_from_client_response


class DJTTestCase(TestCase):
    """A base class for django-taxii-services test cases."""

    def setUp(self):
        settings.DEBUG = True
        add_basics()

    def make_request(self, **kwargs):
        make_request(**kwargs)

    def get(self, path, headers=None):
        """Perform a GET request.

        If headers are not provided, the default TAXII 1.1 headers will be
        used.

        Args:
            path (str): the URL to GET
            headers (dict): HTTP headers

        Returns:
            Django test client Response object
        """
        if headers is None:
            # create copy of dictionary
            headers = dict(TAXII_11_HTTP_Headers)
        return self.client.get(path, **headers)

    def post(self, path, data, headers=None):
        """Perform a POST request.

        If headers are not provided, the default TAXII 1.1 headers will be
        used.

        Args:
            path (str): the URL to GET
            body (str): the payload of the HTTP request
            headers (dict): HTTP headers

        Returns:
            Django test client Response object
        """
        if headers is None:
            # create copy of dictionary
            headers = dict(TAXII_11_HTTP_Headers)
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
            self.assertEqual(status, taxii_message.status_type,
                    taxii_message.message)

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
