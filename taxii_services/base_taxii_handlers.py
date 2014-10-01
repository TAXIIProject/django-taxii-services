# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from .exceptions import StatusMessageException

import libtaxii as t
import libtaxii.taxii_default_query as tdq
from libtaxii.constants import *
from django.conf import settings

class BaseMessageHandler(object):
    """
    MessageHandler is the base class for TAXII Message
    Handlers.

    Child classes MUST specify a value for MessageHandler.supported_request_messages,
    and MUST implement the handle_message function.

    e.g.,::

        import libtaxii.messages_11 as tm11

        MessageHandlerChild(MessageHandler):
            supported_request_messages = tm11.DiscoveryRequest

            @classmethod
            def handle_message(cls, service, taxii_message, django_request):
                dr = tm11.DiscoveryResponse( ... )
                # Code to handle the request against the service would go here
                return dr

        Optionally,register the MessageHandler child:
        import taxii_services.management as m
        m.register_message_handler(MessageHandlerChild, name='MessageHandlerChild')
    """
    
    #: Identify the list of supported request messages
    #: This MUST be a list (well, iterable) defined by the extending class
    #: e.g., [tm11.InboxMessage]
    supported_request_messages = None
        
    @classmethod
    def get_supported_request_messages(cls):
        """
        Returns:
            The supported_request_messages property or raises a ValueError
            if it isn't set.
        """
        if not cls.supported_request_messages:
            raise ValueError('The variable \'supported_request_messages\' has not been defined by the subclass!')
        return cls.supported_request_messages
    
    @classmethod
    def validate_headers(cls, django_request, in_response_to='0'):
        """
        Validates the headers of a django request
        based on the properties of this MessageHandler.

        Specifically, the supported_request_messages property is used to
        infer which version(s) of TAXII this message handler supports and
        from there infer which headers are valid/invalid.

        Arguments:
            django_request - The Django request to validate
            in_response_to - If a StatusMessageException is raised as a result \
                of header validation (e.g., the headers are invalid), \
                in_response_to will be used as the in_response_to \
                field of the Status Message.

        Returns:
            None if all headers are valid. Raises a StatusMessageException otherwise.
        """
        
        # First, make sure required headers exist
        svcs = django_request.META.get('HTTP_X_TAXII_SERVICES', None)
        if not svcs:
            msg =  "The X-TAXII-Services header was not specified"
            if settings.DEBUG:
                msg += "\r\nHeaders: %s " % str(django_request.META)
            raise StatusMessageException(in_response_to, 
                                         ST_FAILURE, 
                                         msg)
        
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
        #for k, v in django_request.META.iteritems():
        #    print '%s: %s' % (k, v)
        
        #Identify which TAXII versions the message handler supports
        supports_taxii_11 = False
        supports_taxii_10 = False
        for message in cls.get_supported_request_messages():
            if message.__module__ == 'libtaxii.messages_11':
                supports_taxii_11 = True
            elif message.__module__ == 'libtaxii.messages_10':
                supports_taxii_10 = True
            else:
                raise ValueError( ("The variable \'supported_request_messages\' "
                                  "contained a non-libtaxii message module: %s") % \
                                  message.__module__)
        
        # Next, determine whether the MessageHandler supports the headers
        # Validate the X-TAXII-Services header
        if svcs not in (VID_TAXII_SERVICES_11, VID_TAXII_SERVICES_10):
            raise StatusMessageException(in_response_to, 
                                         ST_FAILURE, 
                                         "The value of X-TAXII-Services was not recognized.")
        
        if (  (svcs == VID_TAXII_SERVICES_11 and not supports_taxii_11) or 
              (svcs == VID_TAXII_SERVICES_10 and not supports_taxii_10)  ):
            raise StatusMessageException(in_response_to, 
                                         ST_FAILURE, 
                                         ("The specified value of X-TAXII-Services (%s) "
                                         "is not supported by this TAXII Service.") % svcs)
        
        # Validate the Content-Type header
        if ct.lower() != 'application/xml':
            raise StatusMessageException(in_response_to, 
                                         ST_FAILURE, 
                                         "The specified value of Content-Type is not supported.")
        
        # Validate the X-TAXII-Content-Type header
        if xtct not in (VID_TAXII_XML_11, VID_TAXII_XML_10):
            raise StatusMessageException(in_response_to, 
                                         ST_FAILURE, 
                                         "The value of X-TAXII-Content-Type was not recognized.")
        
        if (  (xtct == VID_TAXII_XML_11 and not supports_taxii_11) or
              (xtct == VID_TAXII_XML_10 and not supports_taxii_10)  ):
            raise StatusMessageException(in_response_to,
                                         ST_FAILURE,
                                         "The specified value of X-TAXII-Content-Type is not supported")
        
        # Validate the X-TAXII-Protocol header
        # TODO: Look into the service properties instead of assuming both are supported
        if xtp not in (VID_TAXII_HTTP_10, VID_TAXII_HTTPS_10):
            raise StatusMessageException(in_response_to,
                                         ST_FAILURE,
                                         "The specified value of X-TAXII-Protocol is not supported")
        
        #Validate the accept header
        if accept and accept.lower() != 'application/xml':
            raise StatusMessageException(in_response_to,
                                         ST_FAILURE,
                                         "The specified value of Accept is not supported")
        
        #Validate the X-TAXII-Accept header
        # TODO: Accept more "complex" accept headers (e.g., ones that specify more
        #       than one value)
        if xta not in (VID_TAXII_XML_11, VID_TAXII_XML_10, None):
            raise StatusMessageException(in_response_to,
                                         ST_FAILURE,
                                         "The specified value of X-TAXII-Accept is not recognized")
        
        if not xta: #X-TAXII-Accept not specified, we can pick whatever we want
            xta = VID_TAXII_XML_11
        
        if (  (xta == VID_TAXII_XML_11 and not supports_taxii_11) or 
              (xta == VID_TAXII_XML_10 and not supports_taxii_10)  ):
            raise StatusMessageException(in_response_to,
                                         ST_FAILURE,
                                          "The specified value of X-TAXII-Accept is not supported")
        
        #Headers are valid
        return
    
    @classmethod
    def validate_message_is_supported(cls, taxii_message):
        """
        Checks whether the TAXII Message is supported by this Message Handler.

        Arguments:
            taxii_message - A libtaxii.messages_11 or libtaxii.messages_10 taxii message

        Returns:
            None if the message is supported, raises a StatusMessageException otherwise.
        """
        if taxii_message.__class__ not in cls.get_supported_request_messages():
            raise StatusMessageException(taxii_message.message_id,
                                         ST_FAILURE,
                                         "TAXII Message not supported by Message Handler.")
        return
    
    @classmethod
    def handle_message(cls, service, taxii_message, django_request):
        """
        This method is implemented by child Message Handlers to handle 
        TAXII Service invocations.

        Arguments:
            service - A TAXII Service model object representing the service being invoked
            taxii_message - A libtaxii TAXII message representing the request message
            django_request - The django request associated with the taxii_message

        Returns:
            A libtaxii TAXII Message containing the response. May raise a StatusMessageException.
        """
        raise NotImplementedError()

