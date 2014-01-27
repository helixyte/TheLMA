'''
Created on Jun 22, 2011

@author: berger
'''

from everest.testing import RdbContextManager
from everest.testing import check_attributes
from thelma.interfaces import ITubeRack
from thelma.interfaces import IUser
from thelma.models.job import ExperimentJob
from thelma.models.job import IsoJob
from thelma.models.job import JOB_TYPES
from thelma.models.job import Job
from thelma.testing import ThelmaEntityTestCase
from thelma.interfaces import IPlate


class JobModelTestCase(ThelmaEntityTestCase):

    def _get_data(self):
        label = 'testjob'
        user = self._get_entity(IUser)
        return dict(user=user, label=label)


class JobBaseClassModelTestCase(JobModelTestCase):

    model_class = Job

    def test_init(self):
        self._test_init(abstract_class=True)


class ExperimentJobTestCase(JobModelTestCase):

    model_class = ExperimentJob

    def _get_data(self):
        kw = JobModelTestCase._get_data(self)
        kw['experiments'] = [self._create_experiment()]
        return kw

    def test_init(self):
        attrs = self._get_data()
        ej = self._test_init(attrs)
        self.assert_equal(ej.job_type, JOB_TYPES.EXPERIMENT)
        attrs['experiments'] = None
        self.assert_raises(ValueError, self._create_experiment_job, **attrs)
        attrs['experiments'] = []
        self.assert_raises(ValueError, self._create_experiment_job, **attrs)

    def test_equality(self):
        self._test_id_based_equality(self._create_experiment_job,
                                     self._create_iso_job)

#    # we cannot test the loading here because due to single table inheritance
#    # the query load all sorts of jobs (the casting works correct but not the
#    # filtering
#    def test_load(self):
#        self._test_load()

    def test_persist(self):
        self._test_persist()


class IsoJobTestCase(JobModelTestCase):

    model_class = IsoJob

    def _get_data(self):
        kw = JobModelTestCase._get_data(self)
        iso_request = self._create_lab_iso_request()
        kw['isos'] = [self._create_lab_iso(iso_request=iso_request)]
        kw['number_stock_racks'] = 3
        return kw

    def test_init(self):
        attrs = self._get_data()
        ij = self._test_init(attrs=attrs)
        self.assert_equal(len(ij.iso_job_stock_racks), 0)
        attrs['isos'] = None
        self.assert_raises(ValueError, self._create_iso_job, **attrs)
        attrs['isos'] = []
        self.assert_raises(ValueError, self._create_iso_job, **attrs)

    def test_equality(self):
        self._test_id_based_equality(self._create_iso_job,
                                     self._create_experiment_job)

    def test_iso_request_property(self):
        attrs = self._get_data()
        iso_request = attrs['isos'][0].iso_request
        iso_request.id = -1
        job = self._create_iso_job(**attrs)
        self.assert_equal(job.iso_request, iso_request)
        iso_request2 = self._create_lab_iso_request(id= -2)
        iso2 = self._create_lab_iso(iso_request=iso_request2)
        job.isos.append(iso2)
        self.assert_raises(ValueError, getattr, *(job, 'iso_request'))

#    # we cannot test the loading here because due to single table inheritance
#    # the query load all sorts of jobs (the casting works correct but not the
#    # filtering
#    def test_load(self):
#        self._test_load()

    def test_persist(self):
        self._test_persist()

    def test_persist_all_attributes(self):
        with RdbContextManager() as session:
            attrs = self._get_data()
            ij = self._create_iso_job(**attrs)
            rack = self._get_entity(ITubeRack)
            self._create_iso_job_stock_rack(rack=rack, iso_job=ij)
            plate = self._get_entity(IPlate)
            self._create_iso_job_preparation_plate(rack=plate, iso_job=ij)
            self.assert_not_equal(len(ij.iso_job_stock_racks), 0)
            session.add(ij)
            session.commit()
            session.refresh(ij)
            ij_id = ij.id
            session.expunge(ij)
            del ij
            query = session.query(self.model_class)
            fetched_ij = query.filter_by(id=ij_id).one()
            check_attributes(fetched_ij, attrs)
            self.assert_equal(len(fetched_ij.iso_job_stock_racks), 1)
            self.assert_equal(fetched_ij.iso_job_stock_racks[0].rack, rack)
            self.assert_equal(len(fetched_ij.iso_job_preparation_plates), 1)
            self.assert_equal(fetched_ij.iso_job_preparation_plates[0].rack,
                              plate)
