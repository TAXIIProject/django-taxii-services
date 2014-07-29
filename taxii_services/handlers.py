# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

import models
from django.http import Http404
from itertools import chain
import libtaxii as t
import libtaxii.messages_11 as tm11
import libtaxii.taxii_default_query as tdq
import datetime
import taxiifiers
from dateutil.tz import tzutc
from importlib import import_module

def get_service_from_path(path):
    #TODO: Can this code be cleaned up a bit?
    #TODO: Probably the paths should be unique across all services
    # right now you could have two different services with the same 
    # path and the code search order would determine which
    # one gets returned
    
    #Thought: Have a path object that must be unique and 
    # the path object can only have one outbound relationship?
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

def get_service_handler(service, taxii_message):
    if isinstance(service, models.InboxService):
        if isinstance(taxii_message, tm11.InboxMessage):
            handler_string = service.inbox_message_handler.handler
        else:
            raise Exception("message type not supported")#TODO: Better error
    elif isinstance(service, models.PollService):
        if isinstance(taxii_message, tm11.PollRequest):
            handler_string = service.poll_request_handler.handler
        elif isinstance(taxii_message, tm11.PollFulfillmentRequest):
            handler_string = service.poll_fulfillment_handler.handler
        else:
            raise Exception("message type not supported")#TODO: Better error
    elif isinstance(service, models.DiscoveryService):
        if isinstance(taxii_message, tm11.DiscoveryRequest):
            handler_string = service.discovery_handler.handler
        else:
            raise Exception("message type not supported")#TODO: Better error
    elif isinstance(service, models.CollectionManagementService):
        if isinstance(taxii_message, tm11.CollectionInformationRequest):
            handler_string = service.collection_information_handler.handler
        elif isinstance(taxii_message, tm11.SubscriptionManagementRequest):
            handler_string = service.subscription_management_handler.handler
        else:
            raise Exception("message type not supported")#TODO: Better error
    else:
        raise Exception("This shouldn't happen!")
    
    module_name, method_name = handler_string.rsplit('.', 1)
    module = import_module(module_name)
    handler = getattr(module, method_name)
    
    return handler

def get_push_methods(data_collection):
    #TODO: Implement this.
    #This depends on the ability of taxii_services to push content
    #and includes client capabilities
    return None

#TODO: This is a model -> TAXII 1.1 specific thing. Should it be marked as such, named as such, labeled as such?
#      Not sure how this should be segmented out or whatever. Maybe also take an argument that's the message binding id to provide
#      the right output format?
def get_polling_service_instances(data_collection):
    poll_instances = []
    poll_services = models.PollService.all.filter(data_collections=data_collection)
    for poll_service in poll_services:
        message_bindings = [mb.binding_id for mb in poll_service.supported_message_bindings.all()]
        for supported_protocol_binding in poll_service.supported_protocol_bindings.all():
            poll_instance = tm11.PollingServiceInstance(supported_protocol_binding.binding_id, poll_service.path, message_bindings)
            poll_instances.append(poll_instance)
    
    return poll_instances

def get_subscription_methods(data_collection):
    #TODO: Probably wrong, but here's the idea
    subscription_methods = []
    collection_management_services = models.CollectionManagementService.all.filter(advertised_collections=data_collection)
    for collection_management_service in collection_management_services:
        message_bindings = [mb.binding_id for mb in collection_management_service.supported_message_bindings.all()]
        for supported_protocol_binding in collection_management_service.supported_protocol_bindings.all():
            subscription_method = tm11.SubscriptionMethod(supported_protocol_binding.binding_id, collection_management_service.path, message_bindings)
            subscription_methods.append(subscription_method)
    
    return subscription_methods

