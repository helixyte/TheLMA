'''
Created on May 26, 2011

@author: berger
'''

from thelma.models.subproject import Subproject
from thelma.testing import ThelmaModelTestCase


class SubprojectModelTest(ThelmaModelTestCase):

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.label = 'Astra Pass1'
        self.active = True

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.label
        del self.active

    def test_subproject_init(self):
        sub1 = Subproject(self.label)
        self.assert_not_equal(sub1, None)
        self.assert_equal(sub1.label, self.label)
        self.assert_false(sub1.active)
        self.assert_not_equal(sub1.creation_date, None)
        self.assert_is_none(sub1.slug)
        sub2 = Subproject(self.label, creation_date=None, active=self.active)
        self.assert_true(sub2.active)

#FIXME disabled until subproject slug is moved back to label pylint:disable=W0511
#    def test_subproject_slug(self):
#        label_slug = 'astra-pass1'
#        sub = Subproject(self.label)
#        self.assert_not_equal(sub.slug, self.label)
#        self.assert_equal(sub.slug, label_slug)

    def test_subproject_equality(self):
        project1 = self._create_project()
        project1.id = 4
        sub1 = Subproject(self.label, self.active)
        sub1.project = project1
        sub2 = Subproject(self.label, self.active)
        sub2.project = project1
        project2 = self._create_project()
        project2.id = 8
        sub3 = Subproject(self.label, self.active)
        sub3.project = project2
        sub4 = Subproject('other_label', self.active)
        sub4.project = project1
        sub5 = Subproject(self.label, False)
        sub5.project = project1
        self.assert_equal(sub1, sub2)
        self.assert_not_equal(sub1, sub3)
        self.assert_not_equal(sub1, sub4)
        self.assert_equal(sub1, sub5)
        self.assert_not_equal(sub1, project1)
