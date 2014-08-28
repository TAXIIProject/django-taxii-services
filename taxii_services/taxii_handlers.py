# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

import handlers
import models

import libtaxii as t
import libtaxii.messages_11 as tm11
import libtaxii.messages_10 as tm10
import libtaxii.taxii_default_query as tdq
from libtaxii.constants import *
from libtaxii.common import generate_message_id
from base_taxii_handlers import MessageHandler

from exceptions import StatusMessageException

class DiscoveryRequest11Handler(MessageHandler):
    """
    Built-in TAXII 1.1 Discovery Request Handler.
    """
    supported_request_messages = [tm11.DiscoveryRequest]
    version = "1"
    
    @staticmethod
    def handle_message(discovery_service, discovery_request, django_request):        
        return discovery_service.to_discovery_response_11(discovery_request.message_id)

class DiscoveryRequest10Handler(MessageHandler):
    """
    Built-in TAXII 1.0 Discovery Request Handler
    """
    supported_request_messages = [tm10.DiscoveryRequest]
    version = "1"
    
    @staticmethod
    def handle_message(discovery_service, discovery_request, django_request):        
        return discovery_service.to_discovery_response_10(discovery_request.message_id)

class DiscoveryRequestHandler(MessageHandler):
    """
    Built-in TAXII 1.1 and TAXII 1.0 Discovery Request Handler
    """
    supported_request_messages = [tm10.DiscoveryRequest, tm11.DiscoveryRequest]
    version = "1"
    
    @staticmethod
    def handle_message(discovery_service, discovery_request, django_request):
        if isinstance(discovery_request, tm10.DiscoveryRequest):
            return DiscoveryRequest10Handler.handle_message(discovery_service, discovery_request, django_request)
        elif isinstance(discovery_request, tm11.DiscoveryRequest):
            return DiscoveryRequest11Handler.handle_message(discovery_service, discovery_request, django_request)
        else:
            raise StatusMessageException(taxii_message.message_id,
                                         ST_FAILURE,
                                         "TAXII Message not supported by Message Handler.")

class InboxMessage11Handler(MessageHandler):
    """
    Built-in TAXII 1.1 Inbox Message Handler.
    """
    
    supported_request_messages = [tm11.InboxMessage]
    version = "1"
    
    @staticmethod
    def handle_message(inbox_service, inbox_message, django_request):
        
        collections = inbox_service.validate_destination_collection_names(inbox_message.destination_collection_names, inbox_message.message_id)
        
        # Store certain information about this Inbox Message in the database for bookkeeping
        inbox_message_db = models.InboxMessage.from_inbox_message_11(inbox_message, django_request, received_via = inbox_service)
        inbox_message_db.save()
        
        # Iterate over the ContentBlocks in the InboxMessage and try to add
        # them to the database
        saved_blocks = 0
        for content_block in inbox_message.content_blocks:
            
            saved = False
            cb = models.ContentBlock.from_content_block_11(content_block)
            
            # If there are not any destination collections and the
            # Inbox Service supports the Content Binding and Subtype add the Content Block
            # to the database (by calling .save())
            if len(collections) == 0 and inbox_service.is_content_supported(content_block.content_binding_and_subtype):
                cb.save() # Save the Content Block
                saved = True
            
            # If there are destination collections, for each collection: 
            # If that collection supports the Content Binding and Subtype, associate
            # The ContentBlock with the Data Collection
            for collection in collections:
                if collection.is_content_supported(cb.content_binding_and_subtype):
                    if not saved:
                        cb.save()
                        saved = True
                    collection.content_blocks.add(cb)
            
            # If the ContentBlock was saved to the DB, update
            # the running tally
            if saved:
                saved_blocks += 1
        
        # Update the Inbox Message model with the number of ContentBlocks that were saved
        inbox_message_db.content_blocks_saved = saved_blocks
        inbox_message_db.save()
        
        #Create and return a Status Message indicating success
        status_message = tm11.StatusMessage(message_id = generate_message_id(), 
                                            in_response_to=inbox_message.message_id, 
                                            status_type = ST_SUCCESS)
        return status_message

