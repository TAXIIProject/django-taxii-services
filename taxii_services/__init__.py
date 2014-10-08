# Copyright (C) 2014 - The MITRE Corporation
# For license information, see the LICENSE.txt file

__version__ = "0.1.2"

import message_handlers.base_handlers as bmh
BaseMessageHandler = bmh.BaseMessageHandler

import query_handlers.base_handlers as bqh
BaseQueryHandler = bqh.BaseQueryHandler
BaseXmlQueryHandler = bqh.BaseXmlQueryHandler

import message_handlers.collection_information_request_handlers as cirh
import message_handlers.discovery_request_handlers as drh
import message_handlers.inbox_message_handlers as imh
import message_handlers.poll_fulifllment_request_handlers as pfrh
import message_handlers.poll_request_handlers as prh
import message_handlers.subscription_request_handlers as srh

# CollectionInformationRequest10Handler = cirh.CollectionInformationRequest10Handler
CollectionInformationRequest11Handler = cirh.CollectionInformationRequest11Handler
CollectionInformationRequestHandler = cirh.CollectionInformationRequestHandler

DiscoveryRequest10Handler = drh.DiscoveryRequest10Handler
DiscoveryRequest11Handler = drh.DiscoveryRequest11Handler
DiscoveryRequestHandler = drh.DiscoveryRequestHandler

InboxMessage10Handler = imh.InboxMessage10Handler
InboxMessage11Handler = imh.InboxMessage11Handler
InboxMessageHandler = imh.InboxMessageHandler

PollFulfillmentRequest11Handler = pfrh.PollFulfillmentRequest11Handler

PollRequest10Handler = prh.PollRequest10Handler
PollRequest11Handler = prh.PollRequest10Handler
PollRequestHandler = prh.PollRequestHandler

SubscriptionRequest10Handler = srh.SubscriptionRequest10Handler
SubscriptionRequest11Handler = srh.SubscriptionRequest11Handler
SubscriptionRequestHandler = srh.SubscriptionRequestHandler

import query_handlers.stix_xml_111_handler as sx111h
StixXml111QueryHandler = sx111h.StixXml111QueryHandler


def register_admins(admin_list=None):
    """
    Registers all admins or the subset specified by admin_list.

    Arguments:
        admin_list (list of taxii_services.admin objects to register) - **optional**
    """
    import admin
    admin.register_admins(admin_list)

# TODO: Calling this function borks loaddata with the following error:
# IntegrityError: Problem installing fixture 'yeti\fixtures\initial_data.json': Could not load taxii_services._Handler(pk=1): column
# handler is not unique


def register_message_handlers(handler_list=None):
    """
    Args:
        handler_list (list) - **optional** List of built-in message handlers to register. Defaults
                              to "all handlers"
    """

    if handler_list is None:
        handler_list = [# 'taxii_services.CollectionInformationRequest10Handler',
                        'taxii_services.CollectionInformationRequest11Handler',
                        'taxii_services.CollectionInformationRequestHandler',
                        'taxii_services.DiscoveryRequest10Handler',
                        'taxii_services.DiscoveryRequest11Handler',
                        'taxii_services.DiscoveryRequestHandler',
                        'taxii_services.InboxMessage10Handler',
                        'taxii_services.InboxMessage11Handler',
                        'taxii_services.InboxMessageHandler',
                        'taxii_services.PollFulfillmentRequest11Handler',
                        'taxii_services.PollRequest10Handler',
                        'taxii_services.PollRequest11Handler',
                        'taxii_services.PollRequestHandler',
                        'taxii_services.SubscriptionRequest10Handler',
                        'taxii_services.SubscriptionRequest11Handler',
                        'taxii_services.SubscriptionRequestHandler']

    import management

    for handler in handler_list:
        management.register_message_handler(handler)


def register_query_handlers(handler_list=None):
    """

    :param handler_list: List of strings identifying built-in QueryHandlers
    :return: None
    """

    if handler_list is None:
        handler_list = ['taxii_services.StixXml111QueryHandler',
                        # 'taxii_services.StixXml11QueryHandler',
                        # 'taxii_services.StixXml101QueryHandler',
                        # 'taxii_services.StixXml10QueryHandler'
                        ]

    import management

    for handler in handler_list:
        management.register_query_handler(handler)
