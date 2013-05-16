'''
Created on May 25, 2011

@author: berger
'''

from thelma.models.organization import Organization
from thelma.testing import ThelmaModelTestCase


class OrganizationModelTest(ThelmaModelTestCase):

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.name = 'Nunc'

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.name

    def test_organization_init(self):
        org = Organization(self.name)
        self.assert_not_equal(org, None)
        self.assert_equal(org.name, self.name)
        self.assert_not_equal(org.slug, None)

    def test_organization_slug(self):
        name = 'Nunc Inc'
        name_slug = 'nunc-inc'
        org = Organization(name)
        self.assert_not_equal(org.slug, name)
        self.assert_equal(org.slug, name_slug)

    def test_organization_equality(self):
        id1 = 1
        id2 = 2
        org1 = Organization(self.name)
        org1.id = id1
        org2 = Organization(self.name)
        org2.id = id2
        org3 = Organization('other')
        org3.id = id1
        self.assert_not_equal(org1, org2)
        self.assert_equal(org1, org3)
        self.assert_not_equal(org1, id1)
