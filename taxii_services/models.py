# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file


from .exceptions import StatusMessageException

import libtaxii.messages_11 as tm11
import libtaxii.messages_10 as tm10
import libtaxii.taxii_default_query as tdq
from libtaxii import validation
from libtaxii.common import generate_message_id
from libtaxii.constants import *

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save, pre_save
from django.core.exceptions import ObjectDoesNotExist
from importlib import import_module
from itertools import chain
import uuid
import sys

MAX_NAME_LENGTH = 255

# A number of choice tuples are defined here. In all cases the choices are:
# (database_value, display_value). Where possible, database_value is
# a constant from libtaxii.messages_11. There is one handler per TAXII
# message exchange

#: TAXII 1.1 Inbox Message Handler
INBOX_MESSAGE_11_HANDLER = (MSG_INBOX_MESSAGE,
                            'Inbox Service - Inbox Message Handler (TAXII 1.1)')
#: TAXII 1.0 Inbox Message Handler
INBOX_MESSAGE_10_HANDLER = (MSG_INBOX_MESSAGE,
                            'Inbox Service - Inbox Message Handler (TAXII 1.0)')
#: TAXII 1.1 Poll Request Handler
POLL_REQUEST_11_HANDLER = (MSG_POLL_REQUEST,
                           'Poll Service - Poll Request Handler (TAXII 1.1)')
#: TAXII 1.0 Poll Request Handler
POLL_REQUEST_10_HANDLER = (MSG_POLL_REQUEST,
                           'Poll Service - Poll Request Handler (TAXII 1.0)')
#: TAXII 1.1 Poll Fulfillment Request Handler
POLL_FULFILLMENT_REQUEST_11_HANDLER = (MSG_POLL_FULFILLMENT_REQUEST,
                                       'Poll Service - Poll Fulfillment Request Handler (TAXII 1.1)')
# PollFulfillment is not in TAXII 1.0
#: TAXII 1.1 Discovery Request Handler
DISCOVERY_REQUEST_11_HANDLER = (MSG_DISCOVERY_REQUEST,
                                'Discovery Service - Discovery Request Handler (TAXII 1.1)')
#: TAXII 1.0 Discovery Request Handler
DISCOVERY_REQUEST_10_HANDLER = (MSG_DISCOVERY_REQUEST,
                                'Discovery Service - Discovery Request Handler (TAXII 1.0)')
#: TAXII 1.1 Collection Information Request Handler
COLLECTION_INFORMATION_REQUEST_11_HANDLER = (MSG_COLLECTION_INFORMATION_REQUEST,
                                             'Collection Management Service - \
                                             Collection Information Handler (TAXII 1.1)')
#: TAXII 1.0 Collection Information Request Handler
FEED_INFORMATION_REQUEST_10_HANDLER = (MSG_FEED_INFORMATION_REQUEST,
                                       'Feed Management Service - \
                                       Feed Information Handler (TAXII 1.0)')
#: TAXII 1.1 Subscription Management Request Handler
SUBSCRIPTION_MANAGEMENT_REQUEST_11_HANDLER = (MSG_MANAGE_COLLECTION_SUBSCRIPTION_REQUEST,
                                              'Collection Management Service - \
                                               Subscription Management Handler (TAXII 1.1)')
#: TAXII 1.0 Subscription Management Request Handler
SUBSCRIPTION_MANAGEMENT_REQUEST_10_HANDLER = (MSG_MANAGE_FEED_SUBSCRIPTION_REQUEST,
                                              'Feed Management Service - \
                                              Subscription Management Handler (TAXII 1.0)')
#: Tuple of all message handler choices
MESSAGE_HANDLER_CHOICES = (INBOX_MESSAGE_11_HANDLER, POLL_REQUEST_11_HANDLER,
                           POLL_FULFILLMENT_REQUEST_11_HANDLER, DISCOVERY_REQUEST_11_HANDLER,
                           COLLECTION_INFORMATION_REQUEST_11_HANDLER, SUBSCRIPTION_MANAGEMENT_REQUEST_11_HANDLER,
                           INBOX_MESSAGE_10_HANDLER, POLL_REQUEST_10_HANDLER,
                           DISCOVERY_REQUEST_10_HANDLER, FEED_INFORMATION_REQUEST_10_HANDLER,
                           SUBSCRIPTION_MANAGEMENT_REQUEST_10_HANDLER)

#: Active Subscription Status
ACTIVE_STATUS = (SS_ACTIVE, 'Active')
#: Paused Subscription Status
PAUSED_STATUS = (SS_PAUSED, 'Paused')
#: Unsubscribed Subscription Status
UNSUBSCRIBED_STATUS = (SS_UNSUBSCRIBED, 'Unsubscribed')
#: Tuple of all subscription statuses
SUBSCRIPTION_STATUS_CHOICES = (ACTIVE_STATUS, PAUSED_STATUS, UNSUBSCRIBED_STATUS)

#: Response Type Full
FULL_RESPONSE = (RT_FULL, 'Full')
#: Response Type Count Only
COUNT_RESPONSE = (RT_COUNT_ONLY, 'Count Only')
#: Tuple of all response choices
RESPONSE_CHOICES = (FULL_RESPONSE, COUNT_RESPONSE)

#: Data Feed
DATA_FEED = (CT_DATA_FEED, 'Data Feed')
#: Data Set
DATA_SET = (CT_DATA_SET, 'Data Set')
#: Tuple of all Data Collection types
DATA_COLLECTION_CHOICES = (DATA_FEED, DATA_SET)

#: Field required
REQUIRED = ('REQUIRED', 'required')
#: Field optional
OPTIONAL = ('OPTIONAL', 'optional')
#: Field prohibited
PROHIBITED = ('PROHIBITED', 'prohibited')
#: Tuple of all field req/opt/prohib choices
ROP_CHOICES = (REQUIRED, OPTIONAL, PROHIBITED)

#: Polling is allowed
SUBS_POLL = ('POLL', 'Poll')
#: Pushing is allowed
SUBS_PUSH = ('PUSH', 'Push')
#: Both pushing and polling are allowed
SUBS_BOTH = ('BOTH', 'Both')
#: Tuple of all subscription delivery methods
DELIVERY_CHOICES = (SUBS_POLL, SUBS_PUSH, SUBS_BOTH)

#: Preferred Scope
PREFERRED_SCOPE = ('PREFERRED', 'Preferred')
#: Allowed Scope
ALLOWED_SCOPE = ('ALLOWED', 'Allowed')
#: Tuple of scope choices
SCOPE_CHOICES = (PREFERRED_SCOPE, ALLOWED_SCOPE)


# TODO: Can SupportInfo be moved somewhere else that makes more sense?

class SupportInfo(object):
    """
    An object that contains information related to
    whether something is supported or not.

    This class has two properties:
    is_supported (bool) - Indicates whether the thing is supported
    message (str) - A message about why the thing is or is not supported. Usually used to indicate why \
     something isn't supported.
    """

    def __init__(self, is_supported, message=None):
        """
        Arguments:
            is_supported (bool) - Indicates whether the thing is supported
            message (str) - A message about why the thing is or is not supported **optional**. \
            Usually used to indicate why something isn't supported.
        """
        self.is_supported = is_supported
        self.message = message


