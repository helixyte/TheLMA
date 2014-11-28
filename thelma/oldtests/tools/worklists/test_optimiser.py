"""
Tests for class involved in Biomek layout optimisation.

AAB
"""
from everest.repositories.rdb.testing import check_attributes
from thelma.tools.semiconstants import get_384_rack_shape
from thelma.tools.semiconstants import get_96_rack_shape
from thelma.tools.semiconstants import get_rack_position_from_label
from thelma.tools.metadata.base import TransfectionPosition
from thelma.tools.worklists.optimiser import SourceSubcolumn
from thelma.tools.worklists.optimiser import TransferItem
from thelma.tools.worklists.optimiser import TransferSubcolumn
from thelma.oldtests.tools.tooltestingutils import ToolsAndUtilsTestCase


class _TransferSubcolumnDummy(TransferItem):

    def _get_hash_value(self):
        return self.working_pos.hash_full


class TransferSubcolumnTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.min_row_distance = 0
        self.target_column_index = 1
        self.tid1 = self.__create_transfer_item('A1', 205200)
        self.tid2 = self.__create_transfer_item('B1', 205201)
        self.tid3 = self.__create_transfer_item('C1', 205202)
        self.init_data = dict(target_column_index=self.target_column_index,
                              min_row_distance=self.min_row_distance)

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.min_row_distance
        del self.target_column_index
        del self.tid1
        del self.tid2
        del self.tid3
        del self.init_data

    def __create_transfer_item(self, pos_label, pool_id):
        rack_pos = get_rack_position_from_label(pos_label)
        pool = self._get_pool(pool_id)
        tf_pos = TransfectionPosition(rack_position=rack_pos,
                            molecule_design_pool=pool,
                            reagent_name='mix',
                            reagent_dil_factor='140',
                            final_concentration='10')
        return _TransferSubcolumnDummy(working_pos=tf_pos)

    def __create_test_subcolumn(self, number_tids):
        sc = TransferSubcolumn(**self.init_data)
        tids = [self.tid1, self.tid2, self.tid3]
        for i in range(number_tids):
            sc.add_transfer_item(tids[i])
        return sc

    def test_init(self):
        sc = TransferSubcolumn(**self.init_data)
        self.init_data['last_row_index'] = None
        self.init_data['transfer_items'] = []
        check_attributes(sc, self.init_data)

    def test_add_transfer_item(self):
        sc = TransferSubcolumn(**self.init_data)
        self.assert_equal(len(sc.transfer_items), 0)
        sc.add_transfer_item(self.tid1)
        self.assert_equal(len(sc.transfer_items), 1)
        sc.add_transfer_item(self.tid2)
        self.assert_equal(len(sc.transfer_items), 2)
        # check order
        self.assert_equal(sc.transfer_items, [self.tid1, self.tid2])

    def test_allows_transfer_item(self):
        sc1 = self.__create_test_subcolumn(1)
        self.assert_true(sc1.allows_transfer_item(self.tid2))
        self.assert_true(sc1.allows_transfer_item(self.tid3))
        self.init_data['min_row_distance'] = 1
        sc2 = self.__create_test_subcolumn(1)
        self.assert_false(sc2.allows_transfer_item(self.tid2))
        self.assert_true(sc2.allows_transfer_item(self.tid3))

    def test_remove_transfer_item(self):
        sc = self.__create_test_subcolumn(3)
        self.assert_equal(len(sc.transfer_items), 3)
        sc.remove_transfer_item(self.tid1)
        self.assert_equal(len(sc.transfer_items), 2)
        self.assert_equal(sc.transfer_items, [self.tid2, self.tid3])

    def test_split(self):
        sc = self.__create_test_subcolumn(3)
        new_sc = sc.split(2)
        check_attributes(new_sc, self.init_data)
        self.assert_equal(len(new_sc.transfer_items), 2)
        self.assert_equal(new_sc.transfer_items, [self.tid1, self.tid2])
        self.assert_equal(len(sc.transfer_items), 1)
        self.assert_equal(sc.transfer_items, [self.tid3])

    def test_hash_value(self):
        sc = self.__create_test_subcolumn(3)
        exp_hash = '1-205200mix14010-205201mix14010-205202mix14010'
        self.assert_equal(sc.hash_value, exp_hash)


class SourceSubColumnTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.column_index = 3
        self.row_indices = [0, 2, 4, 6]
        self.init_data = dict(column_index=self.column_index,
                              free_row_indices=self.row_indices)

    def test_init(self):
        ssc = SourceSubcolumn(**self.init_data)
        check_attributes(ssc, self.init_data)
        self.assert_equal(len(ssc), len(self.row_indices))

    def test_get_position(self):
        ssc = SourceSubcolumn(**self.init_data)
        self.assert_equal(ssc.get_position().label, 'A4')
        self.assert_equal(ssc.get_position().label, 'C4')
        self.assert_equal(ssc.get_position().label, 'E4')
        self.assert_equal(ssc.get_position().label, 'G4')
        self.assert_raises(IndexError, ssc.get_position)

    def test_from_rack_shape(self):
        shape_96 = get_96_rack_shape()
        sscs1 = SourceSubcolumn.from_rack_shape(shape_96, min_row_distance=0)
        self.assert_equal(len(sscs1), 12)
        for i in range(12):
            ssc = sscs1[i]
            self.assert_equal(ssc.column_index, i)
            self.assert_equal(ssc.free_row_indices, range(8))
        shape_384 = get_384_rack_shape()
        sscs2 = SourceSubcolumn.from_rack_shape(shape_384, min_row_distance=1)
        self.assert_equal(len(sscs2), 48)
        for i in range(48):
            ssc = sscs2[i]
            self.assert_equal(ssc.column_index, i / 2)
            self.assert_equal(len(ssc.free_row_indices), 8)
            mod = i % 2
            if mod == 0:
                exp_rows = [0, 2, 4, 6, 8, 10, 12, 14]
            else:
                exp_rows = [1, 3, 5, 7, 9, 11, 13, 15]
                self.assert_equal(ssc.free_row_indices, exp_rows)