def get_receiving_inbox_services(data_collection):
    receiving_inbox_services = []
    inbox_services = models.InboxService.all.filter(destination_collections=data_collection)
    for inbox_service in inbox_services:
        message_bindings = [mb.binding_id for mb in inbox_service.supported_message_bindings.all()]
        for supported_protocol_binding in inbox_service.supported_protocol_bindings.all():
            receiving_inbox_service = tm11.ReceivingInboxService(supported_protocol_binding.binding_id, inbox_service.path, message_bindings, supported_contents=None)#TODO: Work on supported_contents
            receiving_inbox_services.append(subscription_method)
    
    return receiving_inbox_services

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
        print 'accepts all content'
        return True
    
    try:
        binding = models.ContentBinding.objects.get(binding_id = binding_id)
    except:
        raise
        return False
    
    if len(obj.supported_content.filter(content_binding = binding, subtype = None)) > 0:
        return True
    
    if not subtype_id:#No further checking can be done 
        print 'no further checking can be done'
        return False
    
    try:
        subtype = models.ContentBindingSubtype.objects.get(parent = binding, subtype_id = subtype_id)
    except:
        raise
        False
    
    if len(obj.supported_content.filter(content_binding = binding, subtype = subtype)) > 0:
        return True
    
    print 'all out of options!'
    return False

def get_supported_queries(poll_service):
    return None#TODO: Implement this

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
        rc = models.RecordCount()
        rc.record_count = inbox_message.record_count.record_count
        if inbox_message.record_count.partial_count:
            rc.partial_count = inbox_message.record_count.partial_count
        rc.save()
        inbox_message_db.record_count = rc
    
    if inbox_message.subscription_information:
        si = models.SubscriptionInformation()
        si.collection_name = inbox_message.subscription_information.collection_name
        si.subscription_id = inbox_message.subscription_information.subscription_id
        #TODO: These might be wrong. Need to test to verify
        if inbox_message.subscription_information.exclusive_begin_timestamp_label:
            si.exclusive_begin_timestamp_label = inbox_message.subscription_information.exclusive_begin_timestamp_label
        if inbox_message.subscription_information.inclusive_end_timestamp_label:
            si.inclusive_begin_timestamp_label = inbox_message.subscription_information.inclusive_begin_timestamp_label
        si.save()
        inbox_message_db.subscription_information = si
    
    if received_via:
        inbox_message_db.received_via = received_via # This is an inbox service
    
    inbox_message_db.original_message = inbox_message.to_xml()
    inbox_message_db.content_block_count = len(inbox_message.content_blocks)
    inbox_message_db.content_blocks_saved = 0
    inbox_message_db.save()
    
    return inbox_message_db

def create_result_set(results, data_collection):
    """
    Creates a result set for later
    """
    
    result_set = models.ResultSet()
    result_set.data_collection = data_collection
    result_set.total_content_blocks = len(results)
    result_set.expires = datetime.datetime.now(tzutc()) + datetime.timedelta(days=7) #Result Sets expire after a week
    result_set.save()
    
    for result in results:
        result_set.content_blocks.add(result)
    
    result_set.save()
    
    return result_set

def discovery_handler(discovery_service, discovery_request, django_request):
    """
    This is the default handler for the Discovery Service Model. It takes a Discovery Service,
    DiscoveryRequest, and Django Request and forms an appropriate DiscoveryResponse.
    
    Args:
        discovery_service (discovery_service model instance): The Discovery Service being invoked
        discovery_request (libtaxii.messages_11 DiscoveryRequest): The Discovery Request being responded to
        django_request (Django request): The Django request being responded to
    
    """
    
    # Chain together all the enabled services that this discovery service advertises
    advertised_services = list(chain(discovery_service.advertised_discovery_services.filter(enabled=True),
                                     discovery_service.advertised_poll_services.filter(enabled=True),
                                     discovery_service.advertised_inbox_services.filter(enabled=True),
                                     discovery_service.advertised_collection_management_services.filter(enabled=True)))
    
    # Create the stub DiscoveryResponse
    discovery_response = tm11.DiscoveryResponse(tm11.generate_message_id(), discovery_request.message_id)
    
    # Iterate over advertised services, creating a service instance for each
    for service in advertised_services:
        service_instances = taxiifiers.service_to_service_instances(service)
        discovery_response.service_instances.extend(service_instances)
    
    # Return the Discovery Response
    return discovery_response

