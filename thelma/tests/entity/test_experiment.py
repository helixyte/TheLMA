import pytest

from everest.repositories.rdb.testing import check_attributes
from everest.repositories.rdb.testing import persist
from thelma.tests.entity.conftest import TestEntityBase


class TestExperimentEntity(TestEntityBase):

    def test_init(self, experiment_fac):
        exp = experiment_fac()
        check_attributes(exp, experiment_fac.init_kw)
        assert len(exp.experiment_racks) == 0

    @pytest.mark.parametrize('kw1,kw2,result',
                             [(dict(id=-1), dict(id=-1), True),
                              (dict(id=-1), dict(id=-2), False)])
    def test_equality(self, experiment_fac, experiment_design_fac, plate_fac,
                      kw1, kw2, result):
        ed1 = experiment_design_fac(**kw1)
        ed2 = experiment_design_fac(**kw2)
        rack1 = plate_fac(**kw1)
        rack2 = plate_fac(**kw2)
        exp1 = experiment_fac(experiment_design=ed1, source_rack=rack1)
        exp2 = experiment_fac(experiment_design=ed2, source_rack=rack2)
        exp3 = experiment_fac(experiment_design=ed2, source_rack=rack1)
        exp4 = experiment_fac(experiment_design=ed1, source_rack=rack2)
        assert (exp1 == exp2) is result
        assert (exp1 == exp3) is result
        assert (exp1 == exp4) is result

    def test_persist(self, nested_session, experiment_fac,
                     experiment_job_fac):
        exp = experiment_fac()
        # FIXME: Working around the circular dependency of experiment and
        #        experiment job here.
        exp_job = experiment_job_fac(experiments=[exp])
        kw = experiment_fac.init_kw
        kw['job'] = exp.job
        exp.job = exp_job
        persist(nested_session, exp, kw, True)


class TestExperimentRackEntity(TestEntityBase):

    def test_init(self, experiment_rack_fac):
        exp_r = experiment_rack_fac()
        check_attributes(exp_r, experiment_rack_fac.init_kw)


class TestExperimentDesignEntity(TestEntityBase):

    def test_init(self, experiment_design_fac):
        exp_dsgn = experiment_design_fac()
        check_attributes(exp_dsgn, experiment_design_fac.init_kw)

    def test_persist(self, nested_session, experiment_design_fac):
        exp_design = experiment_design_fac()
        persist(nested_session, exp_design, experiment_design_fac.init_kw,
                True)


class TestExperimentDesignRackEntity(TestEntityBase):

    def test_init(self, experiment_design_rack_fac):
        exp_dr = experiment_design_rack_fac()
        check_attributes(exp_dr, experiment_design_rack_fac.init_kw)


class TestExperimentMetadataEntity(TestEntityBase):

    def test_init(self, experiment_metadata_fac):
        em = experiment_metadata_fac()
        check_attributes(em, experiment_metadata_fac.init_kw)

    @pytest.mark.parametrize('kw1,kw2,result',
                             [(dict(label='em1'), dict(label='em1'), True),
                              (dict(label='em1'), dict(label='em2'), False)])
    def test_equality(self, subproject_fac, experiment_metadata_fac,
                      kw1, kw2, result):
        sp1 = subproject_fac(**kw1)
        sp2 = subproject_fac(**kw2)
        em1 = experiment_metadata_fac(subproject=sp1, **kw1)
        em2 = experiment_metadata_fac(subproject=sp2, **kw2)
        assert (em1 == em2) is result

    def test_persist(self, nested_session, experiment_metadata_fac):
        exp_metadata = experiment_metadata_fac()
        persist(nested_session, exp_metadata, experiment_metadata_fac.init_kw,
                True)
