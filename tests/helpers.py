# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from libtaxii.constants import *
import libtaxii.messages_10 as tm10
import libtaxii.messages_11 as tm11
from copy import deepcopy
from .constants import *
from taxii_services.models import *
from django.test import Client
import os


def get_message_from_client_response(resp, in_response_to):
    """ helper func"""

    taxii_content_type = resp.get('X-TAXII-Content-Type', None)
    response_message = resp.content

    if taxii_content_type is None:
        m = str(resp) + '\r\n' + response_message
        return tm11.StatusMessage(message_id='0', in_response_to=in_response_to, status_type=ST_FAILURE, message=m)
    elif taxii_content_type == VID_TAXII_XML_10:  # It's a TAXII XML 1.0 message
        return tm10.get_message_from_xml(response_message)
    elif taxii_content_type == VID_TAXII_XML_11:  # It's a TAXII XML 1.1 message
        return tm11.get_message_from_xml(response_message)
    elif taxii_content_type == VID_CERT_EU_JSON_10:
        return tm10.get_message_from_json(response_message)
    else:
        raise ValueError('Unsupported X-TAXII-Content-Type: %s' % taxii_content_type)

    return None


def get_headers(taxii_services_version, is_secure):
    """
    Convenience method for selecting headers
    """
    if taxii_services_version == VID_TAXII_SERVICES_11 and is_secure:
        return deepcopy(TAXII_11_HTTPS_Headers)
    elif taxii_services_version == VID_TAXII_SERVICES_11 and not is_secure:
        return deepcopy(TAXII_11_HTTP_Headers)
    elif taxii_services_version == VID_TAXII_SERVICES_10 and is_secure:
        return deepcopy(TAXII_10_HTTPS_Headers)
    elif taxii_services_version == VID_TAXII_SERVICES_10 and not is_secure:
        return deepcopy(TAXII_10_HTTP_Headers)
    else:
        raise ValueError("Unknown combination for taxii_services_version and is_secure!")


def make_request(path='/', post_data=None, header_dict=None,
                 response_msg_type=None, st=None, sd_keys=None, expected_code=200,
                 num_subscription_instances=None, subscription_status=None, subscription_id=None):
    """
    Makes a TAXII Request. Allows for a lot of munging of the request to test various aspects of the message

    :param path:
    :param post_data:
    :param header_dict:
    :param response_msg_type: Expected Response message type (e.g., MSG_STATUS_MESSAGE)
    :param st: Expected status type (e.g., ST_SUCCESS). Only applies if response_msg_type == MSG_STATUS_MESSAGE
    :param sd_keys: Expected status details (e.g., SD_ITEM). Only applies if response_msg_type == MSG_STATUS_MESSSAGE
    :param expected_code: Expected HTTP response code (defaults to 200)
    :return: A TAXII Message
    """
    c = Client()

    if not header_dict:
        # Use TAXII 1.1 HTTP Headers
        header_dict = get_headers(VID_TAXII_SERVICES_11, is_secure=False)
        header_dict['Accept'] = 'application/xml'
        header_dict['X-TAXII-Accept'] = VID_TAXII_XML_11

    if post_data:  # Make a POST
        resp = c.post(path, data=post_data, content_type='application/xml', **header_dict)
    else:  # Make a GET
        resp = c.get(path, **header_dict)

    if resp.status_code != expected_code:
        msg = resp.content
        raise ValueError("Response code was not %s. Was: %s.\r\n%s" %
                         (str(expected_code), str(resp.status_code), msg))

    msg = get_message_from_client_response(resp, '0')
    msg_xml = msg.to_xml(pretty_print=True)
    if len(msg_xml) > 4096:
        msg_xml = "MESSAGE WAS TOO BIG TO PRINT: %s" % len(msg_xml)

    if (response_msg_type and
        msg.message_type != response_msg_type):
        raise ValueError("Incorrect message type sent in response. Expected: %s. Got: %s.\r\n%s" %
                         (response_msg_type, msg.message_type, msg_xml))

    if st:
        if msg.status_type != st:
            raise ValueError("Incorrect status type. Expected %s got %s)\r\n%s" %
                             (st, msg.status_type, msg_xml))

    if sd_keys:
        for key in sd_keys:
            if key not in msg.status_detail:
                raise ValueError("SD Key not present: %s\r\n%s" %
                                 (key, msg_xml))

    if num_subscription_instances is not None:
        if len(msg.subscription_instances) != num_subscription_instances:
            raise ValueError("Expected %s subscription instances, got %s" % (num_subscription_instances, len(msg.subscription_instances)))

    if subscription_status is not None:
        for si in msg.subscription_instances:
            if si.status != subscription_status:
                raise ValueError("Expected status of %s, got %s" % (subscription_status, si.status))

    if subscription_id is not None:
        for si in msg.subscription_instances:
            if si.subscription_id != subscription_id:
                raise ValueError("Expected a subs id of %s, got %s" % (subscription_id, si.subscription_id))

    return msg


