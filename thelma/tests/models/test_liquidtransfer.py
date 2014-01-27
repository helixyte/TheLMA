"""
Liquid transfer model tests.

AAB
"""

from everest.repositories.rdb.testing import RdbContextManager
from everest.repositories.rdb.testing import check_attributes
from md5 import md5
from thelma.interfaces import IPipettingSpecs
from thelma.interfaces import IPlate
from thelma.interfaces import IRackPosition
from thelma.interfaces import IRackShape
from thelma.interfaces import IReservoirSpecs
from thelma.interfaces import ITube
from thelma.interfaces import ITubeRack
from thelma.interfaces import IUser
from thelma.interfaces import IWell
from thelma.models.liquidtransfer import ExecutedLiquidTransfer
from thelma.models.liquidtransfer import ExecutedRackSampleTransfer
from thelma.models.liquidtransfer import ExecutedSampleDilution
from thelma.models.liquidtransfer import ExecutedSampleTransfer
from thelma.models.liquidtransfer import ExecutedWorklist
from thelma.models.liquidtransfer import PipettingSpecs
from thelma.models.liquidtransfer import PlannedLiquidTransfer
from thelma.models.liquidtransfer import PlannedRackSampleTransfer
from thelma.models.liquidtransfer import PlannedSampleDilution
from thelma.models.liquidtransfer import PlannedSampleTransfer
from thelma.models.liquidtransfer import PlannedWorklist
from thelma.models.liquidtransfer import ReservoirSpecs
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.liquidtransfer import WorklistSeries
from thelma.models.liquidtransfer import WorklistSeriesMember
from thelma.models.rack import RackPosition
from thelma.testing import ThelmaEntityTestCase


class PlannedLiquidTransferModelTestCase(ThelmaEntityTestCase):

    def _get_data(self):
        return dict(volume=0.0001) # 100 ul

    def _test_get_hash_value(self):
        attrs = self._get_data()
        hash_value = attrs['hash_value']
        del attrs['hash_value']
        ent_hash = self.model_class.get_hash_value(**attrs)
        self.assert_equal(hash_value, ent_hash)

class PlannedLiquidTransferBaseModelTestCase(
                                        PlannedLiquidTransferModelTestCase):

    model_class = PlannedLiquidTransfer

    def test_init(self):
        self._test_init(abstract_class=True)


class PlannedSampleDilutionModelTest(PlannedLiquidTransferModelTestCase):

    model_class = PlannedSampleDilution

    def _get_data(self):
        kw = PlannedLiquidTransferModelTestCase._get_data(self)
        kw['target_position'] = self._get_entity(IRackPosition, 'a1')
        kw['diluent_info'] = 'buffer1'
        kw['hash_value'] = md5('100;buffer1;1').hexdigest()
        return kw

    def test_init(self):
        self._test_init()

    def test_get_hash_value(self):
        self._test_get_hash_value()

    def test_load(self):
        self._test_load()

    def test_persist(self):
        self._test_persist()


class PlannedSampleTransferModelTest(PlannedLiquidTransferModelTestCase):

    model_class = PlannedSampleTransfer

    def _get_data(self):
        kw = PlannedLiquidTransferModelTestCase._get_data(self)
        kw['source_position'] = RackPosition.from_label('a1')
        kw['target_position'] = RackPosition.from_label('b2')
        kw['hash_value'] = md5('100;1;50').hexdigest()
        return kw

    def test_init(self):
        self._test_init()

    def test_get_hash_value(self):
        self._test_get_hash_value()

    def test_load(self):
        self._test_load()

    def test_persist(self):
        self._test_persist()


class PlannedRackSampleTransferModelTest(PlannedLiquidTransferModelTestCase):

    model_class = PlannedRackSampleTransfer

    def _get_data(self):
        kw = PlannedLiquidTransferModelTestCase._get_data(self)
        kw['source_sector_index'] = 1
        kw['target_sector_index'] = 2
        kw['number_sectors'] = 4
        kw['hash_value'] = md5('100;4;1;2').hexdigest()
        return kw

    def test_init(self):
        self._test_init()

    def test_get_hash_value(self):
        self._test_get_hash_value()

    def test_load(self):
        self._test_load()

    def test_persist(self):
        self._test_persist()


