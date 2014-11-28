"""
Tests for the helper classes in the lab ISO planner module. The tests
are separated from the actual builder test cases to simplify adjustment
of test cases.

This module only test less complex base function. More complex functions
are only test in the course of the ISO job generator testing since the
test setup would be rather complicated and basically redundant.

AAB
"""
from everest.repositories.rdb.testing import check_attributes
from thelma.tools.semiconstants import PIPETTING_SPECS_NAMES
from thelma.tools.semiconstants import RACK_SHAPE_NAMES
from thelma.tools.semiconstants import RACK_SPECS_NAMES
from thelma.tools.semiconstants import get_96_rack_shape
from thelma.tools.semiconstants import get_rack_position_from_indices
from thelma.tools.semiconstants import get_rack_position_from_label
from thelma.tools.semiconstants import get_reservoir_specs_standard_96
from thelma.tools.iso.lab.base import FinalLabIsoPosition
from thelma.tools.iso.lab.base import LabIsoPosition
from thelma.tools.iso.lab.base import LabIsoPrepLayout
from thelma.tools.iso.lab.base import LabIsoPrepPosition
from thelma.tools.iso.lab.planner import LabIsoBuilder
from thelma.tools.iso.lab.planner import LibraryIsoBuilder
from thelma.tools.iso.lab.planner import RackPositionContainer
from thelma.tools.iso.lab.planner import RackPositionPlateContainer
from thelma.tools.iso.lab.planner import SectorContainer
from thelma.tools.iso.lab.planner import SectorPlateContainer
from thelma.tools.iso.lab.planner import _LocationContainer
from thelma.tools.iso.lab.planner import _PlateContainer
from thelma.tools.iso.lab.planner import _PoolContainer
from thelma.tools.iso.lab.planner import get_transfer_volume
from thelma.tools.stock.tubepicking import TubeCandidate
from thelma.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.tools.utils.iso import IsoRequestLayout
from thelma.tools.utils.iso import IsoRequestPosition
from thelma.tools.utils.layouts import FIXED_POSITION_TYPE
from thelma.tools.utils.layouts import FLOATING_POSITION_TYPE
from thelma.tools.utils.layouts import TransferTarget
from thelma.interfaces import IPlannedSampleDilution
from thelma.entities.liquidtransfer import PlannedRackSampleTransfer
from thelma.entities.liquidtransfer import PlannedSampleTransfer
from thelma.oldtests.tools.tooltestingutils import ToolsAndUtilsTestCase


class LabIsoPlanningFunctionsTestCase(ToolsAndUtilsTestCase):

    def test_get_transfer_volume(self):
        v1 = get_transfer_volume(50, 10, 8)
        # df = 50/10 = 5, vol = target_vol / df = 8 / 5 = 1.6
        self.assert_equal(v1, 1.6)
        v2 = get_transfer_volume(50, 10, 8, dil_factor=8)
        self.assert_equal(v2, 1)
        kw = dict(source_conc=50, target_conc=100, target_vol=3)
        self._expect_error(ValueError, get_transfer_volume,
                        'A dilution factor must not be smaller than 1!', **kw)


class PoolContainerTestCase(ToolsAndUtilsTestCase):

    TEST_CLS = _PoolContainer

    def __get_init_data(self):
        return dict(pool=self._get_pool(205200),
                  position_type=FIXED_POSITION_TYPE,
                  stock_concentration=50000)

    def test_init(self):
        kw = self.__get_init_data()
        pc = self.TEST_CLS(**kw)
        self.assert_is_not_none(pc)
        check_attributes(pc, kw)
        self.assert_equal(len(pc.target_working_positions), 0)

    def test_equality(self):
        kw = self.__get_init_data()
        pc1 = self.TEST_CLS(**kw)
        pc2 = self.TEST_CLS(**kw)
        ori_pool = kw['pool']
        kw['pool'] = 'md_1'
        pc3 = self.TEST_CLS(**kw)
        kw['pool'] = ori_pool
        kw['position_type'] = FLOATING_POSITION_TYPE
        pc4 = self.TEST_CLS(**kw)
        kw['position_type'] = FIXED_POSITION_TYPE
        kw['stock_concentration'] = 10000
        pc5 = self.TEST_CLS(**kw)
        self.assert_equal(pc1, pc2)
        self.assert_not_equal(pc1, pc3)
        self.assert_equal(pc1, pc4)
        self.assert_equal(pc1, pc5)

    def test_add_target_working_position(self):
        kw = self.__get_init_data()
        pc = self.TEST_CLS(**kw)
        rack_pos = get_rack_position_from_label('a1')
        ir_pos = IsoRequestPosition(rack_position=rack_pos,
                        molecule_design_pool=pc.pool,
                        position_type=pc.position_type)
        self.assert_equal(len(pc.target_working_positions), 0)
        pc.add_target_working_position(ir_pos)
        self.assert_equal(pc.target_working_positions, [ir_pos])


