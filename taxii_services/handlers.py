# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

import models
from django.http import Http404
import libtaxii.messages_11 as tm11
import libtaxii.taxii_default_query as tdq
import datetime
from dateutil.tz import tzutc
from importlib import import_module
from exceptions import StatusMessageException
from libtaxii.constants import *

def get_service_from_path(path):
    """
    Given a path, return a TAXII Service model object.
    If no service is found, raise Http404.
    """
    # Note that because these objects all inherit from models._TaxiService,
    # which defines the path field, paths are guaranteed to be unique.
    # That said, this can probably be done more efficiently
    try:
        return models.InboxService.objects.get(path = path, enabled=True)
    except:
        pass
    
    try:
        return models.DiscoveryService.objects.get(path = path, enabled=True)
    except:
        pass
    
    try:
        return models.PollService.objects.get(path = path, enabled=True)
    except:
        pass
    
    try:
        return models.CollectionManagementService.objects.get(path = path, enabled=True)
    except:
        pass
    
    raise Http404("No TAXII service at specified path")

# TODO: This persists even when the registering code 
# doesn't register itself anymore...
#TODO: This fails if the database hasn't been created yet
def register_message_handler(message_handler, name='Default Name'):
    """
    Given a message handler, attempts to create a 
    MessageHandler in the database.
    
    This function overwrites anything already in the database
    """
    
    module = message_handler.__module__
    class_ = message_handler.__name__
    
    handler_string = module + "." + class_
    
    mh, created = models.MessageHandler.objects.get_or_create(handler = handler_string, name=name)
    mh.clean()
    mh.save()

def register_query_handler(query_handler, name='Default Name'):
    """
    Given a QueryHandler, attempts to create a QueryHandler
    in the database.
    
    This function overwrites anything already in the database.
    """
    
    module = query_handler.__module__
    class_ = query_handler.__name__
    handler_string = module + "." + class_
    qh, created = models.QueryHandler.objects.get_or_create(handler = handler_string, name=name)
    qh.clean()
    qh.save()

def get_message_handler(service, taxii_message):
    """
    Given a service and a TAXII Message, return the 
    message handler class.
    """
    
    #Convenience aliases
    st = service.service_type
    mt = taxii_message.message_type
    
    handler = None
    
    if st == SVC_INBOX and mt == MSG_INBOX_MESSAGE:
        handler = service.inbox_message_handler
    elif st == SVC_POLL and mt == MSG_POLL_REQUEST:
        handler = service.poll_request_handler
    elif st == SVC_POLL and mt == MSG_POLL_FULFILLMENT:
        handler = service.poll_fulfillment_handler
    elif st == SVC_DISCOVERY and mt == MSG_DISCOVERY_REQUEST:
        handler = service.discovery_handler
    elif st == SVC_COLLECTION_MANAGEMENT and mt in (MSG_COLLECTION_INFORMATION_REQUEST, MSG_FEED_INFORMATION_REQUEST):
        handler = service.collection_information_handler
    elif st == SVC_COLLECTION_MANAGEMENT and mt in (MSG_MANAGE_COLLECTION_SUBSCRIPTION_REQUEST, MSG_MANAGE_FEED_SUBSCRIPTION_REQUEST):
        handler = service.subscription_management_handler
    
    if not handler:
        raise StatusMessageException(taxii_message.message_id, 
                                     ST_FAILURE, 
                                     "Message Type: %s is not supported by %s" % \
                                     (tm, st))
    
    module_name, class_name = handler.handler.rsplit('.', 1)
    module = import_module(module_name)
    handler_class = getattr(module, class_name)
    
    return handler_class

def add_content_block_to_collection(content_block, collection):
    #If the content block has a binding id only
    # 1) accept if it there is a matching binding id + no subtype
    #If the content block has a binding id and subtype 
    # 2) accept it if there is a matching binding id + no subtype
    # 3) accept it if there is a matching binding id + subtype
    
    #Look up the content binding in the database
    try:
        binding = models.ContentBinding.get(binding_id=content_block.content_binding.binding_id)
    except:
        return False, 'Content Binding not located in database'
    
    #Try to match on content binding only - this satisfies conditions #1 & 2
    if len(collection.supported_content.filter(content_binding=binding, subtype=None)) > 0:
        collection.content_blocks.add(content_block)
    return True, None
    
    if len(content_block.content_binding.subtype_ids) == 0:
        return False, 'No match found for supplied content binding'
    
    #Look up the subtype ID in the database
    try:
        subtype = models.ContentBindingSubtype.get(subtype_id = content_block.content_binding.subtype_ids[0])
    except:
        return False, 'Content Binding Subtype not located in database'
    
    if len(collection.supported_content.filter(content_binding=binding, subtype=subtype)):
        collection.content_blocks.add(content_block)
        return True, None
    
    return False, 'No match could be found'


