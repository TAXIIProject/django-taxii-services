# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from exceptions import StatusMessageException
from libtaxii.constants import *
import libtaxii.taxii_default_query as tdq
import libtaxii as t

class MessageHandler(object):
    """
    Blah blah blah
    Extend this for message exchange support
    """
    
    #: Identify the list of supported request messages
    #: This MUST be a list (well, iterable) defined by the extending class
    #: e.g., [tm11.InboxMessage]
    supported_request_messages = None
    
    @classmethod
    def get_supported_request_messages(cls):
        if not cls.supported_request_messages:
            raise ValueError('The variable \'supported_request_messages\' has not been defined by the subclass!')
        return cls.supported_request_messages
    
    @classmethod
    def validate_headers(cls, django_request, in_response_to='0'):
        """
        Validates the headers of a django request
        against the properties of this MessageHandler
        """
        
        # First, make sure required headers exist
        svcs = django_request.META.get('HTTP_X_TAXII_SERVICES', None)
        if not svcs:
            raise StatusMessageException(in_response_to, 
                                         ST_FAILURE, 
                                         "The X-TAXII-Services header was not specified")
        
        ct = django_request.META.get('CONTENT_TYPE', None)
        if not ct:
            raise StatusMessageException(in_response_to, 
                                         ST_FAILURE, 
                                         "Content-Type header was not specified")
        
        xtct = django_request.META.get('HTTP_X_TAXII_CONTENT_TYPE', None)
        if not xtct:
            raise StatusMessageException(in_response_to, 
                                         ST_FAILURE, 
                                         "The X-TAXII-Content-Type header was not specified")
        
        xtp = django_request.META.get('HTTP_X_TAXII_PROTOCOL', None)
        if not xtp:
            raise StatusMessageException(in_response_to, 
                                         ST_FAILURE, 
                                         "The X-TAXII-Protocol header was not specified")
        
        # These headers are optional
        accept = django_request.META.get('HTTP_ACCEPT', None)
        xta = django_request.META.get('HTTP_X_TAXII_ACCEPT', None)
        
        #Identify which TAXII versions the message handler supports
        supports_taxii_11 = False
        supports_taxii_10 = False
        for message in cls.get_supported_request_messages():
            if message.__module__ == 'libtaxii.messages_11':
                supports_taxii_11 = True
            elif message.__module__ == 'libtaxii.messages_10':
                supports_taxii_10 = True
            else:
                raise ValueError("The variable \'supported_request_messages\' \
                                  contained a non-libtaxii message module: %s" % \
                                  message.__module__)
        
        # Next, determine whether the MessageHandler supports the headers
        # Validate the X-TAXII-Services header
        if svcs not in (t.VID_TAXII_SERVICES_11, t.VID_TAXII_SERVICES_10):
            raise StatusMessageException(in_response_to, 
                                         'FAILURE', 
                                         "The value of X-TAXII-Services was not recognized.")
        
        if (  (svcs == t.VID_TAXII_SERVICES_11 and not supports_taxii_11) or 
              (svcs == t.VID_TAXII_SERVICES_10 and not supports_taxii_10)  ):
            raise StatusMessageException(in_response_to, 
                                         'FAILURE', 
                                         "The specified value of X-TAXII-Services (%s) \
                                         is not supported by this TAXII Service." % svcs)
        
        # Validate the Content-Type header
        if ct.lower() != 'application/xml':
            raise StatusMessageException(in_response_to, 
                                         'FAILURE', 
                                         "The specified value of Content-Type is not supported.")
        
        # Validate the X-TAXII-Content-Type header
        if xtct not in (t.VID_TAXII_XML_11, t.VID_TAXII_XML_10):
            raise StatusMessageException(in_response_to, 
                                         'FAILURE', 
                                         "The value of X-TAXII-Content-Type was not recognized.")
        
        if (  (xtct == t.VID_TAXII_XML_11 and not supports_taxii_11) or
              (xtct == t.VID_TAXII_XML_10 and not supports_taxii_10)  ):
            raise StatusMessageException(in_response_to,
                                         'FAILURE',
                                         "The specified value of X-TAXII-Content-Type is not supported")
        
        # Validate the X-TAXII-Protocol header
        # TODO: Look into the service properties instead of assuming both are supported
        if xtp not in (t.VID_TAXII_HTTP_10, t.VID_TAXII_HTTPS_10):
            raise StatusMessageException(in_response_to,
                                         'FAILURE',
                                         "The specified value of X-TAXII-Protocol is not supported")
        
        #Validate the accept header
        if accept and accept.lower() != 'application/xml':
            raise StatusMessageException(in_response_to,
                                         'FAILURE',
                                         "The specified value of Accept is not supported")
        
        #Validate the X-TAXII-Accept header
        # TODO: Accept more "exotic" accept headers (e.g., ones that specify more
        #       than one value)
        if xta not in (t.VID_TAXII_XML_11, t.VID_TAXII_XML_10):
            raise StatusMessageException(in_response_to,
                                         'FAILURE',
                                         "The specified value of X-TAXII-Accept is not recognized")
        
        if (  (xta == t.VID_TAXII_XML_11 and not supports_taxii_11) or 
              (xta == t.VID_TAXII_XML_10 and not supports_taxii_10)  ):
            raise StatusMessageException(in_response_to,
                                         'FAILURE',
                                          "The specified value of X-TAXII-Accept is not supported")
        
        #Headers are valid
        return
    
    @classmethod
    def validate_message_is_supported(cls, taxii_message):
        if taxii_message.__class__ not in cls.get_supported_request_messages():
            raise StatusMessageException(taxii_message.message_id,
                                         ST_FAILURE,
                                         "TAXII Message not supported by Message Handler.")
        return
    
    @classmethod
    def handle_message(cls, service, taxii_message, django_request):
        """
        Takes a service model, TAXII Message, and django request
        
        MUST return a tm11 TAXII Message
        """
        raise NotImplementedError()

