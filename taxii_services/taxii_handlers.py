# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from .base_taxii_handlers import BaseMessageHandler
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

class DiscoveryRequest11Handler(BaseMessageHandler):
    """
    Built-in TAXII 1.1 Discovery Request Handler.
    """
    supported_request_messages = [tm11.DiscoveryRequest]
    version = "1"
    
    @staticmethod
    def handle_message(discovery_service, discovery_request, django_request):
        """
        Returns a listing of all advertised services.

        Workflow:
            1. Return the results of `DiscoveryService.to_discovery_response_11()`
        """
        return discovery_service.to_discovery_response_11(discovery_request.message_id)

class DiscoveryRequest10Handler(BaseMessageHandler):
    """
    Built-in TAXII 1.0 Discovery Request Handler
    """
    supported_request_messages = [tm10.DiscoveryRequest]
    version = "1"
    
    @staticmethod
    def handle_message(discovery_service, discovery_request, django_request):
        """
        Returns a listing of all advertised services.

        Workflow:
            1. Return the results of `DiscoveryService.to_discovery_response_10()`
        """
        return discovery_service.to_discovery_response_10(discovery_request.message_id)

class DiscoveryRequestHandler(BaseMessageHandler):
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

class InboxMessage11Handler(BaseMessageHandler):
    """
    Built-in TAXII 1.1 Inbox Message Handler.
    """
    
    supported_request_messages = [tm11.InboxMessage]
    version = "1"
    
    @classmethod
    def save_content_block(cls, content_block, supporting_collections):
        """
        Saves the content_block in the database and
        associates it with all DataCollections in supporting_collections.

        This can be overriden to save the content block in a custom way.

        Arguments:
            content_block (tm11.ContentBlock) - The content block to save
            supporting_collections (list of models.DataCollection) - The Data Collections to add this content_block to
        """
        #TODO: Could/should this take an InboxService model object?
        cb = models.ContentBlock.from_content_block_11(content_block)
        cb.save()
        
        for collection in supporting_collections:
            collection.content_blocks.add(cb)
    
    @classmethod
    def handle_message(cls, inbox_service, inbox_message, django_request):
        """
        Attempts to save all Content Blocks in the Inbox Message into the 
        database.

        Workflow:
            #. Validate the request's Destination Collection Names against the InboxService model
            #. Create an InboxMessage model object for bookkeeping
            #. Iterate over each Content Block in the request:
            
             #. Identify which of the request's destination collections support the Content Block's Content Binding
             #. Call `save_content_block(tm11.ContentBlock, <list of Data Collections from 3a>)`
            
            #. Return Status Message with a Status Type of Success

        Raises:
            A StatusMessageException for errors
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
            # 3a. Identify whether the InboxService supports the Content Block's Content Binding
            # TODO: Is this useful?
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

class InboxMessage10Handler(BaseMessageHandler):
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

class InboxMessageHandler(BaseMessageHandler):
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

class PollFulfillmentRequest11Handler(BaseMessageHandler):
    """
    Built-in TAXII 1.1 Poll Fulfillment Request Handler.
    """
    supported_request_messages = [tm11.PollFulfillmentRequest]
    version = "1"
    
    @staticmethod
    def handle_message(poll_service, poll_fulfillment_request, django_request):
        """
        Looks in the database for a matching result set part and return it.

        Workflow:
            1. Look in models.ResultSetPart for a ResultSetPart that matches the criteria of the request
            2. Update the ResultSetPart's parent (models.ResultSet) to store which ResultSetPart was most recently returned
            3. Turn the ResultSetPart into a PollResponse, and return it
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