class _BindingBase(models.Model):
    """
    Base class for Bindings (e.g., Protocol Binding, Content Binding, Message Binding)
    """
    name = models.CharField(max_length=MAX_NAME_LENGTH)
    description = models.TextField(blank=True)
    binding_id = models.CharField(max_length=MAX_NAME_LENGTH, unique=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u'%s (%s)' % (self.name, self.binding_id)


class _Handler(models.Model):
    """
    A handler is an extension point that allows user-defined code to be used
    in conjunction with django-taxii-services
    """
    #: Subclasses use handler_function to indicate what functions they call for handling
    handler_functions = []

    name = models.CharField(max_length=MAX_NAME_LENGTH)
    description = models.TextField(blank=True, editable=False)
    handler = models.CharField(max_length=MAX_NAME_LENGTH, unique=True)
    module_name = models.CharField(max_length=MAX_NAME_LENGTH, editable=False)
    class_name = models.CharField(max_length=MAX_NAME_LENGTH, editable=False)
    # version is used to determine if the class has changed on load
    version = models.CharField(max_length=MAX_NAME_LENGTH, editable=False)

    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def get_handler_class(self):
        """
        Returns:
            An handle on the handler class
        """

        if (self.module_name is None or
            len(self.module_name) == 0 or
            self.class_name is None or
            len(self.class_name) == 0):

            self.clean()

        module = import_module(self.module_name)
        handler_class = getattr(module, self.class_name)
        return handler_class

    def clean(self):
        """
        Given the handler, do lots of validation.
        """

        module_name, class_name = self.handler.rsplit('.', 1)
        self.module_name = module_name
        self.class_name = class_name

        try:
            module = import_module(module_name)
        except:
            raise ValidationError('Module (%s) could not be imported: %s' %
                                  (module_name, str(sys.exc_info())))

        try:
            handler_class = getattr(module, class_name)
        except:
            raise ValidationError('Class (%s) was not found in module (%s).' %
                                  (class_name, module_name))

        for f in self.handler_functions:
            try:
                hf = getattr(handler_class, f)
            except:
                raise ValidationError('Class (%s) does not have a %s function defined!' % (handler_class, f))

            if str(hf).startswith("<unbound"):
                raise ValidationError("Function %s does not appear to be a @staticmethod or @classmethod!" % f)

        try:
            self.description = handler_class.__doc__.strip()
        except:
            raise ValidationError('Class Description could not be found. Attempted %s.__doc__.strip()' % class_name)

        try:
            # TODO: Check the version on load
            self.version = handler_class.version
        except:
            raise ValidationError('Could not read version from class (%s). Does the class have a static version property?' % handler_class)

        return handler_class  # This is used by subclasses to extract subclass-specific attrs

    def __unicode__(self):
        return u'%s (%s)' % (self.name, self.handler)

    class Meta:
        ordering = ['name']


class _Tag(models.Model):
    """
    Not to be used by users directly. Defines common tags used for certain other models.
    """
    tag = models.CharField(max_length=MAX_NAME_LENGTH, unique=True)
    value = models.CharField(max_length=MAX_NAME_LENGTH)

    def __unicode__(self):
        s = self.tag
        if self.value is not None:
            s += " (%s)" % self.value
        return s


class _TaxiiService(models.Model):
    """
    Not to be used by users directly. Defines common fields that all
    TAXII Services use.
    """
    service_type = None
    name = models.CharField(max_length=MAX_NAME_LENGTH)
    path = models.CharField(max_length=MAX_NAME_LENGTH, unique=True)
    description = models.TextField(blank=True)
    supported_message_bindings = models.ManyToManyField('MessageBinding')
    supported_protocol_bindings = models.ManyToManyField('ProtocolBinding')
    enabled = models.BooleanField(default=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def to_service_instances_10(self):
        """
        Returns:
            A list of 1 or 2 (depending on the supported protocol bindings)
            tm10.ServiceInstance objects.
        """
        service_instances = []
        for pb in self.supported_protocol_bindings.all():
            st = self.service_type
            if st == SVC_COLLECTION_MANAGEMENT:
                st = SVC_FEED_MANAGEMENT
            si = tm10.ServiceInstance(service_type=st,
                                      services_version=VID_TAXII_SERVICES_11,
                                      protocol_binding=pb.binding_id,
                                      service_address=self.path,  # TODO: Get the server's real path and prepend it here
                                      message_bindings=[mb.binding_id for mb in self.supported_message_bindings.all()],
                                      available=self.enabled,
                                      message=self.description)
            service_instances.append(si)
        return service_instances

    def to_service_instances_11(self):
        """
        Returns:
            A list of 1 or 2 (depending on the supported protocol bindings)
            tm11.ServiceInstance objects.
        """
        service_instances = []
        for pb in self.supported_protocol_bindings.all():
            si = tm11.ServiceInstance(service_type=self.service_type,
                                      services_version=VID_TAXII_SERVICES_11,
                                      available=self.enabled,
                                      protocol_binding=pb.binding_id,
                                      service_address=self.path,  # TODO: Get the server's real path and prepend it here
                                      message_bindings=[mb.binding_id for mb in self.supported_message_bindings.all()],
                                      message=self.description)
            service_instances.append(si)
        return service_instances

    def get_message_handler(self, taxii_message):
        """
        Given a taxii_message, return the correct
        MessageHandler model object or raise a
        StatusMessage

        MUST be implemented by subclasses.
        Arguments:
            taxii_message (a tm11 or tm10 TAXII Message)

        Returns:
            A models.MessageHandler object
        """
        raise NotImplementedError()

    def __unicode__(self):
        return u'%s (%s)' % (self.name, self.path)

    class Meta:
        ordering = ['name']


class CapabilityModule(_Tag):
    pass


class CollectionManagementService(_TaxiiService):
    """
    Model for Collection Management Service. This is also used
    for Feed Management Service.
    """
    service_type = SVC_COLLECTION_MANAGEMENT
    collection_information_handler = models.ForeignKey('MessageHandler',
                                                       related_name='collection_information',
                                                       limit_choices_to={'supported_messages__contains':
                                                                         'CollectionInformationRequest'},
                                                       blank=True,
                                                       null=True)
    subscription_management_handler = models.ForeignKey('MessageHandler',
                                                        related_name='subscription_management',
                                                        limit_choices_to={'supported_messages__contains':
                                                                          'ManageCollectionSubscriptionRequest'},
                                                        blank=True,
                                                        null=True)
    advertised_collections = models.ManyToManyField('DataCollection', blank=True, null=True)
    supported_queries = models.ManyToManyField('SupportedQuery', blank=True, null=True)

    def get_message_handler(self, taxii_message):
        if taxii_message.message_type == MSG_COLLECTION_INFORMATION_REQUEST:
            return self.collection_information_handler
        elif taxii_message.message_type == MSG_FEED_INFORMATION_REQUEST:
            return self.collection_information_handler
        elif taxii_message.message_type == MSG_MANAGE_COLLECTION_SUBSCRIPTION_REQUEST:
            return self.subscription_management_handler
        elif taxii_message.message_type == MSG_MANAGE_FEED_SUBSCRIPTION_REQUEST:
            return self.subscription_management_handler

        raise StatusMessageException(taxii_message.message_id,
                                     ST_FAILURE,
                                     message="Message not supported by this service")

    def clean(self):
        if (not self.collection_information_handler and
            not self.subscription_management_handler):
            raise ValidationError('At least one of Collection Information Handler or \
                                  Subscription Management Handler must have a value selected.')

    def to_service_instances_11(self):
        service_instances = super(CollectionManagementService, self).to_service_instances_11()
        for si in service_instances:
            for sq in self.supported_queries.all():
                si.supported_query.append(sq.to_query_info_11())
        return service_instances

    def to_feed_information_response_10(self, in_response_to):
        """
        Creates a tm10.FeedInformationResponse
        based on this model

        Returns:
            A tm10.FeedInformationResponse object
        """

        # Create a stub FeedInformationResponse
        fir = tm10.FeedInformationResponse(message_id=generate_message_id(), in_response_to=in_response_to)

        # For each collection that is advertised and enabled, create a Feed Information
        # object and add it to the Feed Information Response
        for collection in self.advertised_collections.filter(enabled=True):
            fir.feed_informations.append(collection.to_feed_information_10())

        return fir

    def to_collection_information_response_11(self, in_response_to):
        """
        Creates a tm11.CollectionInformationResponse
        based on this model

        Returns:
            A tm11.CollectionInformationResponse object
        """

        # Create a stub CollectionInformationResponse
        cir = tm11.CollectionInformationResponse(message_id=generate_message_id(), in_response_to=in_response_to)

        # For each collection that is advertised and enabled, create a Collection Information
        # object and add it to the Collection Information Response
        for collection in self.advertised_collections.filter(enabled=True):
            cir.collection_informations.append(collection.to_collection_information_11())

        return cir

    def validate_collection_name(self, collection_name, in_response_to):
        """
        Arguments:
            collection_name (str) - The name of a collection
            in_response_to (str) - The message_id of the request

        Returns:
            A models.DataCollection object, if this CollectionManagementService
            handles subscriptions DataCollection identified by collection_name
            and that DataCollection has enabled=True

        Raises:
            A StatusMessageException if this CollectionManagementService does not
            handle subscriptions for the DataCollection identified by collection_name
            or the DataCollection has enabled=False.
        """
        try:
            data_collection = self.advertised_collections.get(name=collection_name, enabled=True)
        except DataCollection.DoesNotExist:
            raise StatusMessageException(in_response_to,
                                         ST_NOT_FOUND,
                                         status_detail={'ITEM': collection_name})
        return data_collection

    class Meta:
        verbose_name = "Collection Management Service"


class ContentBinding(_BindingBase):
    """
    Model for Content Binding IDs. Subtypes are stored in a different model.

    See also: ContentBindingAndSubtype
    """
    validator = models.ForeignKey('Validator', blank=True, null=True)

    class Meta:
        verbose_name = "Content Binding"


class ContentBindingAndSubtype(models.Model):
    """
    Model that relates ContentBindings to ContentBindingSubtypes.

    This is the primary mechanism by which ContentBindings and Subtypes
    are visualized / managed.
    """
    content_binding = models.ForeignKey('ContentBinding')
    subtype = models.ForeignKey('ContentBindingSubtype', blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def to_content_binding_11(self):
        """
        TODO: Implement this?
        """
        pass

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


class ContentBindingSubtype(models.Model):
    """
    Model for Content Binding Subtypes. Content Bindings are stored in a different model.

    See also: ContentBindingAndSubtype.
    """
    name = models.CharField(max_length=MAX_NAME_LENGTH)
    description = models.TextField(blank=True)
    parent = models.ForeignKey('ContentBinding')
    subtype_id = models.CharField(max_length=MAX_NAME_LENGTH, unique=True)
    validator = models.ForeignKey('Validator', blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u'%s (%s)' % (self.name, self.subtype_id)

    class Meta:
        verbose_name = "Content Binding Subtype"


def update_content_binding(sender, **kwargs):
    """
    When a Content Binding gets created, a new entry needs to be
    created in ContentBindingAndSubtype. This method performs that
    action.
    """
    if not kwargs['created']:
        return

    cbas = ContentBindingAndSubtype(content_binding=kwargs['instance'], subtype=None)
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
    cbas = ContentBindingAndSubtype(content_binding=subtype.parent, subtype=subtype)
    cbas.save()

# Link the update_content_binding[_subtype] functions to the objects
# Post delete handlers don't need to be written because they are part of how foreign keys work
post_save.connect(update_content_binding, sender=ContentBinding)
post_save.connect(update_content_binding_subtype, sender=ContentBindingSubtype)


class ContentBlock(models.Model):
    """
    Model for a Content Block
    """
    message = models.TextField(blank=True)

    timestamp_label = models.DateTimeField(auto_now_add=True)
    inbox_message = models.ForeignKey('InboxMessage', blank=True, null=True)
    content_binding_and_subtype = models.ForeignKey('ContentBindingAndSubtype')
    content = models.TextField()
    padding = models.TextField(blank=True)

    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def to_content_block_10(self):
        """
        Returns a tm10.ContentBlock
        based on this model

        Returns:
            A tm10.ContentBlock object
        """

        content_binding = self.content_binding_and_subtype.content_binding.binding_id
        cb = tm10.ContentBlock(content_binding=content_binding, content=self.content, padding=self.padding)
        if self.timestamp_label:
            cb.timestamp_label = self.timestamp_label

        return cb

    def to_content_block_11(self):
        """
        Returns a tm11.ContentBlock based
        on this model

        Returns:
            A tm11.ContentBlock object
        """

        content_binding = tm11.ContentBinding(self.content_binding_and_subtype.content_binding.binding_id)
        if self.content_binding_and_subtype.subtype:
            content_binding.subtype_ids.append(self.content_binding_and_subtype.subtype.subtype_id)
        cb = tm11.ContentBlock(content_binding=content_binding, content=self.content, padding=self.padding)
        if self.timestamp_label:
            cb.timestamp_label = self.timestamp_label

        return cb

    @staticmethod
    def from_content_block_10(content_block, inbox_message=None):
        """
        Returns a ContentBlock model object
        based on a tm10.ContentBlock object

        NOTE THAT THIS FUNCTION DOES NOT CALL save() on the
        returned model.

        :param content_block: A tm10.ContentBlock
        :param inbox_message: A tm10.InboxMessage
        :return: An **unsaved** models.ContentBlock instance
        """
        binding_id = content_block.content_binding
        cb = ContentBlock()
        try:
            cbas = ContentBindingAndSubtype.objects.get(content_binding__binding_id=binding_id,
                                                        subtype__subtype_id=None)
            cb.content_binding_and_subtype = cbas
        except ContentBindingAndSubtype.DoesNotExist as dne:
            raise StatusMessageException()

        cb.content = content_block.content
        if content_block.padding:
            cb.padding = content_block.padding
        if inbox_message:
            cb.inbox_message = inbox_message
        # TODO: What about signatures?
        return cb

    @staticmethod
    def from_content_block_11(content_block, inbox_message=None):
        """
        Returns a ContentBlock model object
        based on a tm11.ContentBlock object

        inbox_message is the models.InboxMessage that the
        content block arrived in

        NOTE THAT THIS FUNCTION DOES NOT CALL save() on the
        returned model.

        Returns:
            An **unsaved** models.ContentBlock object
        """
        # Get the Content Binding Binding Id and (if present) Subtype
        binding_id = content_block.content_binding.binding_id
        subtype_id = None
        if len(content_block.content_binding.subtype_ids) > 0:
            subtype_id = content_block.content_binding.subtype_ids[0]

        cb = ContentBlock()

        try:
            cbas = ContentBindingAndSubtype.objects.get(content_binding__binding_id=binding_id,
                                                        subtype__subtype_id=subtype_id)
            cb.content_binding_and_subtype = cbas
        except ContentBindingAndSubtype.DoesNotExist as dne:
            raise StatusMessageException()

        cb.content = content_block.content
        if content_block.padding:
            cb.padding = content_block.padding
        if content_block.message:
            cb.message = content_block.message
        if inbox_message:
            cb.inbox_message = inbox_message
        #  TODO: What about signatures?
        return cb

    def __unicode__(self):
        return u'#%s: %s; %s' % (self.id, self.content_binding_and_subtype, self.timestamp_label.isoformat())

    class Meta:
        ordering = ['timestamp_label']
        verbose_name = "Content Block"


class DataCollection(models.Model):
    """
    Model for a TAXII Data Collection
    """
    name = models.CharField(max_length=MAX_NAME_LENGTH, unique=True)
    description = models.TextField(blank=True)
    type = models.CharField(max_length=MAX_NAME_LENGTH, choices=DATA_COLLECTION_CHOICES)
    enabled = models.BooleanField(default=True)
    accept_all_content = models.BooleanField(default=False)
    supported_content = models.ManyToManyField('ContentBindingAndSubtype', blank=True, null=True)
    content_blocks = models.ManyToManyField('ContentBlock', blank=True, null=True)

    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def get_binding_intersection_10(self, binding_list, in_response_to):
        """
        Given a list of tm10.ContentBinding objects, return the ContentBindingAndSubtypes that are in this
        Data Collection

        :param binding_list: A list of strings representing ContentBinding IDs
        :param in_response_to: The request message's message ID. Used if a StatusMessageException is raised
        :return: A list of ContentBindingAndSubtype objects representing the intersection of this Data Collection's\
                 supported Content Bindings and binding_list.
        """

        if binding_list is None or len(binding_list) == 0:
            return None

        matching_cbas = []

        for content_binding in binding_list:
            try:
                cb = ContentBindingAndSubtype.objects.get(content_binding__binding_id=content_binding,
                                                          subtype=None)  # Subtypes are not in TAXII 1.0
                matching_cbas.append(cb)
            except ContentBindingAndSubtype.DoesNotExist:
                pass # This is OK. Other errors are not

        if len(matching_cbas) == 0:
            if self.accept_all_content:
                bindings = ContentBindingAndSubtype.objects.filter(subtype=None)
            else:
                bindings = self.supported_content.all()

            supported_content = [b.binding_id for b in bindings]
            raise StatusMessageException(in_response_to,
                                         ST_UNSUPPORTED_CONTENT_BINDING,
                                         status_detail={SD_SUPPORTED_CONTENT: supported_content})

            return matching_cbas

    def get_binding_intersection_11(self, binding_list, in_response_to):
        """
        Arguments:
            binding_list - a list of tm11.ContentBinding objects

        Returns:
            A list of ContentBindingAndSubtype objects representing the intersection of this Data Collection's \
            supported Content Bindings and binding_list.

        Raises:
            A StatusMessageException if the intersection is
            an empty set.
        """
        if binding_list is None or len(binding_list) == 0:
            return None

        matching_cbas = []

        for content_binding in binding_list:
            cb_id = content_binding.binding_id
            for subtype_id in content_binding.subtype_ids:
                try:
                    cb = ContentBindingAndSubtype.objects.get(content_binding__binding_id=cb_id,
                                                              subtype__subtype_id=subtype_id)
                    matching_cbas.append(cb)
                except ContentBindingAndSubtype.DoesNotExist:
                    pass  # This is OK. Other errors are not

            if len(content_binding.subtype_ids) == 0:
                matches = ContentBindingAndSubtype.objects.filter(content_binding__binding_id=cb_id)
                matching_cbas.extend(list(matches))

        if len(matching_cbas) == 0:  # No matching ContentBindingAndSubtype objects were found
            if self.accept_all_content:
                bindings = ContentBindingAndSubtype.objects.all()
            else:
                bindings = self.supported_content.all()

            supported_content = [b.to_content_binding_11() for b in bindings]
            raise StatusMessageException(in_response_to,
                                         ST_UNSUPPORTED_CONTENT_BINDING,
                                         status_detail={SD_SUPPORTED_CONTENT: supported_content})

        return matching_cbas

    def is_content_supported(self, cbas):
        """
        Takes an ContentBindingAndSubtype object and determines if
        this data collection supports it.

        Decision process is:
        1. If this accepts any content, return True
        2. If this supports binding ID > (All), return True
        3. If this supports binding ID and subtype ID, return True
        4. Otherwise, return False,
        """

        # 1
        if self.accept_all_content:
            return SupportInfo(True)

        # 2
        if len(self.supported_content.filter(content_binding=cbas.content_binding, subtype=None)) > 0:
            return SupportInfo(True)

        # 2a (e.g., subtype = None so #3 would end up being the same check as #2)
        if not cbas.subtype:  # No further checking can be done
            return SupportInfo(False)

        # 3
        if len(self.supported_content.filter(content_binding=cbas.content_binding, subtype=cbas.subtype)) > 0:
            return SupportInfo(True)

        # 4
        return SupportInfo(False)

    def to_feed_information_10(self):
        """
        Returns:
            A tm10.FeedInformation object
        """
        fi = tm10.FeedInformation(feed_name=self.name,
                                  feed_description=self.description,
                                  supported_contents=self.get_supported_content_10() or "TODO: use a different value here",
                                  available=self.enabled,
                                  push_methods=self.get_push_methods_10(),
                                  polling_service_instances=self.get_polling_service_instances_10(),
                                  subscription_methods=self.get_subscription_methods_10(),
                                  # collection_volume,
                                  # collection_type,
                                  # and receiving_inbox_services can't be expressed in TAXII 1.0
                                  )

        return fi

    def to_collection_information_11(self):
        """
        Returns:
            A tm11.CollectionInformation object
            based on this model
        """

        ci = tm11.CollectionInformation(collection_name=self.name,
                                        collection_description=self.description,
                                        supported_contents=self.get_supported_content_11(),
                                        available=self.enabled,
                                        push_methods=self.get_push_methods_11(),
                                        polling_service_instances=self.get_polling_service_instances_11(),
                                        subscription_methods=self.get_subscription_methods_11(),
                                        collection_volume=None,  # TODO: Maybe add this to the model?
                                        collection_type=self.type,
                                        receiving_inbox_services=self.get_receiving_inbox_services_11())
        return ci

    def get_supported_content_10(self):
        """
        Returns:
            A list of strings indicating the Content Binding IDs that this
            Data Collection supports. None indicates all are supported.
        """
        return_list = []

        if self.accept_all_content:
            return_list = None  # Indicates accept all
        else:
            for content in self.supported_content.filter(subtype=None):
                return_list.append(content.content_binding.binding_id)
        return return_list

    def get_supported_content_11(self):
        """
        Returns:
            A list of tm11.ContentBlock objects indicating which ContentBindings are supported.
            None indicates all are supported.
        """
        return_list = []

        if self.accept_all_content:
            return_list = None  # Indicates accept all
        else:
            supported_content = {}

            for content in self.supported_content.all():
                binding_id = content.content_binding.binding_id
                subtype = content.subtype
                if binding_id not in supported_content:
                    supported_content[binding_id] = tm11.ContentBinding(binding_id=binding_id)

                if subtype and subtype.subtype_id not in supported_content[binding_id].subtype_ids:
                    supported_content[binding_id].subtype_ids.append(subtype.subtype_id)

            return_list = supported_content.values()

        return return_list

    def get_push_methods_10(self):
        """
        TODO: Implement this
        This depends on the ability of taxii_services to push content
        and includes client capabilities
        """
        return None

    def get_push_methods_11(self):
        """
        TODO: Implement this.
        This depends on the ability of taxii_services to push content
        and includes client capabilities
        """
        return None

    def get_polling_service_instances_10(self):
        """
        Returns a list of tm10.PollingServiceInstance objects
        identifying the TAXII Poll Services that can be polled
        for this Data Collection
        """
        poll_instances = []
        poll_services = PollService.objects.filter(data_collections=self, enabled=True)
        for poll_service in poll_services:
            message_bindings = [mb.binding_id for mb in poll_service.supported_message_bindings.all()]
            for supported_protocol_binding in poll_service.supported_protocol_bindings.all():
                poll_instance = tm10.PollingServiceInstance(supported_protocol_binding.binding_id, poll_service.path, message_bindings)
                poll_instances.append(poll_instance)

        return poll_instances

    def get_polling_service_instances_11(self):
        """
        Returns a list of tm11.PollingServiceInstance objects identifying the
        TAXII Poll Services that can be polled for this Data Collection
        """
        poll_instances = []
        poll_services = PollService.objects.filter(data_collections=self, enabled=True)
        for poll_service in poll_services:
            message_bindings = [mb.binding_id for mb in poll_service.supported_message_bindings.all()]
            for supported_protocol_binding in poll_service.supported_protocol_bindings.all():
                poll_instance = tm11.PollingServiceInstance(supported_protocol_binding.binding_id,
                                                            poll_service.path,
                                                            message_bindings)
                poll_instances.append(poll_instance)

        return poll_instances

    def get_subscription_methods_10(self):
        """
        Returns a list of tm10.SubscriptionMethod objects identifying the TAXII
        Collection Management Services handling subscriptions for this Data Collection
        """
        # TODO: Probably wrong, but here's the idea
        subscription_methods = []
        collection_management_services = CollectionManagementService.objects.filter(advertised_collections=self,
                                                                                    enabled=True)
        for collection_management_service in collection_management_services:
            message_bindings = [mb.binding_id for mb in collection_management_service.supported_message_bindings.all()]
            for supported_protocol_binding in collection_management_service.supported_protocol_bindings.all():
                subscription_method = tm10.SubscriptionMethod(supported_protocol_binding.binding_id,
                                                              collection_management_service.path,
                                                              message_bindings)
                subscription_methods.append(subscription_method)

        return subscription_methods

    def get_subscription_methods_11(self):
        """
        Returns a list of tm11.SubscriptionMethod objects identifying the TAXII
        Collection Management Services handling subscriptions for this Data Collection
        """
        # TODO: Probably wrong, but here's the idea
        subscription_methods = []
        collection_management_services = CollectionManagementService.objects.filter(advertised_collections=self,
                                                                                    enabled=True)
        for collection_management_service in collection_management_services:
            message_bindings = [mb.binding_id for mb in collection_management_service.supported_message_bindings.all()]
            for supported_protocol_binding in collection_management_service.supported_protocol_bindings.all():
                subscription_method = tm11.SubscriptionMethod(supported_protocol_binding.binding_id, collection_management_service.path, message_bindings)
                subscription_methods.append(subscription_method)

        return subscription_methods

    def get_receiving_inbox_services_11(self):
        """
        Return a set of tm11.ReceivingInboxService objects identifying the TAXII
        Inbox Services that accept content for this Data Collection.
        """
        receiving_inbox_services = []
        inbox_services = InboxService.objects.filter(destination_collections=self, enabled=True)

        for inbox_service in inbox_services:
            message_bindings = [mb.binding_id for mb in inbox_service.supported_message_bindings.all()]
            for supported_protocol_binding in inbox_service.supported_protocol_bindings.all():
                receiving_inbox_service = tm11.ReceivingInboxService(supported_protocol_binding.binding_id,
                                                                     inbox_service.path,
                                                                     message_bindings,
                                                                     # TODO: Work on supported_contents
                                                                     supported_contents=None)

                receiving_inbox_services.append(receiving_inbox_service)

        return receiving_inbox_services

    def __unicode__(self):
        return u'%s (%s)' % (self.name, self.type)

    class Meta:
        ordering = ['name']
        verbose_name = "Data Collection"


class QueryScope(models.Model):
    """
    Model for Query Scope
    """
    name = models.CharField(max_length=MAX_NAME_LENGTH)
    description = models.TextField(blank=True)
    supported_query = models.ForeignKey('SupportedQuery')
    scope = models.CharField(max_length=MAX_NAME_LENGTH)
    scope_type = models.CharField(max_length=MAX_NAME_LENGTH, choices=SCOPE_CHOICES)

    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def clean(self):
        super(QueryScope, self).clean()
        try:
            validation.do_check(self.scope, 'scope', regex_tuple=tdq.targeting_expression_regex)
        except:
            raise ValidationError('Scope syntax was not valid. Syntax is a list of: (<item>, *, **, or @<item>) separated by a /. No leading slash.')

        handler_class = self.supported_query.query_handler.get_handler_class()

        # TODO: Do something about this. Make a class?
        supported, error = handler_class.is_scope_supported(self.scope)
        if not supported:
            raise ValidationError('This query scope is not supported by the handler: %s' %
                                  str(error))

    def __unicode__(self):
        return u'%s (%s)' % (self.name, self.scope)


class DiscoveryService(_TaxiiService):
    """
    Model for a TAXII Discovery Service
    """
    service_type = SVC_DISCOVERY
    discovery_handler = models.ForeignKey('MessageHandler',
                                          limit_choices_to={'supported_messages__contains':
                                                            'DiscoveryRequest'})
    advertised_discovery_services = models.ManyToManyField('self', blank=True)
    advertised_inbox_services = models.ManyToManyField('InboxService', blank=True)
    advertised_poll_services = models.ManyToManyField('PollService', blank=True)
    advertised_collection_management_services = models.ManyToManyField('CollectionManagementService', blank=True)

    def get_message_handler(self, taxii_message):
        if taxii_message.message_type == MSG_DISCOVERY_REQUEST:
            return self.discovery_handler

        raise StatusMessageException(taxii_message.message_id,
                                     ST_FAILURE,
                                     message="Message not supported by this service")

    def get_advertised_services(self):
        """
        Returns:
            A list of DiscoveryService, InboxService, PollService, and
            CollectionManagementService objects that this DiscoveryService
            advertises
        """
        # Chain together all the enabled services that this discovery service advertises
        advertised_services = list(chain(self.advertised_discovery_services.filter(enabled=True),
                                         self.advertised_poll_services.filter(enabled=True),
                                         self.advertised_inbox_services.filter(enabled=True),
                                         self.advertised_collection_management_services.filter(enabled=True)))
        return advertised_services

    def to_discovery_response_10(self, in_response_to):
        """
        Returns:
            A tm10.DiscoveryResponse based on this model.
        """
        advertised_services = self.get_advertised_services()
        discovery_response = tm10.DiscoveryResponse(generate_message_id(), in_response_to)
        for service in advertised_services:
            service_instances = service.to_service_instances_10()
            discovery_response.service_instances.extend(service_instances)

        # Return the Discovery Response
        return discovery_response

    def to_discovery_response_11(self, in_response_to):
        """
        Returns:
            A tm11.DiscoveryResponse based on this model.
        """
        advertised_services = self.get_advertised_services()
        discovery_response = tm11.DiscoveryResponse(generate_message_id(), in_response_to)
        for service in advertised_services:
            service_instances = service.to_service_instances_11()
            discovery_response.service_instances.extend(service_instances)

        # Return the Discovery Response
        return discovery_response

    class Meta:
        verbose_name = "Discovery Service"


class InboxMessage(models.Model):
    """
    Used to store information about received Inbox Messages
    """
    # TODO: What should I index on?
    # TODO: NONE of these fields should be editable in the admin, but they should all be viewable
    message_id = models.CharField(max_length=MAX_NAME_LENGTH)
    sending_ip = models.CharField(max_length=MAX_NAME_LENGTH)
    datetime_received = models.DateTimeField(auto_now_add=True)
    result_id = models.CharField(max_length=MAX_NAME_LENGTH, blank=True, null=True)

    # Record Count items
    record_count = models.IntegerField(blank=True, null=True)
    partial_count = models.BooleanField(default=False)

    # Subscription Information items
    collection_name = models.CharField(max_length=MAX_NAME_LENGTH, blank=True, null=True)
    subscription_id = models.CharField(max_length=MAX_NAME_LENGTH, blank=True, null=True)
    exclusive_begin_timestamp_label = models.DateTimeField(blank=True, null=True)
    inclusive_end_timestamp_label = models.DateTimeField(blank=True, null=True)

    received_via = models.ForeignKey('InboxService', blank=True, null=True)
    original_message = models.TextField(blank=True, null=True)
    content_block_count = models.IntegerField()
    content_blocks_saved = models.IntegerField()

    @staticmethod
    def from_inbox_message_10(inbox_message, django_request, received_via=None):
        """
        Creates an InboxMessage model object from a tm10.InboxMessage object.

        NOTE THAT THIS FUNCTION DOES NOT CALL .save()

        :param inbox_message: The tm10.InboxMessage to create as a DB object
        :param django_request: The django request that contained the inbox message
        :param receved_via: The inbox service this Inbox Message was received via
        :return: An **unsaved** models.InboxMessage object
        """

        inbox_message_db = InboxMessage()
        inbox_message_db.message_id = inbox_message.message_id
        inbox_message_db.sending_ip = django_request.META.get('REMOTE_ADDR', None)

        if inbox_message.subscription_information:
            si = inbox_message.subscription_information
            inbox_message_db.collection_name = si.feed_name
            inbox_message_db.subscription_id = si.subscription_id
            # TODO: Match up exclusive vs inclusive
            inbox_message_db.exclusive_begin_timestamp_label = si.inclusive_begin_timestamp_label
            inbox_message_db.inclusive_end_timestamp_label = si.inclusive_end_timestamp_label

        if received_via:
            inbox_message_db.received_via = received_via

        inbox_message_db.original_message = inbox_message.to_xml()
        inbox_message_db.content_block_count = len(inbox_message.content_blocks)
        inbox_message_db.content_blocks_saved = 0

        return inbox_message_db

    @staticmethod
    def from_inbox_message_11(inbox_message, django_request, received_via=None):
        """
        Create an InboxMessage model object
        from a tm11.InboxMessage object

        NOTE THAT THIS FUNCTION DOES NOT CALL .save()

        Returns:
            An **unsaved** models.InboxMessage object.
        """

        # For bookkeeping purposes, create an InboxMessage object
        # in the database
        inbox_message_db = InboxMessage()  # The database instance of the inbox message
        inbox_message_db.message_id = inbox_message.message_id
        inbox_message_db.sending_ip = django_request.META.get('REMOTE_ADDR', None)
        if inbox_message.result_id:
            inbox_message_db.result_id = inbox_message.result_id

        if inbox_message.record_count:
            inbox_message_db.record_count = inbox_message.record_count.record_count
            inbox_message_db.partial_count = inbox_message.record_count.partial_count

        if inbox_message.subscription_information:
            si = inbox_message.subscription_information
            inbox_message_db.collection_name = si.collection_name
            inbox_message_db.subscription_id = si.subscription_id
            if si.exclusive_begin_timestamp_label:
                inbox_message_db.exclusive_begin_timestamp_label = si.exclusive_begin_timestamp_label
            if si.inclusive_end_timestamp_label:
                inbox_message_db.inclusive_end_timestamp_label = si.inclusive_end_timestamp_label

        if received_via:
            inbox_message_db.received_via = received_via  # This is an inbox service

        inbox_message_db.original_message = inbox_message.to_xml()
        inbox_message_db.content_block_count = len(inbox_message.content_blocks)
        inbox_message_db.content_blocks_saved = 0

        return inbox_message_db

    def __unicode__(self):
        return u'%s - %s' % (self.message_id, self.datetime_received)

    class Meta:
        ordering = ['datetime_received']
        verbose_name = "Inbox Message"


class InboxService(_TaxiiService):
    """
    Model for a TAXII Inbox Service
    """
    service_type = SVC_INBOX
    inbox_message_handler = models.ForeignKey('MessageHandler',
                                              limit_choices_to={'supported_messages__contains':
                                                                'InboxMessage'})
    destination_collection_status = models.CharField(max_length=MAX_NAME_LENGTH, choices=ROP_CHOICES)
    destination_collections = models.ManyToManyField('DataCollection', blank=True)
    accept_all_content = models.BooleanField(default=False)
    supported_content = models.ManyToManyField('ContentBindingAndSubtype', blank=True, null=True)

    def get_message_handler(self, taxii_message):
        if taxii_message.message_type == MSG_INBOX_MESSAGE:
            return self.inbox_message_handler

        raise StatusMessageException(taxii_message.message_id,
                                     ST_FAILURE,
                                     message="Message not supported by this service")

    def is_content_supported(self, cbas):
        """
        Takes an ContentBindingAndSubtype object and determines if
        this data collection supports it.

        Decision process is:
        1. If this accepts any content, return True
        2. If this supports binding ID > (All), return True
        3. If this supports binding ID and subtype ID, return True
        4. Otherwise, return False,
        """

        # 1
        if self.accept_all_content:
            return SupportInfo(True, None)

        # 2
        if len(self.supported_content.filter(content_binding=cbas.content_binding, subtype=None)) > 0:
            return SupportInfo(True, None)

        # 2a (e.g., subtype = None so #3 would end up being the same check as #2)
        if not cbas.subtype:  # No further checking can be done
            return SupportInfo(False, None)

        # 3
        if len(self.supported_content.filter(content_binding=cbas.content_binding, subtype=cbas.subtype)) > 0:
            return SupportInfo(True, None)

        # 4
        return SupportInfo(False, None)

    def validate_destination_collection_names(self, name_list, in_response_to):
        """
        Returns:
            A list of Data Collections

        Raises:
            A StatusMessageException if any Destination Collection Names are invalid.
        """
        if name_list is None:
            name_list = []

        num = len(name_list)
        if self.destination_collection_status == REQUIRED[0] and num == 0:
            raise StatusMessageException(in_response_to,
                                         ST_DESTINATION_COLLECTION_ERROR,
                                         'A Destination_Collection_Name is required and none were specified',
                                         {SD_ACCEPTABLE_DESTINATION: [str(dc.name) for dc in self.destination_collections.all()]})

        if self.destination_collection_status == PROHIBITED[0] and num > 0:
            raise StatusMessageException(in_response_to,
                                         ST_DESTINATION_COLLECTION_ERROR,
                                         'Destination_Collection_Names are prohibited on this Inbox Service',
                                         {SD_ACCEPTABLE_DESTINATION: [str(dc.name) for dc in self.destination_collections.all()]})

        collections = []
        for name in name_list:
            try:
                collection = self.destination_collections.get(name=name, enabled=True)
                collections.append(collection)
            except:
                raise StatusMessageException(in_response_to,
                                             ST_NOT_FOUND,
                                             'The Data Collection was not found',
                                             {SD_ITEM: name})

        return collections

    def to_service_instances_10(self):
        service_instances = super(InboxService, self).to_service_instances_10()
        if self.accept_all_content:
            return service_instances

        for si in service_instances:
            si.accepted_contents = self.get_supported_content_10()
        return service_instances

    def to_service_instances_11(self):
        service_instances = super(InboxService, self).to_service_instances_11()
        if self.accept_all_content:
            return service_instances

        for si in service_instances:
            si.accepted_contents = self.get_supported_content_11()
        return service_instances

    def get_supported_content_10(self):
        return_list = []

        if self.accept_all_content:
            return_list = None  # Indicates accept all
        else:
            for content in self.supported_content.all():
                return_list.append(content.content_binding.binding_id)
        return return_list

    def get_supported_content_11(self):
        return_list = []

        if self.accept_all_content:
            return_list = None  # Indicates accept all
        else:
            supported_content = {}

            for content in self.supported_content.all():
                binding_id = content.content_binding.binding_id
                subtype = content.subtype
                if binding_id not in supported_content:
                    supported_content[binding_id] = tm11.ContentBinding(binding_id=binding_id)

                if subtype and subtype.subtype_id not in supported_content[binding_id].subtype_ids:
                    supported_content[binding_id].subtype_ids.append(subtype.subtype_id)

            return_list = supported_content.values()

        return return_list

    class Meta:
        verbose_name = "Inbox Service"


class MessageBinding(_BindingBase):
    """
    Represents a Message Binding, used to establish the supported syntax
    for a given TAXII exchange, "e.g., XML".

    Ex:
    XML message binding id : "urn:taxii.mitre.org:message:xml:1.1"
    """
    class Meta:
        verbose_name = "Message Binding"


class MessageHandler(_Handler):
    """
    MessageHandler model object.
    """
    handler_functions = ['handle_message']
    supported_messages = models.CharField(max_length=MAX_NAME_LENGTH, editable=False)

    def clean(self):
        handler_class = super(MessageHandler, self).clean()
        try:
            self.supported_messages = handler_class.get_supported_request_messages()
        except:
            raise ValidationError('There was a problem getting the list of supported messages: %s' %
                                  str(sys.exc_info()))

    class Meta:
        verbose_name = "Message Handler"


class PollService(_TaxiiService):
    """
    Model for a Poll Service
    """
    service_type = SVC_POLL
    poll_request_handler = models.ForeignKey('MessageHandler',
                                             related_name='poll_request',
                                             limit_choices_to={'supported_messages__contains':
                                                               'PollRequest'})
    poll_fulfillment_handler = models.ForeignKey('MessageHandler',
                                                 related_name='poll_fulfillment',
                                                 limit_choices_to={'supported_messages__contains':
                                                                   'PollFulfillmentRequest'},
                                                 blank=True,
                                                 null=True)
    data_collections = models.ManyToManyField('DataCollection')
    supported_queries = models.ManyToManyField('SupportedQuery', blank=True, null=True)
    requires_subscription = models.BooleanField(default=False)
    max_result_size = models.IntegerField(blank=True, null=True)  # Blank means "no limit"

    def clean(self):
        """
        Perform some validation on the model

        :return: Nothing
        """

        if self.max_result_size is not None and self.max_result_size < 1:
            raise ValidationError("Max Result Size must be blank or greater than 1!")

    def get_message_handler(self, taxii_message):
        if taxii_message.message_type == MSG_POLL_REQUEST:
            return self.poll_request_handler
        elif taxii_message.message_type == MSG_POLL_FULFILLMENT_REQUEST:
            return self.poll_fulfillment_handler

        raise StatusMessageException(taxii_message.message_id,
                                     ST_FAILURE,
                                     message="Message not supported by this service")

    def validate_collection_name(self, name, in_response_to):
        """
        Arguments:
            name (str) - The name of a Data Collection
            in_response_to (str) - The message_id to use if this function raises an Exception

        Returns:
            A DataCollection object based on the name

        Raises:
            A StatusMessageException if the named Data Collection does not exist
        """
        try:
            collection = self.data_collections.get(name=name)
        except DataCollection.DoesNotExist as dne:
            raise StatusMessageException(in_response_to,
                                         ST_NOT_FOUND,
                                         'The collection you requested was not found',
                                         {SD_ITEM: name})

        return collection

    def get_supported_query(self, query, in_response_to):
        """
        This function follows this workflow to find a matching query handler:
        TODO: Once the function works, document what it does

        Arguments:
            query - tdq.DefaultQuery object

        Returns:
            a QueryHandler for handling the query

        Raises:
            A StatusMessageException if a QueryHandler was not found
        """

        # 1. filter down by Targeting Expression ID
        tev_kwargs = {'query_handler__targeting_expression_ids__value': query.targeting_expression_id}
        potential_matches = self.supported_queries.filter(**tev_kwargs)

        if len(potential_matches) == 0:
            exprs = []
            for sq in self.supported_queries.all():
                for tev in sq.query_handler.targeting_expression_ids.all():
                    exprs.append(tev.value)

            raise StatusMessageException(in_response_to,
                                         ST_UNSUPPORTED_TARGETING_EXPRESSION_ID,
                                         status_detail={'TARGETING_EXPRESSION_ID': exprs})

        # Build the list of unique targets and capability modules used in the query
        targets = set([])  # Targets
        cms = set([])  # Capability Modules
        to_search = [query.criteria]

        while len(to_search) > 0:
            item = to_search.pop()
            try:
                targets.add(item.target)
                cms.add(item.test.capability_id)
            except AttributeError:
                to_search.extend(item.criteria)
                to_search.extend(item.criterion)

        for cm in cms:
            potential_matches = potential_matches.filter(query_handler__capability_modules__value=cm)
            if len(potential_matches) == 0:
                raise StatusMessageException(in_response_to,
                                             ST_UNSUPPORTED_CAPABILITY_MODULE,
                                             status_detail={SD_CAPABILITY_MODULE: ['TBD']})

        # Targets have to be checked in software (for now ... ?)
        list_potential_matches = list(potential_matches)
        # print 'looking at targets'
        for target in targets:
            for potential_match in list_potential_matches:
                tgt_support = potential_match.query_handler.get_handler_class().is_target_supported(target)
                if not tgt_support.is_supported:
                    list_potential_matches.remove(potential_match)
                    if len(list_potential_matches) == 0:
                        raise StatusMessageException(in_response_to,
                                                     ST_UNSUPPORTED_TARGETING_EXPRESSION,
                                                     message=tgt_support.message)
        # print 'done looking at targets'

        # We've found matches. Arbitrarily pick the first one.
        return list_potential_matches[0]

    def to_service_instances_11(self):
        service_instances = super(PollService, self).to_service_instances_11()

        for si in service_instances:
            for sq in self.supported_queries.all():
                si.supported_query.append(sq.to_query_info_11())
        return service_instances

    class Meta:
        verbose_name = "Poll Service"


class ProtocolBinding(_BindingBase):
    """
    Represents a Protocol Binding, used to establish the supported transport
    for a given TAXII exchange, "e.g., HTTP".

    Ex:
    HTTP Protocol Binding : "urn:taxii.mitre.org:protocol:http:1.0"
    """
    class Meta:
        verbose_name = "Protocol Binding"


class QueryHandler(_Handler):
    """
    A model for Query Handlers. A query handler is a function that
    takes two arguments: A query and a content block and returns
    True if the Content Block passes the query and False otherwise.
    """

    # TODO: Update this list
    handler_functions = ['get_supported_cms',
                         'get_supported_tevs',
                         #'is_scope_supported',
                         'is_target_supported',
                         'filter_content',
                         'update_db_kwargs']

    targeting_expression_ids = models.ManyToManyField('TargetingExpressionId', editable=False, blank=True, null=True)
    capability_modules = models.ManyToManyField('CapabilityModule', editable=False, blank=True, null=True)

    def clean(self):
        handler_class = super(QueryHandler, self).clean()

    def is_tev_supported(self, tev):
        """
        tev is short for targeting expression vocabulary
        :param tev: (string) A targeting expression vocabulary identifier (ID)
        :return: A SupportInfo object indicating whether the tev is supported.
        """
        return self.get_handler_class().is_tev_supported(tev)

    def is_te_supported(self, te):
        """
        :param te: (string) A targeting expression
        :return: A SupportInfo object indicating whether the targeting expression is supported
        """
        return self.get_handler_class().is_te_supported(te)

    def is_cm_supported(self, cm):
        """
        :param cm: (string) A Capability Module ID
        :return: A SupportInfo object indicating whether the capability module is supported
        """
        return self.get_handler_class().is_cm_supported(cm)

    class Meta:
        verbose_name = "Query Handler"


#class QueryHandlerCapabilityModule(models.Model):
#    """
#    Assists in managing the QueryHandler/CapabilityModule relationships
#    """
#    query_handler = models.ForeignKey('QueryHandler')
#    capability_module = models.ForeignKey('CapabilityModule')


def update_query_handler(sender, **kwargs):
    """
    When a QueryHandler gets created, CapabilityModules is a M2M and can't
    be saved when the model is saved.
    """
    instance = kwargs['instance']
    handler_class = instance.get_handler_class()
    for cm in handler_class.get_supported_cms():
        cm_obj = CapabilityModule.objects.get(value=cm)
        instance.capability_modules.add(cm_obj)

    for tev in handler_class.get_supported_tevs():
        tev_obj = TargetingExpressionId.objects.get(value=tev)
        instance.targeting_expression_ids.add(tev_obj)

post_save.connect(update_query_handler, sender=QueryHandler)


class ResultSet(models.Model):
    """
    Model for Result Sets
    """
    data_collection = models.ForeignKey('DataCollection')
    subscription = models.ForeignKey('Subscription', blank=True, null=True)
    total_content_blocks = models.IntegerField()
    # TODO: Figure out how to limit choices to only the ResultSetParts that belong to this ResultSet
    last_part_returned = models.ForeignKey('ResultSetPart', blank=True, null=True)
    expires = models.DateTimeField()
    # TODO: There's nothing in here for pushing. It should be added
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u'ResultSet ID: %s; Collection: %s; Parts: %s.' % \
               (self.id, self.data_collection, self.resultsetpart_set.count())

    class Meta:
        verbose_name = "Result Set"


class ResultSetPart(models.Model):
    """
    Model for Result Set Parts
    """
    result_set = models.ForeignKey('ResultSet')
    part_number = models.IntegerField()
    content_blocks = models.ManyToManyField('ContentBlock')
    content_block_count = models.IntegerField()
    more = models.BooleanField(default=False)
    exclusive_begin_timestamp_label = models.DateTimeField(blank=True, null=True)
    inclusive_end_timestamp_label = models.DateTimeField(blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u'ResultSet ID: %s; Collection: %s; Part#: %s.' % \
               (self.result_set.id, self.result_set.data_collection, self.part_number)

    def to_poll_response_11(self, in_response_to):
        """
        Returns a tm11.PollResponse based on this model
        """

        poll_response = tm11.PollResponse(message_id=tm11.generate_message_id(),
                                          in_response_to=in_response_to,
                                          collection_name=self.result_set.data_collection.name)

        if self.exclusive_begin_timestamp_label:
            poll_response.exclusive_begin_timestamp_label = self.exclusive_begin_timestamp_label

        if self.inclusive_end_timestamp_label:
            poll_response.inclusive_end_timestamp_label = self.inclusive_end_timestamp_label

        if self.result_set.subscription:
            poll_response.subscription_id = self.result_set.subscription.subscription_id

        poll_response.record_count = tm11.RecordCount(self.result_set.total_content_blocks, False)
        poll_response.more = self.more
        poll_response.result_id = str(self.result_set.pk)
        poll_response.result_part_number = self.part_number

        for content_block in self.content_blocks.all():
            cb = content_block.to_content_block_11()
            poll_response.content_blocks.append(cb)

        return poll_response

    class Meta:
        verbose_name = "Result Set Part"
        unique_together = ('result_set', 'part_number',)


class Subscription(models.Model):
    """
    Model for Subscriptions
    """
    subscription_id = models.CharField(max_length=MAX_NAME_LENGTH, unique=True, default=uuid.uuid4) #TODO: See #26
    data_collection = models.ForeignKey('DataCollection')
    response_type = models.CharField(max_length=MAX_NAME_LENGTH, choices=RESPONSE_CHOICES, default=RT_FULL)
    accept_all_content = models.BooleanField(default=False)
    supported_content = models.ManyToManyField('ContentBindingAndSubtype', blank=True, null=True)
    query = models.TextField(blank=True, null=True)
    # push_parameters = models.ForeignKey(PushParameters)  # TODO: Create a push parameters object
    delivery = models.CharField(max_length=MAX_NAME_LENGTH, choices=DELIVERY_CHOICES, default=SUBS_POLL)
    status = models.CharField(max_length=MAX_NAME_LENGTH, choices=SUBSCRIPTION_STATUS_CHOICES, default=SS_ACTIVE)
    date_paused = models.DateTimeField(blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def validate_active(self, in_response_to):
        """
        If the status is not active, raises a StatusMessageException.
        Otherwise, has no effect
        """
        if not self.status == SS_ACTIVE:
            raise StatusMessageException(in_response_to,
                                         ST_FAILURE,
                                         'The Subscription is not active!')

    def to_poll_params_11(self):
        """
        Creates a tm11.PollParameters object based on the
        properties of this Subscription.
        """
        pp = tm11.PollParameters(response_type=self.response_type,
                                 content_bindings=self.supported_content.all(),  # Get supported contents?
                                 allow_asynch=False,  # TODO: This can't be specified?
                                 # delivery_parameters = self.push_parameters)
                                 query=self.query)  # ,  # TODO: Implement push_parameters
        return pp

    def to_subscription_instance_10(self):
        """
        Returns a tm10.SubscriptionInstance object
        based on this model
        """
        delivery_params = None  # TODO: Implement this
        poll_instances = None  # TODO: Implement this

        si = tm10.SubscriptionInstance(subscription_id=str(self.subscription_id),
                                       delivery_parameters=delivery_params,
                                       poll_instances=poll_instances)
        return si

    def to_subscription_instance_11(self):
        """
        Returns a tm11.SubscriptionInstance object based on this
        model
        """
        subscription_params = tm11.SubscriptionParameters(response_type=self.response_type,
                                                          content_bindings=[str(x) for x in self.supported_content.all()])

        if self.query:
            subscription_params.query = self.query.to_query_11()

        push_params = None  # TODO: Implement this
        poll_instances = None  # TODO: Implement this
        si = tm11.SubscriptionInstance(subscription_id=str(self.subscription_id),
                                       status=self.status,
                                       subscription_parameters=subscription_params,
                                       push_parameters=push_params,
                                       poll_instances=poll_instances)
        return si

    def __unicode__(self):
        return u'Subscription ID: %s' % self.subscription_id


class SupportedQuery(models.Model):
    """
    A SupportedQuery Object represents a QueryHandler plus
    an (optional, user-configurable) scope restriction of that
    QueryHandler.
    """
    name = models.CharField(max_length=MAX_NAME_LENGTH)
    description = models.TextField(blank=True)

    query_handler = models.ForeignKey('QueryHandler')
    use_handler_scope = models.BooleanField(default=True)
    preferred_scope = models.ManyToManyField('QueryScope', blank=True, null=True, related_name='preferred_scope')
    allowed_scope = models.ManyToManyField('QueryScope', blank=True, null=True, related_name='allowed_scope')

    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def is_query_supported(self, query):
        """
        :param query: a libtaxii.taxii_default_query.DefaultQuery object
        :return: A SupportInfo object indicating whether the Query is supported.
        """

        # If the Targeting Expression Vocabulary Identifier is not supported, indicate that
        tev_supp_info = self.is_tev_supported(query.targeting_expression_id)
        if tev_supp_info.is_supported is False:
            return tev_supp_info

        # Build the list of unique targets and capability modules used in the query
        targets = set([])  # Targets
        cms = set([])  # Capability Modules
        to_search = [query.criteria]

        while len(to_search) > 0:
            item = to_search.pop()
            try:
                targets.add(item.target)
                cms.add(item.test.capability_id)
            except AttributeError:
                to_search.extend(item.criteria)
                to_search.extend(item.criterion)

        for cm in cms:
            cm_supp_info = self.is_cm_supported(cm)
            if cm_supp_info.is_supported is False:
                return cm_supp_info

        for target in targets:
            tgt_supp_info = self.is_target_supported(target)
            if tgt_supp_info.is_supported is False:
                return tgt_supp_info

        return SupportInfo(is_supported=True)

    def is_tev_supported(self, tev):
        """
        :param tev: (string) A targeting expression vocabulary id
        :return: A SupportInfo object indicating whether the targeting expression vocabulary ID is supported
        """

        # Note: This function primarily exists to provide a future hook

        return self.query_handler.is_tev_supported()

    def is_cm_supported(self, cm):
        """
        :param cm: (string) A capability module id
        :return: a SupportInfo object indicating whether the capability module id is supported
        """

        # Note: This function primarily exists to provide a future hook

        return self.query_handler.is_cm_supported()

    def is_target_supported(self, target):
        """
        :param target: (string) A target
        :return: A SupportInfo object indicating whether the target is supported
        """
        if self.use_handler_scope is True:
            return self.query_handler.is_target_supported(target)
        else:
            raise NotImplementedError("UI Based restrictions of query handler not implemented yet!")

    def to_query_info_11(self):
        """
        Returns a tdq.QueryInfo object
        based on this model
        """
        preferred_scope = [ps.scope for ps in self.preferred_scope.all()]
        allowed_scope = [as_.scope for as_ in self.allowed_scope.all()]
        targeting_expression_id = self.query_handler.targeting_expression_id

        tei = tdq.DefaultQueryInfo.TargetingExpressionInfo(targeting_expression_id=targeting_expression_id,
                                                           preferred_scope=preferred_scope,
                                                           allowed_scope=allowed_scope)

        # TODO: I don't think commas are permitted, but they'd break this processing
        # Probably fix that, maybe through DB field validation
        # This is stored in the DB as a python list, so get rid of all the "extras"
        map_ = dict((ord(char), None) for char in " []\'")
        cm_list = self.query_handler.capability_modules.translate(map_).split(',')

        dqi = tdq.DefaultQueryInfo(targeting_expression_infos=[tei],
                                   capability_modules=cm_list)
        return dqi

    def __unicode__(self):
        return u'%s' % self.name

    class Meta:
        verbose_name = "Supported Query"
        verbose_name_plural = "Supported Queries"


class TargetingExpressionId(_Tag):
    pass


class Validator(_Handler):
    """
    Model for Validators. A Validator, at the moment,
    is an idea only. Eventually, it would be nice to be
    able to have content that comes in be passed to an
    automatic validator before storage.

    At some point, if a validator gets invented, this
    model will leverage that validator concept.
    """
    handler_functions = ['validate']
