# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from ..exceptions import StatusMessageException

import libtaxii.taxii_default_query as tdq
from libtaxii.constants import *

from lxml import etree

EQ_CS = '[%s = \'%s\']'
EQ_CI ='[translate(%s, \'ABCDEFGHIJKLMNOPQRSTUVWXYZ\', \'abcdefghijklmnopqrstuvwxyz\') = \'%s\']'
EQ_N = '[%s = \'%s\']'

NEQ_CS = '[%s != \'%s\']'
NEQ_CI = '[translate(%s, \'ABCDEFGHIJKLMNOPQRSTUVWXYZ\', \'abcdefghijklmnopqrstuvwxyz\') != \'%s\']'
NEQ_N = '[%s != \'%s\']'

GT = '[%s > \'%s\']'
GTE = '[%s >= \'%s\']'
LT = '[%s < \'%s\']'
LTE = '[%s <= \'%s\']'

EX = None
DNE = '????????????????????????????'

BEGIN_CS = '[contains(%s, \'%s\')]'
BEGIN_CI = '[starts-with(translate(%s, \'ABCDEFGHIJKLMNOPQRSTUVWXYZ\', \'abcdefghijklmnopqrstuvwxyz\'), \'%s\')]'

CONTAINS_CS = '[contains(%s, \'%s\')]'
CONTAINS_CI = '[contains(translate(%s, \'ABCDEFGHIJKLMNOPQRSTUVWXYZ\', \'abcdefghijklmnopqrstuvwxyz\'), \'%s\')]'

ENDS_CS = '[substring(%s, string-length(%s) - string-length(\'%s\') + 1) = \'%s\']'
ENDS_CI = '[substring(translate(%s, \'ABCDEFGHIJKLMNOPQRSTUVWXYZ\', \'abcdefghijklmnopqrstuvwxyz\'), string-length(%s) - string-length(\'%s\') + 1) = \'%s\']'


class BaseQueryHandler(object):

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

    supported_tevs = None
    supported_cms = None

    def __init__(self):
        if self.supported_tevs is None:
            raise NotImplementedError("The subclass did not specify a value for supported_tevs")

        if self.supported_cms is None:
            raise NotImplementedError("The subclass did not specify a value for supported_cms")

    @classmethod
    def is_target_supported(cls, target):
        raise NotImplementedError()

    @classmethod
    def get_supported_cms(cls):
        return cls.supported_cms

    @classmethod
    def get_supported_tevs(cls):
        return cls.supported_tevs

    @classmethod
    def is_cm_supported(cls, cm):
        supported = cm in cls.supported_cms
        message = None
        if not supported:
            message = "Supported CMs: %s" % cls.supported_cms

    @classmethod
    def update_db_kwargs(cls, poll_request_properties, db_kwargs):
        """
        This is a hook used by PollRequest11Handler that allows a query handler to modify the params_dict
        before being passed into the database.

        The default behavior of this method is to do nothing.

        Arguments:
            poll_request_properties - a PollRequestProperties object
            db_kwargs - a dict containing the results of PollRequestProperties.get_db_kwargs()
        """
        return db_kwargs

    @classmethod
    def filter_content(cls, poll_request_properties, content_blocks):
        """
        This is a hook used by PollRequest11Handler that allows a query handler to modify the database result set
        after being retrieved from the database and before it is returned to the
        requester. Default behavior is to do nothing.

        :param poll_request_properties: A util.PollRequestProperties object
        :param content_blocks: A list of ContentBlock objects
        :return: a list of ContentBlock objects
        """
        return content_blocks


