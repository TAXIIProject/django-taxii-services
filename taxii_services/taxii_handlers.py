# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

import handlers
import taxiifiers
import models

import libtaxii as t
import libtaxii.messages_11 as tm11
import libtaxii.taxii_default_query as tdq

from exceptions import StatusMessageException
from itertools import chain

class DefaultQueryHandler(object):
    """
    Blah blah blah.
    Extend this for query support
    """
    
    supported_targeting_expression = None
    supported_capability_modules = None
    supported_scope_message = None
    
    @classmethod
    def get_supported_capability_modules(cls):
        """
        Returns a list of strings indicating the Capability Modules this 
        class supports. Pulls from the 
        supported_capability_modules class variable set by the 
        child class
        """
        if not cls.supported_capability_modules:
            raise ValueError('The variable \'supported_capability_modules\' has not been defined by the subclass!')
        return cls.supported_capability_modules
    
    @classmethod
    def get_supported_targeting_expression(cls):
        """
        Returns a string indicating the targeting expression this 
        class supports. Pulls from the 
        supported_targeting_expression class variable set by the 
        child class
        """
        if not cls.supported_targeting_expression:
            raise ValueError('The variable \'supported_targeting_expression\' has not been defined by the subclass!')
        return cls.supported_targeting_expression
    
    @classmethod
    def get_supported_scope_message(cls):
        pass#TODO: is this worthwhile?
    
    @staticmethod
    def is_scope_supported(scope):
        """
        Given a DefaultQueryScope object, return True
        if that scope is supported or False if it is not.
        """
        raise NotImplementedError()
    
    @staticmethod
    def execute_query(content_block_list, query):
        """
        Given a query and a list of tm11.ContentBlock objects,
        return a list of tm11.ContentBlock objects that
        match the query
        """
        raise NotImplementedError()

class MessageHandler(object):
    """
    Blah blah blah
    Extend this for message exchange support
    """
    
    # This variable identifies a list of supported request messages.
    # Each value should be something like libtaxii.messages_11.StatusMessage
    supported_request_messages = None
    
    @classmethod
    def get_supported_request_messages(cls):
        if not cls.supported_request_messages:
            raise ValueError('The variable \'supported_request_messages\' has not been defined by the subclass!')
        return cls.supported_request_messages
    
    @staticmethod
    def handle_message(service, taxii_message, django_request):
        """
        Takes a service model, TAXII Message, and django request
        
        MUST return a tm11 TAXII Message
        """
        raise NotImplementedError()

class DiscoveryRequestHandler(MessageHandler):
    """
    Built-in Discovery Request Handler.
    """
    supported_request_messages = [tm11.DiscoveryRequest]
    
    @staticmethod
    def handle_message(discovery_service, discovery_request, django_request):        
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