def inbox_message_handler(inbox_service, inbox_message, django_request):
    """
    This is the default handler for the Inbox Service Model. It takes an Inbox Service,
    InboxMessage, and Django Request and forms an appropriate Status Message.
    
    Args:
        inbox_service (inbox_service model instance): The Inbox Service being invoked
        inbox_message (libtaxii.messages_11 InboxMessage): The Inbox Message being responded to
        django_request (Django request): The Django request being responded to
    
    """
    
    # Calculate the number of Destination Collection Names present in the InboxMessage
    num_dcns = len(inbox_message.destination_collection_names)
    
    # Error check 1 of 2 for Destination Collection Names
    # If Destination Collection Name is required but there aren't any, return a Status Message
    if inbox_service.destination_collection_status == models.REQUIRED and num_dcns == 0:
        sm = tm11.StatusMessage(tm11.generate_message_id(), in_response_to=inbox_message.message_id, status_type=tm11.ST_DESTINATION_COLLECTION_ERROR)
        sm.message = 'A Destination_Collection_Name is required and none were specified'
        sm.status_detail = get_inbox_acceptable_destinations(inbox_service)
        return sm
    
    # Error check 2 of 2 for Destination Collection Names
    # If Destination Collection Name is prohibited but there are more than one, return a Status Message
    if inbox_service.destination_collection_status == models.PROHIBITED and num_dcns > 0:
        sm = tm11.StatusMessage(tm11.generate_message_id(), in_response_to=inbox_message.message_id, status_type=tm11.ST_DESTINATION_COLLECTION_ERROR)
        sm.message = 'Destination_Collection_Names are prohibited'
        return sm
    
    # For each Destination Collection Name specified in the Inbox Message, attempt to
    # locate it in the database. If a lookup fails, respond with a Status Message
    # If there are no Destination Collection Names specified in the Inbox Message,
    # The code in the loop will not be executed
    collections = []
    for collection_name in inbox_message.destination_collection_names:
        try:
            collections.append(inbox_service.destination_collections.get(name=collection_name, enabled=True))
        except:
            raise
            sm = tm11.StatusMessage(tm11.generate_message_id(), in_response_to=inbox_message.message_id, status_type=tm11.ST_NOT_FOUND)
            sm.message = 'Invalid destination collection name'
            #TODO: Verify that this status_detail is being set right. Its probably not. should probably use a constant for ITEM.
            sm.status_detail = {'ITEM': collection_name}
            return sm
    
    # Store certain information about this Inbox Message in the database for bookkeeping
    inbox_message_db = create_inbox_message_db(inbox_message, django_request, received_via = inbox_service)
    
    # Iterate over the ContentBlocks in the InboxMessage and try to add
    # them to the database
    saved_blocks = 0
    for content_block in inbox_message.content_blocks:
        
        # Get the Content Binding Binding Id and (if present) Subtype
        binding_id = content_block.content_binding.binding_id
        subtype_id = None
        if len(content_block.content_binding.subtype_ids) > 0:
            subtype_id = content_block.content_binding.subtype_ids[0]
        
        saved = False
        try:
            # Attempt to instantiate a ContentBlock model with
            # properties from the InboxMessage's ContentBlock
            cb = models.ContentBlock()
            
            # Note that if the Content Binding ID AND Subtype ID are not known, the next line will raise
            # an exception, causing no further processing of the ContentBlock.
            cb.content_binding_and_subtype = models.ContentBindingAndSubtype.objects.get(content_binding__binding_id=binding_id, subtype__subtype_id=subtype_id)
            
            cb.content = content_block.content
            if content_block.padding:
                cb.padding = content_block.padding
            if content_block.message:
                cb.message = content_block.message
            cb.inbox_message = inbox_message_db
            
            # If there are not any destination collections and the
            # Inbox Service supports the Content Binding and Subtype add the Content Block
            # to the database (by calling .save())
            if len(collections) == 0 and is_content_supported(inbox_service, content_block):
                cb.save() # Save the Content Block
                saved = True
            
            # If there are destination collections, for each collection: 
            # If that collection supports the Content Binding and Subtype, associate
            # The ContentBlock with the Data Collection
            for collection in collections:
                if is_content_supported(collection, content_block):
                    if not saved:
                        cb.save()
                        saved = True
                    collection.content_blocks.add(cb)
                #else:
                #    print 'content is not supported:', content_block.content_binding
            
            # If the ContentBlock was saved to the DB, update
            # the running tally
            if saved:
                saved_blocks += 1
        except: # TODO: Something useful here.
            raise
    
    # Update the Inbox Message model with the number of ContentBlocks that were saved
    inbox_message_db.content_blocks_saved = saved_blocks
    inbox_message_db.save()
    
    #Create and return a Status Message indicating success
    status_message = tm11.StatusMessage(message_id = tm11.generate_message_id(), in_response_to=inbox_message.message_id, status_type = tm11.ST_SUCCESS)
    return status_message
    

