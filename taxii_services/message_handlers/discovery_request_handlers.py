# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from .base_handlers import BaseMessageHandler
from ..exceptions import StatusMessageException

import libtaxii.messages_11 as tm11
import libtaxii.messages_10 as tm10
from libtaxii.constants import *


class DiscoveryRequest11Handler(BaseMessageHandler):
    """
    Built-in TAXII 1.1 Discovery Request Handler.
    """
    supported_request_messages = [tm11.DiscoveryRequest]
    version = "1"

    @staticmethod
    def handle_message(discovery_service, discovery_request, django_request):
        """
        Returns a listing of all advertised services.

        Workflow:
            1. Return the results of `DiscoveryService.to_discovery_response_11()`
        """
        return discovery_service.to_discovery_response_11(discovery_request.message_id)


class DiscoveryRequest10Handler(BaseMessageHandler):
    """
    Built-in TAXII 1.0 Discovery Request Handler
    """
    supported_request_messages = [tm10.DiscoveryRequest]
    version = "1"

    @staticmethod
    def handle_message(discovery_service, discovery_request, django_request):
        """
        Returns a listing of all advertised services.

        Workflow:
            1. Return the results of `DiscoveryService.to_discovery_response_10()`
        """
        return discovery_service.to_discovery_response_10(discovery_request.message_id)


class DiscoveryRequestHandler(BaseMessageHandler):
    """
    Built-in TAXII 1.1 and TAXII 1.0 Discovery Request Handler
    """
    supported_request_messages = [tm10.DiscoveryRequest, tm11.DiscoveryRequest]
    version = "1"

    @staticmethod
    def handle_message(discovery_service, discovery_request, django_request):
        """
        Passes the message off to either DiscoveryRequest10Handler or DiscoveryRequest11Handler
        """
        if isinstance(discovery_request, tm10.DiscoveryRequest):
            return DiscoveryRequest10Handler.handle_message(discovery_service, discovery_request, django_request)
        elif isinstance(discovery_request, tm11.DiscoveryRequest):
            return DiscoveryRequest11Handler.handle_message(discovery_service, discovery_request, django_request)
        else:
            raise StatusMessageException(discovery_request.message_id,
                                         ST_FAILURE,
                                         "TAXII Message not supported by Message Handler.")