class PlannedWorklistModelTest(ThelmaEntityTestCase):

    model_class = PlannedWorklist

    def _get_data(self):
        label = 'PlannedWorklistTestLabel'
        pst = self._create_planned_sample_dilution()
        transfer_type = TRANSFER_TYPES.SAMPLE_DILUTION
        pipetting_specs = self._get_entity(IPipettingSpecs)
        return dict(label=label, planned_liquid_transfers=[pst],
                    transfer_type=transfer_type,
                    pipetting_specs=pipetting_specs)

    def test_init(self):
        pw = self._test_init()
        self.assert_equal(len(pw.executed_worklists), 0)
        self.assert_is_none(pw.worklist_series)
        self.assert_is_none(pw.index)

    def test_equality(self):
        self._test_id_based_equality(self._create_planned_worklist,
                                     self._create_planned_sample_dilution)

    def test_load(self):
        self._test_load()

    def test_persist(self):
        self._test_persist()

    def test_persist_all_attributes(self):
        with RdbContextManager() as session:
            attrs = self._get_data()
            pw = self._create_planned_worklist(**attrs)
            wsm = self._create_worklist_series_member(planned_worklist=pw)
            self.assert_is_not_none(pw.worklist_series)
            self.assert_is_not_none(pw.index)
            ew = self._create_executed_worklist(planned_worklist=pw)
            self.assert_equal(len(pw.executed_worklists), 1)
            session.add(type(pw), pw)
            session.commit()
            session.refresh(pw)
            pw_id = pw.id
            session.expunge(pw)
            del pw
            query = session.query(self.model_class)
            fetched_pw = query.filter_by(id=pw_id).one()
            check_attributes(fetched_pw, attrs)
            self.assert_equal(fetched_pw.worklist_series, wsm.worklist_series)
            self.assert_equal(fetched_pw.executed_worklists[0], ew)
            self.assert_equal(fetched_pw.index, wsm.index)


class WorklistSeriesModelTest(ThelmaEntityTestCase):

    model_class = WorklistSeries

    def _get_data(self):
        return dict()

    def test_init(self):
        ws = self._test_init()
        self.assert_equal(len(ws.planned_worklists), 0)
        self._create_worklist_series_member(worklist_series=ws)
        self.assert_equal(len(ws.planned_worklists), 1)

    def test_equality(self):
        self._test_id_based_equality(self._create_worklist_series,
                                     self._create_planned_worklist)

    def test_load(self):
        self._test_load()

    def test_persist(self):
        with RdbContextManager() as session:
            ws = self._create_worklist_series()
            wsm = self._create_worklist_series_member(worklist_series=ws)
            session.add(type(ws), ws)
            session.commit()
            session.refresh(ws)
            ws_id = ws.id
            session.expunge(ws)
            del ws
            query = session.query(self.model_class)
            fetched_ws = query.filter_by(id=ws_id).one()
            self.assert_equal(len(fetched_ws.worklist_series_members), 1)
            self.assert_equal(fetched_ws.planned_worklists[0],
                              wsm.planned_worklist)


class WorklistSeriesMemberModelTest(ThelmaEntityTestCase):

    model_class = WorklistSeriesMember

    def _get_data(self):
        worklist_series = self._create_worklist_series()
        planned_worklist = self._create_planned_worklist()
        ws_index = 2
        return dict(worklist_series=worklist_series, index=ws_index,
                    planned_worklist=planned_worklist)

    def test_init(self):
        self._test_init()

    def test_equality(self):
        planned_worklist1 = self._create_planned_worklist(id=-1)
        planned_worklist2 = self._create_planned_worklist(id=-2)
        ws = self._create_worklist_series(id=-3)
        wsm1 = self._create_worklist_series_member(index=0,
                                    worklist_series=ws,
                                    planned_worklist=planned_worklist1)
        wsm2 = self._create_worklist_series_member(index=0,
                                    worklist_series=ws,
                                    planned_worklist=planned_worklist2)
        self.assert_equal(wsm1, wsm1)
        self.assert_not_equal(wsm1, wsm2)
        self.assert_not_equal(wsm1, ws)

    def test_load(self):
        self._test_load()

    def test_persist(self):
        with RdbContextManager() as session:
            attrs = self._get_data()
            wsm = self._create_worklist_series_member(**attrs)
            session.add(type(wsm), wsm)
            session.commit()
            session.refresh(wsm)
            planned_worklist_id = wsm.planned_worklist.id
            session.expunge(wsm)
            del wsm
            query = session.query(self.model_class)
            fetched_wsm = query.filter_by(
                                planned_worklist_id=planned_worklist_id).one()
            self.assert_is_not_none(fetched_wsm)
            check_attributes(fetched_wsm, attrs)