class _LocationContainerTestCase(ToolsAndUtilsTestCase):

    TEST_CLS = _LocationContainer

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.TEST_CLS.reset_counter()
        self.volume = 20
        self.target_concentration = 2
        self.parent_concentration = 10
        self.is_final_container = False

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.volume
        del self.target_concentration
        del self.parent_concentration
        del self.is_final_container

    def _get_attrs(self):
        return dict(volume=self.volume,
                    target_concentration=self.target_concentration,
                    parent_concentration=self.parent_concentration,
                    is_final_container=self.is_final_container)

    def _init_container(self, attrs=None):
        if attrs is None: attrs = self._get_attrs()
        return self.TEST_CLS(**attrs)

    def _init_parent_container(self):
        attrs = self._get_attrs()
        attrs['target_concentration'] = self.parent_concentration
        attrs['parent_concentration'] = self.parent_concentration * 2
        return self._init_container(attrs)

    def _test_init(self):
        container = self._init_container()
        self.assert_is_not_none(container)
        self.assert_true(isinstance(container, self.TEST_CLS))
        self.assert_equal(container.final_volume, self.volume)
        self.assert_equal(container.target_concentration,
                          self.target_concentration)
        self.assert_equal(container.parent_concentration,
                          self.parent_concentration)
        self.assert_equal(container.is_final_container, self.is_final_container)
        self.assert_equal(container.allows_modification,
                          not self.is_final_container)
        self.assert_is_none(container.location)
        self.assert_equal(len(container.targets), 0)
        return container

    def _test_location(self, attr_name, attr_value):
        container = self._init_container()
        self.assert_is_none(container.location)
        self.assert_is_none(container.plate_marker)
        self.assert_true(container.allows_modification)
        pm = 'testplate'
        kw = dict(location=attr_value, plate_marker=pm)
        container.set_location(**kw)
        self.assert_equal(container.location, attr_value)
        self.assert_equal(getattr(container, attr_name), attr_value)
        self.assert_equal(container.plate_marker, pm)
        container.disable_modification()
        self.assert_false(container.allows_modification)
        exp_msg = 'The data of this container must not be altered!'
        self._expect_error(AttributeError, container.set_location, exp_msg,
                           **kw)

    def _test_get_planned_liquid_transfers(self, locations=None):
        if locations is None: locations = [1, 2, 3]
        attrs = self._get_attrs()
        lc1 = self._init_container(attrs)
        lc1.set_location(locations[0], 'p1')
        lc2 = self._init_container(attrs)
        lc2.set_location(locations[1], 'p1')
        attrs['volume'] = self.volume * 2
        lc3 = self._init_container(attrs)
        lc3.set_location(locations[2], 'p1')
        attrs['volume'] = self.volume * 3
        lc4 = self._init_container(attrs)
        lc4.set_location(locations[0], 'p2')
        lc2.set_parent_container(lc1) # transfer vol = 20 ul
        lc3.set_parent_container(lc1) # transfer vol = 40 ul
        lc4.set_parent_container(lc1) # transfer vol = 60 ul
        t1, t2, t3 = self._get_exp_liquid_transfers()
        exp_transfers = dict(p1=[t1, t2], p2=[t3])
        transfers = lc1.get_planned_liquid_transfers()
        self.assert_equal(len(transfers), len(exp_transfers))
        for plate_marker, transfer_list in exp_transfers.iteritems():
            self.assert_equal(sorted(transfer_list),
                              sorted(transfers[plate_marker]))

    def _get_exp_liquid_transfers(self):
        raise NotImplementedError


class _LocationContainerDummy(_LocationContainer):
    """
    Allows to test subclass-independent properties.
    """
    LOCATION_ATTR_NAME = 'my_location'
    _PIPETTING_SPECS_NAME = PIPETTING_SPECS_NAMES.BIOMEK
    _STOCK_PIPETTING_SPECS_NAME = PIPETTING_SPECS_NAMES.BIOMEKSTOCK
    _PLANNED_TRANSFER_CLS = PlannedRackSampleTransfer

    def __init__(self, **kw):
        _LocationContainer.__init__(self, **kw)
        self.my_location = None

    def _get_subclass_specific_keywords(self):
        return dict()

    def _get_planned_transfer_kw(self, child_container):
        return dict(source_sector_index=self.my_location,
                    target_sector_index=child_container.my_location,
                    number_sectors=5)


