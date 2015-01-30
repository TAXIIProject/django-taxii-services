# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from django.test import TestCase, Client
from django.conf import settings

from .helpers import *
import libtaxii.messages_11 as tm11
import libtaxii.messages_10 as tm10


class SubscriptionTests11(TestCase):
    def setUp(self):
        settings.DEBUG = True
        add_basics()
        add_collection_service()

    def test_01(self):
        """
        Do a basic status
        :return:
        """

        sr = tm11.ManageCollectionSubscriptionRequest(message_id=generate_message_id(),
                                                      collection_name='default',
                                                      action=ACT_STATUS)
        msg = make_request('/collection-management/',
                           sr.to_xml(),
                           get_headers(VID_TAXII_SERVICES_11, False),
                           MSG_MANAGE_COLLECTION_SUBSCRIPTION_RESPONSE)

        if len(msg.subscription_instances) != 0:
            raise ValueError("Expected zero subscription instances in response!")

    def test_02(self):
        """
        Test creating a subscription
        :return:
        """
        sr = tm11.ManageCollectionSubscriptionRequest(message_id=generate_message_id(),
                                                      collection_name='default',
                                                      action=ACT_SUBSCRIBE)
        msg = make_request('/collection-management/',
                           sr.to_xml(),
                           get_headers(VID_TAXII_SERVICES_11, False),
                           MSG_MANAGE_COLLECTION_SUBSCRIPTION_RESPONSE,
                           num_subscription_instances=1,
                           subscription_status=SS_ACTIVE)

        return msg

    def test_03(self):
        """
        Test creating a subscription then pausing
        :return:
        """
        msg = self.test_02()
        subs_id = msg.subscription_instances[0].subscription_id
        sr = tm11.ManageCollectionSubscriptionRequest(message_id=generate_message_id(),
                                                      collection_name='default',
                                                      action=ACT_PAUSE,
                                                      subscription_id=subs_id)
        msg = make_request('/collection-management/',
                           sr.to_xml(),
                           get_headers(VID_TAXII_SERVICES_11, False),
                           MSG_MANAGE_COLLECTION_SUBSCRIPTION_RESPONSE,
                           num_subscription_instances=1,
                           subscription_status=SS_PAUSED,
                           subscription_id=subs_id)

        return msg

    def test_04(self):
        """
        Test creating a subscription, pausing, then resuming
        :return:
        """

        msg = self.test_03()
        subs_id = msg.subscription_instances[0].subscription_id
        sr = tm11.ManageCollectionSubscriptionRequest(message_id=generate_message_id(),
                                                      collection_name='default',
                                                      action=ACT_RESUME,
                                                      subscription_id=subs_id)

        msg = make_request('/collection-management/',
                           sr.to_xml(),
                           get_headers(VID_TAXII_SERVICES_11, False),
                           MSG_MANAGE_COLLECTION_SUBSCRIPTION_RESPONSE,
                           num_subscription_instances=1,
                           subscription_status=SS_ACTIVE,
                           subscription_id=subs_id)
        return msg

    def test_05(self):
        """
        Test creating a subscription then unsubscribing

        :return:
        """
        msg = self.test_02()
        subs_id = msg.subscription_instances[0].subscription_id
        sr = tm11.ManageCollectionSubscriptionRequest(message_id=generate_message_id(),
                                                      collection_name='default',
                                                      action=ACT_UNSUBSCRIBE,
                                                      subscription_id=subs_id)
        msg = make_request('/collection-management/',
                           sr.to_xml(),
                           get_headers(VID_TAXII_SERVICES_11, False),
                           MSG_MANAGE_COLLECTION_SUBSCRIPTION_RESPONSE,
                           num_subscription_instances=1,
                           subscription_status=SS_UNSUBSCRIBED,
                           subscription_id=subs_id)
        return msg

    def test_06(self):
        """
        Test creating a subscription, unsubscribing, then statusing
        :return:
        """
        msg = self.test_05()
        subs_id = msg.subscription_instances[0].subscription_id
        sr = tm11.ManageCollectionSubscriptionRequest(message_id=generate_message_id(),
                                                      collection_name='default',
                                                      action=ACT_STATUS,
                                                      subscription_id=subs_id)
        msg = make_request('/collection-management/',
                           sr.to_xml(),
                           get_headers(VID_TAXII_SERVICES_11, False),
                           MSG_MANAGE_COLLECTION_SUBSCRIPTION_RESPONSE,
                           num_subscription_instances=1,
                           subscription_status=SS_UNSUBSCRIBED,
                           subscription_id=subs_id)
        return msg

    def test_07(self):
        """
        Test creating 3 subscriptions then doing a status

        :return:
        """

        sr = tm11.ManageCollectionSubscriptionRequest(message_id=generate_message_id(),
                                                      collection_name='default',
                                                      action=ACT_SUBSCRIBE)

        msg1 = make_request('/collection-management/', sr.to_xml(), get_headers(VID_TAXII_SERVICES_11, False))

        sr.subscription_parameters.response_type = RT_COUNT_ONLY

        msg2 = make_request('/collection-management/', sr.to_xml(), get_headers(VID_TAXII_SERVICES_11, False))

        sr.subscription_parameters.content_bindings = [CB_STIX_XML_11,
                CB_STIX_XML_10]

        msg3 = make_request('/collection-management/', sr.to_xml(), get_headers(VID_TAXII_SERVICES_11, False))

        sr.action = ACT_STATUS

        msg = make_request('/collection-management/',
                           sr.to_xml(),
                           get_headers(VID_TAXII_SERVICES_11, False),
                           MSG_MANAGE_COLLECTION_SUBSCRIPTION_RESPONSE,
                           num_subscription_instances=3,
                           subscription_status=SS_ACTIVE)
        return msg


class SubscriptionTests10(TestCase):
    pass