class BaseXmlQueryHandler(BaseQueryHandler):
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
    def is_target_supported(cls, target):
        """
        Overrides the parent class' method.

        If the scope can be turned into an XPath, the scope is supported.

        Note: This function may change in the future (specifically, the returning
        a tuple part)
        """

        try:
            cls.get_xpath_parts(target)
        except ValueError as e:
            return False, e

        return True, None

    @classmethod
    def evaluate_criteria(cls, prp, content_etree, criteria):
        """
        Evaluates the criteria in a query. Note that criteria can have
        child criteria (which will cause recursion) and child criterion.

        Arguments:
            content_etree - an lxml etree to evaluate
            criteria - the criteria to evaluate against the etree

        Returns:
            True or False, indicating whether the content_etree
            matches the criteria

        """

        for child_criteria in criteria.criteria:
            value = cls.evaluate_criteria(content_etree, child_criteria)
            if value and criteria.operator == tdq.OP_OR:
                return True
            elif not value and criteria.operator == tdq.OP_AND:
                return False
            else:  # Don't know anything for sure yet
                pass

        for criterion in criteria.criterion:
            value = cls.evaluate_criterion(prp, content_etree, criterion)
            # TODO: Is there a way to keep this DRY?
            if value and criteria.operator == tdq.OP_OR:
                return True
            elif not value and criteria.operator == tdq.OP_AND:
                return False
            else:  # Don't know anything for sure yet
                pass

        return criteria.operator == tdq.OP_AND

    @classmethod
    def evaluate_criterion(cls, prp, content_etree, criterion):
        """
        Evaluates the criterion in a query by turning the Criterion into an XPath and
        evaluating it against the content_etree

        Arguments:
            content_etree - an lxml etree to evaluate
            criterion - the criterion to evaluate against the etree

        Returns:
            True or False, indicating whether the content_etree
            matches the criterion
        """

        # Based on criterion.target, get the "stub" of an XPath, e.g.,
        # STIX_Package/STIX_Header/Title turns into
        # stix:STIX_Package/stix:STIX_Header/stix:Title
        # Note that the stubs do not contain the matching part of an XPaths
        # (e.g., text() = 'value_to_match')
        xpath_stubs, operand, nsmap = cls.target_to_xpath_stubs(prp, criterion.target)
        to_append = cls.get_xpath_append(prp, operand, criterion.test)

        full_xpaths = []
        for xpath_stub in xpath_stubs:
            full_xpaths.append(xpath_stub + to_append)

        xpath = " or ".join(full_xpaths)

        matches = content_etree.xpath(xpath, namespaces=nsmap)
        # XPath results can be a boolean (True, False) or
        # a NodeSet
        if matches in (True, False):  # The result is boolean, take it literally
            result = matches
        else:  # The result is a NodeSet. The Criterion is True iff there are >0 resulting nodes
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
        target_parts = target.split('/')
        context = cls.mapping_dict['root_context']  # mapping_dict is defined by child classes

        for part in target_parts:
            if part.startswith('@'):  # Its an attribute
                #TODO: Write a unit test that uses an attribute value to see what this is
                operand = part
            elif part == '**':  # Multi-field wild card
                xpath_parts.append('/*')  # This will get made into '//*' at the .join step
            elif part == '*':  # Multi-field wild card
                xpath_parts.append('*')  # This will get made into '/*' at the .join step
            else:  # Regular token
                context = context['children'].get(part, None)
                if context is None:
                    raise ValueError('Unknown token: %s' % part)
                namespace = context.get('namespace', None)
                if namespace:  # Add namespaced info
                    xpath_parts.append(context.get('prefix', 'NoPrefixFound') + ':' + part)
                    nsmap[context.get('prefix', 'NoPrefixFound')] = namespace
                else:  # Add non-namespaced info
                    xpath_parts.append(part)

        return xpath_parts, nsmap

    @classmethod
    def get_xpath_append(cls, prp, operand, test):
        """
        Get the clause to append to the end of an XPath,
        based on the operand and test

        Arguments:
            operand (str) - The operand of the XPath expression (e.g., the left hand side (x) of x = y)
            test - A TAXII Default Query Test object

        Returns:
            A string containing the append part of the xpath

        """
        v = test.parameters.get('value', None)
        relationship = test.relationship
        params = test.parameters

        # Relationship equals
        if relationship == R_EQUALS and params[P_MATCH_TYPE] == 'case_sensitive_string':
            append = EQ_CS % (operand, v)
        elif relationship == R_EQUALS and params[P_MATCH_TYPE] == 'case_insensitive_string':
            append = EQ_CI % (operand, v.lower())
        elif relationship == R_EQUALS and params[P_MATCH_TYPE] == 'number':
            append = EQ_N % (operand, v)

        # Take a breather before jumping into the next relationship, not equals

        elif relationship == R_NOT_EQUALS and params[P_MATCH_TYPE] == 'case_sensitive_string':
            append = NEQ_CS % (operand, v)
        elif relationship == R_NOT_EQUALS and params[P_MATCH_TYPE] == 'case_insensitive_string':
            append = NEQ_CI % (operand, v.lower())
        elif relationship == R_NOT_EQUALS and params[P_MATCH_TYPE] == 'number':
            append = NEQ_N % (operand, v)

        # Next set of relationships, gt, lt, gte, lte

        elif relationship == R_GREATER_THAN:
            append = GT % (operand, v)
        elif relationship == R_GREATER_THAN_OR_EQUAL:
            append = GTE % (operand, v)
        elif relationship == R_LESS_THAN:
            append = LT % (operand, v)
        elif relationship == R_LESS_THAN_OR_EQUAL:
            append = LTE % (operand, v)

        # Next set of relationships, Exists/DoesNotExist

        elif relationship == R_DOES_NOT_EXIST:
            xpath_string = 'not(' + xpath_string + ')'
        elif relationship == R_EXISTS:
            pass  # nothing necessary

        # Next, begins with
        elif relationship == R_BEGINS_WITH and params[P_CASE_SENSITIVE] == 'false':
            append = BEGIN_CS % (operand, v.lower())
        elif relationship == R_BEGINS_WITH and params[P_CASE_SENSITIVE] == 'true':
            append = BEGIN_CI % (operand, v)

        # Next, contains

        elif relationship == R_CONTAINS and params[P_CASE_SENSITIVE] == 'false':
            append = CONTAINS_CS % (operand, v.lower())
        elif relationship == R_CONTAINS and params[P_CASE_SENSITIVE] == 'true':
            append = CONTAINS_CS % (operand, v)

        # Lastly, ends with

        elif relationship == R_ENDS_WITH and params[P_CASE_SENSITIVE] == 'false':
            append = ENDS_CI % (operand, operand, v, v.lower())
        elif relationship == R_ENDS_WITH and params[P_CASE_SENSITIVE] == 'true':
            append = ENDS_CS % (operand, operand, v, v)
        else:
            raise ValueError("Unknown values: %s, %s" % (relationship, params))

        return append

    @classmethod
    def target_to_xpath_stubs(cls, prp, target):
        nsmap = {}
        target_parts = target.split('/')
        xpath_parts = ['']
        context = cls.mapping_dict['root_context']  # Start at the root of the mapping_dict

        for part in target_parts:
            if part.startswith('@'):  # It's an attribute
                operand = part
            elif part == '**':  # It's a multi-field WC
                xpath_parts.append('/*')  # This will become '//*' later on
            elif part == '*':  # Single field WC
                xpath_parts.append(part)  # This will become '/*' later on
                # TODO: This doesn't descend into the context tree like it should (Maybe a look-ahead is needed?)
            else:  # Assume it's a "normal" part
                context = context['children'].get(part, None)
                if context is None:
                    raise ValueError('Unknown token: %s' % part)
                namespace = context.get('namespace', None)
                if namespace:
                    prefix = context['prefix']
                    xpath_parts.append(prefix + ':' + part)
                    nsmap[prefix] = namespace
                else:
                    xpath_parts.append(part)

        # Wild cards need to account for both element values and attribute values
        # A single field WC (*) must add a '/*' and a '/@*' if it's at the end
        # A multi field WC (**) must add a '//*' and a '//@*' if it's at the end

        if xpath_parts[-1] == '/*':  # Multi-field WC
            operand = '.'

            xpath_parts[-1] = '/*'
            elt_stub = '/'.join(xpath_parts)

            xpath_parts[-1] = '/@*'
            attr_stub = '/'.join(xpath_parts)

            xpath_stubs = [elt_stub, attr_stub]

        elif xpath_parts[-1] == '*':  # Single field WC
            operand = '.'

            xpath_parts[-1] = '*'
            elt_stub = '/'.join(xpath_parts)

            xpath_parts[-1] = '@*'
            attr_stub = '/'.join(xpath_parts)

            xpath_stubs = [elt_stub, attr_stub]

        else:
            operand = 'text()'
            stub = '/'.join(xpath_parts)
            xpath_stubs = [stub]

        # print xpath_stubs

        #if '*' in xpath_parts[-1]:  # The last value is a wild card of some sort
        #    operand = '.'
        #
        #    # TODO: Use "if xpath_parts[-1] in ('/*', '*'):" as a reference
        #    raise ValueError('Not really sure how this works')
        #else:  # No special case at the end
        #    operand = 'text()'
        #    stub = '/'.join(xpath_parts)
        #    xpath_stubs = [stub]

        return xpath_stubs, operand, nsmap

    @classmethod
    def filter_content(cls, prp, content_blocks):
        """
        Turns the prp.query into an XPath, runs the XPath against each
        item in `content_blocks`, and returns the items in `content_blocks`
        that match the XPath.

        :param prp: A PollRequestParameters object representing the Poll Request
        :param content_blocks: A list of models.ContentBlock objects to filter
        :return: A list of models.ContentBlock objects matching the query
        """
        if prp.query.targeting_expression_id not in cls.get_supported_tevs():
            raise StatusMessageException(prp.message_id,
                                         ST_UNSUPPORTED_TARGETING_EXPRESSION_ID,
                                         status_detail={SD_TARGETING_EXPRESSION_ID: cls.get_supported_tevs()})

        result_list = []
        for content_block in content_blocks:
            etree_content = etree.XML(content_block.content)
            if cls.evaluate_criteria(prp, etree_content, prp.query.criteria):
                result_list.append(content_block)

        return result_list