class LocationContainerUnspecificTestCase(_LocationContainerTestCase):

    TEST_CLS = _LocationContainerDummy

    def test_init(self):
        container = self._test_init()
        self.assert_is_none(container.my_location)
        self.assert_equal(container.temp_id, 1)
        container2 = self._init_container()
        self.assert_equal(container2.temp_id, 2)

    def test_equality(self):
        attrs = self._get_attrs()
        lc1 = self._init_container()
        self.assert_equal(lc1.temp_id, 1)
        lc2 = self._init_container()
        self.assert_equal(lc2.temp_id, 2)
        attrs['target_concentration'] = self.target_concentration * 2
        lc3 = self._init_container()
        self.assert_equal(lc3.temp_id, 3)
        # do not use not equal method since this is called __cmp__
        self.assert_true(lc1 == lc1)
        self.assert_false(lc1 == lc2)
        self.assert_false(lc1 == lc3)

    def test_allow_modification(self):
        lc = self._init_container()
        self.assert_false(lc.is_final_container)
        self.assert_true(lc.allows_modification)
        lc.disable_modification()
        self.assert_false(lc.is_final_container)
        self.assert_false(lc.allows_modification)

    def test_location(self):
        self._test_location('my_location', 'somewhere')

    def test_comparison(self):
        attrs = self._get_attrs()
        lc1 = self._init_container(attrs)
        lc1.my_location = 1
        lc2 = self._init_container(attrs)
        lc2.my_location = 2
        attrs['target_concentration'] = self.target_concentration * 2
        lc3 = self._init_container(attrs)
        lc3.my_location = 3
        attrs['target_concentration'] = self.target_concentration / 2
        lc4 = self._init_container(attrs)
        lc4.my_location = 4
        l = [lc1, lc2, lc3, lc4]
        exp_list = [lc4, lc1, lc2, lc3]
        self.assert_equal(sorted(l), exp_list)

    def test_parent_container(self):
        lc1 = self._init_container()
        lc2 = self._init_parent_container()
        self.assert_is_none(lc1.parent_container)
        self.assert_is_none(lc2.parent_container)
        lc1.set_parent_container(lc2)
        self.assert_equal(lc1.parent_container, lc2)
        self.assert_is_none(lc2.parent_container)

    def test_stock_values(self):
        lc1 = self._init_container()
        lc2 = self._init_parent_container()
        self.assert_true(lc1.from_stock)
        lc1.set_parent_container(lc2)
        self.assert_false(lc1.from_stock)
        self.assert_true(lc2.from_stock)
        self.assert_equal(lc1.stock_concentration, lc2.parent_concentration)
        self.assert_equal(lc2.stock_concentration, lc2.parent_concentration)

    def test_set_dead_volume(self):
        lc = self._init_container()
        self.assert_equal(lc.full_volume, self.volume)
        lc.set_dead_volume(10)
        self.assert_equal(lc.full_volume, (self.volume + 10))
        lc.disable_modification()
        self._expect_error(AttributeError, lc.set_dead_volume,
                'Adjusting the dead volume for this container is not allowed!',
                **dict(dead_volume=10))

    def test_full_volume(self):
        lc1 = self._init_container()
        lc2 = self._init_container()
        lc3 = self._init_container()
        self.assert_equal(lc1.full_volume, self.volume)
        lc1.targets[lc2] = 2
        self.assert_equal(lc1.full_volume, self.volume + 2)
        lc2.targets[lc3] = 4
        self.assert_equal(lc1.full_volume, self.volume + 2)
        lc4 = self._init_container()
        lc1.targets[lc4] = 3
        self.assert_equal(lc1.full_volume, self.volume + 5)

    def test_adjust_transfer_data(self):
        lc1 = self._init_container()
        lc2 = self._init_parent_container()
        transfer_vol = get_transfer_volume(
                        source_conc=lc2.target_concentration,
                        target_conc=lc1.target_concentration,
                        target_vol=self.volume)
        self.assert_true(transfer_vol > 2)
        self.assert_is_none(lc1.parent_container)
        self.assert_equal(lc2.full_volume, self.volume)
        lc1.set_parent_container(lc2)
        self.assert_equal(lc2.full_volume, (self.volume + transfer_vol))
        lc2.set_dead_volume(10)
        self.assert_equal(lc2.full_volume, (self.volume + transfer_vol + 10))

    def test_get_buffer_volume(self):
        lc1 = self._init_container()
        lc2 = self._init_parent_container()
        lc1.set_parent_container(lc2)
        # df = 5, vol = 20, transfer vol = 4
        self.assert_equal(lc1.get_buffer_volume(), 16)
        # df = 2, vol = 24 (20 + 4), transfer vol = 12
        self.assert_equal(lc2.get_buffer_volume(), 12)

    def test_get_ancestors(self):
        lc1 = self._init_container()
        lc2 = self._init_container()
        lc3 = self._init_container()
        lc4 = self._init_container()
        lc1.set_parent_container(lc2)
        lc2.set_parent_container(lc3)
        lc4.set_parent_container(lc3)
        anc1 = lc1.get_ancestors()
        self.assert_equal(anc1, [lc2, lc3])
        anc2 = lc2.get_ancestors()
        self.assert_equal(anc2, [lc3])
        anc3 = lc3.get_ancestors()
        self.assert_equal(anc3, [])

    def test_get_descendants(self):
        lc1 = self._init_container()
        lc1.my_location = 1
        lc2 = self._init_container()
        lc2.my_location = 2
        lc3 = self._init_container()
        lc4 = self._init_container()
        lc4.my_location = 4
        lc1.set_parent_container(lc2)
        lc2.set_parent_container(lc3)
        lc4.set_parent_container(lc3)
        self.assert_equal(lc1.get_descendants(), [])
        self.assert_equal(lc2.get_descendants(), [lc1])
        self.assert_equal(lc4.get_descendants(), [])
        self.assert_equal(lc3.get_descendants(), [lc4, lc2, lc1])

    def test_get_intraplate_ancestor_count(self):
        lc1 = self._init_container()
        lc1.set_location(1, 'p1')
        lc2 = self._init_container()
        lc2.set_location(2, 'p1')
        lc3 = self._init_container()
        lc3.set_location(3, 'p1')
        lc4 = self._init_container()
        lc4.set_location(4, 'p1')
        lc1.set_parent_container(lc2)
        lc2.set_parent_container(lc3)
        lc4.set_parent_container(lc3)
        self.assert_equal(lc1.get_intraplate_ancestor_count(), 2)
        self.assert_equal(lc2.get_intraplate_ancestor_count(), 1)
        self.assert_equal(lc3.get_intraplate_ancestor_count(), 0)
        self.assert_equal(lc4.get_intraplate_ancestor_count(), 1)
        lc3.plate_marker = 'p2'
        self.assert_equal(lc1.get_intraplate_ancestor_count(), 1)
        self.assert_equal(lc2.get_intraplate_ancestor_count(), 0)
        self.assert_equal(lc3.get_intraplate_ancestor_count(), 0)
        self.assert_equal(lc4.get_intraplate_ancestor_count(), 0)

    def test_create_final_plate_container(self):
        lc = self.TEST_CLS.create_final_plate_container(location=1,
                                volume=self.volume,
                                target_concentration=self.target_concentration,
                                parent_concentration=self.parent_concentration)
        self.assert_is_not_none(lc)
        self.assert_true(lc.is_final_container)
        self.assert_equal(lc.final_volume, self.volume)
        self.assert_equal(lc.target_concentration, self.target_concentration)
        self.assert_equal(lc.parent_concentration, self.parent_concentration)

    def test_create_prep_copy(self):
        lc1 = self._init_container()
        lc1.set_location(1, 'p1')
        lc2 = lc1.create_prep_copy(target_concentration=4, dead_volume=2)
        self.assert_is_not_none(lc2)
        self.assert_false(lc2.is_final_container)
        self.assert_equal(lc2.final_volume, 0)
        self.assert_equal(lc2.full_volume, 2)
        self.assert_equal(lc2.target_concentration, 4)
        self.assert_equal(lc2.parent_concentration, self.parent_concentration)
        self.assert_is_none(lc2.location)

    def test_clones(self):
        lc = self.TEST_CLS.create_final_plate_container(location=1,
                        volume=self.volume,
                        target_concentration=self.target_concentration,
                        parent_concentration=self.parent_concentration)
        lc.plate_marker = 'p1'
        lc_child = self._init_container()
        lc_child.set_parent_container(lc)
        clones = lc.get_clones(3)
        self.assert_equal(len(clones), 3)
        for i in range(len(clones)):
            clone = clones[i]
            self.assert_true(clone.is_final_container)
            self.assert_equal(clone.plate_marker, 'p1')
            if i == 0:
                self.assert_true(clone == lc)
                for child in clone.targets.keys():
                    self.assert_true(child == lc_child)
            else:
                self.assert_false(clone == lc)
                for child in clone.targets.keys():
                    self.assert_false(child == lc_child)
            self.assert_equal(len(clone.targets), 1)
            self.assert_equal(clone.final_volume, self.volume)
            self.assert_equal(clone.target_concentration,
                              self.target_concentration)
            self.assert_equal(clone.parent_concentration,
                              self.parent_concentration)
            self.assert_equal(clone.my_location, 1)

    def _get_exp_liquid_transfers(self):
        t1 = PlannedRackSampleTransfer.get_entity(
                                    20 / VOLUME_CONVERSION_FACTOR, 5, 1, 2)
        t2 = PlannedRackSampleTransfer.get_entity(
                                    40 / VOLUME_CONVERSION_FACTOR, 5, 1, 3)
        t3 = PlannedRackSampleTransfer.get_entity(
                                    60 / VOLUME_CONVERSION_FACTOR, 5, 1, 1)
        return t1, t2, t3

    def test_planned_transfers(self):
        self._test_get_planned_liquid_transfers()


