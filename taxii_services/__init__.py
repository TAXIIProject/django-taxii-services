# Copyright (C) 2014 - The MITRE Corporation
# For license information, see the LICENSE.txt file

__version__ = "0.1"

def register_admins(admin_list=None):
    import admin
    admin.register_admins(admin_list)

def register_message_handlers(handler_list=None):
    """
    Args:
        handler_list () - List of built-in message handlers to register. None inports all handlers
    """
    import taxii_handlers
    taxii_handlers.register_message_handlers(handler_list)
    