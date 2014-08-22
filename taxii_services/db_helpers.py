# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from .models import *

def clear_all_models():
    clear_model()

def clear_model(model_name):
    model_name.objects.all().delete()
    
CollectionManagementService
ContentBinding
ContentBindingAndSubtype
ContentBindingSubtype
ContentBlock
DataCollection
QueryScope
DiscoveryService
InboxMessage
InboxService
MessageBinding
MessageHandler
PollService
ProtocolBinding
QueryHandler
ResultSet
ResultSetPart
Subscription
SupportedQuery
Validator