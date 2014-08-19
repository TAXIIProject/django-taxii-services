# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

#This only contains basic views for basic TAXII Services

from django.views.decorators.csrf import csrf_exempt
import handlers
from utils import request_utils, response_utils
import libtaxii as t
from exceptions import StatusMessageException
from libtaxii.constants import ST_FAILURE

@csrf_exempt
@request_utils.validate_taxii()
def service_router(request, path, taxii_message=None):
    """
    Takes in a request, path, and TAXII Message,
    and routes the taxii_message to the Service Handler.
    """
    
    if not taxii_message:
        raise ValueError("taxii_message was None!")
    
    service = handlers.get_service_from_path(request.path)
    message_handler = handlers.get_message_handler(service, taxii_message)
    message_handler.validate_headers(request, taxii_message.message_id)
    message_handler.validate_message_is_supported(taxii_message)
    
    response_message = message_handler.handle_message(service, taxii_message, request)
    if response_message.__module__ == 'libtaxii.messages_11':
        vid = t.VID_TAXII_XML_11
    elif response_message.__module__ == 'libtaxii.messages_10':
        vid = t.VID_TAXII_XML_10
    else:
        raise Exception("Unknown response message module")
    
    response_headers = response_utils.get_headers(vid, request.is_secure())
        
    return response_utils.HttpResponseTaxii(response_message.to_xml(pretty_print=True), response_headers)
    
