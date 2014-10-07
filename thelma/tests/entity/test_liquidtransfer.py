import md5

import pytest

from everest.entities.utils import slug_from_string
from everest.repositories.rdb.testing import check_attributes
from everest.repositories.rdb.testing import persist
from thelma.models.liquidtransfer import PlannedLiquidTransfer
from thelma.tests.entity.conftest import TestEntityBase


class TestPlannedLiquidTransferEntity(TestEntityBase):

    def test_init_abstract(self):
        with pytest.raises(NotImplementedError):
            PlannedLiquidTransfer(1e-5)

    @pytest.mark.parametrize('planned_liquid_transfer_fac_name,hash_value',
                             [('planned_sample_dilution_fac',
                               md5.md5('5;annealing buffer;1').hexdigest()),
                              ('planned_sample_transfer_fac',
                               md5.md5('5;1;1').hexdigest()),
                              ('planned_rack_sample_transfer_fac',
                               md5.md5('5;4;0;1').hexdigest()),
                              ])
    def test_init(self, request, planned_liquid_transfer_fac_name, hash_value):
        planned_liquid_transfer_fac = \
            request.getfuncargvalue(planned_liquid_transfer_fac_name)
        plt = planned_liquid_transfer_fac()
        check_attributes(plt, planned_liquid_transfer_fac.init_kw)
        assert plt.get_hash_value(**planned_liquid_transfer_fac.init_kw) \
                == hash_value

    @pytest.mark.parametrize('planned_liquid_transfer_fac_name',
                             ['planned_sample_dilution_fac',
                              'planned_sample_transfer_fac',
                              'planned_rack_sample_transfer_fac',
                              ])
    def test_persist(self, request, nested_session,
                     planned_liquid_transfer_fac_name):
        planned_liquid_transfer_fac = \
            request.getfuncargvalue(planned_liquid_transfer_fac_name)
        plt = planned_liquid_transfer_fac()
        persist(nested_session, plt, planned_liquid_transfer_fac.init_kw,
                True)


class TestPlannedWorklistEntity(TestEntityBase):

    def test_init(self, planned_worklist_fac):
        pwl = planned_worklist_fac()
        check_attributes(pwl, planned_worklist_fac.init_kw)
        assert len(pwl.executed_worklists) == 0
        assert pwl.worklist_series is None
        assert pwl.index is None

    def test_persist(self, nested_session, planned_worklist_fac):
        pwl = planned_worklist_fac()
        persist(nested_session, pwl, planned_worklist_fac.init_kw, True)

    def test_persist_all_attributes(self, nested_session,
                                    worklist_series_member_fac,
                                    executed_worklist_fac):
        wsm = worklist_series_member_fac()
        pwl = wsm.planned_worklist
        assert not pwl.worklist_series is None
        assert not pwl.index is None
        assert len(pwl.executed_worklists) == 0
        ewl = executed_worklist_fac(planned_worklist=pwl)
        assert ewl.planned_worklist is pwl
        assert len(pwl.executed_worklists) == 1
        attrs = dict(executed_worklists=pwl.executed_worklists,
                     index=pwl.index,
                     worklist_series=pwl.worklist_series)
        pwl_from_storage = persist(nested_session, pwl, attrs, True)
        assert pwl_from_storage.worklist_series_member == wsm
#        wsm_from_storage = persist(nested_session, wsm, attrs, True)
#        assert len(wsm_from_storage.planned_worklist.executed_worklists) == 1


class TestWorklistSeriesEntity(TestEntityBase):

    def test_init(self, worklist_series_fac, worklist_series_member_fac):
        ws = worklist_series_fac()
        assert len(ws.planned_worklists) == 0
        wsm = worklist_series_member_fac(worklist_series=ws)
        assert ws.planned_worklists == [wsm.planned_worklist]

    def test_persist(self, nested_session, worklist_series_fac,
                     planned_worklist_fac):
        ws = worklist_series_fac()
        pwl = planned_worklist_fac()
        ws.add_worklist(0, pwl)
        attrs = dict(planned_worklists=[pwl])
        persist(nested_session, ws, attrs, True)


class TestWorklistSeriesMemberEntity(TestEntityBase):

    def test_init(self, worklist_series_member_fac):
        wsm = worklist_series_member_fac()
        check_attributes(wsm, worklist_series_member_fac.init_kw)


class TestReservoirSpecsEntity(TestEntityBase):

    def test_init(self, reservoir_specs_fac):
        rs = reservoir_specs_fac()
        check_attributes(rs, reservoir_specs_fac.init_kw)
        assert rs.slug == slug_from_string(rs.name)

    def test_persist(self, nested_session, reservoir_specs_fac):
        rs = reservoir_specs_fac()
        persist(nested_session, rs, reservoir_specs_fac.init_kw, True)


class TestPipettingSpecsEntity(TestEntityBase):

    def test_init(self, pipetting_specs_fac):
        ps = pipetting_specs_fac()
        check_attributes(ps, pipetting_specs_fac.init_kw)

    def test_persist(self, nested_session, pipetting_specs_fac):
        ps = pipetting_specs_fac()
        persist(nested_session, ps, pipetting_specs_fac.init_kw, True)


class TestExecutedLiquidTransferEntity(TestEntityBase):

    @pytest.mark.parametrize('fac_name,key,planned_fac_name',
                             [('executed_sample_dilution_fac',
                               'planned_sample_dilution',
                               'planned_sample_transfer_fac'),
                              ('executed_sample_transfer_fac',
                               'planned_sample_transfer',
                               'planned_sample_dilution_fac'),
                              ('executed_rack_sample_transfer_fac',
                               'planned_rack_sample_transfer',
                               'planned_sample_transfer_fac')
                              ])
    def test_init(self, request, fac_name, key, planned_fac_name):
        fac = request.getfuncargvalue(fac_name)
        elt = fac()
        check_attributes(elt, fac.init_kw)
        kw = fac.init_kw
        pfac = request.getfuncargvalue(planned_fac_name)
        kw[key] = pfac()
        with pytest.raises(ValueError):
            fac(**kw)

    @pytest.mark.parametrize('fac_name',
                             ['executed_sample_dilution_fac',
                              'executed_sample_transfer_fac',
                              'executed_rack_sample_transfer_fac'])
    def test_persist(self, request, nested_session, fac_name):
        fac = request.getfuncargvalue(fac_name)
        elt = fac()
        persist(nested_session, elt, fac.init_kw, True)


class TestExecutedWorklistModelTest(TestEntityBase):

    def test_init(self, executed_worklist_fac):
        ewl = executed_worklist_fac()
        check_attributes(ewl, executed_worklist_fac.init_kw)

    def test_persist(self, nested_session, executed_worklist_fac):
        ewl = executed_worklist_fac()
        persist(nested_session, ewl, executed_worklist_fac.init_kw, True)

