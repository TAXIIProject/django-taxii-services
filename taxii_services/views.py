# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

#This only contains basic views for basic TAXII Services

from django.views.decorators.csrf import csrf_exempt
import handlers
from utils import request_utils, response_utils
from exceptions import StatusMessageException
from libtaxii.constants import *
from libtaxii.validation import SchemaValidator
import libtaxii.messages_11 as tm11
import libtaxii.messages_10 as tm10
from lxml.etree import XMLSyntaxError

@csrf_exempt
def service_router(request, path, do_validate=True):
    """
    Takes in a request, path, and TAXII Message,
    and routes the taxii_message to the Service Handler.
    """
    
    if request.method != 'POST':
        raise StatusMessageException('0', ST_BAD_MESSAGE, 'Request method was not POST!')
    
    xtct = request.META.get('HTTP_X_TAXII_CONTENT_TYPE', None)
    if xtct == VID_TAXII_XML_10:
        sv = SchemaValidator(SchemaValidator.TAXII_10_SCHEMA)
        get_message_from_xml = tm10.get_message_from_xml
    else: # assume xtct == VID_TAXII_XML_11, since the headers have been validated
        sv = SchemaValidator(SchemaValidator.TAXII_11_SCHEMA)
        get_message_from_xml = tm11.get_message_from_xml
    
    if do_validate:
        try:
            result = sv.validate_string(request.body)
            if not result.valid:
                raise StatusMessageException('0', ST_BAD_MESSAGE, 'Request was not schema valid: %s' % [err for err in result.error_log])
        except XMLSyntaxError as e:
            raise StatusMessageException('0', ST_BAD_MESSAGE, 'Request was not well-formed XML: %s' % e.message)
    
    taxii_message = get_message_from_xml(request.body)
    
    service = handlers.get_service_from_path(request.path)
    handler_class = handlers.get_message_handler(service, taxii_message)
    handler_class.validate_headers(request, taxii_message.message_id)
    handler_class.validate_message_is_supported(taxii_message)
    
    response_message = handler_class.handle_message(service, taxii_message, request)
    if response_message.__module__ == 'libtaxii.messages_11':
        vid = VID_TAXII_SERVICES_11
    elif response_message.__module__ == 'libtaxii.messages_10':
        vid = VID_TAXII_SERVICES_10
    else:
        raise ValueError("Unknown response message module")
    
    response_headers = handlers.get_headers(vid, request.is_secure())
        
    return handlers.HttpResponseTaxii(response_message.to_xml(pretty_print=True), response_headers)
    
