"""
Liquid transfer model tests.

AAB
"""

from everest.testing import RdbContextManager
from everest.testing import check_attributes
from everest.testing import persist
from everest.utils import id_generator
from thelma.interfaces import IPlate
from thelma.interfaces import IRackPosition
from thelma.interfaces import IRackShape
from thelma.interfaces import IReservoirSpecs
from thelma.interfaces import ITube
from thelma.interfaces import ITubeRack
from thelma.interfaces import IUser
from thelma.interfaces import IWell
from thelma.models.liquidtransfer import ExecutedContainerDilution
from thelma.models.liquidtransfer import ExecutedContainerTransfer
from thelma.models.liquidtransfer import ExecutedRackTransfer
from thelma.models.liquidtransfer import ExecutedTransfer
from thelma.models.liquidtransfer import ExecutedWorklist
from thelma.models.liquidtransfer import PlannedContainerDilution
from thelma.models.liquidtransfer import PlannedContainerTransfer
from thelma.models.liquidtransfer import PlannedRackTransfer
from thelma.models.liquidtransfer import PlannedTransfer
from thelma.models.liquidtransfer import PlannedWorklist
from thelma.models.liquidtransfer import ReservoirSpecs
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.liquidtransfer import WorklistSeries
from thelma.models.liquidtransfer import WorklistSeriesMember
from thelma.testing import ThelmaModelTestCase
from thelma.models.rack import RackPosition


class PlannedLiquidTransferModelTest(ThelmaModelTestCase):

    def test_init(self):
        self.assert_raises(NotImplementedError, PlannedTransfer, 0.000100)


class PlannedContainerDilutionModelTest(ThelmaModelTestCase):

    model_class = PlannedContainerDilution
    id_gen = id_generator()

    def __get_data(self):
        volume = 0.000100
        target_position = self._get_entity(IRackPosition)
        diluent_info = 'buffer1'
        return dict(volume=volume, target_position=target_position,
                    diluent_info=diluent_info)

    def test_init(self):
        attrs = self.__get_data()
        pcd = self._create_planned_container_dilution(**attrs)
        self.assert_is_not_none(attrs)
        check_attributes(pcd, attrs)
        self.assert_equal(pcd.type, TRANSFER_TYPES.CONTAINER_DILUTION)
        self.assert_equal(len(pcd.executed_transfers), 0)
        self._create_executed_container_dilution(
                                                planned_container_dilution=pcd)
        self.assert_equal(len(pcd.executed_transfers), 1)

    def test_equality(self):
        id1 = self.id_gen.next()
        id2 = self.id_gen.next()
        pcd1 = self._create_planned_container_dilution(id=id1)
        pcd2 = self._create_planned_container_dilution(id=id1)
        pcd3 = self._create_planned_container_dilution(id=id2)
        self.assert_equal(pcd1, pcd2)
        self.assert_not_equal(pcd1, pcd3)
        self.assert_not_equal(pcd1, id1)

    def test_persist(self):
        with RdbContextManager() as session:
            attrs = self.__get_data()
            persist(session, self.model_class, attrs, True)


class PlannedContainerTransferModelTest(ThelmaModelTestCase):

    model_class = PlannedContainerTransfer
    id_gen = id_generator()

    def __get_data(self):
        volume = 0.000100
        source_position = RackPosition.from_label('A1')
        target_position = RackPosition.from_label('B2')
        return dict(volume=volume, source_position=source_position,
                    target_position=target_position)

    def test_init(self):
        attrs = self.__get_data()
        pct = self._create_planned_container_transfer(**attrs)
        self.assert_is_not_none(pct)
        check_attributes(pct, attrs)
        self.assert_equal(pct.type, TRANSFER_TYPES.CONTAINER_TRANSFER)
        self.assert_equal(len(pct.executed_transfers), 0)
        self._create_executed_container_transfer(planned_container_transfer=pct)
        self.assert_equal(len(pct.executed_transfers), 1)

    def test_equality(self):
        id1 = self.id_gen.next()
        id2 = self.id_gen.next()
        pct1 = self._create_planned_container_transfer(id=id1)
        pct2 = self._create_planned_container_transfer(id=id1)
        pct3 = self._create_planned_container_transfer(id=id2)
        self.assert_equal(pct1, pct2)
        self.assert_not_equal(pct1, pct3)
        self.assert_not_equal(pct1, id1)

    def test_persist(self):
        with RdbContextManager() as session:
            attrs = self.__get_data()
            persist(session, self.model_class, attrs, True)