class QueryHandler(object):

    """
    QueryHandler is the base class for TAXII Query
    Handlers.

    Child classes MUST specify a value for QueryHandler.supported_targeting_expression,
    and QueryHandler.supported_capability_modules
    and MUST implement the execute_query function.

    e.g.,::

        import libtaxii.messages_11 as tm11
        import libtaxii.taxii_default_query as tdq
        from libtaxii.constants import *

        QueryHandlerChild(QueryHandler):
            supported_targeting_expression = CB_STIX_XML_111
            supported_capability_modules = [tdq.CM_CORE]

            @classmethod
            def execute_query(cls, content_block_list, query):
                matching_content_blocks = []
                for cb in content_block_list:
                    matches = # code to execute the query
                    if matches:
                    matching_content_blocks.append(cb)
                return matching_content_blocks

    Optionally,register the QueryHandler child:
    import taxii_services.management as m
    m.register_query_handler(QueryHandlerChild, name='QueryHandlerChild')
    """
    
    supported_targeting_expression = None
    supported_capability_modules = None
    #supported_scope_message = None
    
    @classmethod
    def get_supported_capability_modules(cls):
        """
        Returns:
            A list of TAXII Default Query Capability Modules that this QueryHandler supports.
        """
        if not cls.supported_capability_modules:
            raise ValueError('The variable \'supported_capability_modules\' has not been defined by the subclass!')
        return cls.supported_capability_modules
    
    @classmethod
    def get_supported_targeting_expression(cls):
        """
        Returns:
            A string indicating the Targeting Expression this QueryHandler supports.
        """
        if not cls.supported_targeting_expression:
            raise ValueError('The variable \'supported_targeting_expression\' has not been defined by the subclass!')
        return cls.supported_targeting_expression
    
    @classmethod
    def get_supported_scope_message(cls):
        pass#TODO: is this worthwhile?
    
    @staticmethod
    def is_target_supported(target):
        pass
    
    @staticmethod
    def is_scope_supported(scope):
        """
        This method MUST be implemented by child classes.

        Arguments:
            scope (str) - A string indicating the scope of a query.

        Returns:
            A taxii_services.handlers.SupportInfo object indicating support.
        """
        raise NotImplementedError()
    
    @classmethod
    def update_params_dict(params_dict, poll_request):
        """
        This is a hook that allows a query handler to modify the params_dict
        before being passed into the database.

        The default behavior of this method is to do nothing.
        
        Arguments:
            params_dict - a dict containing the results of PollRequest11Handler.get_params_dict_11()
            poll_request - a poll request
        """
        return params_dict
    
    # TODO: What about people who have their own data store? ContentBlock model won't work for them.
    @classmethod
    def execute_query(cls, content_block_list, query):
        """
        This method MUST be implemented by child classes.

        Arguments:
            content_block_list - an iterable of ContentBlock model objects.
            query - The query to be executed

        Returns:
            A list of ContentBlock model objects that match the query, 
            or raises a StatusMessageException
        """        
        raise NotImplementedError()

