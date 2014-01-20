#"""
#Tests for library creation base classes
#
#AAB
#"""
#from everest.testing import check_attributes
#from thelma.automation.tools.libcreation.base \
#    import get_source_plate_transfer_volume
#from thelma.automation.tools.libcreation.base \
#    import get_stock_pool_buffer_volume
#from thelma.automation.tools.libcreation.base import LibraryBaseLayout
#from thelma.automation.tools.libcreation.base import LibraryBaseLayoutConverter
#from thelma.automation.tools.libcreation.base import LibraryBaseLayoutParameters
#from thelma.automation.tools.libcreation.base import LibraryBaseLayoutPosition
#from thelma.automation.tools.libcreation.base import LibraryLayout
#from thelma.automation.tools.libcreation.base import LibraryLayoutConverter
#from thelma.automation.tools.libcreation.base import LibraryParameters
#from thelma.automation.tools.libcreation.base import LibraryPosition
#from thelma.automation.tools.semiconstants import get_96_rack_shape
#from thelma.automation.tools.semiconstants import get_rack_position_from_label
#from thelma.interfaces import IMoleculeDesignPool
#from thelma.models.racklayout import RackLayout
#from thelma.models.tagging import Tag
#from thelma.tests.tools.tooltestingutils import TestingLog
#from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase
#
#
#class LibraryBaseMethodsTestCase(ToolsAndUtilsTestCase):
#
#    def test_get_stock_pool_buffer_volume(self):
#        self.assert_equal(get_stock_pool_buffer_volume(), 36)
#
#    def test_get_source_plate_transfer_volume(self):
#        self.assert_equal(get_source_plate_transfer_volume(), 5.5)
#
#
#class LibraryBaseLayoutPositionTestCase(ToolsAndUtilsTestCase):
#
#    def set_up(self):
#        ToolsAndUtilsTestCase.set_up(self)
#        self.rack_pos = get_rack_position_from_label('A1')
#        self.is_sample_position = True
#        self.is_sample_pos_tag = Tag('library_base_layout',
#                                     'is_sample_position', 'True')
#        self.init_data = dict(rack_position=self.rack_pos,
#                              is_sample_position=self.is_sample_position)
#
#    def tear_down(self):
#        ToolsAndUtilsTestCase.tear_down(self)
#        del self.rack_pos
#        del self.is_sample_position
#        del self.is_sample_pos_tag
#        del self.init_data
#
#    def __get_library_base_position(self):
#        return LibraryBaseLayoutPosition(**self.init_data)
#
#    def test_init(self):
#        base_pos = LibraryBaseLayoutPosition(**self.init_data)
#        self.assert_is_not_none(base_pos)
#        check_attributes(base_pos, self.init_data)
#        # check errors
#        self.init_data['is_sample_position'] = None
#        self.assert_raises(TypeError, LibraryBaseLayoutPosition,
#                           **self.init_data)
#
#    def test_equality(self):
#        base_pos1 = LibraryBaseLayoutPosition(**self.init_data)
#        base_pos2 = LibraryBaseLayoutPosition(**self.init_data)
#        self.init_data['rack_position'] = get_rack_position_from_label('B2')
#        base_pos3 = LibraryBaseLayoutPosition(**self.init_data)
#        self.init_data['rack_position'] = self.rack_pos
#        self.init_data['is_sample_position'] = not self.is_sample_position
#        base_pos4 = LibraryBaseLayoutPosition(**self.init_data)
#        self.assert_equal(base_pos1, base_pos2)
#        self.assert_not_equal(base_pos1, base_pos3)
#        self.assert_not_equal(base_pos1, base_pos4)
#        self.assert_not_equal(base_pos1, self.rack_pos)
#
#    def test_get_parameter_value(self):
#        base_pos = self.__get_library_base_position()
#        self.assert_true(base_pos.get_parameter_value(
#                                    LibraryBaseLayoutParameters.IS_SAMPLE_POS))
#
#    def test_get_parameter_tag(self):
#        base_pos = self.__get_library_base_position()
#        self.assert_equal(self.is_sample_pos_tag, base_pos.get_parameter_tag(
#                                    LibraryBaseLayoutParameters.IS_SAMPLE_POS))
#
#    def test_get_tag_set(self):
#        base_pos = self.__get_library_base_position()
#        exp_tags = [self.is_sample_pos_tag]
#        tag_set = base_pos.get_tag_set()
#        self._compare_tag_sets(exp_tags, tag_set)
#
#
#class LibraryBaseLayoutTestCase(ToolsAndUtilsTestCase):
#
#    def set_up(self):
#        ToolsAndUtilsTestCase.set_up(self)
#        self.shape = get_96_rack_shape()
#        self.a1_pos = get_rack_position_from_label('A1')
#        self.b1_pos = get_rack_position_from_label('B1')
#        self.base_pos1 = LibraryBaseLayoutPosition(rack_position=self.a1_pos,
#                                                   is_sample_position=True)
#        self.base_pos2 = LibraryBaseLayoutPosition(rack_position=self.b1_pos,
#                                                   is_sample_position=False)
#        self.is_sample_pos_tag1 = Tag(LibraryBaseLayoutParameters.DOMAIN,
#                                      LibraryBaseLayoutParameters.IS_SAMPLE_POS,
#                                      'True')
#        self.is_sample_pos_tag2 = Tag(LibraryBaseLayoutParameters.DOMAIN,
#                                      LibraryBaseLayoutParameters.IS_SAMPLE_POS,
#                                      'False')
#
#    def tear_down(self):
#        ToolsAndUtilsTestCase.tear_down(self)
#        del self.shape
#        del self.a1_pos
#        del self.b1_pos
#        del self.base_pos1
#        del self.base_pos2
#        del self.is_sample_pos_tag1
#        del self.is_sample_pos_tag2
#
#    def __create_test_layout(self):
#        layout = LibraryBaseLayout(shape=self.shape)
#        layout.add_position(self.base_pos1)
#        layout.add_position(self.base_pos2)
#        return layout
#
#    def test_init(self):
#        lbl = LibraryBaseLayout(shape=self.shape)
#        self.assert_is_not_none(lbl)
#        self.assert_equal(lbl.shape, self.shape)
#        self.assert_equal(len(lbl), 0)
#
#    def test_add_position(self):
#        lbl = LibraryBaseLayout(shape=self.shape)
#        self.assert_equal(len(lbl), 0)
#        lbl.add_position(self.base_pos1)
#        self.assert_equal(len(lbl), 1)
#        self.assert_raises(TypeError, lbl.add_position, self.a1_pos)
#
#    def test_get_working_position(self):
#        lbl = LibraryBaseLayout(shape=self.shape)
#        self.assert_is_none(lbl.get_working_position(self.a1_pos))
#        lbl.add_position(self.base_pos1)
#        self.assert_equal(self.base_pos1, lbl.get_working_position(self.a1_pos))
#
#    def test_equality(self):
#        lbl1 = self.__create_test_layout()
#        lbl2 = self.__create_test_layout()
#        lbl3 = self.__create_test_layout()
#        lbl3.del_position(self.a1_pos)
#        self.assert_equal(lbl1, lbl2)
#        self.assert_not_equal(lbl1, lbl3)
#
#    def test_get_tags(self):
#        lbl = self.__create_test_layout()
#        exp_tags = [self.is_sample_pos_tag1, self.is_sample_pos_tag2]
#        tag_set = lbl.get_tags()
#        self._compare_tag_sets(exp_tags, tag_set)
#
#    def test_get_positions(self):
#        lbl = self.__create_test_layout()
#        exp_pos = [self.a1_pos, self.b1_pos]
#        pos_set = lbl.get_positions()
#        self._compare_pos_sets(exp_pos, pos_set)
#
#    def test_get_positions_for_tag(self):
#        lbl = self.__create_test_layout()
#        exp_positions = [self.b1_pos]
#        pos_set = lbl.get_positions_for_tag(self.is_sample_pos_tag2)
#        self._compare_pos_sets(exp_positions, pos_set)
#
#    def test_get_tags_for_position(self):
#        lbl = self.__create_test_layout()
#        exp_tags = [self.is_sample_pos_tag2]
#        tag_set = lbl.get_tags_for_position(self.b1_pos)
#        self._compare_tag_sets(exp_tags, tag_set)
#
#    def test_close(self):
#        lbl = self.__create_test_layout()
#        self.assert_equal(len(lbl), 2)
#        self.assert_equal(lbl.get_working_position(self.b1_pos), self.base_pos2)
#        self.assert_false(lbl.is_closed)
#        lbl.close()
#        self.assert_equal(len(lbl), 1)
#        self.assert_is_none(lbl.get_working_position(self.b1_pos))
#        self.assert_true(lbl.is_closed)
#        self.assert_raises(AttributeError, lbl.add_position, self.base_pos2)
#
#    def test_create_rack_layout(self):
#        lbl = self.__create_test_layout()
#        rl = lbl.create_rack_layout()
#        self.assert_equal(lbl.shape, rl.shape)
#        self.assert_equal(len(rl.tagged_rack_position_sets), 1)
#        self._compare_pos_sets(lbl.get_positions(), rl.get_positions())
#        self._compare_tag_sets(lbl.get_tags(), rl.get_tags())
#        self.assert_equal(lbl.get_tags_for_position(self.a1_pos),
#                          rl.get_tags_for_position(self.a1_pos))
#        self.assert_equal(lbl.get_positions_for_tag(self.is_sample_pos_tag1),
#                          rl.get_positions_for_tag(self.is_sample_pos_tag1))
#        self.assert_true(lbl.is_closed)
#
#
#class LibraryBaseLayoutConverterTestCase(ToolsAndUtilsTestCase):
#
#    def set_up(self):
#        ToolsAndUtilsTestCase.set_up(self)
#        self.shape = get_96_rack_shape()
#        self.rack_layout = None
#        self.log = TestingLog()
#        self.a1_pos = get_rack_position_from_label('A1')
#        self.b1_pos = get_rack_position_from_label('B1')
#        self.c1_pos = get_rack_position_from_label('C1')
#        self.true_tag = Tag(LibraryBaseLayoutParameters.DOMAIN,
#                            LibraryBaseLayoutParameters.IS_SAMPLE_POS, 'True')
#        self.false_tag = Tag(LibraryBaseLayoutParameters.DOMAIN,
#                             LibraryBaseLayoutParameters.IS_SAMPLE_POS, 'False')
#        self.other_tag = Tag('some', 'unimportant', 'stuff')
#
#    def tear_down(self):
#        ToolsAndUtilsTestCase.tear_down(self)
#        del self.shape
#        del self.rack_layout
#        del self.log
#        del self.a1_pos
#        del self.b1_pos
#        del self.c1_pos
#        del self.true_tag
#        del self.false_tag
#        del self.other_tag
#
#    def _create_tool(self):
#        self.tool = LibraryBaseLayoutConverter(rack_layout=self.rack_layout,
#                                               log=self.log)
#
#    def __test_and_expect_errors(self, msg=None):
#        self.__create_test_layout()
#        self._test_and_expect_errors(msg)
#
#    def __create_test_layout(self):
#        trp_sets = []
#        true_positions = [self.a1_pos, self.b1_pos]
#        true_tags = [self.true_tag]
#        true_trps = self._create_test_trp_set(true_tags, true_positions)
#        trp_sets.append(true_trps)
#        false_positions = [self.c1_pos]
#        false_tags = [self.false_tag]
#        false_trps = self._create_test_trp_set(false_tags, false_positions)
#        trp_sets.append(false_trps)
#        all_positions = [self.a1_pos, self.b1_pos, self.c1_pos]
#        all_tags = [self.other_tag]
#        all_trps = self._create_test_trp_set(all_tags, all_positions)
#        trp_sets.append(all_trps)
#        self.rack_layout = RackLayout(shape=self.shape,
#                                      tagged_rack_position_sets=trp_sets)
#
#    def test_result(self):
#        self.__create_test_layout()
#        self._create_tool()
#        lbl = self.tool.get_result()
#        self.assert_is_not_none(lbl)
#        exp_tags = [self.true_tag]
#        tag_set = lbl.get_tags()
#        self._compare_tag_sets(exp_tags, tag_set)
#        exp_positions = [self.a1_pos, self.b1_pos]
#        pos_set = lbl.get_positions()
#        self._compare_pos_sets(exp_positions, pos_set)
#        a1_tags = [self.true_tag]
#        a1_tag_set = lbl.get_tags_for_position(self.a1_pos)
#        self._compare_tag_sets(a1_tags, a1_tag_set)
#        true_positions = [self.a1_pos, self.b1_pos]
#        true_pos_set = lbl.get_positions_for_tag(self.true_tag)
#        self._compare_pos_sets(true_positions, true_pos_set)
#
#    def test_invalid_rack_layout(self):
#        self._test_and_expect_errors('The rack layout must be a RackLayout ' \
#                                     'object')
#
#    def test_double_specification(self):
#        self.other_tag.predicate = LibraryBaseLayoutParameters.IS_SAMPLE_POS
#        self.__test_and_expect_errors('specified multiple times')
#
#    def test_invalid_flag(self):
#        self.false_tag.value = 'invalid'
#        self.__test_and_expect_errors('The "sample position" flag must be a ' \
#                    'boolean. The values for some positions are invalid. ' \
#                    'Details: C1 (invalid)')
#
#
#class LibraryPositionTestCase(ToolsAndUtilsTestCase):
#
#    def set_up(self):
#        ToolsAndUtilsTestCase.set_up(self)
#        self.rack_pos = get_rack_position_from_label('A1')
#        self.pool_id = 1056000
#        self.pool = self._get_entity(IMoleculeDesignPool, str(self.pool_id))
#        self.pool_tag = Tag('library', 'pool_id', '1056000')
#        self.mds = []
#        for md in self.pool: self.mds.append(md)
#        self.md_str = '10315676-10319279-10341998'
#        self.md_tag = Tag('library', 'molecule_designs', self.md_str)
#        self.tube_barcodes = ['1002', '1001', '1004']
#        self.tube_tag = Tag('library', 'stock_tube_barcodes', '1002-1001-1004')
#        self.init_data = dict(rack_position=self.rack_pos, pool=self.pool,
#                              stock_tube_barcodes=self.tube_barcodes)
#
#    def tear_down(self):
#        ToolsAndUtilsTestCase.tear_down(self)
#        del self.rack_pos
#        del self.pool_id
#        del self.pool
#        del self.pool_tag
#        del self.mds
#        del self.md_str
#        del self.md_tag
#        del self.tube_barcodes
#        del self.tube_tag
#        del self.init_data
#
#    def __create_test_position(self):
#        return LibraryPosition(**self.init_data)
#
#    def test_init(self):
#        lib_pos = LibraryPosition(**self.init_data)
#        self.assert_is_not_none(lib_pos)
#        check_attributes(lib_pos, self.init_data)
#        self.assert_equal(lib_pos.molecule_designs, self.mds)
#        # check errors
#        self.init_data['pool'] = self.pool_id
#        self.assert_raises(TypeError, LibraryPosition, **self.init_data)
#        self.init_data['pool'] = self.pool
#        self.init_data['stock_tube_barcodes'] = '1002'
#        self.assert_raises(TypeError, LibraryPosition, **self.init_data)
#
#    def test_equality(self):
#        lib_pos1 = self.__create_test_position()
#        lib_pos2 = self.__create_test_position()
#        self.init_data['rack_position'] = get_rack_position_from_label('B1')
#        lib_pos3 = self.__create_test_position()
#        self.init_data['rack_position'] = self.rack_pos
#        self.init_data['pool'] = self._get_entity(IMoleculeDesignPool,
#                                                  '1056001')
#        lib_pos4 = self.__create_test_position()
#        self.assert_equal(lib_pos1, lib_pos2)
#        self.assert_not_equal(lib_pos1, lib_pos3)
#        self.assert_not_equal(lib_pos1, lib_pos4)
#        self.assert_not_equal(lib_pos1, self.pool)
#
#    def test_get_molecule_design_tag(self):
#        lib_pos = self.__create_test_position()
#        self.assert_equal(lib_pos.get_molecule_designs_tag_value(), self.md_str)
#        self.assert_equal(lib_pos.get_molecule_designs_tag(), self.md_tag)
#
#    def test_get_stock_tube_barcode_tag(self):
#        lib_pos = self.__create_test_position()
#        self.assert_equal(lib_pos.get_stock_barcodes_tag_value(),
#                          self.tube_tag.value)
#        self.assert_equal(lib_pos.get_stock_barcodes_tag(), self.tube_tag)
#
#    def test_get_parameter_value(self):
#        lib_pos = self.__create_test_position()
#        self.assert_equal(lib_pos.get_parameter_value(LibraryParameters.POOL),
#                          self.pool)
#        self.assert_equal(self.mds, lib_pos.get_parameter_value(
#                                        LibraryParameters.MOLECULE_DESIGNS))
#        self.assert_equal(self.tube_barcodes, lib_pos.get_parameter_value(
#                                        LibraryParameters.STOCK_TUBE_BARCODES))
#
#    def test_get_parameter_tag(self):
#        lib_pos = self.__create_test_position()
#        self.assert_equal(lib_pos.get_parameter_tag(LibraryParameters.POOL),
#                          self.pool_tag)
#        self.assert_equal(self.md_tag, lib_pos.get_parameter_tag(
#                                        LibraryParameters.MOLECULE_DESIGNS))
#        self.assert_equal(self.tube_tag, lib_pos.get_parameter_tag(
#                                        LibraryParameters.STOCK_TUBE_BARCODES))
#
#    def test_get_tag_set(self):
#        lib_pos = self.__create_test_position()
#        exp_tags = [self.pool_tag, self.md_tag, self.tube_tag]
#        tag_set = lib_pos.get_tag_set()
#        self._compare_tag_sets(exp_tags, tag_set)
#
#    def test_validate_molecule_designs(self):
#        self.assert_true(LibraryPosition.validate_molecule_designs(self.pool,
#                                                                   self.md_str))
#        invalid_str = '10200478-10200480'
#        self.assert_false(LibraryPosition.validate_molecule_designs(self.pool,
#                                                                invalid_str))
#
#
#class LibraryLayoutTestCase(ToolsAndUtilsTestCase):
#
#    def set_up(self):
#        ToolsAndUtilsTestCase.set_up(self)
#        self.shape = get_96_rack_shape()
#        self.a1_pos = get_rack_position_from_label('A1')
#        self.b1_pos = get_rack_position_from_label('B1')
#        self.pool1 = self._get_entity(IMoleculeDesignPool, '1056000')
#        self.pool2 = self._get_entity(IMoleculeDesignPool, '1056001')
#        self.pool_tag1 = Tag(LibraryParameters.DOMAIN, LibraryParameters.POOL,
#                             str(self.pool1.id))
#        self.pool_tag2 = Tag(LibraryParameters.DOMAIN, LibraryParameters.POOL,
#                             str(self.pool2.id))
#        self.md_tag1 = Tag(LibraryParameters.DOMAIN,
#                           LibraryParameters.MOLECULE_DESIGNS,
#                           '10315676-10319279-10341998')
#        self.md_tag2 = Tag(LibraryParameters.DOMAIN,
#                           LibraryParameters.MOLECULE_DESIGNS,
#                           '10315722-10319325-10342044')
#        self.tubes1 = ['1002', '1001', '1007']
#        self.tubes2 = ['1004', '1005', '1008']
#        self.tube_tag1 = Tag(LibraryParameters.DOMAIN,
#                             LibraryParameters.STOCK_TUBE_BARCODES,
#                             '1002-1001-1007')
#        self.tube_tag2 = Tag(LibraryParameters.DOMAIN,
#                             LibraryParameters.STOCK_TUBE_BARCODES,
#                             '1004-1005-1008')
#        self.a1_lp = LibraryPosition(rack_position=self.a1_pos, pool=self.pool1,
#                            stock_tube_barcodes=self.tubes1)
#        self.b1_lp = LibraryPosition(rack_position=self.b1_pos, pool=self.pool2,
#                            stock_tube_barcodes=self.tubes2)
#
#    def tear_down(self):
#        ToolsAndUtilsTestCase.tear_down(self)
#        del self.shape
#        del self.a1_pos
#        del self.b1_pos
#        del self.pool1
#        del self.pool2
#        del self.pool_tag1
#        del self.pool_tag2
#        del self.md_tag1
#        del self.md_tag2
#        del self.tubes1
#        del self.tubes2
#        del self.tube_tag1
#        del self.tube_tag2
#        del self.a1_lp
#        del self.b1_lp
#
#    def __create_test_layout(self):
#        layout = LibraryLayout(shape=self.shape)
#        layout.add_position(self.a1_lp)
#        layout.add_position(self.b1_lp)
#        return layout
#
#    def __create_base_layout(self):
#        layout = LibraryBaseLayout(shape=self.shape)
#        base_pos1 = LibraryBaseLayoutPosition(rack_position=self.a1_pos)
#        base_pos2 = LibraryBaseLayoutPosition(rack_position=self.b1_pos)
#        layout.add_position(base_pos1)
#        layout.add_position(base_pos2)
#        return layout
#
#    def test_init(self):
#        ll = LibraryLayout(shape=self.shape)
#        self.assert_is_not_none(ll)
#        self.assert_equal(ll.shape, self.shape)
#        self.assert_equal(len(ll), 0)
#        self.assert_is_none(ll.base_layout_positions)
#
#    def test_init_from_base_layout(self):
#        base_layout = self.__create_base_layout()
#        ll = LibraryLayout.from_base_layout(base_layout)
#        self.assert_is_not_none(ll)
#        self.assert_equal(ll.shape, self.shape)
#        self.assert_equal(len(ll), 0)
#        self.assert_equal(len(ll.base_layout_positions),
#                              len(base_layout.get_positions()))
#
#    def test_add_position(self):
#        ll1 = LibraryLayout(shape=self.shape)
#        self.assert_equal(len(ll1), 0)
#        ll1.add_position(self.a1_lp)
#        self.assert_equal(len(ll1), 1)
#        c1_lp = LibraryPosition(rack_position=get_rack_position_from_label('C1'),
#                            pool=self.pool1, stock_tube_barcodes=self.tubes1)
#        ll1.add_position(c1_lp)
#        self.assert_equal(len(ll1), 2)
#        # check with base layout
#        base_layout = self.__create_base_layout()
#        ll2 = LibraryLayout.from_base_layout(base_layout)
#        self.assert_equal(len(ll2), 0)
#        ll2.add_position(self.a1_lp)
#        self.assert_equal(len(ll2), 1)
#        self.assert_raises(ValueError, ll2.add_position, c1_lp)
#
#    def test_equality(self):
#        ll1 = self.__create_test_layout()
#        ll2 = self.__create_test_layout()
#        ll3 = self.__create_test_layout()
#        ll3.del_position(self.a1_pos)
#        self.assert_equal(ll1, ll2)
#        self.assert_not_equal(ll1, ll3)
#
#    def test_get_tags(self):
#        ll = self.__create_test_layout()
#        exp_tags = [self.pool_tag1, self.pool_tag2, self.md_tag1, self.md_tag2,
#                    self.tube_tag1, self.tube_tag2]
#        tag_set = ll.get_tags()
#        self._compare_tag_sets(exp_tags, tag_set)
#
#    def test_get_positions(self):
#        ll = self.__create_test_layout()
#        exp_positions = [self.a1_pos, self.b1_pos]
#        pos_set = ll.get_positions()
#        self._compare_pos_sets(exp_positions, pos_set)
#
#    def test_get_tags_for_position(self):
#        ll = self.__create_test_layout()
#        exp_tags = [self.pool_tag1, self.md_tag1, self.tube_tag1]
#        tag_set = ll.get_tags_for_position(self.a1_pos)
#        self._compare_tag_sets(exp_tags, tag_set)
#
#    def test_get_positions_for_tag(self):
#        ll = self.__create_test_layout()
#        exp_positions = [self.a1_pos]
#        pos_set = ll.get_positions_for_tag(self.pool_tag1)
#        self._compare_pos_sets(exp_positions, pos_set)
#
#    def test_create_rack_layout(self):
#        ll = self.__create_test_layout()
#        rl = ll.create_rack_layout()
#        self.assert_equal(ll.shape, rl.shape)
#        self.assert_equal(len(rl.tagged_rack_position_sets), 2)
#        self._compare_tag_sets(ll.get_tags(), rl.get_tags())
#        self._compare_pos_sets(ll.get_positions(), rl.get_positions())
#        self._compare_pos_sets(ll.get_positions_for_tag(self.pool_tag1),
#                               rl.get_positions_for_tag(self.pool_tag1))
#        self._compare_tag_sets(ll.get_tags_for_position(self.a1_pos),
#                               rl.get_tags_for_position(self.a1_pos))
#
#
#class LibraryLayoutConverterTestCase(ToolsAndUtilsTestCase):
#
#    def set_up(self):
#        ToolsAndUtilsTestCase.set_up(self)
#        self.shape = get_96_rack_shape()
#        self.rack_layout = None
#        self.log = TestingLog()
#        self.a1_pos = get_rack_position_from_label('A1')
#        self.b1_pos = get_rack_position_from_label('B1')
#        self.pool_tag1 = Tag(LibraryParameters.DOMAIN, LibraryParameters.POOL,
#                             '1056000')
#        self.pool_tag2 = Tag(LibraryParameters.DOMAIN, LibraryParameters.POOL,
#                             '1056001')
#        self.md_tag1 = Tag(LibraryParameters.DOMAIN,
#                           LibraryParameters.MOLECULE_DESIGNS,
#                           '10315676-10319279-10341998')
#        self.md_tag2 = Tag(LibraryParameters.DOMAIN,
#                           LibraryParameters.MOLECULE_DESIGNS,
#                           '10315722-10319325-10342044')
#        self.tube_tag1 = Tag(LibraryParameters.DOMAIN,
#                             LibraryParameters.STOCK_TUBE_BARCODES,
#                             '1002-1001-1007')
#        self.tube_tag2 = Tag(LibraryParameters.DOMAIN,
#                             LibraryParameters.STOCK_TUBE_BARCODES,
#                             '1004-1005-1008')
#        self.other_tag = Tag('some', 'unimportant', 'stuff')
#
#    def tear_down(self):
#        ToolsAndUtilsTestCase.tear_down(self)
#        del self.shape
#        del self.rack_layout
#        del self.log
#        del self.a1_pos
#        del self.b1_pos
#        del self.pool_tag1
#        del self.pool_tag2
#        del self.md_tag1
#        del self.md_tag2
#        del self.tube_tag1
#        del self.tube_tag2
#        del self.other_tag
#
#    def _create_tool(self):
#        self.tool = LibraryLayoutConverter(rack_layout=self.rack_layout,
#                                           log=self.log)
#
#    def __test_and_expect_errors(self, msg):
#        self.__create_test_layout()
#        self._test_and_expect_errors(msg)
#
#    def __create_test_layout(self):
#        trp_sets = []
#        a1_tags = [self.pool_tag1, self.md_tag1, self.tube_tag1]
#        a1_positions = [self.a1_pos]
#        a1_trps = self._create_test_trp_set(a1_tags, a1_positions)
#        trp_sets.append(a1_trps)
#        b1_tags = [self.pool_tag2, self.md_tag2, self.tube_tag2]
#        b1_positions = [self.b1_pos]
#        b1_trps = self._create_test_trp_set(b1_tags, b1_positions)
#        trp_sets.append(b1_trps)
#        all_positions = [self.a1_pos, self.b1_pos]
#        all_tags = [self.other_tag]
#        all_trps = self._create_test_trp_set(all_tags, all_positions)
#        trp_sets.append(all_trps)
#        self.rack_layout = RackLayout(shape=self.shape,
#                                      tagged_rack_position_sets=trp_sets)
#
#    def test_result(self):
#        self.__create_test_layout()
#        self._create_tool()
#        ll = self.tool.get_result()
#        self.assert_is_not_none(ll)
#        exp_tags = [self.pool_tag1, self.pool_tag2, self.md_tag1, self.md_tag2,
#                    self.tube_tag1, self.tube_tag2]
#        tag_set = ll.get_tags()
#        self._compare_tag_sets(exp_tags, tag_set)
#        exp_positions = [self.a1_pos, self.b1_pos]
#        pos_set = ll.get_positions()
#        self._compare_pos_sets(exp_positions, pos_set)
#        a1_tags = [self.pool_tag1, self.md_tag1, self.tube_tag1]
#        a1_tag_set = ll.get_tags_for_position(self.a1_pos)
#        self._compare_tag_sets(a1_tags, a1_tag_set)
#        pool_pos = [self.a1_pos]
#        pool_pos_set = ll.get_positions_for_tag(self.pool_tag1)
#        self._compare_pos_sets(pool_pos, pool_pos_set)
#
#    def test_invalid_rack_layout(self):
#        self._test_and_expect_errors('rack layout must be a RackLayout')
#
#    def test_double_specification(self):
#        self.other_tag.predicate = LibraryParameters.POOL
#        self.__test_and_expect_errors('specified multiple times')
#
#    def test_missing_pool(self):
#        self.pool_tag1.predicate = 'other'
#        self.__test_and_expect_errors('Some positions do not have a pool ID')
#
#    def test_unknown_pool(self):
#        self.pool_tag1.value = '1'
#        self.__test_and_expect_errors('Some molecule design pool IDs could ' \
#                                      'not be found in the DB')
#
#    def test_mismatching_molecule_designs(self):
#        self.md_tag1.value = self.md_tag2.value
#        self.__test_and_expect_errors('The molecule designs IDs for some ' \
#                                      'pools do not match')
#
#    def test_missing_tubes(self):
#        self.tube_tag1.predicate = 'other'
#        self.__test_and_expect_errors('The following rack position do not ' \
#                                      'contain stock tube barcodes')
#
#    def test_mismatching_tubes(self):
#        self.tube_tag1.value = '1001'
#        self.__test_and_expect_errors('For some positions the number of ' \
#                        'tubes does not match the number of molecule designs')