class InboxMessage10Handler(MessageHandler):
    """
    Built in TAXII 1.0 Message Handler
    """
    supported_request_messages = [tm10.InboxMessage]
    version = "1"
    
    DEBUG=True
    
    @staticmethod
    def handle_message(inbox_service, inbox_message, django_request):
        pass

class InboxMessageHandler(MessageHandler):
    """
    Built-in TAXII 1.1 and 1.0 Message Handler
    """
    supported_request_messages = [tm10.InboxMessage, tm11.InboxMessage]
    version = "1"
    
    DEBUG=True
    
    @staticmethod
    def handle_message(inbox_service, inbox_message, django_request):
        if isinstance(inbox_message, tm10.InboxMessage):
            return InboxMessage10Handler.handle_message(inbox_service, inbox_message, django_request)
        elif isinstance(inbox_message, tm11.InboxMessage):
            return InboxMessage11Handler.handle_message(inbox_service, inbox_message, django_request)
        else:
            raise StatusMessageException(taxii_message.message_id,
                                         ST_FAILURE,
                                         "TAXII Message not supported by Message Handler.")

class PollFulfillmentRequest11Handler(MessageHandler):
    """
    Built-in TAXII 1.1 Poll Fulfillment Request Handler.
    """
    supported_request_messages = [tm11.PollFulfillmentRequest]
    version = "1"
    
    @staticmethod
    def handle_message(poll_service, poll_fulfillment_request, django_request):
        #TODO: poll_service isn't used. does that mean my application logic is wrong?
        try:
            rsp = models.ResultSetPart.objects.get(result_set__pk = poll_fulfillment_request.result_id,
                                           part_number = poll_fulfillment_request.result_part_number,
                                           result_set__data_collection__name = poll_fulfillment_request.collection_name)
            
            poll_response = rsp.to_poll_response_11(poll_fulfillment_request.message_id)
            rsp.result_set.last_part_returned = rsp
            rsp.save()
            return poll_response
        except models.ResultSetPart.DoesNotExist:
            raise StatusMessageException(poll_fulfillment_request.message_id,
                                         ST_NOT_FOUND,
                                         {SD_ITEM: 'TBD'})

# PollFulfillment is new in TAXII 1.1, so there aren't any TAXII 1.0 handlers for it

