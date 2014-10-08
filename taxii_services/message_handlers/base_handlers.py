# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from ..exceptions import StatusMessageException

from libtaxii.constants import *
from django.conf import settings


class BaseMessageHandler(object):
    """
    MessageHandler is the base class for TAXII Message
    Handlers.

    Child classes MUST specify a value for MessageHandler.supported_request_messages,
    and MUST implement the handle_message function.

    e.g.,::

        import libtaxii.messages_11 as tm11

        MessageHandlerChild(MessageHandler):
            supported_request_messages = tm11.DiscoveryRequest

            @classmethod
            def handle_message(cls, service, taxii_message, django_request):
                dr = tm11.DiscoveryResponse( ... )
                # Code to handle the request against the service would go here
                return dr

        Optionally,register the MessageHandler child:
        import taxii_services.management as m
        m.register_message_handler(MessageHandlerChild, name='MessageHandlerChild')
    """

    #: Identify the list of supported request messages
    #: This MUST be a list (well, iterable) defined by the extending class
    #: e.g., [tm11.InboxMessage]
    supported_request_messages = None

    @classmethod
    def get_supported_request_messages(cls):
        """
        Returns:
            The supported_request_messages property or raises a ValueError
            if it isn't set.
        """
        if not cls.supported_request_messages:
            raise ValueError('The variable \'supported_request_messages\' has not been defined by the subclass!')
        return cls.supported_request_messages

    @classmethod
    def validate_headers(cls, django_request, in_response_to='0'):
        """
        Validates the headers of a django request
        based on the properties of this MessageHandler.

        Specifically, the supported_request_messages property is used to
        infer which version(s) of TAXII this message handler supports and
        from there infer which headers are valid/invalid.

        Arguments:
            django_request - The Django request to validate
            in_response_to - If a StatusMessageException is raised as a result \
                of header validation (e.g., the headers are invalid), \
                in_response_to will be used as the in_response_to \
                field of the Status Message.

        Returns:
            None if all headers are valid. Raises a StatusMessageException otherwise.
        """

        # First, make sure required headers exist
        svcs = django_request.META.get('HTTP_X_TAXII_SERVICES', None)
        if not svcs:
            msg = "The X-TAXII-Services header was not specified"
            if settings.DEBUG:
                msg += "\r\nHeaders: %s " % str(django_request.META)
            raise StatusMessageException(in_response_to,
                                         ST_FAILURE,
                                         msg)

        ct = django_request.META.get('CONTENT_TYPE', None)
        if not ct:
            raise StatusMessageException(in_response_to,
                                         ST_FAILURE,
                                         "Content-Type header was not specified")

        xtct = django_request.META.get('HTTP_X_TAXII_CONTENT_TYPE', None)
        if not xtct:
            raise StatusMessageException(in_response_to,
                                         ST_FAILURE,
                                         "The X-TAXII-Content-Type header was not specified")

        xtp = django_request.META.get('HTTP_X_TAXII_PROTOCOL', None)
        if not xtp:
            raise StatusMessageException(in_response_to,
                                         ST_FAILURE,
                                         "The X-TAXII-Protocol header was not specified")

        # These headers are optional
        accept = django_request.META.get('HTTP_ACCEPT', None)
        xta = django_request.META.get('HTTP_X_TAXII_ACCEPT', None)
        # for k, v in django_request.META.iteritems():
        # print '%s: %s' % (k, v)

        # Identify which TAXII versions the message handler supports
        supports_taxii_11 = False
        supports_taxii_10 = False
        for message in cls.get_supported_request_messages():
            if message.__module__ == 'libtaxii.messages_11':
                supports_taxii_11 = True
            elif message.__module__ == 'libtaxii.messages_10':
                supports_taxii_10 = True
            else:
                raise ValueError(("The variable \'supported_request_messages\' "
                                 "contained a non-libtaxii message module: %s") %
                                 message.__module__)

        # Next, determine whether the MessageHandler supports the headers
        # Validate the X-TAXII-Services header
        if svcs not in (VID_TAXII_SERVICES_11, VID_TAXII_SERVICES_10):
            raise StatusMessageException(in_response_to,
                                         ST_FAILURE,
                                         "The value of X-TAXII-Services was not recognized.")

        if ((svcs == VID_TAXII_SERVICES_11 and not supports_taxii_11) or
            (svcs == VID_TAXII_SERVICES_10 and not supports_taxii_10)):
            raise StatusMessageException(in_response_to,
                                         ST_FAILURE,
                                         ("The specified value of X-TAXII-Services (%s) "
                                          "is not supported by this TAXII Service.") % svcs)

        # Validate the Content-Type header
        if ct.lower() != 'application/xml':
            raise StatusMessageException(in_response_to,
                                         ST_FAILURE,
                                         "The specified value of Content-Type is not supported.")

        # Validate the X-TAXII-Content-Type header
        if xtct not in (VID_TAXII_XML_11, VID_TAXII_XML_10):
            raise StatusMessageException(in_response_to,
                                         ST_FAILURE,
                                         "The value of X-TAXII-Content-Type was not recognized.")

        if ((xtct == VID_TAXII_XML_11 and not supports_taxii_11) or
            (xtct == VID_TAXII_XML_10 and not supports_taxii_10)):
            raise StatusMessageException(in_response_to,
                                         ST_FAILURE,
                                         "The specified value of X-TAXII-Content-Type is not supported")

        # Validate the X-TAXII-Protocol header
        # TODO: Look into the service properties instead of assuming both are supported
        if xtp not in (VID_TAXII_HTTP_10, VID_TAXII_HTTPS_10):
            raise StatusMessageException(in_response_to,
                                         ST_FAILURE,
                                         "The specified value of X-TAXII-Protocol is not supported")

        # Validate the accept header
        if accept and accept.lower() != 'application/xml':
            raise StatusMessageException(in_response_to,
                                         ST_FAILURE,
                                         "The specified value of Accept is not supported")

        # Validate the X-TAXII-Accept header
        # TODO: Accept more "complex" accept headers (e.g., ones that specify more
        # than one value)
        if xta not in (VID_TAXII_XML_11, VID_TAXII_XML_10, None):
            raise StatusMessageException(in_response_to,
                                         ST_FAILURE,
                                         "The specified value of X-TAXII-Accept is not recognized")

        if not xta:  # X-TAXII-Accept not specified, we can pick whatever we want
            xta = VID_TAXII_XML_11

        if ((xta == VID_TAXII_XML_11 and not supports_taxii_11) or
            (xta == VID_TAXII_XML_10 and not supports_taxii_10)):
            raise StatusMessageException(in_response_to,
                                         ST_FAILURE,
                                         "The specified value of X-TAXII-Accept is not supported")

        # Headers are valid
        return

    @classmethod
    def validate_message_is_supported(cls, taxii_message):
        """
        Checks whether the TAXII Message is supported by this Message Handler.

        Arguments:
            taxii_message - A libtaxii.messages_11 or libtaxii.messages_10 taxii message

        Returns:
            None if the message is supported, raises a StatusMessageException otherwise.
        """
        if taxii_message.__class__ not in cls.get_supported_request_messages():
            raise StatusMessageException(taxii_message.message_id,
                                         ST_FAILURE,
                                         "TAXII Message not supported by Message Handler.")
        return

    @classmethod
    def handle_message(cls, service, taxii_message, django_request):
        """
        This method is implemented by child Message Handlers to handle
        TAXII Service invocations.

        Arguments:
            service - A TAXII Service model object representing the service being invoked
            taxii_message - A libtaxii TAXII message representing the request message
            django_request - The django request associated with the taxii_message

        Returns:
            A libtaxii TAXII Message containing the response. May raise a StatusMessageException.
        """
        raise NotImplementedError()