class PlannedRackTransferModelTest(ThelmaModelTestCase):

    model_class = PlannedRackTransfer
    id_gen = id_generator()

    def __get_data(self):
        volume = 0.00020
        source_sector_index = 1
        target_sector_index = 2
        sector_number = 4
        return dict(volume=volume, source_sector_index=source_sector_index,
                    target_sector_index=target_sector_index,
                    sector_number=sector_number)

    def test_init(self):
        attrs = self.__get_data()
        prt = self._create_planned_rack_transfer(**attrs)
        self.assert_is_not_none(prt)
        check_attributes(prt, attrs)
        self.assert_equal(prt.type, TRANSFER_TYPES.RACK_TRANSFER)
        self.assert_equal(len(prt.executed_transfers), 0)
        self._create_executed_rack_transfer(planned_rack_transfer=prt)
        self.assert_equal(len(prt.executed_transfers), 1)

    def test_equality(self):
        id1 = self.id_gen.next()
        id2 = self.id_gen.next()
        prt1 = self._create_planned_rack_transfer(id=id1)
        prt2 = self._create_planned_rack_transfer(id=id1)
        prt3 = self._create_planned_rack_transfer(id=id2)
        self.assert_equal(prt1, prt2)
        self.assert_not_equal(prt1, prt3)
        self.assert_not_equal(prt1, id1)

    def test_persist(self):
        with RdbContextManager() as session:
            attrs = self.__get_data()
            persist(session, self.model_class, attrs, True)


class PlannedWorklistModelTest(ThelmaModelTestCase):

    model_class = PlannedWorklist
    id_gen = id_generator()

    def __get_data(self):
        label = 'PlannedWorklistTestLabel'
        planned_transfer = self._create_planned_container_dilution()
        return dict(label=label, planned_transfers=[planned_transfer])

    def test_init(self):
        attrs = self.__get_data()
        pw = self._create_planned_worklist(**attrs)
        self.assert_is_not_none(pw)
        check_attributes(pw, attrs)
        self.assert_equal(len(pw.executed_worklists), 0)
        self.assert_is_none(pw.worklist_series)
        self.assert_is_none(pw.index)

    def test_equality(self):
        id1 = self.id_gen.next()
        id2 = self.id_gen.next()
        pw1 = self._create_planned_worklist(id=id1)
        pw2 = self._create_planned_worklist(id=id1)
        pw3 = self._create_planned_worklist(id=id2)
        self.assert_equal(pw1, pw2)
        self.assert_not_equal(pw1, pw3)
        self.assert_not_equal(pw1, id1)

    def test_persist(self):
        with RdbContextManager() as session:
            attrs = self.__get_data()
            persist(session, self.model_class, attrs, True)

    def test_persist_all_attributes(self):
        with RdbContextManager() as session:
            attrs = self.__get_data()
            pw = self._create_planned_worklist(**attrs)
            wsm = self._create_worklist_series_member(planned_worklist=pw)
            self.assert_is_not_none(pw.worklist_series)
            self.assert_is_not_none(pw.index)
            ew = self._create_executed_worklist(planned_worklist=pw)
            self.assert_equal(len(pw.executed_worklists), 1)
            session.add(pw)
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


class WorklistSeriesModelTest(ThelmaModelTestCase):

    model_class = WorklistSeries
    id_gen = id_generator()

    def test_init(self):
        ws = self._create_worklist_series()
        self.assert_equal(len(ws.planned_worklists), 0)
        self._create_worklist_series_member(worklist_series=ws)
        self.assert_equal(len(ws.planned_worklists), 1)

    def test_equality(self):
        id1 = self.id_gen.next()
        id2 = self.id_gen.next()
        ws1 = self._create_worklist_series(id=id1)
        ws2 = self._create_worklist_series(id=id1)
        ws3 = self._create_worklist_series(id=id2)
        self.assert_equal(ws1, ws2)
        self.assert_not_equal(ws1, ws3)
        self.assert_not_equal(ws1, id1)

    def test_persist(self):
        with RdbContextManager() as session:
            ws = self._create_worklist_series()
            wsm = self._create_worklist_series_member(worklist_series=ws)
            session.add(ws)
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


