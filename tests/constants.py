# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

# Constants related to testing

from libtaxii.constants import *

INBOX_PATH = '/inbox/'
DISCOVERY_PATH = '/discovery/'
POLL_PATH = '/poll/'
COLLECTION_PATH = '/collection-management/'

# Requests that come through via the test harness
# don't have their headers normalized by Django.
# This means I can't reuse application code from elsewhere.

# TOOD: Django will set the content type header automatically.

TAXII_11_HTTPS_Headers = {'CONTENT_TYPE': 'application/xml',
                          'HTTP_X_TAXII_CONTENT_TYPE': VID_TAXII_XML_11,
                          'HTTP_X_TAXII_PROTOCOL': VID_TAXII_HTTPS_10,
                          'HTTP_X_TAXII_SERVICES': VID_TAXII_SERVICES_11,
                          'HTTP_ACCEPT': 'application/xml',
                          'HTTP_X_TAXII_ACCEPT': VID_TAXII_XML_11}

TAXII_11_HTTP_Headers = {'CONTENT_TYPE': 'application/xml',
                         'HTTP_X_TAXII_CONTENT_TYPE': VID_TAXII_XML_11,
                         'HTTP_X_TAXII_PROTOCOL': VID_TAXII_HTTP_10,
                         'HTTP_X_TAXII_SERVICES': VID_TAXII_SERVICES_11,
                         'HTTP_ACCEPT': 'application/xml',
                         'HTTP_X_TAXII_ACCEPT': VID_TAXII_XML_11}

TAXII_10_HTTPS_Headers = {'CONTENT_TYPE': 'application/xml',
                          'HTTP_X_TAXII_CONTENT_TYPE': VID_TAXII_XML_10,
                          'HTTP_X_TAXII_PROTOCOL': VID_TAXII_HTTPS_10,
                          'HTTP_X_TAXII_SERVICES': VID_TAXII_SERVICES_10,
                          'HTTP_ACCEPT': 'application/xml',
                          'HTTP_X_TAXII_ACCEPT': VID_TAXII_XML_10}

TAXII_10_HTTP_Headers = {'CONTENT_TYPE': 'application/xml',
                         'HTTP_X_TAXII_CONTENT_TYPE': VID_TAXII_XML_10,
                         'HTTP_X_TAXII_PROTOCOL': VID_TAXII_HTTP_10,
                         'HTTP_X_TAXII_SERVICES': VID_TAXII_SERVICES_10,
                         'HTTP_ACCEPT': 'application/xml',
                         'HTTP_X_TAXII_ACCEPT': VID_TAXII_XML_10}

stix_watchlist_111 = '''
<stix:STIX_Package
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:stix="http://stix.mitre.org/stix-1"
    xmlns:indicator="http://stix.mitre.org/Indicator-2"
    xmlns:cybox="http://cybox.mitre.org/cybox-2"
    xmlns:DomainNameObj="http://cybox.mitre.org/objects#DomainNameObject-1"
    xmlns:cyboxVocabs="http://cybox.mitre.org/default_vocabularies-2"
    xmlns:stixVocabs="http://stix.mitre.org/default_vocabularies-1"
    xmlns:example="http://example.com/"
    xsi:schemaLocation=
    "http://stix.mitre.org/stix-1 ../stix_core.xsd
    http://stix.mitre.org/Indicator-2 ../indicator.xsd
    http://cybox.mitre.org/default_vocabularies-2 ../cybox/cybox_default_vocabularies.xsd
    http://stix.mitre.org/default_vocabularies-1 ../stix_default_vocabularies.xsd
    http://cybox.mitre.org/objects#DomainNameObject-1 ../cybox/objects/Domain_Name_Object.xsd"
    id="example:STIXPackage-f61cd874-494d-4194-a3e6-6b487dbb6d6e"
    timestamp="2014-05-08T09:00:00.000000Z"
    version="1.1.1"
    >
    <stix:STIX_Header>
        <stix:Title>Example watchlist that contains domain information.</stix:Title>
        <stix:Package_Intent xsi:type="stixVocabs:PackageIntentVocab-1.0">Indicators - Watchlist</stix:Package_Intent>
    </stix:STIX_Header>
    <stix:Indicators>
        <stix:Indicator xsi:type="indicator:IndicatorType" id="example:Indicator-2e20c5b2-56fa-46cd-9662-8f199c69d2c9" timestamp="2014-05-08T09:00:00.000000Z">
            <indicator:Type xsi:type="stixVocabs:IndicatorTypeVocab-1.1">Domain Watchlist</indicator:Type>
            <indicator:Description>Sample domain Indicator for this watchlist</indicator:Description>
            <indicator:Observable id="example:Observable-87c9a5bb-d005-4b3e-8081-99f720fad62b">
                <cybox:Object id="example:Object-12c760ba-cd2c-4f5d-a37d-18212eac7928">
                    <cybox:Properties xsi:type="DomainNameObj:DomainNameObjectType" type="FQDN">
                        <DomainNameObj:Value condition="Equals" apply_condition="ANY">malicious1.example.com##comma##malicious2.example.com##comma##malicious3.example.com</DomainNameObj:Value>
                    </cybox:Properties>
                </cybox:Object>
            </indicator:Observable>
        </stix:Indicator>
    </stix:Indicators>
</stix:STIX_Package>'''

