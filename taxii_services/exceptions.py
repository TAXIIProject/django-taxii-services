# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

class StatusMessageException(Exception):
    def __init__(self, status_message, **kwargs):
        super(StatusMessageException, self).__init__(**kwargs)
        self.status_message = status_message