def poll_request_handler(poll_service, poll_request, django_request):
    """
    This is the default handler for the Poll Service Model. It takes a Poll Service,
    Poll Request Message, and Django Request and forms an appropriate Poll Response (or Status Message).
    
    Args:
        poll_service (poll_service model instance): The Inbox Service being invoked
        poll_request (libtaxii.messages_11 PollRequest): The Inbox Message being responded to
        django_request (Django request): The Django request being responded to
    
    The Poll Service is actually a little complicated, so the workflow for this method is documented here:
    
    1. Check if the named Data Collection exists. Return a Status Message if the Data Collection doesn't exist.
    2. Pull the request parameters out of the stored subscription or
    3. Pull the request parameters our of the request itself.
    4. Make a database query (Note: Not a TAXII Query, yet) to get a list of potential results.
    5. If a TAXII Query is present in the query, loop over each potential result and apply the query
    6. Decide whether or not results are available "now". This app just uses a bool, real code would use something real
    7. If the results are available "now":
        8. Decide whether to split the results across multiple poll responses
        9. If splitting, split across multiple responses
        10. If not splitting, don't split across multiple responses
    11. If the results are NOT available "now":
        12. If request.allow_asynch, send a Pending Status Message 
        13. elif delivery parameters exist *and* this code supports them, send the results using the delivery parameters
        14. Return a Status Message of Failure (?)
    """
    
    # The check for #1
    try:
        collection = poll_service.data_collections.get(name=poll_request.collection_name)
    except:
        sm = tm11.StatusMessage(tm11.generate_message_id(), in_response_to=poll_request.message_id, status_type = tm11.ST_NOT_FOUND)
        sm.message = 'The collection you requested was not found'
        sm.status_detail = {'ITEM': poll_request.collection_name}
        return sm
    
    filter_kwargs = {}
    
    if collection.type == models.DATA_FEED:#Only data feeds care about timestamp labels
        current_datetime = datetime.datetime.now(tzutc())
        
        #If the request specifies a timestamp label in an acceptable range, use it. Otherwise, don't use a begin timestamp label
        if poll_request.exclusive_begin_timestamp_label  and (poll_request.exclusive_begin_timestamp_label < current_datetime):
            filter_kwargs['timestamp_label__gt'] = poll_request.exclusive_begin_timestamp_label
        
        #Use either the specified end timestamp label; or the current time iff the specified end timestmap label is after the current time
        if poll_request.inclusive_end_timestamp_label  and (poll_request.inclusive_end_timestamp_label < current_datetime):
            filter_kwargs['timestamp_label__lte'] = inclusive_end_timestamp_label
        else:
            filter_kwargs['timestamp_label__lte'] = current_datetime
    
    #Set all aspects of a Poll Request to their defaults
    allow_asynch = False
    response_type = tm11.RT_FULL
    content_binding = None
    query = None
    delivery_parameters = None
    
    # Step #2
    subscription = None
    if poll_request.subscription_id:
        try:
            subscription = models.Subscription.get(subscription_id = poll_request.subscription_id)
        except:
            sm = tm11.StatusMessage(tm11.generate_message_id(), in_response_to=poll_request.message_id, status_type=tm11.ST_NOT_FOUND)
            sm.message = 'The Subscription was not found!'
            sm.status_detail = {'ITEM': poll_request.subscription_id}
            return sm
        
        if subscription.status != tm11.SS_ACTIVE:
            raise Exception("Subscription not active!")#TODO: Status Message
        
        allow_asynch = False#subscription.allow_asynch; MSD: This isn't in a subscription???
        response_type = subscription.response_type
        content_bindings = subscription.content_binding_and_subtype.all()
        query = tdq.DefaultQuery.from_xml(subscription.query)
        delivery_parameters = subscription.push_parameters
    # Step #3
    elif poll_request.poll_parameters:
        allow_asynch = poll_request.poll_parameters.allow_asynch == 'true'
        response_type = poll_request.poll_parameters.response_type
        query = poll_request.poll_parameters.query
        
        content_bindings = []
        for content_binding in poll_request.poll_parameters.content_bindings:
            #TOOD: These can throw an error, handle it better
            #      The error can probably be safely ignored since if the system doesn't know the content binding / subtype, there isn't
            #      any content that matches it anyway
            if len(content_binding.subtype_ids) == 0:
                content_bindings.append(models.ContentBindingAndSubtype.objects.get(content_binding__binding_id = content_binding.binding_id, subtype__subtype_id = None))
            for subtype_id in content_binding.subtype_ids:
                content_bindings.append(models.ContentBindingAndSubtype.objects.get(content_binding__binding_id = content_binding.binding_id, subtype__subtype_id = subtype_id))
        
        delivery_parameters = poll_request.poll_parameters.delivery_parameters#TODO: Remediate with database object
    else:
        raise Exception("Bad message!")#TODO: Return a status message
    
    if len(content_bindings) > 0:#A filter has been specified in the request or the subscription
        filter_kwargs['content_binding_and_subtype__in'] = content_bindings
    
    # Step #4
    results = collection.content_blocks.filter(**filter_kwargs).order_by('timestamp_label')
    
    # Step #5
    if poll_request.poll_parameters.query is not None:
        #TODO: convert query to an XPath statement
        # run xpath against each content block
        # or, maybe have a separate/pluggable query processor for query?
        pass
    
    # Step #6
    # This is notional; real code would make a real decision here
    #TODO: maybe these should be a part of the model?
    results_available = True #TODO: Make this configurable, rather than hard coded
    split_results = True #TODO: Make this configurable, rather than hard coded
    will_push = True#TODO: Make this configurable rather than hard coded
    
    if results_available:
        #Create the stub poll_response that both cases use
        poll_response = tm11.PollResponse(message_id = tm11.generate_message_id(), in_response_to = poll_request.message_id, collection_name = collection.name)
        poll_response.result_part_number = 1
        if subscription:
                poll_response.subscription_id = subscription.subscription_id
        
        if split_results and len(results) > 1 and response_type != tm11.RT_COUNT_ONLY: #Create a result set and return the first result
            result_set = create_result_set(results, collection)
            #TODO: Add in timestamp labels (if necessary)
            poll_response.more = True
            cb_model = result_set.content_blocks.all().order_by('timestamp_label')[1]
            cb = taxiifiers.content_block_to_content_block(cb_model)
            poll_response.content_blocks.append(cb)
            poll_response.result_id = str(result_set.pk)
            return poll_response
        else: # Don't split the results
            poll_response.more = False
            poll_response.exclusive_begin_timestamp_label = filter_kwargs.get('timestamp_label__gt', None)
            poll_response.inclusive_end_timestamp_label = filter_kwargs.get('timestamp_label__lte', None)
            poll_response.record_count = tm11.RecordCount(len(results), False)
            
            if poll_request.poll_parameters.response_type == tm11.RT_FULL:
                for result in results:
                    cb = taxiifiers.content_block_to_content_block(result)
                    poll_response.content_blocks.append(cb)
            
            return poll_response
    else: #Results aren't available "now"
        if poll_request.allow_asynch:
            result_set = create_result_set(results, data_collection)
            sm = tm11.StatusMessage(message_id = tm11.generate_message_id, in_response_to = poll_request.message_id, status_type = tm11.ST_PENDING)
            sm.status_details = {'ESTIMATED_WAIT': 0, 'RESULT_ID': result_set.result_id, 'WILL_PUSH': False}
            return sm
        elif poll_request.delivery_parameters is not None and will_push: #We can do delivery parameters!
            result_set = create_result_set(results, data_collection)
            sm = tm11.StatusMessage(message_id = tm11.generate_message_id, in_response_to = poll_request.message_id, status_type = tm11.ST_PENDING)
            sm.status_details = {'ESTIMATED_WAIT': 0, 'RESULT_ID': result_set.result_id, 'WILL_PUSH': True}
            # TODO: How to build pushing into the system? This part of the workflow is broken until pushing is implemented somehow
            return sm
        else: # The results are not available, and we have no way to give them later!
            sm = tm11.StatusMessage(message_id = tm11.generate_message_id, in_response_to = poll_request.message_id, status_type = tm11.ST_FAILURE)
            sm.message = "The results were not available now and the request had allow_asynch=False and no Delivery Parameters were specified."
            return sm
        
    
    return "KJDLKSJALDKS"

