# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from .base_taxii_handlers import MessageHandler
from .exceptions import StatusMessageException
import handlers
import models
from .util import PollRequestProperties

import libtaxii as t
import libtaxii.messages_11 as tm11
import libtaxii.messages_10 as tm10
import libtaxii.taxii_default_query as tdq
from libtaxii.constants import *
from libtaxii.common import generate_message_id

import dateutil.parser
import datetime
from dateutil.tz import tzutc

class DiscoveryRequest11Handler(MessageHandler):
    """
    Built-in TAXII 1.1 Discovery Request Handler.
    """
    supported_request_messages = [tm11.DiscoveryRequest]
    version = "1"
    
    @staticmethod
    def handle_message(discovery_service, discovery_request, django_request):
        """
        Returns a listing of all advertised services.
        """
        return discovery_service.to_discovery_response_11(discovery_request.message_id)

class DiscoveryRequest10Handler(MessageHandler):
    """
    Built-in TAXII 1.0 Discovery Request Handler
    """
    supported_request_messages = [tm10.DiscoveryRequest]
    version = "1"
    
    @staticmethod
    def handle_message(discovery_service, discovery_request, django_request):
        """
        Returns a listing of all advertised services.
        """
        return discovery_service.to_discovery_response_10(discovery_request.message_id)

class DiscoveryRequestHandler(MessageHandler):
    """
    Built-in TAXII 1.1 and TAXII 1.0 Discovery Request Handler
    """
    supported_request_messages = [tm10.DiscoveryRequest, tm11.DiscoveryRequest]
    version = "1"
    
    @staticmethod
    def handle_message(discovery_service, discovery_request, django_request):
        """
        Passes the message off to either DiscoveryRequest10Handler or DiscoveryRequest11Handler
        """
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
    
    @classmethod
    def save_content_block(cls, content_block, supporting_collections):
        """
        Saves the content_block in the database and
        associates it with all specified supporting_collections.
        
        This can be overriden to save the content block in a custom way.
        
        Arguments:
            content_block (tm11.ContentBlock) - The content block to save
            supporting_collections (list of models.DataCollection) - The Data Collections to add this content_block to
            inbox_service (models.InboxService) - The inbox service to add this content_block to, or None
        
        """
        cb = models.ContentBlock.from_content_block_11(content_block)
        cb.save()
        
        for collection in supporting_collections:
            collection.content_blocks.add(cb)
    
    @classmethod
    def handle_message(cls, inbox_service, inbox_message, django_request):
        """
        1. Validate the Destination Collection Names against the inbox_service
        model, 
        
        2. Create a models.InboxMessage for bookkeeping
        
        3. For each content_block in the inbox_message, 
        3a. If not supported by the inbox_service or any Destination Collection Name, skip
        3b. Otherwise, add it to the database and associate it with any Destination Collections 
            that support the content binding
        """
        
        collections = inbox_service.validate_destination_collection_names(
                                    inbox_message.destination_collection_names, 
                                    inbox_message.message_id)
        
        # Store certain information about this Inbox Message in the database for bookkeeping
        inbox_message_db = models.InboxMessage.from_inbox_message_11(
                                                        inbox_message, 
                                                        django_request, 
                                                        received_via = inbox_service)
        inbox_message_db.save()
        
        # Iterate over the ContentBlocks in the InboxMessage and try to add
        # them to the database
        saved_blocks = 0
        for content_block in inbox_message.content_blocks:
            inbox_support_info = inbox_service.is_content_supported(content_block.content_binding)
                
            supporting_collections = []
            for collection in collections:
                collection_support_info = collection.is_content_supported(content_block.content_binding)
                if collection_support_info.is_supported:
                    supporting_collections.append(collection)
            
            if len(supporting_collections) == 0 and not inbox_support_info.is_supported:
                # There's nothing to add this content block to
                continue
            
            cls.save_content_block(content_block, supporting_collections)
            
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
    
    @staticmethod
    def handle_message(inbox_service, inbox_message, django_request):
        """
        TODO: Implement this handler
        """
        raise NotImplementedError()

class InboxMessageHandler(MessageHandler):
    """
    Built-in TAXII 1.1 and 1.0 Message Handler
    """
    supported_request_messages = [tm10.InboxMessage, tm11.InboxMessage]
    version = "1"
    
    @staticmethod
    def handle_message(inbox_service, inbox_message, django_request):
        """
        Passes the request to either InboxMessage10Handler or InboxMessage11Handler
        """
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
        """
        Looks in the database for a matching result set part and return it
        """
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
                                         {SD_ITEM: str(poll_fulfillment_request.result_id)  })

# PollFulfillment is new in TAXII 1.1, so there aren't any TAXII 1.0 handlers for it