class DefaultQueryHandler(object):
    """
    Blah blah blah.
    Extend this for query support
    """
    
    supported_targeting_expression = None
    supported_capability_modules = None
    #supported_scope_message = None
    
    @classmethod
    def get_supported_capability_modules(cls):
        """
        Returns a list of strings indicating the Capability Modules this 
        class supports. Pulls from the 
        supported_capability_modules class variable set by the 
        child class
        """
        if not cls.supported_capability_modules:
            raise ValueError('The variable \'supported_capability_modules\' has not been defined by the subclass!')
        return cls.supported_capability_modules
    
    @classmethod
    def get_supported_targeting_expression(cls):
        """
        Returns a string indicating the targeting expression this 
        class supports. Pulls from the 
        supported_targeting_expression class variable set by the 
        child class
        """
        if not cls.supported_targeting_expression:
            raise ValueError('The variable \'supported_targeting_expression\' has not been defined by the subclass!')
        return cls.supported_targeting_expression
    
    @classmethod
    def get_supported_scope_message(cls):
        pass#TODO: is this worthwhile?
    
    @staticmethod
    def is_scope_supported(scope):
        """
        Given a DefaultQueryScope object, return True
        if that scope is supported or False if it is not.
        """
        raise NotImplementedError()
    
    @classmethod
    def execute_query(cls, content_block_list, query):
        """
        Given a query and a list of tm11.ContentBlock objects,
        return a list of tm11.ContentBlock objects that
        match the query
        """        
        raise NotImplementedError()

