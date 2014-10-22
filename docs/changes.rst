Release Notes
=============

0.2
---
The structure of Message Handlers and Query Handlers were significantly reorganized:

* Message Handlers used to be in base_taxii_handlers.py and taxii_handlers.py. They are now in the message_handlers module, which consists of the following files:
 * base_handlers.py - Contains the BaseMessageHandler class. All Message Handler classes inherit from this class
 * collection_information_request_handlers.py - Contains all Collection/Feed Information Request Handlers (TAXII 1.0 and 1.1)
 * discovery_request_handlers.py - Contains all Discovery Request Handlers (TAXII 1.0 and 1.1)
 * inbox_message_handlers.py - Contains all Inbox Message Handlers (TAXII 1.0 and 1.1)
 * poll_fulfillment_request_handlers.py - Contains the Poll Fullfillment Request Handler (TAXII 1.1)
 * poll_request_handlers.py - Contains all Poll Request Handlers (TAXII 1.0 and 1.1)
 * subscription_request_handlers.py - Contains all Subscription Handlers (TAXII 1.0 and 1.1)

Note that each Message Handler, or BaseMessageHandler, can be extended and customized for custom TAXII Message Handling

* Query Handlers used to be in base_taxii_handlers.py and has been moved to the query_handlers module, which consists of the following files:
 * base_handlers.py - Contains the BaseQueryHandler and BaseXmlQueryHandler class. The BaseXmlQueryHandler class is a general TAXII Query to XPath mapping class
 * stix_xml_111_handler.py - Contains an incomplete STIX 1.1.1 Query Handler that is a subclass of BaseXmlQueryHandler.

Closed issues:

* #16 - https://github.com/TAXIIProject/django-taxii-services/issues/16
* #17 - https://github.com/TAXIIProject/django-taxii-services/issues/17
* #24 - https://github.com/TAXIIProject/django-taxii-services/issues/24

Other changes

* Quite a few PEP8 changes
* Added testing and test content (see: test/)


0.1.2
-----

The dependencies are now listed correctly, making it easier for
people to use django-taxii-services

0.1.1
-----

There was a critical bug in 0.1 that was somehow missed. (#13). 
This bug fix release is simply to fix that bug.

0.1
---

0.1 is the first version of django-taxii-services. Please note that since the
version number is below 1.0, the API is unstable and may change in a future minor 
release.

The intent of this release is to gauge interest for django-taxii-services
and determine whether it makes sense to keep working on future versions.

The major items accomplished in this release are: 
 
* Established core concepts, paradigms, and structures of the library
* Set the technical direction of MessageHandler extension points
* Baseline API documentation: http://taxii-services.readthedocs.org/en/latest/index.html
* YETI 2.0a (An experimental release of YETI) now uses django-taxii-services.

There are some notable/major TBDs in this release of django-taxii-services:

* Non-API documentation (We tried to get API documentation at least usable)
* Logging (https://github.com/TAXIIProject/django-taxii-services/issues/5)
* Testing (https://github.com/TAXIIProject/django-taxii-services/issues/3)
* QueryHandlers need to be fleshed out more (https://github.com/TAXIIProject/django-taxii-services/issues/6)
* Many portions of the library are experimental and untested