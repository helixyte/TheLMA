'''
Created on May 26, 2011

@author: berger
'''

from datetime import datetime
from everest.repositories.rdb.testing import RdbContextManager
from everest.repositories.rdb.testing import check_attributes
from everest.repositories.rdb.testing import persist
from thelma.interfaces import IUser
from thelma.models.organization import Organization
from thelma.models.project import Project
from thelma.models.subproject import Subproject
from thelma.models.user import User
from thelma.testing import ThelmaModelTestCase
import pytz


class ProjectModelTest(ThelmaModelTestCase):

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.label = 'project_label'
        self.subproject = self._create_subproject()
        self.leader = self._get_entity(IUser, 'it')
        self.customer = self._create_organization()

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.label
        del self.subproject
        del self.leader
        del self.customer

    def test_load_10_projects(self):
        with RdbContextManager() as session:
            query = session.query(Project)
            projects = query.limit(10).all()
            self.assert_equal(len(projects), 10)

    def test_create_project(self):
        with RdbContextManager() as session:
            leader = session.query(User).filter_by(username='It').one()
            customer = \
                    session.query(Organization).filter_by(name='Cenix').one()

            subproject = \
                    Subproject('supproject 1', datetime.now(pytz.utc), True)
            attrs = dict(label='db test project',
                         leader=leader,
                         customer=customer,
                         creation_date=datetime.now(pytz.utc),
                         subprojects=[subproject])
            persist(session, Project, attrs)

    def test_load_project_with_subprojects(self):
        with RdbContextManager() as session:
            query = session.query(Project)
            project = query.filter_by(label='Test').one()
            self.assert_equal(len(project.subprojects), 1)

    def test_project_init(self):
        project = Project(self.label, self.leader, self.customer,
                          creation_date=None, subprojects=[self.subproject])
        self.assert_not_equal(project, None)
        attributes = dict(label=self.label,
                          title=self.label,
                          customer=self.customer,
                          leader=self.leader)
        check_attributes(project, attributes)
        self.assert_true(project.id is None)
        self.assert_not_equal(project.creation_date, None)
        self.assert_not_equal(project.slug, None)

    def test_project_slug(self):
        label = 'Astra Project1'
        label_slug = 'astra-project1'
        project = Project(label, self.leader)
        self.assert_not_equal(project.slug, label)
        self.assert_equal(project.slug, label_slug)

    def test_project_equality(self):
        id1 = 1
        id2 = 2
        project1 = Project(self.label, self.leader)
        project1.id = id1
        project2 = Project(self.label, self.leader)
        project2.id = id2
        project3 = Project('other_label', self.leader)
        project3.id = id1
        other_leader = self._get_entity(IUser, 'it')
        other_leader.id = 4
        project4 = Project(self.label, other_leader)
        project4.id = id1
        self.assert_not_equal(project1, project2)
        self.assert_equal(project1, project3)
        self.assert_equal(project1, project4)
        self.assert_not_equal(project1, id1)
