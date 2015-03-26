# Copyright (C) 2014 - The MITRE Corporation
# For license information, see the LICENSE.txt file

__version__ = "0.4"

def register_admins(admin_list=None):
    """
    Registers all admins or the subset specified by admin_list.

    Arguments:
        admin_list (list of taxii_services.admin objects to register) - **optional**
    """
    import admin
    admin.register_admins(admin_list)

DEFAULT_MESSAGE_HANDLERS = [
    # TODO: Implement this one.
    # 'taxii_services.message_handlers.CollectionInformationRequest10Handler',
    'taxii_services.message_handlers.CollectionInformationRequest11Handler',
    'taxii_services.message_handlers.CollectionInformationRequestHandler',
    'taxii_services.message_handlers.DiscoveryRequest10Handler',
    'taxii_services.message_handlers.DiscoveryRequest11Handler',
    'taxii_services.message_handlers.DiscoveryRequestHandler',
    'taxii_services.message_handlers.InboxMessage10Handler',
    'taxii_services.message_handlers.InboxMessage11Handler',
    'taxii_services.message_handlers.InboxMessageHandler',
    'taxii_services.message_handlers.PollFulfillmentRequest11Handler',
    'taxii_services.message_handlers.PollRequest10Handler',
    'taxii_services.message_handlers.PollRequest11Handler',
    'taxii_services.message_handlers.PollRequestHandler',
    'taxii_services.message_handlers.SubscriptionRequest10Handler',
    'taxii_services.message_handlers.SubscriptionRequest11Handler',
    'taxii_services.message_handlers.SubscriptionRequestHandler',
]

DEFAULT_QUERY_HANDLERS = [
    'taxii_services.query_handlers.StixXml111QueryHandler',
    # TODO: Implement these.
    # 'taxii_services.query_handlers.StixXml11QueryHandler',
    # 'taxii_services.query_handlers.StixXml101QueryHandler',
    # 'taxii_services.query_handlers.StixXml10QueryHandler'
]

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
        handler_list = DEFAULT_MESSAGE_HANDLERS

    import management

    for handler in handler_list:
        management.register_message_handler(handler)


def register_query_handlers(handler_list=None):
    """

    :param handler_list: List of strings identifying built-in QueryHandlers
    :return: None
    """

    if handler_list is None:
        handler_list = DEFAULT_QUERY_HANDLERS

    import management

    for handler in handler_list:
        management.register_query_handler(handler)