def add_protocol_bindings():
    pb1 = ProtocolBinding(name='TAXII HTTP v1.0',
                          binding_id=VID_TAXII_HTTP_10)
    pb1.save()
    pb2 = ProtocolBinding(name='TAXII HTTPS v1.0',
                          binding_id=VID_TAXII_HTTPS_10)
    pb2.save()


def add_message_bindings():
    mb1 = MessageBinding(name='TAXII XML v1.0',
                         binding_id=VID_TAXII_XML_10)
    mb1.save()
    mb2 = MessageBinding(name='TAXII XML v1.1',
                         binding_id=VID_TAXII_XML_11)
    mb2.save()


def add_content_bindings():
    content_bindings = {'STIX XML v1.0': CB_STIX_XML_10,
                        'STIX XML v1.0.1': CB_STIX_XML_101,
                        'STIX XML v1.1': CB_STIX_XML_11,
                        'STIX XML v1.1.1': CB_STIX_XML_111}
    for k, v in content_bindings.iteritems():
        cb, created = ContentBinding.objects.get_or_create(name=k, binding_id=v)
        cb.save()


def add_message_handlers():
    import taxii_services
    taxii_services.register_message_handlers()


def add_query_basics():
    cm_list = {'Core': CM_CORE,
               'Regex': CM_REGEX,
               'Timestamp': CM_TIMESTAMP}

    for k, v in cm_list.iteritems():
        cm = CapabilityModule(tag=k, value=v)
        cm.save()

    tev_list = {'STIX 1.0': CB_STIX_XML_10,
                'STIX 1.0.1': CB_STIX_XML_101,
                'STIX 1.1': CB_STIX_XML_11,
                'STIX 1.1.1': CB_STIX_XML_111}

    for k, v in tev_list.iteritems():
        tev = TargetingExpressionId(tag=k, value=v)
        tev.save()


def add_query_handlers():
    import taxii_services
    taxii_services.register_query_handlers()


def add_supported_queries():
    qh = QueryHandler.objects.get(handler='taxii_services.query_handlers.StixXml111QueryHandler')
    sq = SupportedQuery(name='All STIX 1.1.1',
                        description='tmp description',
                        query_handler=qh,
                        use_handler_scope=True)
    sq.save()


def add_collections():
    dc = DataCollection(name='default',
                        description='Test collection',
                        type=CT_DATA_FEED,
                        enabled=True,
                        accept_all_content=True)
    dc.save()


def add_basics():
    add_protocol_bindings()
    add_message_bindings()
    add_content_bindings()
    add_message_handlers()
    add_query_basics()
    add_query_handlers()
    add_supported_queries()
    add_collections()


def add_collection_service():
    cih = MessageHandler.objects.get(handler='taxii_services.message_handlers.CollectionInformationRequestHandler')
    smh = MessageHandler.objects.get(handler='taxii_services.message_handlers.SubscriptionRequestHandler')

    cis = CollectionManagementService(name='Test Collection Management Service 1',
                                      path=COLLECTION_PATH,
                                      description='Test Description',
                                      collection_information_handler=cih,
                                      subscription_management_handler=smh)
    cis.save()
    cis.advertised_collections = [DataCollection.objects.get(name='default')]
    cis.save()