class SectorContainerTestCase(_LocationContainerTestCase):

    TEST_CLS = SectorContainer

    def set_up(self):
        _LocationContainerTestCase.set_up(self)
        self.number_sectors = 4

    def tear_down(self):
        _LocationContainerTestCase.tear_down(self)
        del self.number_sectors

    def test_init(self):
        container = self._test_init()
        self.assert_is_none(container.sector_index)
        self.assert_is_none(container.number_sectors)

    def test_location(self):
        self._test_location('sector_index', 3)

    def test_create_aliquot_position(self):
        sc = self._init_container()
        sc.set_location(2, 'p1')
        pool = self._get_pool(205200)
        rack_pos = get_rack_position_from_label('a1')
        irp = IsoRequestPosition(rack_position=rack_pos,
                molecule_design_pool=pool,
                position_type=FIXED_POSITION_TYPE)
        tt = TransferTarget(rack_position=get_rack_position_from_label('b2'),
                            transfer_volume=7, target_rack_marker='a1')
        fpp = sc.create_aliquot_position(irp, [tt], True)
        exp_attrs = dict(rack_position=rack_pos,
                    molecule_design_pool=pool,
                    position_type=FIXED_POSITION_TYPE,
                    concentration=self.target_concentration,
                    volume=self.volume, from_job=True,
                    transfer_targets=[tt],
                    stock_tube_barcode=FinalLabIsoPosition.TEMP_STOCK_DATA,
                    stock_rack_marker=FinalLabIsoPosition.TEMP_STOCK_DATA,
                    sector_index=2)
        self.assert_true(isinstance(fpp, FinalLabIsoPosition))
        check_attributes(fpp, exp_attrs)

    def test_get_planned_liquid_transfers(self):
        locations = [1, 2, 3]
        attrs = self._get_attrs()
        lc1 = self._init_container(attrs)
        lc1.number_sectors = self.number_sectors
        lc1.set_location(locations[0], 'p1')
        lc2 = self._init_container(attrs)
        lc2.number_sectors = self.number_sectors
        lc2.set_location(locations[1], 'p1')
        attrs['volume'] = self.volume * 2
        lc3 = self._init_container(attrs)
        lc3.set_location(locations[2], 'p1')
        lc3.number_sectors = self.number_sectors
        attrs['volume'] = self.volume * 3
        lc4 = self._init_container(attrs)
        lc4.number_sectors = self.number_sectors
        lc4.set_location(locations[0], 'p2')
        lc2.set_parent_container(lc1) # transfer vol = 20 ul
        lc3.set_parent_container(lc1) # transfer vol = 40 ul
        lc4.set_parent_container(lc1) # transfer vol = 60 ul
        t1, t2, t3 = self._get_exp_liquid_transfers()
        exp_transfers = dict(p1=[t1, t2], p2=[t3])
        transfers = lc1.get_planned_liquid_transfers()
        self.assert_equal(len(transfers), len(exp_transfers))
        for plate_marker, transfer_list in exp_transfers.iteritems():
            self.assert_equal(sorted(transfer_list),
                              sorted(transfers[plate_marker]))

    def _get_exp_liquid_transfers(self):
        t1 = PlannedRackSampleTransfer.get_entity(
                20 / VOLUME_CONVERSION_FACTOR, self.number_sectors, 1, 2)
        t2 = PlannedRackSampleTransfer.get_entity(
                40 / VOLUME_CONVERSION_FACTOR, self.number_sectors, 1, 3)
        t3 = PlannedRackSampleTransfer.get_entity(
                60 / VOLUME_CONVERSION_FACTOR, self.number_sectors, 1, 1)
        return t1, t2, t3