class PollRequest11Handler(MessageHandler):
    """
    Built-in TAXII 1.1 Poll Request Handler.
    
    This handler has multiple extension points for developers
    who want to extend and/or customize this class.
    """
    
    supported_request_messages = [tm11.PollRequest]
    version = "1"
    
    @classmethod
    def get_content(cls, prp, query_kwargs):
        """
        Given a poll_params_dict get content from the database.
        Arguments:
            params_dict - The parameters of the search for content
        Returns:
            An list of models.ContentBlock objects. Classes that override
            this method only need to return an iterable where each class has
            a 'to_content_block_11()' function.
        """
        content = prp.collection.content_blocks.filter(**query_kwargs).order_by('timestamp_label')
        
        return content
    
    @classmethod
    def create_poll_response(cls, poll_service, prp, content):
        """
        Creates a poll response.
        
        If the request's response type is "Count Only", 
        a single poll response w/ more=False used.
        
        If the content size is less than the poll_service's
        max_result_size, a poll response w/ more=False is used.
        
        If the poll_service's max_result_size is blank,
        a poll response w/ more=False used.
        
        If the response type is "Full" and the total
        number of contents are greater than the 
        poll_service's max_result_size, a ResultSet
        is created, and a PollResponse w/more=True is used.
        """
        
        content_count = len(content)
        
        # RT_COUNT_ONLY - Always use a single result
        # RT_FULL - Use a single response if 
        #           poll_service.max_result_size is None or
        #           len(content) <= poll_service.max_result_size
        #           Use a Multi-Part response otherwise
        
        if ( prp.response_type == RT_COUNT_ONLY or 
             poll_service.max_result_size is None or
             content_count <= poll_service.max_result_size):
            poll_response = tm11.PollResponse(message_id = generate_message_id(), 
                                              in_response_to = prp.message_id, 
                                              collection_name = prp.collection.name,
                                              result_part_number = 1,
                                              more = False,
                                              exclusive_begin_timestamp_label = prp.exclusive_begin_timestamp_label,
                                              inclusive_end_timestamp_label = prp.inclusive_end_timestamp_label,
                                              record_count = tm11.RecordCount(content_count, False))
            if prp.subscription:
                    poll_response.subscription_id = prp.subscription.subscription_id
            
            if prp.response_type == RT_FULL:
                for c in content:
                    poll_response.content_blocks.append(c.to_content_block_11())
        else:
            # Split into multiple result sets
            result_set = handlers.create_result_set(poll_service, prp, content)
            rsp_1 = models.ResultSetPart.objects.get(result_set__pk = result_set.pk, part_number = 1)
            poll_response = rsp_1.to_poll_response_11(prp.message_id)
            result_set.last_part_returned = rsp_1
            result_set.save()
            response = poll_response
        
        return poll_response
    
    @classmethod
    def create_pending_response(cls, poll_service, prp, content):
        """
        This method returns a StatusMessage with a Status Type 
        of pending OR raises a StatusMessageException
        based on the following table:
        
        asynch | Delivery_Params | can_push || Response Type
        ----------------------------------------------------
        True   | -               | -        || Pending - Asynch
        False  | Yes             | Yes      || Pending - Push
        False  | Yes             | No       || StatusMessageException
        False  | No              | -        || StatusMessageException
        """
        
        
        # Identify the Exception conditions first (e.g., rows #3 and #4)
        if (  params_dict['allow_asynch'] is False and 
             (params_dict['delivery_parameters'] is None or can_push is False)  ): 
            raise StatusMessageException(poll_request.message_id, 
                                         ST_FAILURE, 
                                         "The content was not available now and \
                                         the request had allow_asynch=False and no \
                                         Delivery Parameters were specified.")
        
        # Rows #1 and #2 are both Status Messages with a type of Pending
        result_set = cls.create_result_set(content, prp, poll_service)
        sm = tm11.StatusMessage(message_id = generate_message_id(), in_response_to = poll_request.message_id, status_type = ST_PENDING)
        if poll_request.allow_asynch:
            sm.status_details = {SD_ESTIMATED_WAIT: 300, SD_RESULT_ID: result_set.pk, SD_WILL_PUSH: False}
        else:
            #TODO: Check and see if the requested delivery parameters are supported
            sm.status_details = {SD_ESTIMATED_WAIT: 300, SD_RESULT_ID: result_set.pk, SD_WILL_PUSH: True}
            #TODO: Need to try pushing or something.
        return sm
    
    @classmethod
    def handle_message(cls, poll_service, poll_request, django_request):
        """
        Handles a TAXII 1.1 Poll Request.
        """
        # Populate a PollRequestProperties object from the poll request
        prp = PollRequestProperties.from_poll_request_11(poll_service, poll_request)
        
        # Try to get a query handler
        query_handler = None
        if prp.query:
            query_handler = poll_service.get_query_handler(prp)
        
        # Get the kwargs to search the DB with
        db_kwargs = prp.get_db_kwargs()
        
        # If a query handler exists, allow it to 
        # inject kwargs
        if query_handler:
            query_handler.update_db_kwargs(prp, db_kwargs)
        
        # Get content from the database.
        # content MUST be an iterable where each
        # object has a `to_content_block_11()` function
        content = cls.get_content(prp, db_kwargs)
        
        # If there is a query handler,
        # allow it do to post-dbquery filtering
        if query_handler:
            content = query_handler.filter_content(prp, content)
        
        # The way this handler is written, this will never be false
        # TODO: Allow this to be configurable for testing
        results_available = True # TODO: Can this flag be usefully implemented?
        
        if results_available:
            response = cls.create_poll_response(poll_service, prp, content)
        else:
            response = cls.create_pending_response(poll_service, prp, content)
        
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
    def handle_message(poll_service, poll_request, django_request):
        if isinstance(poll_request, tm10.PollRequest):
            return PollRequest10Handler.handle_message(poll_service, poll_request, django_request)
        elif isinstance(poll_request, tm11.PollRequest):
            return PollRequest11Handler.handle_message(poll_service, poll_request, django_request)
        else:
            raise StatusMessageException(poll_request.message_id,
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
        except models.DataCollection.DoesNotExist:
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
            except models.Subscription.DoesNotExist:
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
            if ( inspect.isclass(obj) and 
                 obj.__module__ == 'taxii_services.taxii_handlers' and
                 issubclass(obj, MessageHandler) ):
                handler_list.append(name)
    
    for handler in handler_list:
        obj = v.get(handler, None)
        if (  not obj or
              not inspect.isclass(obj)  or
              not obj.__module__ == 'taxii_services.taxii_handlers' ):
            raise ValueError('%s is not a valid Message Handler' % handler)
        
        assert issubclass(obj, MessageHandler)
        
        management.register_message_handler(obj, handler)
