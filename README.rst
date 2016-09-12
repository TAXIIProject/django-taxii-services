django-taxii-services
=====================

Add TAXII support to Django projects.

:Source: https://github.com/TAXIIProject/django-taxii-services
:Documentation: http://taxii-services.readthedocs.io
:Information: http://taxiiproject.github.io/
:Download: https://pypi.python.org/pypi/taxii-services

|travis badge| |landscape.io badge| |version badge| |downloads badge|

.. |travis badge| image:: https://api.travis-ci.org/TAXIIProject/django-taxii-services.svg?branch=master
   :target: https://travis-ci.org/TAXIIProject/django-taxii-services
   :alt: Build Status
.. |landscape.io badge| image:: https://landscape.io/github/TAXIIProject/django-taxii-services/master/landscape.svg?style=flat
   :target: https://landscape.io/github/TAXIIProject/django-taxii-services/master
   :alt: Code Health
.. |version badge| image:: https://img.shields.io/pypi/v/taxii-services.svg?maxAge=3600
   :target: https://pypi.python.org/pypi/taxii-services/
.. |downloads badge| image:: https://img.shields.io/pypi/dm/taxii-services.svg?maxAge=3600
   :target: https://pypi.python.org/pypi/taxii-services/

Overview
--------

django-taxii-services is an installable Django app that enables
application developers to rapidly create TAXII Applications that cover
any aspect of TAXII 1.0 and TAXII 1.1. Key aspects of
django-taxii-services include:

-  Reusable - You can install it
-  Extensible - You can extend (almost) any aspect of
   django-taxii-services to perform your custom application logic
-  Complete - Covers 100% of TAXII 1.0 and TAXII 1.1 (this is more of a
   goal, at the moment)
-  Easy - Always a subjective term, but django-taxii-services aims to be
   easy to use.

**Please Note** that this library is under rapid development. If you see
anything you'd like to ask a question on, please open an issue on GitHub or contact the TAXII Team at taxii@mitre.org.

Using django-taxii-services
---------------------------

Create your own Django project, install django-taxii-services, and
modify your settings.py to add ``taxii_services`` (e.g.,):

.. code:: python

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

Some Key Features
-----------------

(This section is kind of a brain dump and should eventually be moved to
readthedocs when it matures)

-  exceptions.StatusMessageException /
   middleware.StatusMessageExceptionMiddleware - These, when used
   together, allow developers to raise a StatusMessageException()
   anywhere and have the server automagically create a StatusMessage in
   response (might be a TAXII 1.0 or 1.1 Status Message depending on the
   request). If you have
   ``taxii_services.middleware.StatusMessageExceptionMiddleware`` in
   your MIDDLEWARAE\_CLASSES, you can just
   ``raise taxii_services.exceptions.StatusMessageException( ... )``
   from anywhere and have django-taxii-services send back a
   StatusMessage.

-  Register your own message handler - use
   taxii\_services.management.register\_message\_handler()

-  Some convenience methods:
-  taxii\_services.register\_admins - Register some/all admins to the
   Django admin interface
-  taxii\_services.register\_message\_handlers - Register some/all
   built-in message handlers

Dependencies
------------

TODO: Document the dependencies

Feedback
--------

Please provide feedback and/or comments on open issues to taxii@mitre.org.

License
-------

For license information, see the LICENSE.txt file.