class InboxMessageHandler(MessageHandler):
    """
    Built-in Inbox Message Handler.
    """
    
    supported_request_messages = [tm11.InboxMessage]
    
    @staticmethod
    def check_dcns(inbox_service, inbox_message):
        """
        Helper method to validate the number of Destination
        Collection Names present in the message
        """
        
        # Calculate the number of Destination Collection Names present in the InboxMessage
        num_dcns = len(inbox_message.destination_collection_names)
        
        # Error check 1 of 2 for Destination Collection Names
        # If Destination Collection Name is required but there aren't any, return a Status Message
        if inbox_service.destination_collection_status == models.REQUIRED and num_dcns == 0:
            sm = tm11.StatusMessage(tm11.generate_message_id(), in_response_to=inbox_message.message_id, status_type=tm11.ST_DESTINATION_COLLECTION_ERROR)
            sm.message = 'A Destination_Collection_Name is required and none were specified'
            sm.status_detail = get_inbox_acceptable_destinations(inbox_service)
            raise StatusMessageException(sm)
        
        # Error check 2 of 2 for Destination Collection Names
        # If Destination Collection Name is prohibited but there are more than one, return a Status Message
        if inbox_service.destination_collection_status == models.PROHIBITED and num_dcns > 0:
            sm = tm11.StatusMessage(tm11.generate_message_id(), in_response_to=inbox_message.message_id, status_type=tm11.ST_DESTINATION_COLLECTION_ERROR)
            sm.message = 'Destination_Collection_Names are prohibited'
            raise StatusMessageException(sm)
    
    @staticmethod
    def get_destination_data_collections(inbox_service, inbox_message):
        """
        For each Destination Collection Name specified in the Inbox Message, attempt to
        locate it in the database. If a lookup fails, respond with a Status Message
        If there are no Destination Collection Names specified in the Inbox Message,
        The code in the loop will not be executed
        """
        
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
                raise StatusMessageException(sm)
        
        return collections
    
    @staticmethod
    def handle_message(inbox_service, inbox_message, django_request):
        
        InboxMessageHandler.check_dcns(inbox_service, inbox_message)
        collections = InboxMessageHandler.get_destination_data_collections(inbox_service, inbox_message)
        
        # Store certain information about this Inbox Message in the database for bookkeeping
        inbox_message_db = handlers.create_inbox_message_db(inbox_message, django_request, received_via = inbox_service)
        
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
                if len(collections) == 0 and handlers.is_content_supported(inbox_service, content_block):
                    cb.save() # Save the Content Block
                    saved = True
                
                # If there are destination collections, for each collection: 
                # If that collection supports the Content Binding and Subtype, associate
                # The ContentBlock with the Data Collection
                for collection in collections:
                    if handlers.is_content_supported(collection, content_block):
                        if not saved:
                            cb.save()
                            saved = True
                        collection.content_blocks.add(cb)
                
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

class PollFulfillmentRequestHandler(MessageHandler):
    """
    Built-in Poll Fulfillment Request Handler.
    """
    supported_request_messages = [tm11.PollFulfillmentRequest]
    
    @staticmethod
    def handle_message(poll_service, poll_fulfillment_request, django_request):
        #TODO: poll_service isn't used. does that mean my application logic is wrong?
        try:
            rsp = models.ResultSetPart.get(result_set__pk = poll_fulfillment_request.result_id,
                                           result_part_number = poll_fulfillment_request.result_part_number,
                                           result_set__collection__name = poll_fullfillment_request.collection_name)
            
            poll_response = taxiifiers.result_set_part_to_poll_response(rsp, poll_fulfillment_request.message_id)
            rsp.result_set.last_part_returned = rsp
            return poll_response
        except:
            raise #TODO: After this has been tested, return an appropriate Status Message

