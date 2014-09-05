Handlers
========

This page has documentation for two concepts specific to django-taxii-services:
QueryHandlers and MessageHandlers.

MessageHandlers
---------------

In django-taxii-services, MessageHandlers are how a TAXII Service handles a request and
creates a response. Each TAXII Service can have one message handler per message exchange.

1. A Django request is passed to `taxii_services.views.service_router`
2. `service_router` looks at the request's X-TAXII-Content-Type header to identify whether it's a TAXII 1.0 or TAXII 1.1 message
3. If validation is requested, validation is attempted. If validation fails, a StatusMessage is automatically returned
4. Message deserialization is attempted using libtaxii. If deserialization fails, a StatusMessage is automatically returned
5. Based on the path portion of the request URL (e.g., '/path/to_a_service/'), get a TAXII Service from the database. If no service is found, return an HTTP 404.
6. 

Every MessageHandler inherits from taxii_services.base_taxii_handlers.MessageHandler.

**Built-In Message Handlers**

django-taxii-services comes with built in message handlers for every message exchange in TAXII:
* **DiscoveryRequest11Handler** - Handles TAXII 1.1 Discovery Requests (Discovery Service)
* **DiscoveryRequest10Handler** - Handles TAXII 1.0 Discovery Requests (Discovery Service)
* **DiscoveryRequestHandler** - Handles TAXII 1.1 and TAXII 1.0 Discovery Requests. (Discovery Service)
* **InboxMessage11Handler** - Handles TAXII 1.1 Inbox Messages (Inbox Service)
* **InboxMessage10Handler** - Handles TAXII 1.0 Inbox Messages (Inbox Service)
* **InboxMessageHandler** - Handles TAXII 1.1 and TAXII 1.0 Inbox Messages (Inbox Service)
* **PollRequest11Handler** - Handles TAXII 1.1 Poll Requests (Poll Service)
* **PollRequest10Handler** - Handles TAXII 1.0 Poll Requests (Poll Service)
* **PollRequestHandler** - Handles TAXII 1.1 and TAXII 1.0 Poll Requests (Poll Service)
* **PollFulfillmentRequest11Handler** - Handles TAXII 1.1 Poll Fulfillment Requests  (Poll Service) - Poll Fulfillment did not exist in TAXII 1.0, so there is not a Poll Fulfillment handler for TAXII 1.0
* **CollectionInformationRequest11Handler** - Handles TAXII 1.1 Collection Information Requests (Collection Management Service)
* **FeedInformationRequest11Handler** - Handles TAXII 1.0 Feed Information Requests (Collection Management Service)
* **CollectionInformationRequestHandler** - Handles TAXII 1.1 Collection Information and TAXII 1.0 Feed Information Requests (Collection Management Service)
* **SubscriptionRequest11Handler** - Handles TAXII 1.1 Manage Collection Subscription Requests (Collection Management Service)
* **SubscriptionRequest10Handler** - Handles TAXII 1.0 Manage Feed Subscription Requests (Collection Management Service)
* **SubscriptionRequestHandler** - Handles TAXII 1.1 Manage Collection Subscription Requests and TAXII 1.0 Manage Feed Collection Subscription Requests (Collection Management Service)



QueryHandlers
-------------
(TODO: Write this)