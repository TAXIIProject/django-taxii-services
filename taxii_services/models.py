# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from django.db import models
from django.db.models.signals import post_save
from validators import validate_importable
from importlib import import_module
import sys

from django.core.exceptions import ValidationError

import libtaxii.messages_11 as tm11

MAX_NAME_LENGTH = 256

#A number of choice tuples are defined here. In all cases the choices are:
# (database_value, display_value). Where possible, database_value is 
# a constant from libtaxii.messages_11. There is one handler per TAXII
# message exchange


INBOX_MESSAGE_HANDLER = (tm11.MSG_INBOX_MESSAGE, 'Inbox Service - Inbox Message Handler')
POLL_REQUEST_HANDLER = (tm11.MSG_POLL_REQUEST, 'Poll Service - Poll Request Handler')
POLL_FULFILLMENT_REQUEST_HANDLER = (tm11.MSG_POLL_FULFILLMENT_REQUEST , 'Poll Service - Poll Fulfillment Request Handler')
DISCOVERY_REQUEST_HANDLER = (tm11.MSG_DISCOVERY_REQUEST, 'Discovery Service - Discovery Request Handler')
COLLECTION_INFORMATION_REQUEST_HANDLER = (tm11.MSG_COLLECTION_INFORMATION_REQUEST, 'Collection Management Service - Collection Information Handler')
SUBSCRIPTION_MANAGEMENT_REQUEST_HANDLER = (tm11.MSG_MANAGE_COLLECTION_SUBSCRIPTION_REQUEST , 'Collection Management Service - Subscription Management Handler')

MESSAGE_HANDLER_CHOICES = (INBOX_MESSAGE_HANDLER, POLL_REQUEST_HANDLER, POLL_FULFILLMENT_REQUEST_HANDLER, 
                DISCOVERY_REQUEST_HANDLER, COLLECTION_INFORMATION_REQUEST_HANDLER, 
                SUBSCRIPTION_MANAGEMENT_REQUEST_HANDLER)

ACTIVE_STATUS = (tm11.SS_ACTIVE, 'Active')
PAUSED_STATUS = (tm11.SS_PAUSED, 'Paused')
UNSUBSCRIBED_STATUS = (tm11.SS_UNSUBSCRIBED, 'Unsubscribed')

SUBSCRIPTION_STATUS_CHOICES = (ACTIVE_STATUS, PAUSED_STATUS, UNSUBSCRIBED_STATUS)

FULL_RESPONSE = (tm11.RT_FULL, 'Full')
COUNT_RESPONSE = (tm11.RT_COUNT_ONLY, 'Count Only')

RESPONSE_CHOICES = (FULL_RESPONSE, COUNT_RESPONSE)

DATA_FEED = (tm11.CT_DATA_FEED, 'Data Feed')
DATA_SET = (tm11.CT_DATA_SET, 'Data Set')

DATA_COLLECTION_CHOICES = (DATA_FEED, DATA_SET)

REQUIRED = ('REQUIRED', 'required')
OPTIONAL = ('OPTIONAL', 'optional')
PROHIBITED = ('PROHIBITED', 'prohibited')

ROP_CHOICES = (REQUIRED, OPTIONAL, PROHIBITED)

#TODO: probably "unique=True" could be used at least once in each model. should try to figure out where it makes sense.

class Validator(models.Model):
    """
    Model for Validators. A Validator, at the moment,
    is an idea only. Eventually, it would be nice to be
    able to have content that comes in be passed to an
    automatic validator before storage.
    
    At some point, if a validator gets invented, this 
    model will leverage that validator concept.
    """
    
    name = models.CharField(max_length=MAX_NAME_LENGTH)
    description = models.TextField(blank=True)
    validator = models.CharField(max_length=MAX_NAME_LENGTH, unique=True, validators=[validate_importable])
    
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    
    def __unicode__(self):
        return u'%s (%s)' % (self.name, self.validator)
    
    class Meta:
        ordering = ['name']