class ReservoirSpecsModelTest(ThelmaEntityTestCase):

    model_class = ReservoirSpecs

    def _get_data(self):
        name = 'test specs'
        description = 'some more information'
        rack_shape = self._get_entity(IRackShape)
        max_volume = 0.005000
        min_dead_volume = 0.000010
        max_dead_volume = 0.000020
        return dict(name=name, rack_shape=rack_shape, max_volume=max_volume,
                    description=description,
                    min_dead_volume=min_dead_volume,
                    max_dead_volume=max_dead_volume)

    def test_init(self):
        self._test_init()

    def test_slug(self):
        attrs = self._get_data()
        rs = self._create_reservoir_specs(**attrs)
        exp_slug = 'test-specs'
        self.assert_equal(rs.slug, exp_slug)

    def test_equality(self):
        name1 = 'name1'
        name2 = 'name2'
        rack_shape1 = self._get_entity(IRackShape, '8x12')
        rack_shape2 = self._get_entity(IRackShape, '16x24')
        max_vol1 = 0.000100
        max_vol2 = 0.000200
        min_dead_vol1 = 0.000010
        min_dead_vol2 = 0.000020
        max_dead_vol1 = 0.000020
        max_dead_vol2 = 0.000030
        rs1 = self._create_reservoir_specs(name=name1, rack_shape=rack_shape1,
                            max_volume=max_vol1, min_dead_volume=min_dead_vol1,
                            max_dead_volume=max_dead_vol1)
        rs2 = self._create_reservoir_specs(name=name1, rack_shape=rack_shape1,
                            max_volume=max_vol1, min_dead_volume=min_dead_vol1,
                            max_dead_volume=max_dead_vol1)
        rs3 = self._create_reservoir_specs(name=name2, rack_shape=rack_shape1,
                            max_volume=max_vol1, min_dead_volume=min_dead_vol1,
                            max_dead_volume=max_dead_vol1)
        rs4 = self._create_reservoir_specs(name=name1, rack_shape=rack_shape2,
                            max_volume=max_vol1, min_dead_volume=min_dead_vol1,
                            max_dead_volume=max_dead_vol1)
        rs5 = self._create_reservoir_specs(name=name1, rack_shape=rack_shape1,
                            max_volume=max_vol2, min_dead_volume=min_dead_vol1,
                            max_dead_volume=max_dead_vol1)
        rs6 = self._create_reservoir_specs(name=name1, rack_shape=rack_shape1,
                            max_volume=max_vol1, min_dead_volume=min_dead_vol2,
                            max_dead_volume=max_dead_vol1)
        rs7 = self._create_reservoir_specs(name=name1, rack_shape=rack_shape1,
                            max_volume=max_vol1, min_dead_volume=min_dead_vol1,
                            max_dead_volume=max_dead_vol2)
        self.assert_equal(rs1, rs2)
        self.assert_equal(rs1, rs3)
        self.assert_not_equal(rs1, rs4)
        self.assert_not_equal(rs1, rs5)
        self.assert_not_equal(rs1, rs6)
        self.assert_not_equal(rs1, rs7)
        self.assert_not_equal(rs1, name1)

    def test_load(self):
        self._test_load()

    def test_persist(self):
        self._test_persist()


class PipettingSpecsModelTestCase(ThelmaEntityTestCase):

    model_class = PipettingSpecs

    def _get_data(self):
        name = 'model_test'
        min_transfer_volume = 0.000001
        max_transfer_volume = 0.000100
        max_dilution_factor = 20
        has_dynamic_dead_volume = True
        is_sector_bound = True
        return dict(name=name, min_transfer_volume=min_transfer_volume,
                    max_transfer_volume=max_transfer_volume,
                    max_dilution_factor=max_dilution_factor,
                    has_dynamic_dead_volume=has_dynamic_dead_volume,
                    is_sector_bound=is_sector_bound)

    def test_init(self):
        self._test_init()

    def test_equality(self):
        name1 = 'specs1'
        name2 = 'specs2'
        min_tv1 = 0.000002
        min_tv2 = 0.000004
        ps1 = self._create_pipetting_specs(name=name1,
                                           min_transfer_volume=min_tv1)
        ps2 = self._create_pipetting_specs(name=name1,
                                           min_transfer_volume=min_tv1)
        ps3 = self._create_pipetting_specs(name=name2,
                                           min_transfer_volume=min_tv1)
        ps4 = self._create_pipetting_specs(name=name1,
                                           min_transfer_volume=min_tv2)
        self.assert_equal(ps1, ps2)
        self.assert_not_equal(ps1, ps3)
        self.assert_equal(ps1, ps4)
        self.assert_not_equal(ps1, ps1.name)

    def test_load(self):
        self._test_load()

    def test_persist(self):
        self._test_persist()