def poll_fulfillment_handler(poll_service, poll_fulfillment_request, django_request):
    pass

def collection_information_handler(collection_management_service, collection_information_request, django_request):
    """
    This is the default handler for Collection Information Requests. It takes an Collection Management Service,
    CollectionInformationRequest, and Django Request and forms an appropriate DiscoveryResponse.
    
    Args:
        collection_management_service (collection_management_service model instance): The Collection Management Service being invoked
        collection_information_request (libtaxii.messages_11 CollectionInformationRequest): The Collection Information Request being responded to
        django_request (Django request): The Django request being responded to
    
    """
    
    # Create a stub CollectionInformationResponse
    cir = tm11.CollectionInformationResponse(message_id = tm11.generate_message_id(), in_response_to = collection_information_request.message_id)
    
    # For each collection that is advertised and enabled, create a Collection Information
    # object and add it to the Collection Information Response
    for collection in collection_management_service.advertised_collections.filter(enabled=True):
        ci = tm11.CollectionInformation(
            collection_name = collection.name,
            collection_description = collection.description,
            supported_contents = get_supported_content(collection),
            available = True,
            push_methods = get_push_methods(collection),
            polling_service_instances = get_polling_service_instances(collection),
            subscription_methods = get_subscription_methods(collection),
            collection_volume = None,#TODO: Maybe add this to the model?
            collection_type = collection.type,
            receiving_inbox_services = get_receiving_inbox_services(collection),
        )
        
        cir.append(ci)
    
    return cir

