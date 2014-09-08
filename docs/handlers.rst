Handlers
========

This page has documentation for two concepts specific to django-taxii-services:
QueryHandlers and MessageHandlers.

MessageHandlers
---------------

In django-taxii-services, MessageHandlers are how a TAXII Service handles a request and
creates a response. Each TAXII Service can have one message handler per message exchange.

The base_taxii_handlers.MessageHandler class is the base class for all TAXII Message Handlers 
and has a single extension point – the ‘handle_message’ function. Implementers who wish to 
have the most power over their MessageHandler should extend MessageHandler and implement the 
‘handle_message’ function. Implementers can also re-use django-taxii-service’s built-in 
TAXII Message Handlers for less power, but more work already done for them.

Built-in TAXII Message Handlers have two goals: first, to provide correct functionality 
for the TAXII Message Exchange they support; second, to provide an extensible/reusable 
class where implementers can make (hopefully) simple modification(s) to a built-in MessageHandler 
to achieve functionality specific to their needs. Note that all built-in TAXII Message Handlers 
extend the base_taxii_handlers.MessageHandler class. To meet the second goal of extensibility/reusability, 
some built-in TAXII Message Handlers have extension points in addition to the ‘handle_message’ 
function. These extension points (functions) are called by the ‘handle_message’ function of the 
built-in TAXII Message Handler as part of the workflow for handling that message. One example 
of this is the ‘save_content_block’ method of the InboxMessage11Handler, which allows 
implementers to override just the InboxMessage11Handler’s default logic for saving content 
without needing to re-implement the rest of the handler’s processing logic.

The MessageHandlers are documented in taxii_services.MessageHandlers section of the API.


QueryHandlers
-------------
(TODO: Write this)