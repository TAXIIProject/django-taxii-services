# Copyright (C) 2014 - The MITRE Corporation
# For license information, see the LICENSE.txt file

__version__ = "0.3"

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


DEFAULT_MESSAGE_HANDLERS = [
    # TODO: Implement this.
    # 'taxii_services.handlers.default.CollectionInformationRequest10Handler',
    'taxii_services.handlers.default.CollectionInformationRequest11Handler',
    'taxii_services.handlers.default.CollectionInformationRequestHandler',
    'taxii_services.handlers.default.DiscoveryRequest10Handler',
    'taxii_services.handlers.default.DiscoveryRequest11Handler',
    'taxii_services.handlers.default.DiscoveryRequestHandler',
    'taxii_services.handlers.default.InboxMessage10Handler',
    'taxii_services.handlers.default.InboxMessage11Handler',
    'taxii_services.handlers.default.InboxMessageHandler',
    'taxii_services.handlers.default.PollFulfillmentRequest11Handler',
    'taxii_services.handlers.default.PollRequest10Handler',
    'taxii_services.handlers.default.PollRequest11Handler',
    'taxii_services.handlers.default.PollRequestHandler',
    'taxii_services.handlers.default.SubscriptionRequest10Handler',
    'taxii_services.handlers.default.SubscriptionRequest11Handler',
    'taxii_services.handlers.default.SubscriptionRequestHandler',
]

DEFAULT_QUERY_HANDLERS = [
    'taxii_services.handlers.default.StixXml111QueryHandler',
    # TODO: Implement these.
    # 'taxii_services.handlers.default.StixXml11QueryHandler',
    # 'taxii_services.handlers.default.StixXml101QueryHandler',
    # 'taxii_services.handlers.default.StixXml10QueryHandler'
]


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
