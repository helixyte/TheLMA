'''
Created on Jun 22, 2011

@author: berger
'''

from everest.entities.utils import get_root_aggregate
from everest.testing import RdbContextManager
from everest.testing import check_attributes
from everest.testing import persist
from everest.utils import id_generator
from thelma.interfaces import IJobType
from thelma.interfaces import ISubproject
from thelma.interfaces import ITubeRack
from thelma.interfaces import IUser
from thelma.models.job import ExperimentJob
from thelma.models.job import IsoJob
from thelma.models.job import JOB_STATUS_TYPES
from thelma.models.job import JOB_TYPES
from thelma.models.job import JobType
from thelma.models.job import OtherJob
from thelma.testing import ThelmaModelTestCase


class JobTypeModelTest(ThelmaModelTestCase):

    model_class = JobType

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.name = 'RNAI_EXPERIMENT'
        self.label = 'RNAi Experiment'

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.name
        del self.label

    def test_load_2_job_types(self):
        with RdbContextManager() as session:
            query = session.query(self.model_class)
            job_types = query.limit(2).all()
            self.assert_equal(len(job_types), 2)

    def test_job_type_values(self):
        with RdbContextManager() as session:
            jt = session.query(self.model_class).filter_by(id=1).one()
            attributes = dict(id=1,
                              name='CHERRYPICKING',
                              label='Cherrypicking',
                              slug='cherrypicking')
            check_attributes(jt, attributes)

    def test_job_type_init(self):
        jt = JobType(self.name, self.label, '<xml></xml>')
        self.assert_not_equal(jt, None)
        self.assert_not_equal(jt.slug, None)
        attributes = dict(name=self.name, label=self.label)
        check_attributes(jt, attributes)

    def test_job_type_equality(self):
        jt1 = JobType(self.name, self.label, '<xml></xml>')
        jt2 = JobType(self.name, self.label, '<xml></xml>')
        jt3 = JobType('other_name', self.label, '<xml></xml>')
        jt4 = JobType(self.name, 'label', '<xml></xml>')
        self.assert_equal(jt1, jt2)
        self.assert_not_equal(jt1, jt3)
        self.assert_equal(jt1, jt4)
        self.assert_not_equal(jt1, self.name)


class OtherJobModelTest(ThelmaModelTestCase):

    model_class = OtherJob
    id_gen = id_generator()

    def __get_data(self):
        label = 'OtherJob.Test.Label'
        description = 'more info'
        status = JOB_STATUS_TYPES.IN_PROGRESS
        job_type = self._get_entity(IJobType)
        subproject = self._get_entity(ISubproject)
        user = self._get_entity(IUser, 'it')
        return dict(label=label,
                    job_type=job_type,
                    user=user,
                    subproject=subproject,
                    description=description,
                    status=status)

    def test_init(self):
        attrs = self.__get_data()
        oj = self._create_other_job(**attrs)
        self.assert_is_not_none(oj)
        check_attributes(oj, attrs)
        self.assert_equal(oj.type, JOB_TYPES.OTHER)

    def test_equality(self):
        id1 = self.id_gen.next()
        id2 = self.id_gen.next()
        oj1 = self._create_other_job(id=id1)
        oj2 = self._create_other_job(id=id1)
        oj3 = self._create_other_job(id=id2)
        self.assert_equal(oj1, oj2)
        self.assert_not_equal(oj1, oj3)
        self.assert_not_equal(oj1, id1)

    def test_persist(self):
        with RdbContextManager() as session:
            attrs = self.__get_data()
            persist(session, self.model_class, attrs, True)

    def test_load(self):
        with RdbContextManager() as session:
            query = session.query(self.model_class)
            ojs = query.limit(10).all()
            self.assert_equal(len(ojs), 10)


