# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from django.test import TestCase, Client
from django.conf import settings


class TETestObj(object):
    def __init__(self, target, expected_stubs, expected_operand=None, expected_nsmap=None):
        self.target = target
        self.expected_stub_set = set(expected_stubs)
        self.expected_operand = expected_operand
        self.expected_nsmap = expected_nsmap

    def check_result(self, xpath_builders, operand=None, nsmap=None):
        xpath_stubs = ['/'.join(xb.xpath_parts) for xb in xpath_builders]
        xpath_stub_set = set(xpath_stubs)
        if self.expected_stub_set != xpath_stub_set:
            raise ValueError('Expected XPath Stubs failure!\n'
                             'Expected: %s\n'
                             'Actual  : %s\n' % (self.expected_stub_set, xpath_stub_set))

        if self.expected_operand is not None:
            if self.expected_operand != operand:
                raise ValueError('Expected operand failure!\n'
                                 'Expected: %s\n'
                                 'Actual  : %s\n' % (self.expected_operand, operand))

        if self.expected_nsmap is not None:
            if self.expected_nsmap != nsmap:
                raise ValueError('Expected nsmap failure!\n'
                                 'Expected: %s\n'
                                 'Actual  : %\n' % (self.expected_nsmap, nsmap))

no_wc_001 = TETestObj(target='STIX_Package/STIX_Header/Handling/Marking/Marking_Structure/Terms_Of_Use',
                      expected_stubs=[
                          '/stix:STIX_Package/stix:STIX_Header/stix:Handling/marking:Marking/marking:Marking_Structure/'
                          'terms:Terms_Of_Use',
                                      ])

l_wc_001 = TETestObj(target='**/NameElement',
                     expected_stubs=['//xal:NameElement', ])

l_wc_002 = TETestObj(target='*/STIX_Header/Title',
                     expected_stubs=['/*/stix:STIX_Header/stix:Title', ])

l_wc_003 = TETestObj(target='**/@cybox_major_version',
                     expected_stubs=['//@cybox_major_version',])

m_wc_001 = TETestObj(target='STIX_Package/*/Title',
                     expected_stubs=['/stix:STIX_Package/*/stix:Title'])

m_wc_002 = TETestObj(target='STIX_Package/**/NameElement',
                     expected_stubs=['/stix:STIX_Package//xal:NameElement'])

t_wc_001 = TETestObj(target='STIX_Package/STIX_Header/*',
                     expected_stubs=['/stix:STIX_Package/stix:STIX_Header/*',
                                     '/stix:STIX_Package/stix:STIX_Header/@*'])

t_wc_002 = TETestObj(target='STIX_Package/TTPs/**',
                     expected_stubs=['/stix:STIX_Package/stix:TTPs//*',
                                     '/stix:STIX_Package/stix:TTPs//@*'])


class BaseXmlQueryHandlerTests(TestCase):

    def test_01(self):
        """
        Test the target_to_xpath_stubs2() function
        :return:
        """

        test_tes = (no_wc_001,
                    l_wc_001, l_wc_002,
                    m_wc_001, m_wc_002,
                    t_wc_001, t_wc_002)

        from taxii_services.query_handlers.stix_xml_111_handler import StixXml111QueryHandler

        for test_te in test_tes:
            xpath_builders, nsmap = StixXml111QueryHandler.target_to_xpath_builders(None, test_te.target)
            test_te.check_result(xpath_builders, nsmap)