class ExecutedLiquidTransferModelTestCase(ThelmaEntityTestCase):

    def _get_data(self):
        return dict(user=self._get_entity(IUser, 'it'))


class ExecutedLiquidTransferBaseTestCase(ExecutedLiquidTransferModelTestCase):

    model_class = ExecutedLiquidTransfer

    def test_init(self):
        attrs = self._get_data()
        attrs['planned_liquid_transfer'] = \
                                        self._create_planned_sample_dilution()
        self._test_init(attrs, abstract_class=True)


class ExecutedSampleDilutionModelTest(ExecutedLiquidTransferModelTestCase):

    model_class = ExecutedSampleDilution

    def _get_data(self):
        kw = ExecutedLiquidTransferModelTestCase._get_data(self)
        kw['planned_sample_dilution'] = self._create_planned_sample_dilution()
        kw['reservoir_specs'] = self._get_entity(IReservoirSpecs)
        kw['target_container'] = self._get_entity(ITube)
        return kw

    def test_init(self):
        attrs = self._get_data()
        self._test_init(attrs)
        attrs['planned_sample_dilution'] = \
                                    self._create_planned_sample_transfer()
        self.assert_raises(ValueError, self._create_executed_sample_dilution,
                           **attrs)

    def test_equality(self):
        self._test_id_based_equality(self._create_executed_sample_dilution,
                                     self._create_executed_sample_transfer)

    def test_load(self):
        self._test_load()

    def test_persist(self):
        self._test_persist()


class ExecutedContainerTransferModelTest(ExecutedLiquidTransferModelTestCase):

    model_class = ExecutedSampleTransfer

    def _get_data(self):
        kw = ExecutedLiquidTransferModelTestCase._get_data(self)
        kw['source_container'] = self._get_entity(ITube)
        kw['target_container'] = self._get_entity(IWell)
        kw['planned_sample_transfer'] = self._create_planned_sample_transfer()
        return kw

    def test_init(self):
        attrs = self._get_data()
        self._test_init(attrs)
        attrs['planned_sample_transfer'] = \
                                    self._create_planned_sample_dilution()
        self.assert_raises(ValueError, self._create_executed_sample_transfer,
                           **attrs)

    def test_equality(self):
        self._test_id_based_equality(self._create_executed_sample_transfer,
                                     self._create_executed_sample_dilution)

    def test_load(self):
        self._test_load()

    def test_persist(self):
        self._test_persist()


class ExecutedRackTransferModelTest(ExecutedLiquidTransferModelTestCase):

    model_class = ExecutedRackSampleTransfer

    def _get_data(self):
        kw = ExecutedLiquidTransferModelTestCase._get_data(self)
        kw['source_rack'] = self._get_entity(ITubeRack)
        kw['target_rack'] = self._get_entity(IPlate)
        kw['planned_rack_sample_transfer'] = \
                                self._create_planned_rack_sample_transfer()
        return kw

    def test_init(self):
        attrs = self._get_data()
        self._test_init(attrs)
        attrs['planned_rack_sample_transfer'] = \
                                    self._create_planned_sample_transfer()
        self.assert_raises(ValueError,
                           self._create_executed_rack_sample_transfer, **attrs)

    def test_equality(self):
        self._test_id_based_equality(self._create_executed_rack_sample_transfer,
                                     self._create_executed_sample_transfer)

    def test_load(self):
        self._test_load()

    def test_persist(self):
        self._test_persist()


class ExecutedWorklistModelTest(ThelmaEntityTestCase):

    model_class = ExecutedWorklist

    def _get_data(self):
        planned_worklist = self._create_planned_worklist()
        elt = self._create_executed_sample_dilution()
        return dict(planned_worklist=planned_worklist,
                    executed_liquid_transfers=[elt])

    def test_init(self):
        self._test_init()

    def test_equality(self):
        self._test_id_based_equality(self._create_executed_worklist,
                                     self._create_planned_worklist)

    def test_load(self):
        self._test_load()

    def test_persist(self):
        self._test_persist()

