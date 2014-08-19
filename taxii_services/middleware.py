# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

import logging
from django.http import HttpResponseServerError

import libtaxii as t
import libtaxii.messages_11 as tm11
import libtaxii.messages_10 as tm10

from taxii_services.utils import response_utils
from exceptions import StatusMessageException
import settings
import traceback

class StatusMessageExceptionMiddleware(object):
    """
    If a StatusMessageException is passed in, this class will
    create a StatusMessage response. Otherwise, this class will
    pass on the Exception to the next Middleware object
    """
    def process_exception(self, request, exception):
        if not isinstance(exception, StatusMessageException):
            return None # This class only handles StatusMessageExceptions
        
        a = request.META.get('HTTP_ACCEPT', None)
        if a not in ('application/xml', None): # This application doesn't know how to handle this
            return HttpResponse(status_code=406) # Unacceptable
        
        xta = request.META.get('HTTP_X_TAXII_ACCEPT', None)
        if xta is None: # Can respond with whatever we want, try to use the X-TAXII-Content-Type header to pick
            xtct = request.META.get('HTTP_X_TAXII_CONTENT_TYPE', None)
            if xtct in (t.VID_TAXII_XML_11, t.VID_TAXII_XML_10):
                xta = xtct
            else:#Well, we tried - use TAXII XML 1.1 as a default
                xta = t.VID_TAXII_XML_11
        
        if xta in (t.VID_TAXII_XML_11, t.VID_TAXII_XML_10):
            sm = exception.get_status_message(xta)
        else:
            raise Exception("Unknown X-TAXII-Accept value: %s" % xta)
        
        response_headers = response_utils.get_headers(xta, request.is_secure())
        return response_utils.create_taxii_response(sm.to_xml(pretty_print=True), response_headers)