# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

import libtaxii as t
import libtaxii.messages_11 as tm11
import libtaxii.messages_10 as tm10

class StatusMessageException(Exception):
    """
    StatusMessageException is an exception that can be raised and can be caught by
    TaxiiStatusMessageMiddleware. This class holds all the information necessary to
    create either a TAXII 1.1 or TAXII 1.0 Status Message.
    """
    def __init__(self, in_response_to, status_type, message=None, status_detail=None, extended_headers=None, **kwargs):
        """
        Arguments:
            in_response_to (string) - The message_id of the request
            status_type (string) - The Status Type for the Status Message
            message (string) - A string message for the Status Message
            status_details (dict) - A dictionary containing the status details for the Status Message
            extended_headers (dict) - The extended headers for the Status Message
        """
        super(StatusMessageException, self).__init__(**kwargs)
        self.in_response_to = in_response_to
        self.status_type = status_type
        self.message = message
        self.status_detail = status_detail or {}
        self.extended_headers = extended_headers or {}
    
    def get_status_message(self, format=t.VID_TAXII_XML_11):
        """
        Creates a TAXII Status Message in TAXII 1.1 or TAXII 1.0 
        depending on the value of the format argument
        
        Arguments:
            format (string) - The format of the Status Message
        """
        if format == t.VID_TAXII_XML_11:
            return self.get_status_message_11()
        elif format == t.VID_TAXII_XML_10:
            return self.get_status_message_10()
        else:
            raise ValueError("Unknown value for format: %s" % format)
    
    def get_status_message_11(self):
        """
        Creates a TAXII 1.1 Status Message based on the 
        properties of this object
        """
        sm = tm11.StatusMessage(message_id = tm11.generate_message_id(), 
                                in_response_to = self.in_response_to,
                                extended_headers = self.extended_headers,
                                status_type = self.status_type,
                                status_detail = self.status_detail,
                                message = self.message)
        return sm
    
    def get_status_message_10(self):
        """
        Creates a TAXII 1.0 Status Message based on the 
        properties of this object
        """
        sm = tm10.StatusMessage(message_id = tm10.generate_message_id(),
                                in_response_to = self.in_response_to(),
                                extended_headers = self.extended_headers(),
                                status_type = self.status_type,
                                status_detail = str(self.status_detail),
                                message = self.message)
        return sm