stix_watchlist_10 = '''
<stix:STIX_Package
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:stix="http://stix.mitre.org/stix-1"
    xmlns:indicator="http://stix.mitre.org/Indicator-2"
    xmlns:cybox="http://cybox.mitre.org/cybox-2"
    xmlns:URIObject="http://cybox.mitre.org/objects#URIObject-2"
    xmlns:cyboxVocabs="http://cybox.mitre.org/default_vocabularies-2"
    xmlns:stixVocabs="http://stix.mitre.org/default_vocabularies-1"
    xmlns:example="http://example.com/"
    xsi:schemaLocation=
    "http://stix.mitre.org/stix-1 http://stix.mitre.org/XMLSchema/core/1.0/stix_core.xsd
    http://stix.mitre.org/Indicator-2 http://stix.mitre.org/XMLSchema/indicator/2.0/indicator.xsd
    http://cybox.mitre.org/default_vocabularies-2 http://cybox.mitre.org/XMLSchema/default_vocabularies/2.0.0/cybox_default_vocabularies.xsd
    http://stix.mitre.org/default_vocabularies-1 http://stix.mitre.org/XMLSchema/default_vocabularies/1.0.0/stix_default_vocabularies.xsd
    http://cybox.mitre.org/objects#URIObject-2 http://cybox.mitre.org/XMLSchema/objects/URI/2.0/URI_Object.xsd"
    id="example:STIXPackage-f61cd874-494d-4194-a3e6-6b487dbb6d6e"
    version="1.0">
    <stix:STIX_Header>
        <stix:Title>Example watchlist that contains domain information.</stix:Title>
        <stix:Package_Intent xsi:type="stixVocabs:PackageIntentVocab-1.0">Indicators - Watchlist</stix:Package_Intent>
    </stix:STIX_Header>
    <stix:Indicators>
        <stix:Indicator xsi:type="indicator:IndicatorType" id="example:Indicator-2e20c5b2-56fa-46cd-9662-8f199c69d2c9">
            <indicator:Type xsi:type="stixVocabs:IndicatorTypeVocab-1.0">Domain Watchlist</indicator:Type>
            <indicator:Description>Sample domain Indicator for this watchlist</indicator:Description>
            <indicator:Observable id="example:Observable-87c9a5bb-d005-4b3e-8081-99f720fad62b">
                <cybox:Object id="example:Object-12c760ba-cd2c-4f5d-a37d-18212eac7928">
                    <cybox:Properties xsi:type="URIObject:URIObjectType">
                        <URIObject:Value condition="Equals" apply_condition="ANY">malicious1.example.com,malicious2.example.com,malicious3.example.com,</URIObject:Value>
                    </cybox:Properties>
                </cybox:Object>
            </indicator:Observable>
        </stix:Indicator>
    </stix:Indicators>
</stix:STIX_Package>'''
