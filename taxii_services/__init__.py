# Copyright (C) 2014 - The MITRE Corporation
# For license information, see the LICENSE.txt file

__version__ = "0.1"

def register_admins(admin_list=None):
    import admin
    admin.register_admins(admin_list)

# TODO: Calling this function borks loaddata with the following error:
# IntegrityError: Problem installing fixture 'yeti\fixtures\initial_data.json': Could not load taxii_services._Handler(pk=1): column
 # handler is not unique
def register_message_handlers(handler_list=None):
    """
    Args:
        handler_list () - List of built-in message handlers to register. None inports all handlers
    """
    import taxii_handlers
    taxii_handlers.register_message_handlers(handler_list)
    