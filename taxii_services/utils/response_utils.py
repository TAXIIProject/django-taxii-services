# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

# from django.http import HttpResponse
# from libtaxii.constants import *

# def create_taxii_response(string_message, headers, status_code=200):
    # """
    # string_message - A string that will go in the HTTPResponse. Should be a serialized TAXII Message
    # status_code - The status code to use. Defaults to 200
    # headers - The headers to use in the response. Must be a dict. Can be a
              # dict defined by response_utils or custom dict.
    # """
    
    # resp = HttpResponse()
    # for name, value in headers.iteritems():
        # resp[name] = value
    # resp.content = string_message
    # resp.status_code = status_code
    # return resp

# class HttpResponseTaxii(HttpResponse):
    # """
    # A Django TAXII HTTP Response. Extends the base django.http.HttpResponse 
    # to allow quick and easy specification of TAXII HTTP headers.in
    # """
    # def __init__(self, string_message, taxii_headers, *args, **kwargs):
        # super(HttpResponse, self).__init__(*args, **kwargs)
        # self.content = string_message
        # for k, v in taxii_headers.iteritems():
            # self[k.lower()] = v

# TAXII_11_HTTPS_Headers = {'Content-Type': 'application/xml',
                          # 'X-TAXII-Content-Type': VID_TAXII_XML_11,
                          # 'X-TAXII-Protocol': VID_TAXII_HTTPS_10,
                          # 'X-TAXII-Services': VID_TAXII_SERVICES_11}

# TAXII_11_HTTP_Headers = {'Content-Type': 'application/xml',
                         # 'X-TAXII-Content-Type': VID_TAXII_XML_11,
                         # 'X-TAXII-Protocol': VID_TAXII_HTTP_10,
                         # 'X-TAXII-Services': VID_TAXII_SERVICES_11}

# TAXII_10_HTTPS_Headers = {'Content-Type': 'application/xml',
                          # 'X-TAXII-Content-Type': VID_TAXII_XML_10,
                          # 'X-TAXII-Protocol': VID_TAXII_HTTPS_10,
                          # 'X-TAXII-Services': VID_TAXII_SERVICES_10}

# TAXII_10_HTTP_Headers = {'Content-Type': 'application/xml',
                         # 'X-TAXII-Content-Type': VID_TAXII_XML_10,
                         # 'X-TAXII-Protocol': VID_TAXII_HTTP_10,
                         # 'X-TAXII-Services': VID_TAXII_SERVICES_10}

# def get_headers(taxii_services_version, is_secure):
    # """
    # Convenience method for selecting headers
    # """
    # if taxii_xml_version_id == VID_TAXII_SERVICES_11 and is_secure:
        # return TAXII_11_HTTPS_Headers
    # elif taxii_xml_version_id == VID_TAXII_SERVICES_11 and not is_secure:
        # return TAXII_11_HTTP_Headers
    # elif taxii_xml_version_id == VID_TAXII_SERVICES_10 and is_secure:
        # return TAXII_10_HTTPS_Headers
    # elif taxii_xml_version_id == VID_TAXII_SERVICES_10 and not is_secure:
        # return TAXII_10_HTTP_Headers
    # else:
        # raise ValueError("Unknown combination for taxii_xml_version_id and is_secure!")
    
