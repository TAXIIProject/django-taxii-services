# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

import libtaxii as t
import libtaxii.messages_11 as tm11
import libtaxii.taxii_default_query as tdq
import models

# All functions in this file follow the following convention:
# <model>_to_<libtaxii.messages_11 object> (For mapping a model to a TAXII Object)
# or
# <model>_get_<taxii.messages_11 object> (For extracting info from a model into a TAXII Object)


def service_to_service_instances(taxii_service):
    """
    Takes a TAXII Service (models.DiscoveryService, models.InboxService, 
    models.PollService, or models.CollectionManagementService) and returns 
    a list of TAXII objects. The return list may contain
    one or more service instances (usually 1 or 2).
    """
    
    service_instances = []
    
    st = None # placeholder for service_type
    sq = None # placeholder for supported_query
    isac = None # placeholder for inbox_service_accepted_content
    if isinstance(taxii_service, models.DiscoveryService):
        st = tm11.SVC_DISCOVERY # This is a Discovery Service
    elif isinstance(taxii_service, models.PollService):
        st = tm11.SVC_POLL # This is a Poll Service
        sq = service_get_supported_queries(taxii_service)
    elif isinstance(taxii_service, models.InboxService):
        st = tm11.SVC_INBOX # This is an Inbox Service
        isac = model_get_supported_content(taxii_service)
    elif isinstance(taxii_service, models.CollectionManagementService):
        st = tm11.SVC_COLLECTION_MANAGEMENT # This is a Collection Management Service
        sq = service_get_supported_queries(taxii_service)
    else: # TODO: use a better exception
        raise Exception("Unknown service class %s" % service.__class__.__name__)
    
    # In TAXII, each protocol binding is a seprate service instance, so we need to 
    # iterate over all protocol bindings and create one service instance for each one
    for pb in taxii_service.supported_protocol_bindings.all():
        si = tm11.ServiceInstance(
                     service_type = st,
                     services_version = t.VID_TAXII_SERVICES_11,
                     available = True,
                     protocol_binding = pb.binding_id,
                     service_address = taxii_service.path,#TODO: Get the server's real path and prepend it here
                     message_bindings = [mb.binding_id for mb in taxii_service.supported_message_bindings.all()],
                     supported_query = sq,
                     inbox_service_accepted_content = isac,
                     message = taxii_service.description
                     )
        # Add the service instance to the Discovery Response
        service_instances.append(si)
    
    return service_instances

def subscription_to_subscription_instance(subscription):
    """
    Takes a Subscription (models.Subscription) and returns 
    a SubscriptionInstance
    """
    
    subscription_params = tm11.SubscriptionParameters(
                                response_type = subscription.response_type,
                                content_bindings = get_supported_content(subscription))
    if subscription.query:
        subscription_params.query = tdq.Query.from_xml(subscription.query)
    
    push_params = None # TODO: Implement this
    poll_instances = None # TODO: Implement this
    
    si = tm11.SubscriptionInstance(
                        subscription_id = subscription.subscription_id,
                        status = subscription.status,
                        subscription_parameters = subscription_params,
                        push_parameters = push_params,
                        poll_instances = poll_instances)
    return si

def content_block_to_content_block(content_block):
    """
    Takes a ContentBlock (models.ContentBlock) and returns
    a Content Block
    """
    
    content_binding = tm11.ContentBinding(content_block.content_binding_and_subtype.content_binding.binding_id)
    if content_block.content_binding_and_subtype.subtype:
        content_binding.subtype_ids.append(content_block.content_binding_and_subtype.subtype.subtype_id)
    cb = tm11.ContentBlock(content_binding = content_binding, content = content_block.content, padding = content_block.padding)
    if content_block.timestamp_label:
        cb.timestamp_label = content_block.timestamp_label
    
    return cb

def result_set_part_to_poll_response(result_set_part, in_response_to):
    """
    ResultSetPart (models.ResultSetPart) and an in_response_to (string) and returns a 
    Poll Response.
    """
    
    poll_response = poll_response = tm11.PollResponse(
                                        message_id = tm11.generate_message_id(), 
                                        in_response_to = in_response_to,
                                        collection_name = result_set_part.result_set.data_collection.name)
    
    if result_set_part.exclusive_begin_timestamp_label:
        poll_response.exclusive_begin_timestamp_label = result_set_part.exclusive_begin_timestamp_label
    
    if result_set_part.inclusive_end_timestamp_label:
        poll_response.inclusive_end_timestamp_label = result_set_part.inclusive_end_timestamp_label
    
    if result_set_part.result_set.subscription:
        poll_response.subscription_id = result_set_part.result_set.subscription.subscription_id
    
    poll_response.record_count = tm11.RecordCount(result_set_part.result_set.total_content_blocks, False)
    poll_response.more = result_set_part.more
    poll_response.result_id = str(result_set_part.result_set.pk)
    poll_response.result_part_number = result_set_part.part_number
    
    for content_block in result_set_part.content_blocks.all():
        cb = content_block_to_content_block(content_block)
        poll_response.content_blocks.append(cb)
    
    return poll_response