def add_discovery_service():
    disc_handler = MessageHandler.objects.get(handler='taxii_services.message_handlers.DiscoveryRequestHandler')
    ds = DiscoveryService(name='Test Discovery Service 1',
                          path=DISCOVERY_PATH,
                          description='Test description.',
                          discovery_handler=disc_handler)

    # TODO: Add advertised services
    ds.save()


def add_inbox_service():
    ih = MessageHandler.objects.get(handler='taxii_services.message_handlers.InboxMessageHandler')
    inbox_1 = InboxService(name='Test Inbox 1',
                           path='/test_inbox_1/',
                           description='Description!',
                           inbox_message_handler=ih,
                           destination_collection_status=REQUIRED[0],
                           accept_all_content=True)
    inbox_1.save()
    inbox_1.supported_message_bindings = MessageBinding.objects.all()
    inbox_1.supported_protocol_bindings = ProtocolBinding.objects.all()
    inbox_1.destination_collections = DataCollection.objects.filter(name='default')
    inbox_1.save()

    ih = MessageHandler.objects.get(handler='taxii_services.message_handlers.InboxMessageHandler')
    inbox_2 = InboxService(name='Test Inbox 2',
                           path='/test_inbox_2/',
                           description='Description!',
                           inbox_message_handler=ih,
                           destination_collection_status=OPTIONAL[0],
                           accept_all_content=True)
    inbox_2.save()
    inbox_2.supported_message_bindings = MessageBinding.objects.all()
    inbox_2.supported_protocol_bindings = ProtocolBinding.objects.all()
    inbox_2.destination_collections = DataCollection.objects.filter(name='default')
    inbox_2.save()

    ih = MessageHandler.objects.get(handler='taxii_services.message_handlers.InboxMessageHandler')
    inbox_3 = InboxService(name='Test Inbox 3',
                           path='/test_inbox_3/',
                           description='Description!',
                           inbox_message_handler=ih,
                           destination_collection_status=PROHIBITED[0],
                           accept_all_content=True)
    inbox_3.save()
    inbox_3.supported_message_bindings = MessageBinding.objects.all()
    inbox_3.supported_protocol_bindings = ProtocolBinding.objects.all()
    inbox_3.save()


def add_poll_service():
    prh = MessageHandler.objects.get(handler='taxii_services.message_handlers.PollRequestHandler')
    pfh = MessageHandler.objects.get(handler='taxii_services.message_handlers.PollFulfillmentRequest11Handler')

    ps = PollService(name='Test Poll 1',
                     path='/test_poll_1/',
                     description='Desc!',
                     poll_request_handler=prh,
                     poll_fulfillment_handler=pfh,
                     max_result_size=5)
    ps.save()
    ps.data_collections = DataCollection.objects.filter(name='default')
    sqs = SupportedQuery.objects.filter(query_handler__handler='taxii_services.query_handlers.StixXml111QueryHandler')
    ps.supported_queries = sqs
    ps.save()


def add_test_content(collection, filenames=None):
    """

    :param collection: The collection to add the content to
    :param filenames: The filenames to add. By default adds everything in tests/test_content/
    :return:
    """

    collection = DataCollection.objects.get(name=collection)

    base_content_dir = 'tests/test_content/'
    for content_dir in os.listdir(base_content_dir):
        if content_dir == 'stix_111':
            content_binding = CB_STIX_XML_111
        else:
            raise ValueError('Content Binding ID could not be inferred from directory!')

        cbas = ContentBindingAndSubtype.objects.get(content_binding__binding_id=content_binding)
        for filename in os.listdir(os.path.join(base_content_dir, content_dir)):
            f = open(os.path.join(base_content_dir, content_dir, filename), 'r')
            content = f.read()
            cb = ContentBlock(content_binding_and_subtype=cbas, content=content)
            cb.save()
            collection.content_blocks.add(cb)
            collection.save()
