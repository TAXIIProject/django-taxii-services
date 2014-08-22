# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

import logging
from django.http import HttpResponseServerError

from libtaxii.constants import *

import handlers
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
        
        version = None
        
        a = request.META.get('HTTP_ACCEPT', None)
        if a not in ('application/xml', None): # This application doesn't know how to handle this
            return HttpResponse(status_code=406) # Unacceptable
        
        xta = request.META.get('HTTP_X_TAXII_ACCEPT', None)
        if xta is None: # Can respond with whatever we want. try to use the X-TAXII-Content-Type header to pick
            xtct = request.META.get('HTTP_X_TAXII_CONTENT_TYPE', None)
            if xtct == VID_TAXII_XML_10:
                sm = exception.get_status_message_10()
                version = VID_TAXII_SERVICES_10
            else:#Well, we tried - use TAXII XML 1.1 as a default
                sm = exception.get_status_message_11()
                version = VID_TAXII_SERVICES_11
        elif xta == VID_TAXII_XML_10:
            sm = exception.get_status_message_10()
            version = VID_TAXII_SERVICES_10
        elif xta == VID_TAXII_XML_11:
            sm = exception.get_status_message_11()
            version = VID_TAXII_SERVICES_11
        else:
            #TODO: Not sure what to return here. Need to dig into this a bit to find out
            raise ValueError("Unknown X-TAXII-Accept value: %s" % xta)
        
        response_headers = handlers.get_headers(version, request.is_secure())
        return handlers.HttpResponseTaxii(sm.to_xml(pretty_print=True), response_headers)