class PollRequestHandler(MessageHandler):
    """
    Built-in Poll Request Handler
    """
    
    supported_request_messages = [tm11.PollRequest]
    
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
            if split_results and len(results) > 3 and response_type == tm11.RT_FULL: #Create a result set and return the first result
                result_set = handlers.create_result_set(results, collection)
                rsp_1 = models.ResultSetPart.objects.get(result_set__pk = result_set.pk, part_number = 1)
                poll_response = taxiifiers.result_set_part_to_poll_response(rsp_1, poll_request.message_id)
                result_set.last_part_returned = rsp_1
                result_set.save()
                response = poll_response
            else: # Don't split the results
                poll_response = tm11.PollResponse(message_id = tm11.generate_message_id(), 
                                                  in_response_to = poll_request.message_id, 
                                                  collection_name = collection.name,
                                                  result_part_number = 1,
                                                  more = False,
                                                  exclusive_begin_timestamp_label = filter_kwargs.get('timestamp_label__gt', None),
                                                  inclusive_end_timestamp_label = filter_kwargs.get('timestamp_label__lte', None),
                                                  record_count = tm11.RecordCount(len(results), False))
                if subscription:
                        poll_response.subscription_id = subscription.subscription_id
                
                if poll_request.poll_parameters.response_type == tm11.RT_FULL:
                    for result in results:
                        cb = taxiifiers.content_block_to_content_block(result)
                        poll_response.content_blocks.append(cb)
                
                response = poll_response
        else: #Results aren't available "now"
            if poll_request.allow_asynch:
                result_set = create_result_set(results, collection)
                sm = tm11.StatusMessage(message_id = tm11.generate_message_id, in_response_to = poll_request.message_id, status_type = tm11.ST_PENDING)
                sm.status_details = {'ESTIMATED_WAIT': 0, 'RESULT_ID': result_set.pk, 'WILL_PUSH': False}
                response = sm
            elif poll_request.delivery_parameters is not None and will_push: #We can do delivery parameters!
                result_set = create_result_set(results, data_collection)
                sm = tm11.StatusMessage(message_id = tm11.generate_message_id, in_response_to = poll_request.message_id, status_type = tm11.ST_PENDING)
                sm.status_details = {'ESTIMATED_WAIT': 0, 'RESULT_ID': result_set.pk, 'WILL_PUSH': True}
                # TODO: How to build pushing into the system? This part of the workflow is broken until pushing is implemented somehow
                response = sm
            else: # The results are not available, and we have no way to give them later!
                sm = tm11.StatusMessage(message_id = tm11.generate_message_id, in_response_to = poll_request.message_id, status_type = tm11.ST_FAILURE)
                sm.message = "The results were not available now and the request had allow_asynch=False and no Delivery Parameters were specified."
                response = sm
            
        return response


class CollectionInformationRequestHandler(MessageHandler):
    """
    Built-in Collection Information Request Handler.
    """
    supported_request_messages = [tm11.CollectionInformationRequest]
    
    @staticmethod
    def handle_message(collection_management_service, collection_information_request, django_request):
        # Create a stub CollectionInformationResponse
        cir = tm11.CollectionInformationResponse(message_id = tm11.generate_message_id(), in_response_to = collection_information_request.message_id)
        
        # For each collection that is advertised and enabled, create a Collection Information
        # object and add it to the Collection Information Response
        for collection in collection_management_service.advertised_collections.filter(enabled=True):
            ci = tm11.CollectionInformation(
                collection_name = collection.name,
                collection_description = collection.description,
                supported_contents = taxiifiers.model_get_supported_content(collection),
                available = True,
                push_methods = taxiifiers.data_collection_get_push_methods(collection),
                polling_service_instances = taxiifiers.data_collection_get_polling_service_instances(collection),
                subscription_methods = taxiifiers.data_collection_get_subscription_methods(collection),
                collection_volume = None,#TODO: Maybe add this to the model?
                collection_type = collection.type,
                receiving_inbox_services = taxiifiers.data_collection_get_receiving_inbox_services(collection),
            )
            
            cir.collection_informations.append(ci)
        
        return cir

class ManageCollectionSubscriptionRequestHandler(MessageHandler):
    """
    Built-in Management Collection Subscription Request Handler.
    """
    
    supported_request_messages = [tm11.ManageCollectionSubscriptionRequest]
    
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
        if smr.action == tm11.ACT_RESUME:
            subscription.status = models.ACTIVE_STATUS
            subscription.save()
            response.subscription_instances.append(get_subscription_instance(subscription))
            return response
        
        if smr.action == tm11.ACT_STATUS:
            response.subscription_instances.append(get_subscription_instance(subscription))
            return response
            
        
        raise Exception("This code shouldn't be reached!")

class Stix111QueryHandler(DefaultQueryHandler):
    """
    Handles TAXII Default Queries for STIX 1.1.1
    """
    
    supported_targeting_expression = t.CB_STIX_XML_111
    supported_capability_modules = [tdq.CM_CORE, tdq.CM_REGEX, tdq.CM_TIMESTAMP]
    
    @staticmethod
    def is_scope_supported(scope):
        return False, "Nothing is supported at the moment"
    
    @staticmethod
    def execute_query(content_block_list, query):
        #TODO: Actually implement this!
        return content_block_list