def subscription_management_handler(collection_management_service, subscription_management_request, django_request):
    """
    This is the default handler for Subscription Management Requests. It takes an Collection Management Service,
    SubscriptionManagementRequest, and Django Request and forms an appropriate DiscoveryResponse.
    
    Args:
        collection_management_service (collection_management_service model instance): The Collection Management Service being invoked
        subscription_management_request (libtaxii.messages_11 SubscriptionManagementRequest): The Subscription Management Information Request being responded to
        django_request (Django request): The Django request being responded to
    
    This handler blindly allows all requests.
    """
    
    # Create an alias because the name is long as fiddlesticks
    smr = subscription_management_request
        
    # This code follows the guidance in the TAXII Services Spec 1.1 Section 4.4.6. 
    # This code could probably be optimized, but it exists in part to be readable.
    
    # 1. This code doesn't do authentication, so this step is skipped
    
    # 2. If the Collection Name does not exist, respond with a Status Message
    try:
        data_collection = models.DataCollection.objects.get(collection_name = smr.collection_name, enabled=True)
    except:
        sm = tm11.StatusMessage(tm11.generate_message_id(), in_response_to=smr.message_id, status_type = tm11.ST_NOT_FOUND)
        sm.message = 'The collection you requested was not found'
        sm.status_detail = {'ITEM': smr.collection_name}
        return sm
    
    # 3. Unsubscribe actions should always succeed, even if there was not a subscription
    if smr.action == tm11.ACT_UNSUBSCRIBE:
        try:
            subscription = models.Subscription.get(subscription_id = smr.subscription_id)
            subscription.status == models.UNSUBSCRIBED_STATUS
            subscription.save()
        except:
            pass
        
        response = tm11.CollectionManagementResponse(message_id = tm11.generate_message_id(), in_response_to = smr.message_id)
        response.subscription_instance = tm11.SubscriptionInstance(
                                                subscription_id = smr.subscription_id,
                                                status = tm11.SS_UNSUBSCRIBED)
        return response
    
    # Create a stub ManageCollectionSubscriptionResponse
    response = tm11.ManageCollectionSubscriptionResponse(
                            message_id = tm11.generate_message_id(), 
                            in_response_to = smr.message_id,
                            collection_name = data_collection.collection_name)
    
    # 4. (paraphrased) Error checking
    if smr.action == tm11.ACT_SUBSCRIBE:
        # TODO: Check for supported push methods (e.g., inbox protocol, delivery message binding)
        
        # Check for unsupported / unknown Content Bindings / Subtypes
        
        # Supporting all is not an error
        accept_all_content = False
        if len(smr.subscription_parameters.content_bindings) == 0: # All bindings are supported
            accept_all_content = True
        
        #Iterate over specified content_bindings
        supported_contents = []
        for content_binding in smr.subscription_parameters.content_bindings:
            binding_id = content_binding.binding_id
            if len(content_binding.subtype_ids) == 0:
                # TODO: This probably needs to be in a try/catch block that returns the correct status message
                cbas = data_collection.supported_content.get(content_binding__binding_id = binding_id, subtype__subtype_id = None)
                supported_contents.append(cbas)
            else:
                for subtype_id in content_binding.subtype_ids:
                    # TODO: This probably needs to be in a try/catch block that returns the correct status message
                    cbas = data_collection.supported_content.get(content_binding__binding_id = binding_id, subtype__subtype_id = subtype_id)
                    supported_contents.append(cbas)
        
        # TODO: Check the query format and see if it works
        # TODO: Implement query
        
        # 5. Attempts to create a duplicate subscription should just return the existing subscription
        try:
            existing_subscription = models.Subscription.objects.get(
                            response_type = smr.subscription_parameters.response_type, 
                            accept_all_content = accept_all_content,
                            supported_content = supported_contents, # TODO: This is probably wrong
                            query = None, # TODO: Implement query
                            )
            
            response.subscription_instances.append(get_subscription_instance(existing_subscription))
            return response
        except:
            pass
        
        
        subscription = models.Subscription()
        # TODO: Set properties of the subscription
        subscription.save()
        
        response.subscription_instances.append(get_subscription_instance(subscription))
        return response
    
    if smr.action == tm11.ACT_STATUS and not smr.subscription_id:
        # This request is requesting the status of ALL subscriptions.
        # This is just a dummy PoC, so it returns all subscriptions
        # in the system for that Data Collection =)
        
        for subscription in models.Subscription.objects.filter(data_collection=data_collection):
            si = get_subscription_instance(subscription)
            response.subscription_instances.append(si)
        
        return response
    
    # 7. (OK - this one is out of order because it makes sense to put it out of order)
    #    Attempts to Pause/resume/status a non existent subscription should result
    #    in a Not Found Status Message
    try:
        subscription = models.Subscription.get(subscription_id = smr.subscription_id)
    except:
        sm = tm11.StatusMessage(tm11.generate_message_id(), in_response_to=smr.message_id, status_type = tm11.ST_NOT_FOUND)
        sm.message = 'The Subscription ID you requested was not found'
        sm.status_detail = {'ITEM': smr.subscription_id}
        return sm
    
    # 6. Pausing is idempotent
    if smr.action == tm11.ACT_PAUSE:
        subscription.status = models.PAUSED_STATUS
        subscription.save()
        response.subscription_instances.append(get_subscription_instance(subscription))
        return response
    
    # 6. Resuming is idempotent
    if smr.action == tm11.ACT_RESUME:
        subscription.status = models.ACTIVE_STATUS
        subscription.save()
        response.subscription_instances.append(get_subscription_instance(subscription))
        return response
    
    if smr.action == tm11.ACT_STATUS:
        response.subscription_instances.append(get_subscription_instance(subscription))
        return response
        
    
    raise Exception("This code shouldn't be reached!")
    

