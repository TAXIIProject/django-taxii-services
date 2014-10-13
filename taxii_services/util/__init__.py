# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from .. import models
from ..exceptions import StatusMessageException
from libtaxii.constants import *
import datetime
import dateutil
from dateutil.tz import tzutc


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

    def __str__(self):
        return "supported=%s;msg=%s;" % (self.is_supported, self.message)


class PollRequestProperties(object):
    """
    Holds a bunch of different items
    relating to fulfilling a PollRequest.

    It's similar to a tm11.PollRequest object,
    but holds some items specific to how
    django-taxii-services does things
    """

    def __init__(self):
        self.poll_request = None
        self.message_id = None
        self.collection = None
        self.subscription = None
        self.response_type = None
        self.content_bindings = None
        self.allow_asynch = None
        self.query = None
        self.supported_query = None
        self.exclusive_begin_timestamp_label = None
        self.inclusive_end_timestamp_label = None
        self.delivery_parameters = None

    def get_db_kwargs(self):
        kwargs = {}
        if self.collection.type == CT_DATA_FEED:
            if self.exclusive_begin_timestamp_label:
                kwargs['timestamp_label__gt'] = self.exclusive_begin_timestamp_label
            if self.inclusive_end_timestamp_label:
                kwargs['timestamp_label__lte'] = self.inclusive_end_timestamp_label
        if self.content_bindings:
            kwargs['content_binding__in'] = self.content_bindings
        return kwargs

    @staticmethod
    def from_poll_request_10(poll_service, poll_request):
        prp = PollRequestProperties()
        prp.poll_request = poll_request
        prp.message_id = poll_request.message_id
        prp.collection = poll_service.validate_collection_name(poll_request.feed_name, poll_request.message_id)

        if poll_request.subscription_id:
            try:
                s = models.Subscription.objects.get(subscription_id=poll_request.subscription_id)
                prp.subscription = s
            except models.Subscription.DoesNotExist:
                raise StatusMessageException(poll_request.message_id,
                                             ST_NOT_FOUND,
                                             status_detail={SD_ITEM: poll_request.subscription_id})
            prp.response_type = None
            prp.content_bindings = s.content_binding.all()
            prp.allow_asynch = None
            prp.delivery_parameters = s.delivery_parameters
        else:
            prp.response_type = None
            prp.content_bindings = prp.collection.get_binding_intersection_10(poll_request.content_bindings, prp.message_id)
            prp.delivery_parameters = poll_request.delivery_parameters

        if prp.collection.type != CT_DATA_FEED:  # Only Data Feeds existed in TAXII 1.0
            raise StatusMessageException(poll_request.message_id,
                                         ST_NOT_FOUND,
                                         "The Named Data Collection is not a Data Feed, it is a Data Set. "
                                         "Only Data Feeds can be"
                                         "Polled in TAXII 1.0",
                                         {SD_ITEM: poll_request.feed_name})

        current_datetime = datetime.datetime.now(tzutc())
        # If the request specifies a timestamp label in an acceptable range, use it.
        # Otherwise, don't use a begin timestamp label
        if poll_request.exclusive_begin_timestamp_label:
            pr_ebtl = poll_request.exclusive_begin_timestamp_label
            if pr_ebtl < current_datetime:
                prp.exclusive_begin_timestamp_label = poll_request.exclusive_begin_timestamp_label

        # Use either the specified end timestamp label;
        # or the current time iff the specified end timestmap label is after the current time
        prp.inclusive_end_timestamp_label = current_datetime
        if poll_request.inclusive_end_timestamp_label:
            pr_ietl = poll_request.inclusive_end_timestamp_label
            if pr_ietl < current_datetime:
                prp.inclusive_end_timestamp_label = poll_request.inclusive_end_timestamp_label

        if ((prp.inclusive_end_timestamp_label is not None and prp.exclusive_begin_timestamp_label is not None) and
            prp.inclusive_end_timestamp_label < prp.exclusive_begin_timestamp_label):
            raise StatusMessageException(prp.message_id,
                                         ST_FAILURE,
                                         message="Invalid Timestamp Labels: End TS Label is earlier "
                                                 "than Begin TS Label")

        return prp

    @staticmethod
    def from_poll_request_11(poll_service, poll_request):
        prp = PollRequestProperties()
        prp.poll_request = poll_request
        prp.message_id = poll_request.message_id
        prp.collection = poll_service.validate_collection_name(poll_request.collection_name, poll_request.message_id)

        if poll_request.subscription_id:
            try:
                s = models.Subscription.objects.get(subscription_id=poll_request.subscription_id)
                prp.subscription = s
            except models.Subscription.DoesNotExist:
                raise StatusMessageException(poll_request.message_id,
                                             ST_NOT_FOUND,
                                             "The subscription was not found",
                                             {SD_ITEM: poll_request.subscription_id})
            prp.response_type = s.response_type
            prp.content_bindings = s.content_binding.all()
            prp.allow_asynch = False
            prp.query = s.query
            if prp.query:
                prp.supported_query = poll_service.get_supported_query(prp.query, prp.message_id)
            else:
                prp.supported_query = None
            prp.delivery_parameters = s.delivery_parameters
        else:
            pp = poll_request.poll_parameters
            prp.response_type = pp.response_type
            prp.content_bindings = prp.collection.get_binding_intersection_11(pp.content_bindings, prp.message_id)
            prp.allow_asynch = pp.allow_asynch
            prp.query = pp.query
            if prp.query:
                prp.supported_query = poll_service.get_supported_query(prp.query, prp.message_id)
            else:
                prp.supported_query = None
            prp.delivery_parameters = pp.delivery_parameters

        if prp.collection.type == CT_DATA_FEED:  # Only data feeds care about timestamp labels
            current_datetime = datetime.datetime.now(tzutc())

            # If the request specifies a timestamp label in an acceptable range, use it.
            # Otherwise, don't use a begin timestamp label
            if poll_request.exclusive_begin_timestamp_label:
                pr_ebtl = poll_request.exclusive_begin_timestamp_label
                if pr_ebtl < current_datetime:
                    prp.exclusive_begin_timestamp_label = poll_request.exclusive_begin_timestamp_label

            # Use either the specified end timestamp label;
            # or the current time iff the specified end timestmap label is after the current time
            prp.inclusive_end_timestamp_label = current_datetime
            if poll_request.inclusive_end_timestamp_label:
                pr_ietl = poll_request.inclusive_end_timestamp_label
                if pr_ietl < current_datetime:
                    prp.inclusive_end_timestamp_label = poll_request.inclusive_end_timestamp_label

            if ((prp.inclusive_end_timestamp_label is not None and prp.exclusive_begin_timestamp_label is not None) and
                prp.inclusive_end_timestamp_label < prp.exclusive_begin_timestamp_label):
                raise StatusMessageException(prp.message_id,
                                             ST_FAILURE,
                                             message="Invalid Timestamp Labels: End TS Label is earlier "
                                                     "than Begin TS Label")

        return prp
