'''
Created on Jun 20, 2011

@author: berger
'''


from thelma.models.status import ItemStatus
from thelma.testing import ThelmaModelTestCase


class ItemStatusModelTest(ThelmaModelTestCase):

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.desc = 'more info'
        self.name = 'managed'

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.desc
        del self.name

    def test_status_init(self):
        status = ItemStatus(self.name)
        self.assert_not_equal(status, None)
        self.assert_equal(status.name, self.name)
        self.assert_not_equal(status.slug, None)
        self.assert_true(status.description is None)
        status2 = ItemStatus(self.name, self.desc)
        self.assert_equal(status2.description, self.desc)

    def test_status_slug(self):
        name = 'Default Status'
        name_slug = 'default-status'
        status = ItemStatus(name)
        self.assert_not_equal(status.slug, name)
        self.assert_equal(status.slug, name_slug)

    def test_status_equality(self):
        id1 = 1
        id2 = 2
        status1 = ItemStatus(self.name)
        status1.id = id1
        status2 = ItemStatus(self.name)
        status2.id = id2
        status3 = ItemStatus('other name')
        status3.id = id1
        self.assert_not_equal(status1, status2)
        self.assert_equal(status1, status3)
        self.assert_not_equal(status1, id1)
