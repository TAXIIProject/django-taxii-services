# Copyright (C) 2014 - The MITRE Corporation
# For license information, see the LICENSE.txt file

__version__ = "0.1.2"

import django
django.setup()

from taxii_handlers import *

def register_admins(admin_list=None):
    """
    Registers all admins or the subset specified by admin_list.

    Arguments:
        admin_list (list of taxii_services.admin objects to register) - **optional**
    """
    import admin
    admin.register_admins(admin_list)

# TODO: Calling this function borks loaddata with the following error:
# IntegrityError: Problem installing fixture 'yeti\fixtures\initial_data.json': Could not load taxii_services._Handler(pk=1): column
 # handler is not unique
def register_message_handlers(handler_list=None):
    """
    Args:
        handler_list (list) - **optional** List of built-in message handlers to register. Defaults
                              to "all handlers"
    """
    import taxii_handlers
    taxii_handlers.register_message_handlers(handler_list)
    