class WorklistSeriesMemberModelTest(ThelmaModelTestCase):

    model_class = WorklistSeriesMember
    id_gen = id_generator()

    def __get_data(self):
        worklist_series = self._create_worklist_series()
        planned_worklist = self._create_planned_worklist()
        ws_index = 2
        return dict(worklist_series=worklist_series, index=ws_index,
                    planned_worklist=planned_worklist)

    def test_init(self):
        attrs = self.__get_data()
        wsm = self._create_worklist_series_member(**attrs)
        self.assert_is_not_none(wsm)
        check_attributes(wsm, attrs)

    def test_equality(self):
        planned_worklist1 = self._create_planned_worklist(id=self.id_gen.next())
        planned_worklist2 = self._create_planned_worklist(id=self.id_gen.next())
        ws = self._create_worklist_series(id=self.id_gen.next())
        wsm1 = self._create_worklist_series_member(index=0,
                                    worklist_series=ws,
                                    planned_worklist=planned_worklist1)
        wsm2 = self._create_worklist_series_member(index=0,
                                    worklist_series=ws,
                                    planned_worklist=planned_worklist2)
        self.assert_equal(wsm1, wsm1)
        self.assert_not_equal(wsm1, wsm2)
        self.assert_not_equal(wsm1, ws)

    def test_persist(self):
        with RdbContextManager() as session:
            attrs = self.__get_data()
            wsm = self._create_worklist_series_member(**attrs)
            session.add(wsm)
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


class ReservoirSpecsModelTest(ThelmaModelTestCase):

    model_class = ReservoirSpecs

    def __get_data(self):
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
        attrs = self.__get_data()
        rs = self._create_reservoir_specs(**attrs)
        self.assert_is_not_none(rs)
        check_attributes(rs, attrs)

    def test_slug(self):
        attrs = self.__get_data()
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

    def test_persist(self):
        with RdbContextManager() as session:
            attrs = self.__get_data()
            persist(session, self.model_class, attrs, True)


class ExecutedTransferModelTest(ThelmaModelTestCase):

    def test_init(self):
        attrs = dict(planned_transfer=self._create_planned_container_dilution(),
                     user=self._get_entity(IUser, 'it'))
        self.assert_raises(NotImplementedError, ExecutedTransfer, **attrs)


class ExecutedContainerDilutionModelTest(ThelmaModelTestCase):

    model_class = ExecutedContainerDilution
    id_gen = id_generator()

    def __get_data(self):
        planned_container_dilution = self._create_planned_container_dilution()
        reservoir_specs = self._get_entity(IReservoirSpecs)
        target_container = self._get_entity(ITube)
        user = self._get_entity(IUser, 'it')
        return dict(target_container=target_container, user=user,
                    reservoir_specs=reservoir_specs,
                    planned_container_dilution=planned_container_dilution)

    def test_init(self):
        attrs = self.__get_data()
        ecd = self._create_executed_container_dilution(**attrs)
        self.assert_is_not_none(ecd)
        check_attributes(ecd, attrs)
        self.assert_equal(ecd.type, TRANSFER_TYPES.CONTAINER_DILUTION)
        attrs['planned_container_dilution'] = \
                                    self._create_planned_rack_transfer()
        self.assert_raises(ValueError,
                           self._create_executed_container_dilution, **attrs)

    def test_equality(self):
        id1 = self.id_gen.next()
        id2 = self.id_gen.next()
        ecd1 = self._create_executed_container_dilution(id=id1)
        ecd2 = self._create_executed_container_dilution(id=id1)
        ecd3 = self._create_executed_container_dilution(id=id2)
        self.assert_equal(ecd1, ecd2)
        self.assert_not_equal(ecd1, ecd3)
        self.assert_not_equal(ecd1, id1)

    def test_persist(self):
        with RdbContextManager() as session:
            attrs = self.__get_data()
            persist(session, self.model_class, attrs, True)


