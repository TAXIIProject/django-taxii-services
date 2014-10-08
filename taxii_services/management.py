# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from .models import MessageHandler, QueryHandler

from django.core.exceptions import AppRegistryNotReady
from django.db.models.signals import post_syncdb
from django.db.utils import DatabaseError

query_handlers_to_retry = []
message_handlers_to_retry = []


def register_message_handler(message_handler, name=None, retry=True):
    """
    Attempts to create a MessageHandler model for the
    specified message_handler.

    If retry=True, DatabaseErrors will cause a retry.
    Other Errors will not. A retry consists of retrying
    this method when Django's post_syncdb signal is called.

    Args:
        message_handler (class or string) - The message handler to be registered
        name (str) - The name of the message handler to be registered
        retry (bool) - If registration fails, whether or not to retry later
    """
    try:
        if isinstance(message_handler, basestring):
            handler_string = message_handler
            if name is None:
                name = handler_string
        else:  # Try it as a class
            module = message_handler.__module__
            class_ = message_handler.__name__
            handler_string = module + "." + class_
            if name is None:
                name = str(class_)

        mh, created = MessageHandler.objects.get_or_create(handler=handler_string)
        mh.name = name
        mh.clean()
        mh.save()
        # print "saved", message_handler
    except DatabaseError as dbe:  # Assume this is because DB isn't set up yet
        if retry:
            message_handlers_to_retry.append((message_handler, name))
            # print "retry", message_handler
            print dbe.__class__
        else:
            # print "raise", message_handler
            raise


def register_query_handler(query_handler, name=None, retry=True):
    """
    Attempts to create a QueryHandler model for the
    specified query_handler.

    If retry=True, DatabaseErrors will cause a retry.
    Other Errors will not. A retry consists of retrying
    this method when Django's post_syncdb signal is called.

    Args:
        query_handler (class or string) - The message handler to be registered
        name (str) - The name of the message handler to be registered
        retry (bool) - If registration fails, whether or not to retry later
    """
    try:
        if isinstance(query_handler, basestring):
            handler_string = query_handler
            if name is None:
                name = handler_string
        else:  # Try it as a class
            module = query_handler.__module__
            class_ = query_handler.__name__
            handler_string = module + '.' + class_
            if name is None:
                name = str(class_)

        # TODO: This might not be the most efficient method of registering query handlers
        qh, created = QueryHandler.objects.get_or_create(handler=handler_string)
        qh.name = name
        qh.clean()
        qh.save()
    except DatabaseError as dbe:  # Assume this is because DB isn't set up yet
        if retry:
            query_handlers_to_retry.append((query_handler, name))
        else:
            raise


def retry_handler_registration(sender, **kwargs):
    """
    Goes through each of the handlers to retry
    and retries them w/ retry=False
    """

    while len(query_handlers_to_retry):
        qh = query_handlers_to_retry.pop()
        register_query_handler(qh[0], qh[1], retry=False)

    while len(message_handlers_to_retry):
        mh = message_handlers_to_retry.pop()
        print "retrying", mh[0]
        register_message_handler(mh[0], mh[1], retry=False)

# Leaving the sender blank is probably not right, but
# after a few hours digging in django source code i couldn't
# figure out another way to connect this handler so
# it stays this way for now
post_syncdb.connect(retry_handler_registration)