class BaseXmlQueryHandler(QueryHandler):
    """
    Extends the QueryHandler for general XML / XPath
    processing. This class still needs to be extended
    to support specific XML formats (e.g., specific
    versions of STIX).

    There is a generate_xml_query_extension.py script 
    to help with extending this class

    Note that correctly specifying the mapping_dict is
    a critical aspect of extending this class. The mapping_dict
    should adhere to the following format::

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
        """
        Overrides the parent class' method.

        If the scope can be turned into an XPath, the scope is supported.

        Note: This function may change in the future (specifically, the returning 
        a tuple part)
        """
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

        Arguments:
            content_etree - an lxml etree to evaluate
            criteria - the criteria to evaluate against the etree

        Returns: 
            True or False, indicating whether the content_etree 
            matches the criteria
        
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
        """
        Evaluates the criterion in a query.

        Arguments:
            content_etree - an lxml etree to evaluate
            criterion - the criterion to evaluate against the etree

        Returns: 
            True or False, indicating whether the content_etree 
            matches the criterion
        """
        
        if criterion.test.capability_id not in cls.get_supported_capability_modules():
            #TODO: Should be a StatusMessageException
            raise Exception("Capability module not supported")
        
        xpath, nsmap = cls.criterion_get_xpath(criterion)
        matches = content_etree.xpath(xpath, namespaces = nsmap)
        # XPath results can be a boolean (True, False) or
        # a NodeSet
        if matches in (True, False): # The result is boolean, take it literally
            result = matches
        else: # The result is a NodeSet. The Criterion is True iff there are >0 resulting nodes
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

        Arguments:
            target (str) - A string containing the Target of a Criterion

        Returns: 
            A tuple containing a list of XPath Parts and an nsmap dict
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

        Arguments:
            operand (str) - The operand of the XPath expression (e.g., the left hand side (x) of x = y)
            test - A TAXII Default Query Test object

        Returns: 
            A string containing the append part of the xpath
        
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
            #TODO: Should be a statusmessageexception
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

        Arguments:
            criterion - a TAXII Default Query criterion object

        Returns:
            an XPath and an nsmap to use with the XPath
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