class RackPositionContainerTestCase(_LocationContainerTestCase):

    TEST_CLS = RackPositionContainer

    def set_up(self):
        _LocationContainerTestCase.set_up(self)
        self.pool = self._get_pool(205200)
        self.position_type = FLOATING_POSITION_TYPE

    def tear_down(self):
        _LocationContainerTestCase.tear_down(self)
        del self.pool
        del self.position_type

    def _get_attrs(self):
        kw = _LocationContainerTestCase._get_attrs(self)
        kw['pool'] = self.pool
        kw['position_type'] = self.position_type
        return kw

    def test_init(self):
        container = self._test_init()
        self.assert_is_none(container.rack_position)

    def test_location(self):
        self._test_location('rack_position', get_rack_position_from_label('a1'))

    def test_from_iso_request_position(self):
        rack_pos = get_rack_position_from_label('a1')
        irp = IsoRequestPosition(rack_position=rack_pos,
            molecule_design_pool=self.pool,
            iso_concentration=self.target_concentration,
            iso_volume=self.volume)
        rpc = self.TEST_CLS.from_iso_request_position(irp,
                                                      stock_concentration=50000)
        self.assert_true(isinstance(rpc, self.TEST_CLS))
        exp_attrs = dict(final_volume=self.volume,
                    parent_concentration=50000,
                    target_concentration=self.target_concentration,
                    is_final_container=True, location=rack_pos,
                    pool=self.pool, position_type=FIXED_POSITION_TYPE)
        check_attributes(rpc, exp_attrs)

    def test_from_lab_iso_position(self):
        rack_pos = get_rack_position_from_label('a1')
        lip = LabIsoPosition(rack_position=rack_pos,
                    molecule_design_pool=self.pool,
                    position_type=self.position_type,
                    concentration=self.target_concentration,
                    volume=self.volume)
        pool_container = _PoolContainer(pool=self._get_pool(205200),
                                        position_type=FIXED_POSITION_TYPE,
                                        stock_concentration=50000)
        pool_container.store_target_position_with_origin(lip, 'p#1')
        rpc = self.TEST_CLS.from_lab_iso_position(lip, pool_container)
        self.assert_true(isinstance(rpc, self.TEST_CLS))
        exp_attrs = dict(final_volume=self.volume,
                parent_concentration=50000,
                target_concentration=self.target_concentration,
                is_final_container=False, location=rack_pos,
                allows_modification=False, pool=self.pool,
                position_type=self.position_type,
                plate_marker='p#1')
        check_attributes(rpc, exp_attrs)

    def test_create_final_lab_iso_position(self):
        self.position_type = FIXED_POSITION_TYPE
        rcp = self._init_container()
        rack_pos = get_rack_position_from_label('a1')
        rcp.set_location(rack_pos, 'p1')
        tt = TransferTarget(rack_position=get_rack_position_from_label('b2'),
                            transfer_volume=7, target_rack_marker='a1')
        fpp = rcp.create_final_lab_iso_position([tt], True)
        exp_attrs = dict(rack_position=rack_pos, from_job=True,
                molecule_design_pool=self.pool,
                position_type=FIXED_POSITION_TYPE,
                concentration=self.target_concentration,
                volume=self.volume, transfer_targets=[tt],
                stock_tube_barcode=FinalLabIsoPosition.TEMP_STOCK_DATA,
                stock_rack_marker=FinalLabIsoPosition.TEMP_STOCK_DATA)
        self.assert_true(isinstance(fpp, FinalLabIsoPosition))
        check_attributes(fpp, exp_attrs)

    def test_preparation_position(self):
        pos_a1 = get_rack_position_from_label('a1')
        pos_b2 = get_rack_position_from_label('b2')
        pos_c3 = get_rack_position_from_label('c3')
        tt1 = TransferTarget(rack_position=pos_b2, transfer_volume=1,
                             target_rack_marker='p1')
        tt2 = TransferTarget(rack_position=pos_c3, transfer_volume=2,
                             target_rack_marker='a')
        rpc = self._init_container()
        rpc.set_location(pos_a1, 'p1')
        pp = rpc.create_preparation_position(preparation_targets=[tt1],
                                             final_targets=[tt2])
        exp_attrs = dict(rack_position=pos_a1, molecule_design_pool=self.pool,
                 position_type=self.position_type, volume=self.volume,
                 concentration=self.target_concentration,
                 transfer_targets=[tt1], external_targets=[tt2],
                 stock_tube_barcode=FinalLabIsoPosition.TEMP_STOCK_DATA,
                 stock_rack_marker=FinalLabIsoPosition.TEMP_STOCK_DATA)
        self.assert_true(isinstance(pp, LabIsoPrepPosition))
        check_attributes(pp, exp_attrs)

    def test_get_planned_liquid_transfers(self):
        rack_positions = (get_rack_position_from_label('b1'),
                          get_rack_position_from_label('b2'),
                          get_rack_position_from_label('b3'))
        self._test_get_planned_liquid_transfers(rack_positions)

    def _get_exp_liquid_transfers(self):
        pos_b1 = get_rack_position_from_label('b1')
        t1 = PlannedSampleTransfer.get_entity(
                volume=20 / VOLUME_CONVERSION_FACTOR,
                source_position=pos_b1,
                target_position=get_rack_position_from_label('b2'))
        t2 = PlannedSampleTransfer.get_entity(
                volume=40 / VOLUME_CONVERSION_FACTOR,
                source_position=pos_b1,
                target_position=get_rack_position_from_label('b3'))
        t3 = PlannedSampleTransfer.get_entity(
                volume=60 / VOLUME_CONVERSION_FACTOR,
                source_position=pos_b1, target_position=pos_b1)
        return t1, t2, t3


