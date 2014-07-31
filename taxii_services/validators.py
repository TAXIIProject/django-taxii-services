# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from django.core.exceptions import ValidationError
from importlib import import_module

def validate_importable(handler_string):
    """
    Validates whether or not a particular handler_string 
    (e.g., taxii_services.handlers.discovery_handler) is
    importable. Raises a ValidationError if not.
    """
   
    module_name, method_name = handler_string.rsplit('.', 1)
    try:
        module = import_module(module_name)
    except:
        raise ValidationError('Module could not be imported: %s' % module_name)
    
    try:
        handler = getattr(module, method_name)
    except:
        raise ValidationError('Method (%s) was not found in module (%s).' % (method_name, module_name))
    
    if not callable(handler):
        raise ValidationError('Method is not callable: %s' % handler_string)
    
    # TODO: Are there other checks i can make?