class ContentBinding(models.Model):
    """
    Model for Content Binding IDs. Subtypes are stored in a different model.
    
    See also: ContentBindingAndSubtype
    """
    
    name = models.CharField(max_length=MAX_NAME_LENGTH)
    description = models.TextField(blank=True)
    binding_id = models.CharField(max_length=MAX_NAME_LENGTH, unique=True)
    validator = models.ForeignKey(Validator, blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u'%s (%s)' % (self.name, self.binding_id)
        
    class Meta:
        verbose_name = "Content Binding"

class ContentBindingSubtype(models.Model):
    """
    Model for Content Binding Subtypes. Content Bindings are stored in a different model.
    
    See also: ContentBindingAndSubtype.
    """
    
    name = models.CharField(max_length=MAX_NAME_LENGTH)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(ContentBinding)
    subtype_id = models.CharField(max_length=MAX_NAME_LENGTH, unique=True)
    validator = models.ForeignKey(Validator, blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    
    def __unicode__(self):
        return u'%s (%s)' % (self.name, self.subtype_id)
        
    class Meta:
        verbose_name = "Content Binding Subtype"

class ContentBindingAndSubtype(models.Model):
    """
    Model that relates ContentBindings to ContentBindingSubtypes.
    """
    
    content_binding = models.ForeignKey(ContentBinding)
    subtype = models.ForeignKey(ContentBindingSubtype, blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    
    def __unicode__(self):
        uni = "%s > " % self.content_binding.name
        if self.subtype:
            uni += "%s" % self.subtype.name
        else:
            uni += "(All)"
        
        return uni
    
    class Meta:
        verbose_name = "Content Binding And Subtype"
        unique_together = ('content_binding', 'subtype',)

def update_content_binding(sender, **kwargs):
    """
    When a Content Binding gets created, a new entry needs to be
    created in ContentBindingAndSubtype. This method performs that
    action.
    """
    
    if not kwargs['created']:
        return
    
    cbas = ContentBindingAndSubtype(content_binding = kwargs['instance'], subtype=None)
    cbas.save()

def update_content_binding_subtype(sender, **kwargs):
    """
    When a Content Binding Subtype gets created, a new entry needs to be
    created in ContentBindingAndSubtype. This method performs that
    action.
    """
    
    if not kwargs['created']:
        return
    subtype = kwargs['instance']
    cbas = ContentBindingAndSubtype(content_binding = subtype.parent, subtype = subtype)
    cbas.save()

# Link the update_content_binding[_subtype] functions to the objects
# Post delete handlers don't need to be written because they are part of how foreign keys work
post_save.connect(update_content_binding, sender=ContentBinding)
post_save.connect(update_content_binding_subtype, sender=ContentBindingSubtype)

class MessageBinding(models.Model):
    """
    Represents a Message Binding, used to establish the supported syntax
    for a given TAXII exchange, "e.g., XML".
    
    Ex:
    XML message binding id : "urn:taxii.mitre.org:message:xml:1.1"
    """
    
    name = models.CharField(max_length=MAX_NAME_LENGTH, blank=True)
    description = models.TextField(blank=True)
    binding_id = models.CharField(max_length=MAX_NAME_LENGTH, unique=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u'%s (%s)' % (self.name, self.binding_id)

    class Meta:
        verbose_name = "Message Binding"

class ProtocolBinding(models.Model):
    """
    Represents a Protocol Binding, used to establish the supported transport
    for a given TAXII exchange, "e.g., HTTP".
    
    Ex:
    HTTP Protocol Binding : "urn:taxii.mitre.org:protocol:http:1.0"
    """
    
    name = models.CharField(max_length=MAX_NAME_LENGTH, blank=True)
    description = models.TextField(blank=True)
    binding_id = models.CharField(max_length=MAX_NAME_LENGTH, unique=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u'%s (%s)' % (self.name, self.binding_id)

    class Meta:
        verbose_name = "Protocol Binding"

class DataCollection(models.Model):
    """
    Model for a TAXII Data Collection
    """
    
    name = models.CharField(max_length=MAX_NAME_LENGTH, unique=True)
    description = models.TextField(blank=True)
    type = models.CharField(max_length=MAX_NAME_LENGTH, choices=DATA_COLLECTION_CHOICES)#Choice - Data Feed or Data Set
    enabled = models.BooleanField(default=True)
    accept_all_content = models.BooleanField(default=False)
    supported_content = models.ManyToManyField(ContentBindingAndSubtype, blank=True, null=True)
    content_blocks = models.ManyToManyField('ContentBlock', blank=True, null=True)
    
    #TODO: Does query info go here?
    
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    
    def __unicode__(self):
        return u'%s (%s)' % (self.name, self.type)

    class Meta:
        ordering = ['name']
        verbose_name = "Data Collection"

class MessageHandler(models.Model):
    """
    Testing out a new concept.
    """
    
    name = models.CharField(max_length=MAX_NAME_LENGTH)
    description = models.TextField(blank=True, editable=False)
    handler = models.CharField(max_length=MAX_NAME_LENGTH, unique=True)
    module_name = models.CharField(max_length=MAX_NAME_LENGTH, editable=False)
    class_name = models.CharField(max_length=MAX_NAME_LENGTH, editable= False)
    supported_messages = models.CharField(max_length=MAX_NAME_LENGTH, editable=False)
    class_hash = models.CharField(max_length=MAX_NAME_LENGTH, editable=False) #This is used to determine if the class has changed on load
    
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    
    def clean(self):
        module_name, class_name = self.handler.rsplit('.', 1)
        try:
            module = import_module(module_name)
        except:
            raise ValidationError('Module (%s) could not be imported: %s' % (module_name, str(sys.exc_info())))
        
        try:
            handler_class = getattr(module, class_name)
        except:
            raise ValidationError('Class (%s) was not found in module (%s).' % (class_name, module_name))
        
        if (  'handle_message' not in dir(handler_class) or
           not str(handler_class.handle_message).startswith("<function")  ):
            raise ValidationError('Class (%s) does not appear to have a \'handle_message\' @staticmethod function declared!' % class_name)
        
        try:
            handler_class()
        except:
            print 'There was a problem instantiating the class!'
            raise
        
        self.module_name = module_name
        self.class_name = class_name
        
        try:
            self.description = handler_class.__doc__.strip()
        except:
            raise ValidationError('Class Description could not be found. Attempted .__doc__.strip()' % (method_name, module_name))
        
        try:
            self.supported_messages = handler_class.get_supported_request_messages()
        except:
            raise ValidationError('There was a problem getting the list of supported messages: %s' % str(sys.exc_info()))
        
        try:
            self.class_hash = hash(handler_class)
        except:
            print 'There was a problem getting the list of supported messages!'
            raise
            
    
    def __unicode__(self):
        return u'%s (%s)' % (self.name, self.handler)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Message Handler"

class _TaxiiService(models.Model):
    """
    Not to be used by users directly. Defines common fields that all 
    TAXII Services use
    """
    
    name = models.CharField(max_length=MAX_NAME_LENGTH)
    path = models.CharField(max_length=MAX_NAME_LENGTH, unique=True)
    description = models.TextField(blank=True)
    supported_message_bindings = models.ManyToManyField(MessageBinding)
    supported_protocol_bindings = models.ManyToManyField(ProtocolBinding)
    enabled = models.BooleanField(default=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    
    def __unicode__(self):
        return u'%s (%s)' % (self.name, self.path)
    
    class Meta:
        ordering = ['name']
        

class InboxService(_TaxiiService):
    inbox_message_handler = models.ForeignKey(MessageHandler, limit_choices_to={'supported_messages__contains': 'InboxMessage'})
    destination_collection_status = models.CharField(max_length=MAX_NAME_LENGTH, choices=ROP_CHOICES)
    destination_collections = models.ManyToManyField(DataCollection, blank=True)
    accept_all_content = models.BooleanField(default=False)
    supported_content = models.ManyToManyField(ContentBindingAndSubtype, blank=True, null=True)
    
    #TODO: Whast does it mean when the inbox supports a content binding that it's underlying data collections dont?
    #TODO: How does destination_collections impact which
    #      Content Bindings are supported?

    class Meta:
        verbose_name = "Inbox Service"

class InboxMessage(models.Model):
    """
    Used to store information about received Inbox Messages
    """
    #TODO: What should I index on?
    #TODO: NONE of these fields should be editable in the admin
    message_id = models.CharField(max_length=MAX_NAME_LENGTH)
    sending_ip = models.CharField(max_length=MAX_NAME_LENGTH)
    datetime_received = models.DateTimeField(auto_now_add=True)
    result_id = models.CharField(max_length=MAX_NAME_LENGTH, blank=True, null=True)
    
    #Record Count items
    record_count = models.IntegerField(blank=True, null=True)
    partial_count = models.BooleanField(default=False)
    
    #Subscription Information items
    collection_name = models.CharField(max_length=MAX_NAME_LENGTH, blank=True, null=True)
    subscription_id = models.CharField(max_length=MAX_NAME_LENGTH, blank=True, null=True)
    exclusive_begin_timestamp_label = models.DateTimeField(blank=True, null=True)
    inclusive_end_timestamp_label = models.DateTimeField(blank=True, null=True)
    
    received_via = models.ForeignKey(InboxService, blank=True, null=True)
    original_message = models.TextField(blank=True, null=True)
    content_block_count = models.IntegerField()
    content_blocks_saved = models.IntegerField()
    
    def __unicode__(self):
        return u'%s - %s' % (self.message_id, self.datetime_received)
    
    class Meta:
        ordering = ['datetime_received']
        verbose_name = "Inbox Message"

class ContentBlock(models.Model):
    message = models.TextField(blank=True)
    
    timestamp_label = models.DateTimeField(auto_now_add=True)
    inbox_message = models.ForeignKey(InboxMessage, blank=True, null=True)
    
    #TAXII Properties of a content block
    content_binding_and_subtype = models.ForeignKey(ContentBindingAndSubtype)
    content = models.TextField()
    padding = models.TextField(blank=True)
    
    date_created = models.DateTimeField(auto_now_add=True) # look at this for problems with apache instances
    date_updated = models.DateTimeField(auto_now=True)
    
    def __unicode__(self):
        return u'#%s: %s; %s' % (self.id, self.content_binding_and_subtype, self.timestamp_label.isoformat())

    class Meta:
        ordering = ['timestamp_label']
        verbose_name = "Content Block"

class PollService(_TaxiiService):
    poll_request_handler = models.ForeignKey(MessageHandler, related_name='poll_request', limit_choices_to={'supported_messages__contains': 'PollRequest'})
    poll_fulfillment_handler = models.ForeignKey(MessageHandler, related_name='poll_fulfillment', limit_choices_to={'supported_messages__contains': 'PollFulfillmentRequest'}, blank=True, null=True)
    data_collections = models.ManyToManyField(DataCollection)
    supported_queries = models.ManyToManyField('SupportedQuery', blank=True, null=True)
    
    class Meta:
        verbose_name = "Poll Service"


class CollectionManagementService(_TaxiiService):
    collection_information_handler = models.ForeignKey(MessageHandler, related_name='collection_information', limit_choices_to={'supported_messages__contains': 'CollectionInformationRequest'}, blank=True, null=True)
    subscription_management_handler = models.ForeignKey(MessageHandler, related_name='subscription_management', limit_choices_to={'supported_messages__contains': 'ManageCollectionSubscriptionRequest'}, blank=True, null=True)
    advertised_collections = models.ManyToManyField(DataCollection, blank=True, null=True)#TODO: This field is also used to determine which Collections this service processes subscriptions for. Is that right?
    #TODO: Add a validation step to make sure at least one of subscription management or collection_information handler is selected.
    supported_queries = models.ManyToManyField('SupportedQuery', blank=True, null=True)
    
    class Meta:
        verbose_name = "Collection Management Service"

class DiscoveryService(_TaxiiService):
    discovery_handler = models.ForeignKey(MessageHandler, limit_choices_to={'supported_messages__contains': 'DiscoveryRequest'})
    advertised_discovery_services = models.ManyToManyField('self', blank=True)
    advertised_inbox_services = models.ManyToManyField(InboxService, blank=True)
    advertised_poll_services = models.ManyToManyField(PollService, blank=True)
    advertised_collection_management_services = models.ManyToManyField(CollectionManagementService, blank=True)
    
    class Meta:
        verbose_name = "Discovery Service"

class Subscription(models.Model):
    subscription_id = models.CharField(max_length=MAX_NAME_LENGTH, unique=True)
    data_collection = models.ForeignKey(DataCollection)
    response_type = models.CharField(max_length=MAX_NAME_LENGTH, choices = RESPONSE_CHOICES, default=tm11.RT_FULL)
    accept_all_content = models.BooleanField(default=False)
    supported_content = models.ManyToManyField(ContentBindingAndSubtype, blank=True, null=True)
    query = models.TextField(blank=True)
    #push_parameters = models.ForeignKey(PushParameters)#TODO: Create a push parameters object
    status = models.CharField(max_length=MAX_NAME_LENGTH, choices = SUBSCRIPTION_STATUS_CHOICES, default=tm11.SS_ACTIVE)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    
    def __unicode__(self):
        return u'Subscription ID: %s' % self.subscription_id

class ResultSet(models.Model):
    #pk is a django auto-field
    data_collection = models.ForeignKey(DataCollection)
    subscription = models.ForeignKey(Subscription, blank=True, null=True)
    total_content_blocks = models.IntegerField()
    #TODO: Figure out how to limit choices to only the ResultSetParts that belong to this ResultSet
    last_part_returned = models.ForeignKey('ResultSetPart', blank=True, null=True)
    expires = models.DateTimeField()
    # TODO: There's nothing in here for pushing. It should be added
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    
    def __unicode__(self):
        return u'ResultSet ID: %s; Collection: %s; Parts: %s.' % (self.id, self.data_collection, self.resultsetpart_set.count())
    
    class Meta:
        verbose_name = "Result Set"

class ResultSetPart(models.Model):
    result_set = models.ForeignKey(ResultSet)
    part_number = models.IntegerField()
    content_blocks = models.ManyToManyField(ContentBlock)
    content_block_count = models.IntegerField()
    more = models.BooleanField()
    exclusive_begin_timestamp_label = models.DateTimeField(blank=True, null=True)
    inclusive_end_timestamp_label = models.DateTimeField(blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    
    def __unicode__(self):
        return u'ResultSet ID: %s; Collection: %s; Part#: %s.' % (self.result_set.id, self.result_set.data_collection, self.part_number)
    
    class Meta:
        verbose_name = "Result Set Part"
        unique_together = ('result_set', 'part_number',)

class DefaultQueryScope(models.Model):
    name = models.CharField(max_length=MAX_NAME_LENGTH)
    description = models.TextField(blank=True)
    scope = models.CharField(max_length=MAX_NAME_LENGTH)
    
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    
    def __unicode__(self):
        return u'%s (%s)' % (self.name, self.scope)

class QueryHandler(models.Model):
    """
    A model for Query Handlers. A query handler is a function that
    takes two arguments: A query and a content block and returns 
    True if the Content Block passes the query and False otherwise.
    """
    
    name = models.CharField(max_length=MAX_NAME_LENGTH)
    targeting_expression_id = models.CharField(max_length=MAX_NAME_LENGTH, unique=True)
    description = models.TextField(blank=True)
    handler = models.CharField(max_length=MAX_NAME_LENGTH, validators=[validate_importable])
    #type = models.CharField(max_length=MAX_NAME_LENGTH, choices = MESSAGE_HANDLER_CHOICES)
    
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    
    def __unicode__(self):
        return u'%s (%s)' % (self.name, self.handler)
    
    class Meta:
        ordering = ['name']

class SupportedQuery(models.Model):
    """
    QueryInformation maps most directly to the 
    Targeting Expression Info field in the TAXII Default
    Query spec.
    """
    name = models.CharField(max_length=MAX_NAME_LENGTH)
    description = models.TextField(blank=True)
    
    query_handler = models.ForeignKey(QueryHandler)
    preferred_scope = models.ManyToManyField(DefaultQueryScope, blank=True, null=True, related_name='preferred_scope')
    allowed_scope = models.ManyToManyField(DefaultQueryScope, blank=True, null=True, related_name='allowed_scope')
    
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    
    def __unicode__(self):
        return u'%s' % self.name
    
    class Meta:
        verbose_name = "Supported Query"
        verbose_name_plural = "Supported Queries"