class _PlateContainerTestCase(ToolsAndUtilsTestCase):

    TEST_CLS = _PlateContainer

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.plate_marker = 'p1'
        self.available_locations = None

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.plate_marker
        del self.available_locations

    def _get_attrs(self):
        return dict(plate_marker=self.plate_marker,
                    available_locations=self.available_locations)

    def _init_plate_container(self, attrs=None):
        if attrs is None:
            attrs = self._get_attrs()
        return self.TEST_CLS(**attrs)

    def _test_init(self):
        attrs = self._get_attrs()
        pc = self._init_plate_container(attrs)
        self.assert_is_not_none(pc)
        self.assert_true(isinstance(pc, self.TEST_CLS))
        self.assert_equal(pc.plate_marker, self.plate_marker)
        self.assert_true(pc.has_empty_locations())
        self.assert_equal(sorted(pc.get_locations()),
                          sorted(self.available_locations))

    def _test_equality(self):
        attrs = self._get_attrs()
        pc1 = self._init_plate_container(attrs)
        pc2 = self._init_plate_container(attrs)
        attrs['plate_marker'] = 'other'
        pc3 = self._init_plate_container(attrs)
        self.assert_equal(pc1, pc2)
        self.assert_not_equal(pc1, pc3)
        self.assert_not_equal(pc1, self.plate_marker)


class _PlateContainerDummy(_PlateContainer):
    """
    Allows to test subclass-independent properties.
    """

    def _find_location(self, container, preferred_locations):
        if preferred_locations is None:
            preferred_locations = []
        for pc in preferred_locations:
            return pc
        for location in sorted(self._location_map):
            if self._location_map[location] is None:
                return location
        raise AttributeError('There is no empty locations left!')


class PlateContainerUnspecificTestCase(_PlateContainerTestCase):

    TEST_CLS = _PlateContainerDummy

    def set_up(self):
        _PlateContainerTestCase.set_up(self)
        self.available_locations = [1, 2, 3, 4]

    def test_init(self):
        self._test_init()

    def test_equality(self):
        self._test_equality()

    def __get_container(self):
        return _LocationContainerDummy(volume=10, parent_concentration=20,
                                       target_concentration=10)

    def test_location_assignment(self):
        pc = self._init_plate_container()
        self.assert_true(pc.has_empty_locations())
        for loc in self.available_locations:
            self.__check_empty_location(pc, loc)
        self.assert_equal(pc.get_containers(), [])
        c1 = self.__get_container()
        self.assert_is_none(c1.location)
        pc.set_container(c1, None)
        self.assert_true(pc.has_empty_locations())
        self.assert_equal(pc.get_containers(), [c1])
        self.__check_occupied_location(pc, 1, c1)
        for loc in self.available_locations[1:]:
            self.__check_empty_location(pc, loc)
        c3 = self.__get_container()
        self.assert_is_none(c3.location)
        self.assert_is_none(c3.plate_marker)
        pc.set_container(c3, [3])
        self.assert_true(pc.has_empty_locations())
        self.assert_equal(sorted(pc.get_containers()), [c1, c3])
        self.__check_occupied_location(pc, 1, c1)
        self.__check_occupied_location(pc, 3, c3)
        for loc in (2, 4):
            self.__check_empty_location(pc, loc)
        c2 = self.__get_container()
        self.assert_is_none(c2.location)
        self.assert_is_none(c2.plate_marker)
        self._expect_error(ValueError, pc.set_container,
                'Location "3" is already occupied!',
                **dict(container=c2, locations=[3]))
        pc.set_container(c2, None)
        c4 = self.__get_container()
        pc.set_container(c4, None)
        self.assert_false(pc.has_empty_locations())

    def __check_empty_location(self, pc, loc):
        self.assert_true(pc.is_empty_location(loc))
        self.assert_is_none(pc.get_container_for_location(loc))

    def __check_occupied_location(self, pc, loc, container):
        self.assert_equal(pc.get_container_for_location(loc), container)
        self.assert_equal(container.location, loc)
        self.assert_equal(container.plate_marker, self.plate_marker)


class SectorPlateContainerTestCase(_PlateContainerTestCase):

    TEST_CLS = SectorPlateContainer

    def set_up(self):
        _PlateContainerTestCase.set_up(self)
        self.available_locations = [0, 1]

    def test_init(self):
        self._test_init()

    def test_equality(self):
        self._test_equality()

    def __get_sector_container(self):
        sc = SectorContainer(volume=10, parent_concentration=20,
                               target_concentration=10)
        sc.number_sectors = 2
        return sc

    def test_location_assignment(self):
        spc = self._init_plate_container()
        self.assert_equal(spc.get_containers(), [])
        self.assert_is_none(spc.get_container_for_location(0))
        sc1 = self.__get_sector_container()
        spc.set_container(sc1, [])
        self.assert_equal(spc.get_containers(), [sc1])
        self.assert_equal(spc.get_container_for_location(0), sc1)
        sc2 = self.__get_sector_container()
        spc.set_container(sc2, [])
        self.assert_equal(sorted(spc.get_containers()), [sc1, sc2])
        self.assert_equal(spc.get_container_for_location(1), sc2)
        sc3 = self.__get_sector_container()
        self._expect_error(AttributeError, spc.set_container,
                           'There is no empty sector left!',
                           **dict(container=sc3, locations=[]))


