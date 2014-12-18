Query Configuration
===================

Within TAXII, Queries can be specified in two scenarios: as part of a Poll Request (used when accessing a TAXII Poll
Service) and as part of a Manage Collection Subscription Request (used when accessing a TAXII Collection Management
Service). This page describes how to configure django-taxii-services to support queries for Poll Services and
Collection Management Services.

Poll Service Query Configuration
--------------------------------

In order for a Poll Service to support queries, a number of database objects must be properly configured:
a Query Handler, a Supported Query, and a Poll Service. This section describes how to configure each of these database
objects so that queries can be made against a particular Poll Service.


Collection Management Service Query Configuration
-------------------------------------------------

TBD