# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

import libtaxii as t
import libtaxii.messages_11 as tm11

# All functions in this file follow the following convention:
# <model>_to_<taxii_object> (For mapping a model to a TAXII Object)
# or
# <model>_get_<taxii_object> (For extracting info from a model into a TAXII Object)


def service_to_service_instances(taxii_service, format=t.VID_TAXII_XML_11):
    """
    Takes a TAXII Service (models.DiscoveryService, models.InboxService, 
    models.PollService, or models.CollectionManagementService) and returns 
    a list of TAXII objects according to the format. The return list may contain
    one or more service instances (usually 1 or 2).
    """
    
    service_instances = []
    
    if format == t.VID_TAXII_XML_11:
        st = None # placeholder for service_type
        sq = None # placeholder for supported_query
        isac = None # placeholder for inbox_service_accepted_content
        if isinstance(taxii_service, models.DiscoveryService):
            st = tm11.SVC_DISCOVERY # This is a Discovery Service
        elif isinstance(taxii_service, models.PollService):
            st = tm11.SVC_POLL # This is a Poll Service
            sq = get_supported_queries(service)
        elif isinstance(taxii_service, models.InboxService):
            st = tm11.SVC_INBOX # This is an Inbox Service
            isac = get_supported_content(service)
        elif isinstance(taxii_service, models.CollectionManagementService):
            st = tm11.SVC_COLLECTION_MANAGEMENT # This is a Collection Management Service
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
                         service_address = service.path,#TODO: Get the server's real path and prepend it here
                         message_bindings = [mb.binding_id for mb in service.supported_message_bindings.all()],
                         supported_query = sq,
                         inbox_service_accepted_content = isac,
                         message = service.description
                         )
            # Add the service instance to the Discovery Response
            service_instances.append(si)
    else:
        raise Exception("Format not supported: %s" % format)
    
    return service_instances

def model_get_supported_content(model, format=t.VID_TAXII_XML_11):
    """
    Works on any model with 'accept_any_content' (bool) and 
    'supported_content' (many to many to ContentBindingAndSubtype) fields
    
    Returns a list of ContentBinding objects
    """
    
    return_list = []
    
    if format == t.VID_TAXII_XML_11:
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
    else:
        raise Exception("Format not supported: %s" % format)
    
    return return_list

def subscription_to_subscription_instance(subscription, format=t.VID_TAXII_XML_11):
    """
    Takes a Subscription (models.Subscription) and returns 
    a SubscriptionInstance according to the format.
    """
    
    if format != t.VID_TAXII_XML_11:
        raise NotImplementedError()
    
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

def content_block_to_content_block(content_block, format=t.VID_TAXII_XML_11):
    """
    Takes a ContentBlock (models.ContentBlock) and returns
    a Content Block according to the format
    """
    
    if format != t.VID_TAXII_XML_11:
        raise NotImplementedError()
    
    content_binding = tm11.ContentBinding(content_block.content_binding_and_subtype.content_binding.binding_id)
    if content_block.content_binding_and_subtype.subtype:
        content_binding.subtype_ids.append(content_block.content_binding_and_subtype.subtype.subtype_id)
    cb = tm11.ContentBlock(content_binding = content_binding, content = content_block.content, padding = content_block.padding)
    if content_block.timestamp_label:
        cb.timestamp_label = content_block.timestamp_label
    
    return cb
