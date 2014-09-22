import pytest

from everest.repositories.rdb.testing import check_attributes
from everest.repositories.rdb.testing import persist
from thelma.models.job import JOB_TYPES
from thelma.models.job import Job
from thelma.tests.entity.conftest import TestEntityBase


class TestJobEntity(TestEntityBase):
    def test_init_abstract(self):
        with pytest.raises(NotImplementedError):
            Job('test job', None)

    @pytest.mark.parametrize('job_fac_name,job_type',
                             [('iso_job_fac', JOB_TYPES.ISO),
                              ('experiment_job_fac', JOB_TYPES.EXPERIMENT)
                              ])
    def test_init(self, request, job_fac_name, job_type):
        job_fac = request.getfuncargvalue(job_fac_name)
        job = job_fac()
        check_attributes(job, job_fac.init_kw)
        assert job.job_type == job_type

    @pytest.mark.parametrize('job_fac_name',
                             ['iso_job_fac',
                              'experiment_job_fac'
                              ])
    def test_persist(self, request, nested_session, job_fac_name):
        job_fac = request.getfuncargvalue(job_fac_name)
        job = job_fac()
        persist(nested_session, job, job_fac.init_kw, True)


class TestIsoJobEntity(TestEntityBase):

    def test_iso_request_property(self, iso_job_fac, lab_iso_request_fac,
                                  rack_layout_fac, lab_iso_fac):
        job = iso_job_fac()
        lir2 = lab_iso_request_fac(id=-2, rack_layout=rack_layout_fac.new())
        li2 = lab_iso_fac(label='test iso 2',
                          rack_layout=rack_layout_fac.new(),
                          iso_request=lir2)
        job.isos.append(li2)
        with pytest.raises(ValueError):
            getattr(job, 'iso_request')

    def test_persist_all_attributes(self, nested_session, iso_job_fac,
                                    iso_job_stock_rack_fac,
                                    iso_job_preparation_plate_fac):
        ij = iso_job_fac()
        kw = iso_job_fac.init_kw
        ijsr = iso_job_stock_rack_fac(iso_job=ij)
        assert len(ij.iso_job_stock_racks) == 1
        kw['iso_job_stock_racks'] = [ijsr]
        ijpp = iso_job_preparation_plate_fac(iso_job=ij)
        assert len(ij.iso_job_preparation_plates) == 1
        kw['iso_job_preparation_plates'] = [ijpp]
        persist(nested_session, ij, kw, True)