class PollRequest11Handler(BaseMessageHandler):
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
            prp (util.PollRequestProperties) - Not used in this function, \
                    but can be used by implementers extending this function.
            query_kwargs (dict) - The parameters of the search for content

        Returns:
            An list of models.ContentBlock objects. Classes that override \
            this method only need to return an iterable where each class has \
            a 'to_content_block_11()' function.
        """
        content = prp.collection.content_blocks.filter(**query_kwargs).order_by('timestamp_label')
        
        return content
    
    @classmethod
    def create_poll_response(cls, poll_service, prp, content):
        """
        Creates a poll response.
        
        1. If the request's response type is "Count Only", 
        a single poll response w/ more=False used.
        2. If the content size is less than the poll_service's
        max_result_size, a poll response w/ more=False is used.
        3. If the poll_service's max_result_size is blank,
        a poll response w/ more=False used.
        4. If the response type is "Full" and the total
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
        Arguments:
            poll_service (models.PollService) - The TAXII Poll Service being invoked
            prp (util.PollRequestProperties) - The Poll Request Properties of the Poll Request
            content - A list of content (nominally, models.ContentBlock objects). 
        
        This method returns a StatusMessage with a Status Type 
        of Pending OR raises a StatusMessageException
        based on the following table::
        
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
        
        Workflow:
            1. Create a util.PollRequestProperties object from the tm11.PollRequest
            2. If a Query Handler exists, call the `QueryHandler.update_db_kwargs( ... )` 
               method of the Query Handler. This allows the QueryHandler a hook to modify the 
               database query arguments before the query is sent do the database.
            3. Call `content = class.get_content(PollRequestProperties, db_kwargs)`, which returns a list of
               objects, each of which must have a `to_content_block_11()` function.
            4. If a Query Handler exists, call the `QueryHandler.filter_content( ... )` 
               function. This allows the QueryHandler a hook to modify the results after they have been returned
               from the database, but before they are returned to the requestor.
            5. If the results are available "now", return the result of calling
               `create_poll_response`.
            6. (Experimental) If the results are not available "now", return the result
                of calling `create_pending_response`.
        """
        # Populate a PollRequestProperties object from the poll request
        prp = PollRequestProperties.from_poll_request_11(poll_service, poll_request)
        
        # Get the kwargs to search the DB with
        db_kwargs = prp.get_db_kwargs()
        
        # If a query handler exists, allow it to 
        # inject kwargs
        if prp.query_handler:
            prp.query_handler.update_db_kwargs(prp, db_kwargs)
        
        # Get content from the database.
        # content MUST be an iterable where each
        # object has a `to_content_block_11()` function
        content = cls.get_content(prp, db_kwargs)
        
        # If there is a query handler,
        # allow it do to post-dbquery filtering
        if prp.query_handler:
            content = query_handler.filter_content(prp, content)
        
        # The way this handler is written, this will never be false
        # TODO: Allow this to be configurable for testing
        results_available = True # TODO: Can this flag be usefully implemented?
        
        if results_available:
            response = cls.create_poll_response(poll_service, prp, content)
        else:
            response = cls.create_pending_response(poll_service, prp, content)
        
        return response

class PollRequest10Handler(BaseMessageHandler):
    """
    Built-in TAXII 1.0 Poll Request Handler
    """
    supported_request_messages = [tm10.PollRequest]
    version = "1"
    
    @staticmethod
    def handle_message(poll_service, poll_message, django_request):
        """
        TODO: Implement this.
        """
        pass

class PollRequestHandler(BaseMessageHandler):
    """
    Built-in TAXII 1.1 and TAXII 1.0 Poll Request Handler
    """
    
    supported_request_messages = [tm10.PollRequest, tm11.PollRequest]
    version = "1"
    
    @staticmethod
    def handle_message(poll_service, poll_request, django_request):
        """
        Passes the request to either PollRequest10Handler or PollRequest11Handler
        """
        if isinstance(poll_request, tm10.PollRequest):
            return PollRequest10Handler.handle_message(poll_service, poll_request, django_request)
        elif isinstance(poll_request, tm11.PollRequest):
            return PollRequest11Handler.handle_message(poll_service, poll_request, django_request)
        else:
            raise StatusMessageException(poll_request.message_id,
                                         ST_FAILURE,
                                         "TAXII Message not supported by Message Handler.")

class CollectionInformationRequest11Handler(BaseMessageHandler):
    """
    Built-in TAXII 1.1 Collection Information Request Handler.
    """
    supported_request_messages = [tm11.CollectionInformationRequest]
    version = "1"
    
    @staticmethod
    def handle_message(collection_management_service, collection_information_request, django_request):
        """
        Workflow:
            1. Returns the result of `models.CollectionManagementService.to_collection_information_response_11()`
        """
        in_response_to = collection_information_request.message_id
        return collection_management_service.to_collection_information_response_11(in_response_to)

class FeedInformationRequest10Handler(BaseMessageHandler):
    """
    Built-in TAXII 1.0 Feed Information Request Handler
    """
    supported_request_messages = [tm10.FeedInformationRequest]
    version = "1"
    
    @staticmethod
    def handle_message(collection_management_service, feed_information_request, django_request):
        """
        Workflow:
            1. Returns the result of `models.CollectionManagementService.to_feed_information_response_10()`
        """
        in_response_to = feed_information_request.message_id
        return collection_management_service.to_feed_information_response_10(in_response_to)

class CollectionInformationRequestHandler(BaseMessageHandler):
    """
    Built-in TAXII 1.1 and 1.0 Collection/Feed Information Request handler.
    """
    
    supported_request_messages = [tm10.FeedInformationRequest, tm11.CollectionInformationRequest]
    version = "1"
    
    @staticmethod
    def handle_message(collection_management_service, collection_information_request, django_request):
        """
        Passes the request to either FeedInformationRequest10Handler 
        or CollectionInformationRequestRequest11Handler.
        """
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

class SubscriptionRequest11Handler(BaseMessageHandler):
    """
    Built-in TAXII 1.1 Manage Collection Subscription Request Handler.
    """
    
    supported_request_messages = [tm11.ManageCollectionSubscriptionRequest]
    version = "1"
    
    @staticmethod
    def unsubscribe(request, subscription=None):
        """
        Recall from the TAXII 1.1 Services Specification:
        "Attempts to unsubscribe (UNSUBSCRIBE action) where the Subscription ID does not correspond 
        to an existing subscription on the named TAXII Data Collection by the identified Consumer
        SHOULD be treated as a successful attempt to unsubscribe and result in a TAXII Manage 
        Collection Subscription Response without changing existing subscriptions. In other words, the 
        requester is informed that there is now no subscription with that Subscription ID (even though 
        there never was one in the first place)."
        
        Arguments:
            request (tm11.ManageCollectionSubscriptionRequest) - The request message
            subscription (models.Subscription) - The subscription to unsubscribe, \
                        can be None if there is no corresponding subscription

        Returns:
            A tm11.SubscriptionInstance (to be put in a tm11.CollectionManagementResponse

        Workflow:
            1. If the subscription exits, set the state to Unsubscribed
            2. Return a response indicating success
        """
        if subscription:
            subscription.status == SS_UNSUBSCRIBED
            subscription.save()
            si = subscription.to_subscription_instance_11()
        else:        
            si = tm11.SubscriptionInstance(
                            subscription_id = request.subscription_id,
                            status = SS_UNSUBSCRIBED)
        
        return si
    
    @staticmethod
    def pause(request, subscription):
        """
        Workflow:
            1. Sets the subscription status to SS_PAUSED
            2. Returns `subscription.to_subscription_instance_11()`

        Arguments:
            request (tm11.ManageCollectionSubscriptionRequest) - The request message
            subscription (models.Subscription) - The subscription to unsubscribe

        Returns:
            A tm11.SubscriptionInstance object
        """
        #TODO: For pause, need to note when the pause happened so delivery of content can resume
        # later on
        subscription.status = SS_PAUSED
        subscription.save()
        return subscription.to_subscription_instance_11()
    
    @staticmethod
    def resume(request, subscription):
        """
        Workflow:
            1. Sets the subscription status to SS_ACTIVE
            2. Returns `subscription.to_subscription_instance_11()`

        Arguments:
            request (tm11.ManageCollectionSubscriptionRequest) - The request message
            subscription (models.Subscription) - The subscription to unsubscribe

        Returns:
            A tm11.SubscriptionInstance object
        """
        subscription.status = SS_ACTIVE
        subscription.save()
        return subscription.to_subscription_instance_11()
    
    @staticmethod
    def single_status(request, subscription):
        """
        Workflow:
            1. Returns `subscription.to_subscription_instance_11()`

        Arguments:
            request (tm11.ManageCollectionSubscriptionRequest) - The request message
            subscription (models.Subscription) - The subscription to unsubscribe

        Returns:
            A tm11.SubscriptionInstance object
        """
        return subscription.to_subscription_instance_11()
    
    @staticmethod
    def multi_status(request):
        """
        Workflow:
            1. For every subscription in the system, call `subscription.to_subscription_instance_11()`

        Arguments:
            request (tm11.ManageCollectionSubscriptionRequest) - The request message

        Returns:
            A list of tm11.SubscriptionInstance objects
        """
        subscriptions = models.Subscription.objects.all()
        subscription_list = []
        for subscription in subscriptions:
            subscription_list.append(subscription.to_subscription_instance_11())
        return subscription_list
    
    @staticmethod
    def subscribe(request):
        """
        This method needs to be tested before it's 
        behavior can be documented.
        """
        # TODO: Check for supported push methods (e.g., inbox protocol, delivery message binding)
            
        # TODO: Check for unsupported / unknown Content Bindings / Subtypes
        
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
        subscription = models.Subscription.objects.get_or_create(
                        response_type = smr.subscription_parameters.response_type, 
                        accept_all_content = accept_all_content,
                        supported_content = supported_contents, # TODO: This is probably wrong
                        query = None, # TODO: Implement query
                        )
        return subscription.to_subscription_instance_11()
    
    @classmethod
    def handle_message(cls, collection_management_service, manage_collection_subscription_request, django_request):
        """
        Workflow:
        (Kinda big)
        #. Validate the Data Collection that the request identifies
        #. Validate a variety of aspects of the request message
        #. If there's a subscription_id in the request message, attempt to identify that \
           subscription in the database
        #. If Action == Subscribe, call `subscribe(request)`
        #. If Action == Unsubscribe, call `unsubscribe(request, subscription)`
        #. If Action == Pause, call `pause(request, subscription)`
        #. If Action == Resume, call `resume(request, subscription)`
        #. If Action == Status and there is a `subscription_id, call single_status(request, subscription)`
        #. If Action == Status and there is not a `subscription_id, call `multi_status(request)`
        #. Return a CollectionManageSubscriptionResponse

        """
        # Create an alias because the name is long as fiddlesticks
        smr = manage_collection_subscription_request
        cms = collection_management_service
            
        # This code follows the guidance in the TAXII Services Spec 1.1 Section 4.4.6. 
        # This code could probably be optimized, but it exists in part to be readable.
        
        # 1. This code doesn't do authentication, so this step is skipped
        
        # 2. If the Collection Name does not exist, respond with a Status Message
        data_collection = cms.validate_collection_name(smr.collection_name, smr.message_id)
        
        # The following code executes this truth table:
        # Action      | Subscription ID | Subscription ID  
        #             |   in message?   |   DB match?      
        # -------------------------------------------------
        # Subscribe   |   Prohibited    |       N/A        
        # Unsubscribe |    Required     |    Not Needed    
        # Pause       |    Required     |     Needed       
        # Resume      |    Required     |     Needed       
        # Status      |    Optional     | Yes, if specified
        
        if smr.action not in ACT_TYPES:
            raise StatusMessageException(smr.message_id,
                                         ST_BAD_MESSAGE,
                                         message="The specified value of Action was invalid.")
        
        # "For messages where the Action field is UNSUBSCRIBE, PAUSE, or RESUME, [subscription id] MUST be present"
        if smr.action in (ACT_UNSUBSCRIBE, ACT_PAUSE, ACT_RESUME) and not smr.subscription_id:
            raise StatusMessageException(smr.message_id,
                                         ST_BAD_MESSAGE,
                                         message="The %s action requires a subscription id." % smr.action)
        
        # Attempt to identify a subscription in the database
        if smr.subscription_id:
            try:
                subscription = models.Subscription.objects.get(subscription_id = request.subscription_id)
            except models.Subscription.DoesNotExist:
                subscription = None # This is OK for certain circumstances
        
        # If subscription is None for Unsubscribe, that's OK, but it's not OK
        # for Pause/Resume
        if subscription is None and smr.action in (ACT_PAUSE, ACT_RESUME):
            raise StatusMessageException(smr.message_id,
                                         ST_NOT_FOUND,
                                         status_detail={SD_ITEM: smr.subscription_id})
        
        
        # Create a stub ManageCollectionSubscriptionResponse
        response = tm11.ManageCollectionSubscriptionResponse(
                                message_id = generate_message_id(), 
                                in_response_to = smr.message_id,
                                collection_name = data_collection.collection_name)
        
        # This code can probably be optimized
        if smr.action == ACT_SUBSCRIBE:
            subs_instance = cls.subscribe(smr)
            response.subscription_instances.append(subs_instance)
        elif smr.action == ACT_UNSUBSCRIBE:
            subs_instance = cls.subscribe(smr)
            response.subscription_instances.append(subs_instance)
        elif smr.action == ACT_PAUSE:
            subs_instance = cls.pause(smr, subscription)
            response.subscription_instances.append(subs_instance)
        elif smr.action == ACT_RESUME:
            subs_instance = cls.resume(smr, subscription)
            response.subscription_instances.append(subs_instance)
        elif smr.action == ACT_STATUS and subscription:
            subs_instance = cls.single_status(smr, subscription)
            response.subscription_instances.append(subs_instance)
        elif smr.action == ACT_STATUS and not subscription:
            subs_instances = cls.multi_status(smr)
            for subs_instance in subs_instances:
                response.subscription_instances.append(subs_instance)
        else:
            raise ValueError("Unknown Action!")
            
        return response

class SubscriptionRequest10Handler(BaseMessageHandler):
    """
    Built-in TAXII 1.0 Manage Collection Subscription Request Handler.
    """
    
    supported_request_messages = [tm10.ManageFeedSubscriptionRequest]
    version = "1"
    
    @staticmethod
    def handle_message(feed_management_service, manage_feed_subscription_request, django_request):
        """
        TODO: Implement this.
        """
        pass

class SubscriptionRequestHandler(BaseMessageHandler):
    """
    Built-in TAXII 1.1 and TAXII 1.0 Management Collection/Feed Subscription Request Handler.
    """
    
    supported_request_messages = [tm11.ManageCollectionSubscriptionRequest, tm10.ManageFeedSubscriptionRequest]
    version = "1"
    
    @staticmethod
    def handle_message(collection_management_service, manage_collection_subscription_request, django_request):
        """
        Passes the request to either SubscriptionRequest10Handler 
        or SubscriptionRequest11Handler.
        """
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
    """
    registers some or all TAXII Message Handlers from
    taxii_services.taxii_handlers (this module). If handler_list
    is empty, all Message Handlers in this module will be registered.

    Each registration goes through `management.register_message_handler`

    Arguments:
        handler_list (list of strings) - A list of handler class names to register
    """
    import management, inspect, taxii_services.taxii_handlers
        
    v = vars(taxii_services.taxii_handlers)
    
    if not handler_list:
        handler_list = []
        for name, obj in v.iteritems():
            if ( inspect.isclass(obj) and 
                 obj.__module__ == 'taxii_services.taxii_handlers' and
                 issubclass(obj, BaseMessageHandler) ):
                handler_list.append(name)
    
    for handler in handler_list:
        obj = v.get(handler, None)
        if (  not obj or
              not inspect.isclass(obj)  or
              not obj.__module__ == 'taxii_services.taxii_handlers' ):
            raise ValueError('%s is not a valid Message Handler' % handler)
        
        assert issubclass(obj, BaseMessageHandler)
        
        management.register_message_handler(obj, handler)