class ExperimentJobTestCase(ThelmaModelTestCase):

    model_class = ExperimentJob
    id_gen = id_generator()

    def __get_data(self):
        experiment = self._create_experiment()
        label = 'ExperimentJobTestLabel'
        return dict(label=label, experiments=[experiment])

    def test_init(self):
        attrs = self.__get_data()
        ej = self._create_experiment_job(**attrs)
        self.assert_is_not_none(ej)
        check_attributes(ej, attrs)
        self.assert_equal(ej.type, JOB_TYPES.RNAI_EXPERIMENT)
        jt_agg = get_root_aggregate(IJobType)
        jt = jt_agg.get_by_id('11')
        self.assert_equal(ej.job_type, jt)
        attrs['experiments'] = None
        self.assert_raises(ValueError, self._create_experiment_job, **attrs)

    def test_equality(self):
        id1 = self.id_gen.next()
        id2 = self.id_gen.next()
        ej1 = self._create_experiment_job(id=id1)
        ej2 = self._create_experiment_job(id=id2)
        self.assert_not_equal(ej1, ej2)
        self.assert_not_equal(ej1, id1)

    def test_persist(self):
        with RdbContextManager() as session:
            attrs = self.__get_data()
            jt_agg = get_root_aggregate(IJobType)
            jt = jt_agg.get_by_id('11')
            attrs['job_type'] = jt
            attrs['user'] = self._get_entity(IUser, 'it')
            persist(session, self.model_class, attrs, True)

    def test_load(self):
        with RdbContextManager() as session:
            query = session.query(self.model_class)
            ojs = query.limit(5).all()
            self.assert_equal(len(ojs), 5)


class IsoJobTestCase(ThelmaModelTestCase):

    model_class = IsoJob
    id_gen = id_generator()

    def __get_data(self):
        label = 'IsoJobTestLabel'
        iso = self._create_iso()
        return dict(label=label, isos=[iso])

    def test_init(self):
        attrs = self.__get_data()
        ij = self._create_iso_job(**attrs)
        self.assert_is_not_none(ij)
        check_attributes(ij, attrs)
        self.assert_is_none(ij.iso_control_stock_rack)
        self.assert_is_not_none(ij.job_type)

    def test_equality(self):
        id1 = self.id_gen.next()
        id2 = self.id_gen.next()
        ij1 = self._create_iso_job(id=id1)
        ij2 = self._create_iso_job(id=id2)
        self.assert_not_equal(ij1, ij2)
        self.assert_not_equal(ij1, id1)

    def test_iso_request_property(self):
        attrs = self.__get_data()
        isos = attrs['isos']
        iso_request1 = isos[0].iso_request
        job = self._create_iso_job(**attrs)
        self.assert_equal(job.iso_request, iso_request1)
        id2 = self.id_gen.next()
        iso_request2 = self._create_iso_request(id=id2)
        iso2 = self._create_iso(iso_request=iso_request2)
        job.isos.append(iso2)
        self.assert_raises(ValueError, getattr, *(job, 'iso_request'))

    def test_persist(self):
        with RdbContextManager() as session:
            attrs = self.__get_data()
            jt_agg = get_root_aggregate(IJobType)
            jt = jt_agg.get_by_id(15)
            self.assert_is_not_none(jt)
            attrs['job_type'] = jt
            attrs['user'] = self._get_entity(IUser, 'it')
            persist(session, self.model_class, attrs, True)

    def test_persist_all_attributes(self):
        with RdbContextManager() as session:
            attrs = self.__get_data()
            jt_agg = get_root_aggregate(IJobType)
            jt = jt_agg.get_by_id(15)
            self.assert_is_not_none(jt)
            attrs['job_type'] = jt
            attrs['user'] = self._get_entity(IUser, 'it')
            ij = self._create_iso_job(**attrs)
            rack = self._get_entity(ITubeRack)
            self._create_iso_control_stock_rack(rack=rack, iso_job=ij)
            self.assert_is_not_none(ij.iso_control_stock_rack)
            session.add(ij)
            session.commit()
            session.refresh(ij)
            ij_id = ij.id
            session.expunge(ij)
            del ij
            query = session.query(self.model_class)
            fetched_ij = query.filter_by(id=ij_id).one()
            check_attributes(fetched_ij, attrs)
            self.assert_is_not_none(fetched_ij.iso_control_stock_rack)
            self.assert_equal(fetched_ij.iso_control_stock_rack.rack, rack)