class ExecutedContainerTransferModelTest(ThelmaModelTestCase):

    model_class = ExecutedContainerTransfer
    id_gen = id_generator()

    def __get_data(self):
        source_container = self._get_entity(ITube)
        target_container = self._get_entity(IWell)
        user = self._get_entity(IUser, 'it')
        planned_container_transfer = self._create_planned_container_transfer()
        return dict(source_container=source_container,
                    target_container=target_container,
                    user=user,
                    planned_container_transfer=planned_container_transfer)

    def test_init(self):
        attrs = self.__get_data()
        ect = self._create_executed_container_transfer(**attrs)
        self.assert_is_not_none(ect)
        check_attributes(ect, attrs)
        self.assert_equal(ect.type, TRANSFER_TYPES.CONTAINER_TRANSFER)
        attrs['planned_container_transfer'] = \
                                    self._create_planned_container_dilution()
        self.assert_raises(ValueError, self._create_executed_container_transfer,
                           **attrs)

    def test_equality(self):
        id1 = self.id_gen.next()
        id2 = self.id_gen.next()
        ect1 = self._create_executed_container_transfer(id=id1)
        ect2 = self._create_executed_container_transfer(id=id1)
        ect3 = self._create_executed_container_transfer(id=id2)
        self.assert_equal(ect1, ect2)
        self.assert_not_equal(ect1, ect3)
        self.assert_not_equal(ect1, id1)

    def test_persist(self):
        with RdbContextManager() as session:
            attrs = self.__get_data()
            persist(session, self.model_class, attrs, True)


class ExecutedRackTransferModelTest(ThelmaModelTestCase):

    model_class = ExecutedRackTransfer
    id_gen = id_generator()

    def __get_data(self):
        source_rack = self._get_entity(ITubeRack)
        target_rack = self._get_entity(IPlate)
        planned_rack_transfer = self._create_planned_rack_transfer()
        user = self._get_entity(IUser, 'it')
        return dict(source_rack=source_rack, target_rack=target_rack,
                    user=user, planned_rack_transfer=planned_rack_transfer)

    def test_init(self):
        attrs = self.__get_data()
        ert = self._create_executed_rack_transfer(**attrs)
        self.assert_is_not_none(ert)
        check_attributes(ert, attrs)
        self.assert_equal(ert.type, TRANSFER_TYPES.RACK_TRANSFER)
        attrs['planned_rack_transfer'] = \
                                    self._create_planned_container_transfer()
        self.assert_raises(ValueError, self._create_executed_rack_transfer,
                           **attrs)

    def test_equality(self):
        id1 = self.id_gen.next()
        id2 = self.id_gen.next()
        ert1 = self._create_executed_rack_transfer(id=id1)
        ert2 = self._create_executed_rack_transfer(id=id1)
        ert3 = self._create_executed_rack_transfer(id=id2)
        self.assert_equal(ert1, ert2)
        self.assert_not_equal(ert1, ert3)
        self.assert_not_equal(ert1, id1)

    def test_persist(self):
        with RdbContextManager() as session:
            attrs = self.__get_data()
            persist(session, self.model_class, attrs, True)


class ExecutedWorklistModelTest(ThelmaModelTestCase):

    model_class = ExecutedWorklist
    id_gen = id_generator()

    def __get_data(self):
        planned_worklist = self._create_planned_worklist()
        executed_transfer = self._create_executed_container_dilution()
        return dict(planned_worklist=planned_worklist,
                    executed_transfers=[executed_transfer])

    def test_init(self):
        attrs = self.__get_data()
        ew = self._create_executed_worklist(**attrs)
        self.assert_is_not_none(ew)
        check_attributes(ew, attrs)

    def test_equality(self):
        id1 = self.id_gen.next()
        id2 = self.id_gen.next()
        ew1 = self._create_executed_worklist(id=id1)
        ew2 = self._create_executed_worklist(id=id1)
        ew3 = self._create_executed_worklist(id=id2)
        self.assert_equal(ew1, ew2)
        self.assert_not_equal(ew1, ew3)
        self.assert_not_equal(ew1, id1)

    def test_persist(self):
        with RdbContextManager() as session:
            attrs = self.__get_data()
            persist(session, self.model_class, attrs, True)