class RackPositionPlateContainerTestCase(_PlateContainerTestCase):

    TEST_CLS = RackPositionPlateContainer

    def set_up(self):
        _PlateContainerTestCase.set_up(self)
        self.available_locations = []
        for i in range(3):
            for j in range(3):
                rack_pos = get_rack_position_from_indices(i, j)
                self.available_locations.append(rack_pos)

    def __create_container(self, pool_id):
        pool = self._get_pool(pool_id)
        return RackPositionContainer(pool=pool,
                    position_type=FIXED_POSITION_TYPE,
                    volume=10, parent_concentration=20, target_concentration=10)

    def test_init(self):
        self._test_init()

    def test_equality(self):
        self._test_equality()

    def test_location_assignment(self):
        rppc = self._init_plate_container()
        self.assert_equal(len(rppc.get_locations()), 9)
        pool1 = 205200
        pool2 = 330001
        self.__check_position(rppc, pool1, (0, 0))
        self.__check_position(rppc, pool1, (0, 1))
        self.__check_position(rppc, pool2, (1, 0))
        self.__check_position(rppc, pool1, (0, 2))
        self.__check_position(rppc, pool1, (2, 0))
        self.__check_position(rppc, 205201, (1, 1))
        self.__check_position(rppc, pool2, (1, 2))
        self.__check_position(rppc, 205201, (2, 1))
        self.__check_position(rppc, 205202, (2, 2))
        self._expect_error(AttributeError, rppc.set_container,
                'There are no empty positions left!',
                **dict(container=self.__create_container(pool1),
                       locations=None))

    def __check_position(self, plate_container, pool_id, expected_pos_indices):
        container = self.__create_container(pool_id)
        pos = get_rack_position_from_indices(*expected_pos_indices)
        self.assert_is_none(plate_container.get_container_for_location(pos))
        plate_container.set_container(container, None)
        self.assert_equal(plate_container.get_container_for_location(pos),
                          container)


class _LabIsoBuilderTestCase(ToolsAndUtilsTestCase):
    """
    The ISO creation methods are very complex and therefore only tested
    as part of the ISO job generator.
    """

    TEST_CLS = LabIsoBuilder

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.ticket_number = 123
        em = self._create_experiment_metadata(ticket_number=self.ticket_number)
        rs = get_reservoir_specs_standard_96()
        self.iso_request = self._create_lab_iso_request(
                experiment_metadata=em, iso_plate_reservoir_specs=rs)
        self.excluded_racks = ['09999999']
        self.requested_tubes = ['1001', '1002']

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.ticket_number
        del self.iso_request
        del self.excluded_racks
        del self.requested_tubes

    def _init_builder(self):
        kw = dict(iso_request=self.iso_request,
                  excluded_racks=self.excluded_racks,
                  requested_tubes=self.requested_tubes)
        return self.TEST_CLS(**kw)

    def _test_init(self):
        builder = self._init_builder()
        self.assert_is_not_none(builder)
        self.assert_true(isinstance(builder, LabIsoBuilder))
        self.assert_equal(len(builder.final_iso_layout), 0)
        self.assert_equal(builder.final_iso_layout.shape.name,
                          RACK_SHAPE_NAMES.SHAPE_96)
        self.assert_equal(len(builder.preparation_layouts), 0)
        self.assert_equal(len(builder.job_layouts), 0)
        exp_plate_specs = {'a' : RACK_SPECS_NAMES.from_name(
                                                RACK_SPECS_NAMES.STANDARD_96)}
        self.assert_equal(builder.plate_specs, exp_plate_specs)
        self.assert_equal(len(builder.planned_dilutions), 0)
        self.assert_equal(len(builder.intraplate_transfers), 0)
        self.assert_equal(len(builder.interplate_transfers), 0)
        return builder