def is_content_supported(obj, content_block): #binding_id, subtype_id = None):
    """
    Takes an object and a content block and determines whether
    obj (usually an Inbox Service or Data Collection) supports that (
    e.g., whether the content block can be added).
    
    Decision process is:
    1. If obj accepts any content, return True
    2. If obj supports binding ID > (All), return True
    3. If obj supports binding ID and subtype ID, return True
    4. Otherwise, return False,
    
    Works on any model with 'accept_all_content' (bool) and 
    'supported_content' (many to many to ContentBindingAndSubtype) fields
    """
    
    binding_id = content_block.content_binding.binding_id
    subtype_id = None
    if len(content_block.content_binding.subtype_ids) > 0:
        subtype_id = content_block.content_binding.subtype_ids[0]
    
    #TODO: I think this works, but this logic can probably be cleaned up
    if obj.accept_all_content:
        return True
    
    try:
        binding = models.ContentBinding.objects.get(binding_id = binding_id)
    except:
        raise
        return False
    
    if len(obj.supported_content.filter(content_binding = binding, subtype = None)) > 0:
        return True
    
    if not subtype_id:#No further checking can be done 
        return False
    
    try:
        subtype = models.ContentBindingSubtype.objects.get(parent = binding, subtype_id = subtype_id)
    except:
        raise
        False
    
    if len(obj.supported_content.filter(content_binding = binding, subtype = subtype)) > 0:
        return True
    
    return False

def create_inbox_message_db(inbox_message, django_request, received_via=None):
    """
    The InboxMessage model is used for bookkeeping purposes.
    """
    
    # For bookkeeping purposes, create an InboxMessage object
    # in the database
    inbox_message_db = models.InboxMessage() # The database instance of the inbox message
    inbox_message_db.message_id = inbox_message.message_id
    inbox_message_db.sending_ip = django_request.META.get('REMOTE_ADDR', None)
    if inbox_message.result_id:
        inbox_message_db.result_id = inbox_message.result_id
    
    if inbox_message.record_count:
        inbox_message_db.record_count = inbox_message.record_count.record_count
        inbox_message_db.partial_count = inbox_message.record_count.partial_count
    
    if inbox_message.subscription_information:
        inbox_message_db.collection_name = inbox_message.subscription_information.collection_name
        inbox_message_db.subscription_id = inbox_message.subscription_information.subscription_id
        #TODO: These might be wrong. Need to test to verify
        if inbox_message.subscription_information.exclusive_begin_timestamp_label:
            inbox_message_db.exclusive_begin_timestamp_label = inbox_message.subscription_information.exclusive_begin_timestamp_label
        if inbox_message.subscription_information.inclusive_end_timestamp_label:
            inbox_message_db.inclusive_begin_timestamp_label = inbox_message.subscription_information.inclusive_begin_timestamp_label
    
    if received_via:
        inbox_message_db.received_via = received_via # This is an inbox service
    
    inbox_message_db.original_message = inbox_message.to_xml()
    inbox_message_db.content_block_count = len(inbox_message.content_blocks)
    inbox_message_db.content_blocks_saved = 0
    inbox_message_db.save()
    
    return inbox_message_db

def create_result_set(results, data_collection, exclusive_begin_timestamp_label = None, inclusive_end_timestamp_label = None):
    """
    Creates a result set and result set parts depending on parameters
    """
    
    # Create the parent result set
    result_set = models.ResultSet()
    result_set.data_collection = data_collection
    result_set.total_content_blocks = len(results)
    result_set.last_part_returned = None
    result_set.expires = datetime.datetime.now(tzutc()) + datetime.timedelta(days=7) #Result Sets expire after a week
    result_set.save()
    
    # Create the individual parts    
    content_blocks_per_result_set = 3 #TODO: Should this be configurable?
    part_number = 1
    i = 0
    while i < len(results):
        rsp = models.ResultSetPart()
        rsp.result_set = result_set
        rsp.part_number = part_number
        
        # Pick out the content blocks that will be part of this result set
        content_blocks = results[i: i + content_blocks_per_result_set]
        rsp.content_block_count = len(content_blocks)
        
        if data_collection.type == tm11.CT_DATA_FEED: # Need to set timestamp label fields
            # Set the begin TS label
            # For the first part, use the exclusive begin timestamp label supplied as an arg,
            # as that's the exclusive begin timestmap label for the whole result set and 
            # is not necessarily equal to the timestamp label of the first content block.
            # For all subsequent parts, use the timestamp label of the i-1 content block
            # as the exclusive begin timestamp label
            if part_number == 1:# This is the first result set part
                rsp.exclusive_begin_timestamp_label = exclusive_begin_timestamp_label
            else: #This is not the first result set, use the i-1 Content Block's timestamp label
                rsp.exclusive_begin_timestamp_label = results[i-1].timestamp_label
            
            # Set the end TS label
            # For the last part, use the inclusive end timestamp label supplied as an arg,
            # as that's the inclusive end timestamp label for the whole result set and
            # is not necessariy equal to the timestamp label of the last content block.
            # For all other parts, use the timestamp label of the last content block in the 
            # result part.
            if i + content_blocks_per_result_set >= len(results): # There won't be any more result parts
                rsp.inclusive_end_timestamp_label = inclusive_end_timestamp_label
            else: #There will be more result parts
                rsp.inclusive_end_timestamp_label = content_blocks[-1].timestamp_label
        else: #Don't need to set timestamp label fields for Data Sets
            pass
        
        if i + content_blocks_per_result_set >= len(results): # This is the last result set part
            rsp.more = False
        else:
            rsp.more = True
        
        rsp.save()
        i += len(content_blocks)
        part_number += 1
        
        #Add content_blocks to the result set part
        for cb in content_blocks:
            rsp.content_blocks.add(cb)
        rsp.save()
    
    return result_set