class BaseXmlQueryHandler(DefaultQueryHandler):
    """
    Extends the DefaultQueryHandler for general XML 
    processing. This class still needs to be extended
    to support specific XML formats (e.g., specific
    versions of STIX).
    
    There is a generate_xml_query_extension.py script 
    to help with extending this class
    
    Note that correctly specifying the mapping_dict is
    a critical aspect of extending this class. The mapping_dict
    should adhere to the following format:
    
    { 'root_context':
        {'children':
            '<xml_root_element_name>': 
            {
               'has_text': True/False,
               'namespace': '<namespace>',
               'prefix': 'prefix', # aka namespace alias
               'children':
               {
                  '@<attribute_child>': { # can have 0-n of these
                    'has_text': True, # attributes can always have text
                    'namespace': <namespace> or None,
                    'prefix': <prefix> or None,
                    'children': {} #Attributes can't have children
                  }, 
                  '<element_child>': { # Can have 0-n of these
                    'has_text': True or False, #Depending on whether the element value can hold text
                    'namespace': <namespace> or None,
                    'prefix': <prefix> or None,
                    'children': { ... } # Any number of @<attribute_child> or <element_child> instances
                  },
               }
            }
        }
    }
    """
    
    supported_capability_modules = [tdq.CM_CORE]
    version = "1"
    
    mapping_dict = None
        
    @classmethod
    def is_scope_supported(cls, scope):
        try:
            cls.get_xpath_parts(scope)
        except ValueError as e:
            return False, e
        
        return True, None
    
    @classmethod
    def evaluate_criteria(cls, content_etree, criteria):
        """
        Evaluates the criteria in a query. Note that criteria can have
        child criteria (aka recursion) and child criterion.
        """
        for criteria in criteria.criteria:
            value = cls.evaluate_criteria(content_etree, criteria)
            if value and criteria.operator == tdq.OP_OR:
                return True
            elif not value and criteria.operator == tdq.OP_AND:
                return False
            else:#Don't know anything for sure yet
                pass
        
        for criterion in criteria.criterion:
            value = cls.evaluate_criterion(content_etree, criterion)
            #TODO: Is there a way to keep this DRY?
            if value and criteria.operator == tdq.OP_OR:
                return True
            elif not value and criteria.operator == tdq.OP_AND:
                return False
            else:#Don't know anything for sure yet
                pass
        
        return operator == tdq.OP_AND
    
    @classmethod
    def evaluate_criterion(cls, content_etree, criterion):
        
        if criterion.test.capability_id not in cls.get_supported_capability_modules():
            #TODO: Should be a Status Message
            raise Exception("Capability module not supported")
        
        xpath, nsmap = cls.criterion_get_xpath(criterion)
        content_etree.xpath(xpath, namespaces = nsmap)
        if matches in (True, False):
            result = matches
        else:
            result = len(matches) > 0
        
        if criterion.negate:
            return not result
        return result
    
    @classmethod
    def get_xpath_parts(cls, target):
        """
        Given a Targeting Expression, return a list of 
        XPath parts (which can be used to construct the 
        beginning part of an XPath) and nsmap for use in an XPath.
        
        The last item in the list might be a wildcard, which
        will need to be handled by the calling function
        """
        
        nsmap = {}
        xpath_parts = ['']
        #operand = 'text()' #should this be handled by the caller?
        target_parts = target.split('/')
        context = cls.mapping_dict['root_context']
        for part in target_parts:
            if part.startswith('@'): # Its an attribute
                operand = part
            elif part == '**': # Multi-field wild card
                xpath_parts.append('/*') # This will get made into '//*' at the .join step
            elif part == '*': # Multi-field wild card
                xpath_parts.append('*') # This will get made into '/*' at the .join step
            else: # Regular token
                context = context['children'].get(part, None)
                if context is None:
                    raise ValueError('Unknown token: %s' % part)
                namespace  = context.get('namespace', None)
                if namespace:
                    xpath_parts.append(context.get('alias', 'NoAliasFound') + ':' + part)
                    nsmap[context.get('prefix', 'NoPrefixFound')] = namespace
                else:
                    xpath_parts.append(part)
        
        return xpath_parts, nsmap
    
    @classmethod
    def get_xpath_append(cls, operand, test):
        """
        Get the clause to append to the end of an XPath, 
        based on the operand and test
        """
        v = None
        if criterion.test.parameters and 'value' in criterion.test.parameters:
            v = criterion.test.parameters['value']
            
        append = ''
        
        if relationship == 'equals':
            if params['match_type'] == 'case_sensitive_string':
                append = '[%s = \'%s\']' % (operand, v)
            elif params['match_type'] == 'case_insensitive_string':
                append = '[translate(%s, \'ABCDEFGHIJKLMNOPQRSTUVWXYZ\', \'abcdefghijklmnopqrstuvwxyz\') = \'%s\']' % (operand, v.lower())
            elif params['match_type'] == 'number':
                append = '[%s = \'%s\']' % (operand, v)
        elif relationship == 'not equals':
            if params['match_type'] == 'case_sensitive_string':
                append = '[%s != \'%s\']' % (operand, v)
            elif params['match_type'] == 'case_insensitive_string':
                append = '[translate(%s, \'ABCDEFGHIJKLMNOPQRSTUVWXYZ\', \'abcdefghijklmnopqrstuvwxyz\') != \'%s\']' % (operand, v.lower())
            elif params['match_type'] == 'number':
                append = '[%s != \'%s\']' % (operand, v)
        elif relationship == 'greater than':
            append = '[%s > \'%s\']' % (operand, v)
        elif relationship == 'greater than or equal':
            append = '[%s >= \'%s\']' % (operand, v)
        elif relationship == 'less than':
            append = '[%s < \'%s\']' % (operand, v)
        elif relationship == 'less than or equal':
            append = '[%s <= \'%s\']' % (operand, v)
        #Not sure how I would really do these
        elif relationship == 'does not exist':
            xpath_string = 'not(' + xpath_string + ')'
        elif relationship == 'exists':
            pass#nothing necessary
        elif relationship == 'begins with':
            if params['case_sensitive'] == 'false':
                append = '[starts-with(translate(%s, \'ABCDEFGHIJKLMNOPQRSTUVWXYZ\', \'abcdefghijklmnopqrstuvwxyz\'), \'%s\')]' % (operand, v.lower())
            elif params['case_sensitive'] == 'true':
                append = '[starts-with(%s, \'%s\')]' % (operand, v)
        elif relationship == 'ends with':
            #ends-with($s, $t)
            #$t = substring($s, string-length() - string-length($t) +1)
            if params['case_sensitive'] == 'false':
                append = '[substring(translate(%s, \'ABCDEFGHIJKLMNOPQRSTUVWXYZ\', \'abcdefghijklmnopqrstuvwxyz\'), string-length(%s) - string-length(\'%s\') + 1) = \'%s\']' % (operand, operand, v, v.lower())
            elif params['case_sensitive'] == 'true':
                append = '[substring(%s, string-length(%s) - string-length(\'%s\') + 1) = \'%s\']' % (operand, operand, v, v)
        elif relationship == 'contains':
            if params['case_sensitive'] == 'false':
                append = '[contains(translate(%s, \'ABCDEFGHIJKLMNOPQRSTUVWXYZ\', \'abcdefghijklmnopqrstuvwxyz\'), \'%s\')]' % (operand, v.lower())
            elif params['case_sensitive'] == 'true':
                append = '[contains(%s, \'%s\')]' % (operand, v)
        else:
            raise Exception('Invalid relationship: %s' % relationship)
        
        return append
    
    # Some functional restrictions I learned about Targeting Expressions
    # - Multi-field wild card has to be at the beginning or end
    # - Single-field wild card can by anywhere
    # - Attribute has to be at the end
    @classmethod
    def criterion_get_xpath(cls, criterion):
        """
        Given a criterion, translate it into an XPath that can be 
        evaluated against an XML instance document to determine 
        whether the document matches the criterion
        
        Returns an XPath and an nsmap to use with the XPath
        """
        if criterion.relationship not in cls.supported_relationships:
            raise Exception("Relationship not supported")
        
        xpath_parts, nsmap = cls.get_xpath_parts(criterion.target)
        
        xpath_list = []
        
        # If the expression ends with a wildcard, attribute and element values have to be considered. e.g.,
        # /stix:STIX_Package//*[contains(., 'value')] or /stix:STIX_Package//@*[contains(., 'value')]
        if xpath_parts[-1] in ('/*','*'):
            operand = '.'
            
            wc = ''
            if xpath_parts[-1] == '/*':
                wc = '/'
            
            xpath_parts[-1] = wc + '*%s'
            element_xpath = '/'.join(xpath_parts)
            xpath_list.append(element_xpath)
            
            xpath_parts[-1] = wc + '@*%s'
            attribute_target = '/'.join(xpath_parts)
            xpath_list.append(attribute_target)
            
        else: # No special case
            operand = 'text()'
            xpath = '/'.join(xpath_parts)
            xpath_list.append( xpath )
        
        #append = cls.append_xpath_critera(criterion)
        append = cls.get_xpath_append(operand, criterion.test)
        
        appended_xpath_list = []
        for xpath_item in xpath_list:
            appended_xpath_list.append(xpath_item + append)
        
        final_xpath = ' or '.join(appended_xpath_list)
        #print 'xpath: %s' % final_xpath
        return final_xpath, nsmap
    
    @classmethod
    def execute_query(cls, content_block_list, query):
        if query.targeting_expression_vocabulary_id != cls.get_supported_targeting_expressions():
            raise Exception("Targeting expression vocabulary not supported by this handler!")#TODO: Better exception
        
        result_list = []
        for content_block in content_block_list:
            etree_content = etree.parse(content_block.content)
            if cls.evaluate_criteria(etree_content, query.criteria):
                result_list.append(content_block)
        
        return result_list