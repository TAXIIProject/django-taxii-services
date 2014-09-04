django-taxii-services
---------------------

## Overview
django-taxii-services is an installable Django app that enables application developers to 
rapidly create TAXII Applications that cover any aspect of TAXII 1.0 and TAXII 1.1. Key aspects
of django-taxii-services include:

* Reusable - You can install it
* Extensible - You can extend (almost) any aspect of django-taxii-services to perform your custom application logic
* Complete - Covers 100% of TAXII 1.0 and TAXII 1.1 (this is more of a goal, at the moment)
* Easy - Always a subjective term, but django-taxii-services aims to be easy to use.

**Please Note** that this library is under rapid development. If you see anything you'd like to ask a 
question on, please open an issue on GitHub or contact the public discussion list (taxii-discussion-list@lists.mitre.org)
 or contact the TAXII Team privately at taxii@mitre.org 

## Using django-taxii-services
Create your own Django project, install django-taxii-services, and modify your settings.py to add `taxii_services` (e.g.,):
```python
INSTALLED_APPS = (
    ...
    'taxii_services',
)

MIDDLEWARE_CLASSES = (
    ...
    'taxii_services.middleware.StatusMessageExceptionMiddleware'
)

# Add a logger if you'd like
LOGGING = {
    ...
    'loggers': {
        ...
        'taxii_services': {
            'handlers': ['normal','stdout'],
            'level': LOG_LEVEL,
            'propagate': True,
        },
    }
}
```

## Some Key Features
(This section is kind of a brain dump and should eventually be moved to readthedocs when it matures)

* exceptions.StatusMessageException / middleware.StatusMessageExceptionMiddleware - These, when used together,
allow developers to raise a StatusMessageException() anywhere and have the server automagically create a 
StatusMessage in response (might be a TAXII 1.0 or 1.1 Status Message depending on the request). 
If you have `taxii_services.middleware.StatusMessageExceptionMiddleware` in your MIDDLEWARAE_CLASSES, you can
just `raise taxii_services.exceptions.StatusMessageException( ... )` from anywhere and have django-taxii-services
send back a StatusMessage.

* Register your own message handler - use taxii_services.management.register_message_handler()

* Some convenience methods:
 * taxii_services.register_admins - Register some/all admins to the Django admin interface
 * taxii_services.register_message_handlers - Register some/all built-in message handlers

## Dependencies
TODO: Document the dependencies


## Feedback 
You are encouraged to provide feedback by commenting on open issues or signing up for the TAXII
discussion list and posting your questions (http://taxii.mitre.org/community/registration.html).

## License
For license information, see the LICENSE.txt file.