def supported_query_to_query_info(supported_query):
    
    preferred_scope = [ps.scope for ps in supported_query.preferred_scope.all()]
    allowed_scope = [as_.scope for as_ in supported_query.allowed_scope.all()]
    targeting_expression_id = supported_query.query_handler.targeting_expression_id
    
    tei = tdq.DefaultQueryInfo.TargetingExpressionInfo(
            targeting_expression_id = targeting_expression_id,
            preferred_scope = preferred_scope,
            allowed_scope = allowed_scope)
    
    #TODO: I don't think commas are permitted, but they'd break this processing
    # Probably fix that, maybe through DB field validation
    map = dict((ord(char), None) for char in " []\'")# This is stored in the DB as a python list, so get rid of all the "extras"
    cm_list = supported_query.query_handler.capability_modules.translate(map).split(',')

    dqi = tdq.DefaultQueryInfo(
                targeting_expression_infos = [tei],
                capability_modules = cm_list)
    return dqi

def model_get_supported_content(obj):
    """
    Works on any model with 'accept_any_content' (bool) and 
    'supported_content' (many to many to ContentBindingAndSubtype) fields
    
    Returns a list of ContentBinding objects
    """
    
    return_list = []
    
    
    if obj.accept_all_content:
        return_list = None # Indicates accept all
    else:
        supported_content = {}
        
        for content in obj.supported_content.all():
            binding_id = content.content_binding.binding_id
            subtype = content.subtype
            if binding_id not in supported_content:
                supported_content[binding_id] = tm11.ContentBinding(binding_id = binding_id)
            
            if subtype and subtype.subtype_id not in supported_content[binding_id].subtype_ids:
                supported_content[binding_id].subtype_ids.append(subtype.subtype_id)
        
        return_list = supported_content.values()
    
    return return_list

def data_collection_get_push_methods(data_collection):
    #TODO: Implement this.
    #This depends on the ability of taxii_services to push content
    #and includes client capabilities
    return None

def data_collection_get_polling_service_instances(data_collection):
    """
    Return a set of tm11.PollingServiceInstance objects identifying the 
    TAXII Poll Services that can be polled for this Data Collection
    """
    poll_instances = []
    poll_services = models.PollService.objects.filter(data_collections=data_collection)
    for poll_service in poll_services:
        message_bindings = [mb.binding_id for mb in poll_service.supported_message_bindings.all()]
        for supported_protocol_binding in poll_service.supported_protocol_bindings.all():
            poll_instance = tm11.PollingServiceInstance(supported_protocol_binding.binding_id, poll_service.path, message_bindings)
            poll_instances.append(poll_instance)
    
    return poll_instances

def data_collection_get_subscription_methods(data_collection):
    """
    Return a set of tm11.SubscriptionMethod objects identifying the TAXII
    Collection Management Services handling subscriptions for this Data Collection
    """
    # TODO: Probably wrong, but here's the idea
    subscription_methods = []
    collection_management_services = models.CollectionManagementService.objects.filter(advertised_collections=data_collection)
    for collection_management_service in collection_management_services:
        message_bindings = [mb.binding_id for mb in collection_management_service.supported_message_bindings.all()]
        for supported_protocol_binding in collection_management_service.supported_protocol_bindings.all():
            subscription_method = tm11.SubscriptionMethod(supported_protocol_binding.binding_id, collection_management_service.path, message_bindings)
            subscription_methods.append(subscription_method)
    
    return subscription_methods

def data_collection_get_receiving_inbox_services(data_collection):
    """
    Return a set of tm11.ReceivingInboxService objects identifying the TAXII
    Inbox Services that accept content for this Data Collection.
    """
    receiving_inbox_services = []
    inbox_services = models.InboxService.objects.filter(destination_collections=data_collection)
    for inbox_service in inbox_services:
        message_bindings = [mb.binding_id for mb in inbox_service.supported_message_bindings.all()]
        for supported_protocol_binding in inbox_service.supported_protocol_bindings.all():
            receiving_inbox_service = tm11.ReceivingInboxService(supported_protocol_binding.binding_id, inbox_service.path, message_bindings, supported_contents=None)#TODO: Work on supported_contents
            receiving_inbox_services.append(receiving_inbox_service)
    
    return receiving_inbox_services

def service_get_supported_queries(service):
    """
    Works for any service with a 'supported_queries' property
    """
    
    supported_queries = []
    
    for query in service.supported_queries.all():
        query_info = supported_query_to_query_info(query)
        supported_queries.append(query_info)
    
    return supported_queries