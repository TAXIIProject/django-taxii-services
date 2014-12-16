# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

# This only contains basic views for basic TAXII Services

from .exceptions import StatusMessageException
from .util import request_utils
import handlers

import libtaxii.messages_11 as tm11
import libtaxii.messages_10 as tm10
from libtaxii.constants import *
from libtaxii.validation import SchemaValidator

import collections
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from lxml.etree import XMLSyntaxError
from StringIO import StringIO
import traceback
import sys
from models import SiteConfiguration
from importlib import import_module

ParseTuple = collections.namedtuple('ParseTuple', ['validator', 'parser'])

TAXII_10_ParseTuple = ParseTuple(SchemaValidator(SchemaValidator.TAXII_10_SCHEMA), tm10.get_message_from_xml)
TAXII_11_ParseTuple = ParseTuple(SchemaValidator(SchemaValidator.TAXII_11_SCHEMA), tm11.get_message_from_xml)

xtct_map = {VID_TAXII_XML_10: TAXII_10_ParseTuple,
            VID_TAXII_XML_11: TAXII_11_ParseTuple}

PV_ERR = "There was an error parsing and validating the request message."

logger = SiteConfiguration.get_logger(__name__)

@csrf_exempt
def service_router(request, path, do_validate=True):
    """
    Takes in a request, path, and TAXII Message,
    and routes the taxii_message to the Service Handler.
    """
    logger.debug('Entering service_router')
    if request.method != 'POST':
        logger.info('Raising StatusMessageException; Request was not POST.')
        raise StatusMessageException('0', ST_BAD_MESSAGE, 'Request method was not POST!')

    xtct = request.META.get('HTTP_X_TAXII_CONTENT_TYPE', None)
    if not xtct:
        logger.info('Raising StatusMessageException; Request did not have an X-TAXII-Content-Type Header.')
        raise StatusMessageException('0', ST_BAD_MESSAGE, 'The X-TAXII-Content-Type Header was not present.')

    parse_tuple = xtct_map.get(xtct)
    if not parse_tuple:
        logger.info('Raising StatusMessageException; Request did not have a supported X-TAXII-Content-Type Header.')
        raise StatusMessageException('0', ST_BAD_MESSAGE, 'The X-TAXII-Content-Type Header is not supported.')

    if do_validate:
        msg = None  # None means no error, a non-None value means an error happened
        try:
            result = parse_tuple.validator.validate_string(request.body)
            if not result.valid:
                if settings.DEBUG is True:
                    msg = 'Request was not schema valid: %s' % [err for err in result.error_log]
                else:
                    msg = PV_ERR
        except XMLSyntaxError as e:
            if settings.DEBUG is True:
                msg = 'Request was not well-formed XML: %s' % str(e)
            else:
                msg = PV_ERR

        if msg is not None:
            logger.info('Raising StatusMessageException;', msg)
            raise StatusMessageException('0', ST_BAD_MESSAGE, msg)

    try:
        taxii_message = parse_tuple.parser(request.body)
    except tm11.UnsupportedQueryException as e:
        # TODO: Is it possible to give the real message id?
        # TODO: Is it possible to indicate which query aspects are supported?
        # This might require a change in how libtaxii works
        logger.info('Raising StatusMessageException; Query Format Unsupported.')
        raise StatusMessageException('0',
                                     ST_UNSUPPORTED_QUERY)

    service = handlers.get_service_from_path(request.path)
    handler = service.get_message_handler(taxii_message)
    module_name, class_name = handler.handler.rsplit('.', 1)

    try:
        module = import_module(module_name)
        handler_class = getattr(module, class_name)
    except Exception as e:
        type, value, tb = sys.exc_info()
        msg = "Error importing handler: %s" % handler.handler, type, value
        logger.error(msg)
        raise type, msg, tb
    logger.debug("Successfully loaded message handler: %s" % handler.handler)
    handler_class.validate_headers(request, taxii_message.message_id)
    logger.debug("Validated headers")
    handler_class.validate_message_is_supported(taxii_message)
    logger.debug("Message is supported: %s" % taxii_message.message_type)

    try:
        response_message = handler_class.handle_message(service, taxii_message, request)
    except StatusMessageException as sme:
        # TODO: Should this get logged?
        raise  # The handler_class has intentionally raised this
    except Exception as e:  # Something else happened
        msg = "There was a failure while executing the message handler"
        if settings.DEBUG:  # Add the stacktrace
            msg += "\r\n" + traceback.format_exc()
        logger.error(msg)
        raise StatusMessageException(taxii_message.message_id,
                                     ST_FAILURE,
                                     msg)

    try:
        response_message.message_type
    except AttributeError as e:
        msg = "The message handler (%s) did not return a TAXII Message!" % handler_class
        if settings.DEBUG:
            msg += ("\r\n The returned value was: %s (class=%s)" %
                    (response_message, response_message.__class__.__name__))
        logger.error(msg)
        raise StatusMessageException(taxii_message.message_id,
                                     ST_FAILURE,
                                     msg)
    logger.debug("Response message type: %s" % response_message.message_type)
    if response_message.__module__ == 'libtaxii.messages_11':
        vid = VID_TAXII_SERVICES_11
    elif response_message.__module__ == 'libtaxii.messages_10':
        vid = VID_TAXII_SERVICES_10
    else:
        # TODO: What kind of error belongs here?
        raise ValueError("Unknown response message module")
    # logger.debug(response_message.to_xml(pretty_print=True))
    response_headers = handlers.get_headers(vid, request.is_secure())
    logger.debug('Leaving service_router')
    return handlers.HttpResponseTaxii(response_message.to_xml(pretty_print=True), response_headers)