class LabIsoBuilderTestCase(_LabIsoBuilderTestCase):

    def test_init(self):
        self._test_init()

    def test_add_final_iso_plate_position(self):
        builder = self._init_builder()
        self.assert_equal(len(builder.final_iso_layout), 0)
        fpp = FinalLabIsoPosition(
                rack_position=get_rack_position_from_label('a1'),
                molecule_design_pool=self._get_pool(205200),
                position_type=FIXED_POSITION_TYPE,
                concentration=50, volume=10)
        builder.add_final_iso_plate_position(fpp)
        self.assert_equal(len(builder.final_iso_layout), 1)

    def test_add_preparation_layout(self):
        builder = self._init_builder()
        self.assert_equal(len(builder.preparation_layouts), 0)
        self.assert_equal(len(builder.plate_specs), 1)
        ps = RACK_SPECS_NAMES.from_name(RACK_SPECS_NAMES.STANDARD_384)
        layout = LabIsoPrepLayout(ps.shape)
        plate_marker = 'p2'
        builder.add_preparation_layout(plate_marker, layout, ps)
        exp_ps = {'a' : RACK_SPECS_NAMES.from_name(
                                                RACK_SPECS_NAMES.STANDARD_96),
                  plate_marker : ps}
        self.assert_equal(builder.plate_specs, exp_ps)
        exp_layouts = {plate_marker : layout}
        self.assert_equal(builder.preparation_layouts, exp_layouts)

    def test_add_job_preparation_layout(self):
        builder = self._init_builder()
        self.assert_equal(len(builder.job_layouts), 0)
        self.assert_equal(len(builder.plate_specs), 1)
        ps = RACK_SPECS_NAMES.from_name(RACK_SPECS_NAMES.STANDARD_384)
        layout = LabIsoPrepLayout(ps.shape)
        plate_marker = 'p2'
        builder.add_job_preparation_layout(plate_marker, layout, ps)
        exp_ps = {'a' : RACK_SPECS_NAMES.from_name(
                                                RACK_SPECS_NAMES.STANDARD_96),
                  plate_marker : ps}
        self.assert_equal(builder.plate_specs, exp_ps)
        exp_layouts = {plate_marker : layout}
        self.assert_equal(builder.job_layouts, exp_layouts)

    def test_get_all_layouts(self):
        builder = self._init_builder()
        specs_prep = RACK_SPECS_NAMES.from_name(RACK_SPECS_NAMES.STANDARD_96)
        layout_prep = LabIsoPrepLayout(shape=specs_prep.shape)
        prep_marker = 'p1'
        builder.add_preparation_layout(prep_marker, layout_prep, specs_prep)
        specs_job = RACK_SPECS_NAMES.from_name(RACK_SPECS_NAMES.DEEP_96)
        layout_job = LabIsoPrepLayout(shape=specs_job.shape)
        job_marker = 'jp1'
        builder.add_preparation_layout(job_marker, layout_job, specs_job)
        exp_layouts = {'a' : builder.final_iso_layout,
                       prep_marker : layout_prep,
                       job_marker : layout_job}
        self.assert_equal(builder.get_all_layouts(), exp_layouts)

    def test_planned_dilution(self):
        builder = self._init_builder()
        self.assert_equal(len(builder.planned_dilutions), 0)
        psd = self._get_entity(IPlannedSampleDilution)
        builder.add_dilution(psd, 'p1')
        exp_map = {'p1' : [psd]}
        self.assert_equal(builder.planned_dilutions, exp_map)

    def test_add_intraplate_transfer(self):
        builder = self._init_builder()
        self.assert_equal(len(builder.intraplate_transfers), 0)
        pst1 = self._create_planned_sample_transfer(volume=0.001)
        pst2 = self._create_planned_sample_transfer(volume=0.002)
        pst3 = self._create_planned_sample_transfer(volume=0.003)
        builder.add_intraplate_transfer(pst1, 'p1', 2)
        builder.add_intraplate_transfer(pst2, 'p1', 2)
        builder.add_intraplate_transfer(pst3, 'p1', 1)
        exp_map = {'p1' : {1 : [pst3],
                           2 : [pst1, pst2]}}
        self.assert_equal(builder.intraplate_transfers, exp_map)

    def test_add_interplate_transfer(self):
        builder = self._init_builder()
        self.assert_equal(len(builder.interplate_transfers), 0)
        pst1 = self._create_planned_sample_transfer(volume=0.001)
        pst2 = self._create_planned_sample_transfer(volume=0.002)
        pst3 = self._create_planned_sample_transfer(volume=0.003)
        builder.add_interplate_transfer(pst1, 'p1', 'p2')
        builder.add_interplate_transfer(pst2, 'p1', 'p2')
        builder.add_interplate_transfer(pst3, 'p1', 'p3')
        exp_map = {'p1' : {'p2' : [pst1, pst2], 'p3' : [pst3]}}
        self.assert_equal(exp_map, builder.interplate_transfers)

    def __create_tube_candidate(self, pool_id):
        return TubeCandidate(pool_id, rack_barcode='09999999',
                      rack_position=get_rack_position_from_label('a1'),
                      tube_barcode='1%08i' % (pool_id),
                      concentration=0.001, volume=5 / VOLUME_CONVERSION_FACTOR)

    def test_immutable_value(self):
        builder = self._init_builder()
        tc1 = self.__create_tube_candidate(205200)
        tc2 = self.__create_tube_candidate(1056000)
        m = [('_fixed_candidates', builder.set_fixed_candidates,
                dict(fixed_candidates={self._get_pool(205200) : tc1})),
             ('_floating_candidates', builder.set_floating_candidates,
                dict(floating_candidates=[tc1, tc2])),
             ('_isos_to_generate', builder.set_number_of_isos,
                dict(number_isos=3))]
        for tup in m:
            meth = tup[1]
            kw = tup[2]
            # no error
            meth(**kw)
            exp_msg = 'The %s attribute has been set before!' % (tup[0])
            self._expect_error(AttributeError, meth, exp_msg, **kw)
            break


class LibraryIsoBuilderTestCase(_LabIsoBuilderTestCase):

    TEST_CLS = LibraryIsoBuilder

    def test_init(self):
        self._test_init()

    def test_immutable_value(self):
        builder = self._init_builder()
        m = [('_iso_request_layout', builder.set_iso_request_layout,
                dict(iso_request_layout=IsoRequestLayout(
                                                shape=get_96_rack_shape()))),
             ('_library_plates', builder.set_library_plates,
                dict(floating_candidates=[self._create_library_plate()]))]
        for tup in m:
            meth = tup[1]
            kw = tup[2]
            # no error
            meth(**kw)
            exp_msg = 'The %s attribute has been set before!' % (tup[0])
            self._expect_error(AttributeError, meth, exp_msg, **kw)
            break
