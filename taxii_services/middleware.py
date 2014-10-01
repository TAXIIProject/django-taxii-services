# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

import handlers
from .exceptions import StatusMessageException

from libtaxii.constants import *

from django.http import HttpResponseServerError, HttpResponse
import logging
from django.conf import settings


class StatusMessageExceptionMiddleware(object):
    """
    If a StatusMessageException is passed in, this class will
    create a StatusMessage response. Otherwise, this class will
    pass on the Exception to the next Middleware object
    """
    def process_exception(self, request, exception):
        """
        Arguments:
            request - a Django request
            exception - An Exception
        Returns:
            None if the exception is not a StatusMessageException
            an HttpResponseTaxii if it is
        """

        if not isinstance(exception, StatusMessageException):
            return None  # This class only handles StatusMessageExceptions

        version = None

        a = request.META.get('HTTP_ACCEPT', None)
        if a:
            a = a.lower()
        if a not in ('application/xml', None):  # This application doesn't know how to handle this
            # print "accept: ", a
            r = HttpResponse()
            r.status_code = 406  # Unacceptable
            return r

        xta = request.META.get('HTTP_X_TAXII_ACCEPT', None)
        if xta is None:  # Can respond with whatever we want. try to use the X-TAXII-Content-Type header to pick
            xtct = request.META.get('HTTP_X_TAXII_CONTENT_TYPE', None)
            if xtct == VID_TAXII_XML_10:
                sm = exception.to_status_message_10()
                version = VID_TAXII_SERVICES_10
            else:  # Well, we tried - use TAXII XML 1.1 as a default
                sm = exception.to_status_message_11()
                version = VID_TAXII_SERVICES_11
        elif xta == VID_TAXII_XML_10:
            sm = exception.to_status_message_10()
            version = VID_TAXII_SERVICES_10
        elif xta == VID_TAXII_XML_11:
            sm = exception.to_status_message_11()
            version = VID_TAXII_SERVICES_11
        else:
            # For now, just pretend X-TAXII-Accept was TAXII 1.1
            # Not 100% sure what the right response is... HTTP Unacceptable?
            # Squash the exception argument and create a new one for unknown HTTP Accept?
            sm = exception.to_status_message_11()
            version = VID_TAXII_SERVICES_11

        response_headers = handlers.get_headers(version, request.is_secure())
        return handlers.HttpResponseTaxii(sm.to_xml(pretty_print=True), response_headers)