class PollRequest11Handler(MessageHandler):
    """
    Built-in TAXII 1.1 Poll Request Handler
    """
    
    supported_request_messages = [tm11.PollRequest]
    version = "1"
    
    @staticmethod
    def handle_message(poll_service, poll_request, django_request):
        """
        The Poll Service is actually a little complicated, so the workflow for this method is documented here:
        
        1. Check if the named Data Collection exists. Return a Status Message if the Data Collection doesn't exist.
        2. Pull the request parameters out of the stored subscription OR
        3. Pull the request parameters our of the request itself.
        4. Make a database query (Note: Not a TAXII Query, yet) to get a list of potential results.
        5. If a TAXII Query is present in the request, loop over each potential result and apply the query
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
        collection = poll_service.validate_collection_name(poll_request.collection_name, poll_request.message_id)
        
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
        response_type = RT_FULL
        content_binding = None
        query = None
        delivery_parameters = None
        
        # Step #2
        subscription = None
        if poll_request.subscription_id:
            try:
                subscription = models.Subscription.get(subscription_id = poll_request.subscription_id)
            except:
                raise StatusMessageException(poll_request.message_id, 
                                             ST_NOT_FOUND, 
                                             'The Subscription ID was not found in the system!',
                                             {SD_ITEM: poll_request.subscription_id})
            
            if subscription.status != SS_ACTIVE:
                raise StatusMessageException(poll_request.message_id,
                                             ST_FAILURE,
                                             'The Subscription is not active!')
            
            allow_asynch = False#subscription.allow_asynch; MSD: This isn't in a subscription???
            response_type = subscription.response_type
            content_bindings = subscription.content_binding_and_subtype.all()
            query = tdq.DefaultQuery.from_xml(subscription.query) # TODO: Something needs to be done here
            delivery_parameters = subscription.push_parameters
        # Step #3
        elif poll_request.poll_parameters:
            allow_asynch = poll_request.poll_parameters.allow_asynch
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
        # (Query is a libtaxii.taxii_default_query object)
        if query is not None:
            try:
                #In theory, you could have two supported_query objects that use
                #The same query handler but have different Supported/Preferred Queries
                # Unless.... The Supported/Preferred Queries is a property of the 
                # Class and not a configuration item.
                # That would be nice!
                query_handler = poll_service.supported_queries.get(query_handler__targeting_expression_id = query.targeting_expression_id)
            except:
                raise # TODO: Return a proper Status Message saying query not supported
            
            #TODO: Add a part where we ask the query handler if it supported
            # the query or something
            
            result_set = []
            for result in results:#TODO: The code in this block hasn't been tested and will probably fail
                if query_handler(result, query):
                    result_set.append(result)
            
            results = result_set
        
        # Step #6
        # This is notional; real code would make a real decision here
        #TODO: maybe these should be a part of the model?
        results_available = True #TODO: Make this configurable, rather than hard coded
        split_results = True #TODO: Make this configurable, rather than hard coded
        will_push = True#TODO: Make this configurable rather than hard coded
        if results_available:
            # TODO: The "magic number" 3 should be made a property of the Poll Service
            if split_results and len(results) > 3 and response_type == RT_FULL: #Create a result set and return the first result
                result_set = handlers.create_result_set(results, collection)
                rsp_1 = models.ResultSetPart.objects.get(result_set__pk = result_set.pk, part_number = 1)
                poll_response = rsp_1.to_poll_response_11(poll_request.message_id)
                result_set.last_part_returned = rsp_1
                result_set.save()
                response = poll_response
            else: # Don't split the results
                poll_response = tm11.PollResponse(message_id = generate_message_id(), 
                                                  in_response_to = poll_request.message_id, 
                                                  collection_name = collection.name,
                                                  result_part_number = 1,
                                                  more = False,
                                                  exclusive_begin_timestamp_label = filter_kwargs.get('timestamp_label__gt', None),
                                                  inclusive_end_timestamp_label = filter_kwargs.get('timestamp_label__lte', None),
                                                  record_count = tm11.RecordCount(len(results), False))
                if subscription:
                        poll_response.subscription_id = subscription.subscription_id
                
                if poll_request.poll_parameters.response_type == RT_FULL:
                    for result in results:
                        poll_response.content_blocks.append(result.to_content_block_11())
                
                response = poll_response
        else: #Results aren't available "now"
            if poll_request.allow_asynch:
                result_set = create_result_set(results, collection)
                sm = tm11.StatusMessage(message_id = generate_message_id(), in_response_to = poll_request.message_id, status_type = ST_PENDING)
                sm.status_details = {'ESTIMATED_WAIT': 0, 'RESULT_ID': result_set.pk, 'WILL_PUSH': False}
                response = sm
            elif poll_request.delivery_parameters is not None and will_push: #We can do delivery parameters!
                result_set = create_result_set(results, data_collection)
                sm = tm11.StatusMessage(message_id = generate_message_id(), in_response_to = poll_request.message_id, status_type = ST_PENDING)
                sm.status_details = {'ESTIMATED_WAIT': 0, 'RESULT_ID': result_set.pk, 'WILL_PUSH': True}
                # TODO: How to build pushing into the system? This part of the workflow is broken until pushing is implemented somehow
                response = sm
            else: # The results are not available, and we have no way to give them later!
                sm = tm11.StatusMessage(message_id = generate_message_id(), in_response_to = poll_request.message_id, status_type = ST_FAILURE)
                sm.message = "The results were not available now and the request had allow_asynch=False and no Delivery Parameters were specified."
                response = sm
            
        return response

class PollRequest10Handler(MessageHandler):
    """
    Built-in TAXII 1.0 Poll Request Handler
    """
    supported_request_messages = [tm10.PollRequest]
    version = "1"
    
    @staticmethod
    def handle_message(poll_service, poll_message, django_request):
        pass

class PollRequestHandler(MessageHandler):
    """
    Built-in TAXII 1.1 and TAXII 1.0 Poll Request Handler
    """
    
    supported_request_messages = [tm10.PollRequest, tm11.PollRequest]
    version = "1"
    
    @staticmethod
    def handle_message(poll_service, poll_message, django_request):
        if isinstance(poll_message, tm10.InboxMessage):
            return PollRequest10Handler.handle_message(poll_service, poll_message, django_request)
        elif isinstance(poll_message, tm11.InboxMessage):
            return PollRequest11Handler.handle_message(poll_service, poll_message, django_request)
        else:
            raise StatusMessageException(taxii_message.message_id,
                                         ST_FAILURE,
                                         "TAXII Message not supported by Message Handler.")

class CollectionInformationRequest11Handler(MessageHandler):
    """
    Built-in TAXII 1.1 Collection Information Request Handler.
    """
    supported_request_messages = [tm11.CollectionInformationRequest]
    version = "1"
    
    @staticmethod
    def handle_message(collection_management_service, collection_information_request, django_request):
        """
        Just a straightforward response.
        """
        in_response_to = collection_information_request.message_id
        return collection_management_service.to_collection_information_response_11(in_response_to)

class FeedInformationRequest10Handler(MessageHandler):
    """
    Built-in TAXII 1.0 Feed Information Request Handler
    """
    supported_request_messages = [tm10.FeedInformationRequest]
    version = "1"
    
    @staticmethod
    def handle_message(collection_management_service, feed_information_request, django_request):
        """
        Just a straightforward response.
        """
        in_response_to = feed_information_request.message_id
        return collection_management_service.to_feed_information_response_10(in_response_to)

class CollectionInformationRequestHandler(MessageHandler):
    """
    Built-in TAXII 1.1 and 1.0 Collection/Feed Information Request handler.
    """
    
    supported_request_messages = [tm10.FeedInformationRequest, tm11.CollectionInformationRequest]
    version = "1"
    
    @staticmethod
    def handle_message(collection_management_service, collection_information_request, django_request):
        #aliases because the names are long
        cms = collection_management_service
        cir = collection_information_request
        dr = django_request
        
        if isinstance(collection_information_request, tm10.FeedInformationRequest):
            return FeedInformationRequest10Handler.handle_message(cms, cir, dr)
        elif isinstance(collection_information_request, tm11.CollectionInformationRequest):
            return CollectionInformationRequest11Handler.handle_message(cms, cir, dr)
        else:
            raise ValueError("Unsupported message!")

class SubscriptionRequest11Handler(MessageHandler):
    """
    Built-in TAXII 1.1 Manage Collection Subscription Request Handler.
    """
    
    supported_request_messages = [tm11.ManageCollectionSubscriptionRequest]
    version = "1"
    
    @staticmethod
    def handle_message(collection_management_service, manage_collection_subscription_request, django_request):
        # Create an alias because the name is long as fiddlesticks
        smr = manage_collection_subscription_request
            
        # This code follows the guidance in the TAXII Services Spec 1.1 Section 4.4.6. 
        # This code could probably be optimized, but it exists in part to be readable.
        
        # 1. This code doesn't do authentication, so this step is skipped
        
        # 2. If the Collection Name does not exist, respond with a Status Message
        try:
            data_collection = models.DataCollection.objects.get(collection_name = smr.collection_name, enabled=True)
        except:
            sm = tm11.StatusMessage(generate_message_id(), in_response_to=smr.message_id, status_type = ST_NOT_FOUND)
            sm.message = 'The collection you requested was not found'
            sm.status_detail = {'ITEM': smr.collection_name}
            return sm
        
        # 3. Unsubscribe actions should always succeed, even if there was not a subscription
        if smr.action == ACT_UNSUBSCRIBE:
            try:
                subscription = models.Subscription.get(subscription_id = smr.subscription_id)
                subscription.status == models.UNSUBSCRIBED_STATUS
                subscription.save()
            except:
                pass
            
            response = tm11.CollectionManagementResponse(message_id = generate_message_id(), in_response_to = smr.message_id)
            response.subscription_instance = tm11.SubscriptionInstance(
                                                    subscription_id = smr.subscription_id,
                                                    status = SS_UNSUBSCRIBED)
            return response
        
        # Create a stub ManageCollectionSubscriptionResponse
        response = tm11.ManageCollectionSubscriptionResponse(
                                message_id = generate_message_id(), 
                                in_response_to = smr.message_id,
                                collection_name = data_collection.collection_name)
        
        # 4. (paraphrased) Error checking
        if smr.action == ACT_SUBSCRIBE:
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
        
        if smr.action == ACT_STATUS and not smr.subscription_id:
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
            sm = tm11.StatusMessage(generate_message_id(), in_response_to=smr.message_id, status_type = ST_NOT_FOUND)
            sm.message = 'The Subscription ID you requested was not found'
            sm.status_detail = {'ITEM': smr.subscription_id}
            return sm
        
        # 6. Pausing is idempotent
        if smr.action == ACT_PAUSE:
            #TODO: For pause, need to note when the pause happened so delivery of content can resum
            # continuously
            # Maybe update to say if status != paused_status
            #                               status = paused_status
            # and use the last_udpated as a note of when the pause happened
            subscription.status = models.PAUSED_STATUS
            subscription.save()
            response.subscription_instances.append(get_subscription_instance(subscription))
            return response
        
        # 6. Resuming is idempotent
        if smr.action == ACT_RESUME:
            subscription.status = models.ACTIVE_STATUS
            subscription.save()
            response.subscription_instances.append(get_subscription_instance(subscription))
            return response
        
        if smr.action == ACT_STATUS:
            response.subscription_instances.append(get_subscription_instance(subscription))
            return response
            
        
        raise Exception("This code shouldn't be reached!")

class SubscriptionRequest10Handler(MessageHandler):
    """
    Built-in TAXII 1.0 Manage Collection Subscription Request Handler.
    """
    
    supported_request_messages = [tm10.ManageFeedSubscriptionRequest]
    version = "1"
    
    @staticmethod
    def handle_message(feed_management_service, manage_feed_subscription_request, django_request):
        pass

class SubscriptionRequestHandler(MessageHandler):
    """
    Built-in TAXII 1.1 and TAXII 1.0 Management Collection/Feed Subscription Request Handler.
    """
    
    supported_request_messages = [tm11.ManageCollectionSubscriptionRequest, tm10.ManageFeedSubscriptionRequest]
    version = "1"
    
    @staticmethod
    def handle_message(collection_management_service, manage_collection_subscription_request, django_request):
        #aliases because names are long
        cms = collection_management_service
        mcsr = manage_collection_subscription_request
        dr = django_request
        
        if isinstance(mcsr, tm10.ManageFeedSubscriptionRequest):
            return SubscriptionRequest10Handler.handle_message(cms, mcsr, dr)
        elif isinstance(mcsr, tm11.ManageCollectionSubscriptionRequest):
            return SubscriptionRequest11Handler.handle_message(cms, mcsr, dr)
        else:
            raise StatusMessageException(taxii_message.message_id,
                                         ST_FAILURE,
                                         "TAXII Message not supported by Message Handler.")

def register_message_handlers(handler_list=None):
    import management, inspect, taxii_services.taxii_handlers
        
    v = vars(taxii_services.taxii_handlers)
    
    if not handler_list:
        handler_list = []
        for name, obj in v.iteritems():
            if inspect.isclass(obj) and obj.__module__ == 'taxii_services.taxii_handlers':
                handler_list.append(name)
    
    for handler in handler_list:
        obj = v.get(handler, None)
        if (  not obj or
              not inspect.isclass(obj)  or
              not obj.__module__ == 'taxii_services.taxii_handlers' ):
            raise ValueError('%s is not a valid Message Handler' % handler)
        
        assert issubclass(obj, MessageHandler)
        
        management.register_message_handler(obj, handler)
