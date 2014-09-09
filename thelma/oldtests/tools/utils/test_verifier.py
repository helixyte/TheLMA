#"""
#Tests the verification tools.
#
#AAB, Jan 2012
#"""
#from everest.utils import id_generator
#from thelma.automation.tools.iso.prep_utils import PrepIsoLayout
#from thelma.automation.tools.iso.prep_utils import PrepIsoPosition
#from thelma.automation.tools.semiconstants import get_96_rack_shape
#from thelma.automation.tools.semiconstants import get_item_status_managed
#from thelma.automation.tools.semiconstants import get_positions_for_shape
#from thelma.automation.tools.semiconstants import get_rack_position_from_label
#from thelma.automation.tools.utils.base import TransferTarget
#from thelma.automation.tools.utils.iso import IsoLayout
#from thelma.automation.tools.utils.iso import IsoParameters
#from thelma.automation.tools.utils.iso import IsoPosition
#from thelma.automation.tools.utils.verifier import IsoRackVerifier
#from thelma.automation.tools.experiment.base import SourceRackVerifier
#from thelma.interfaces import IMoleculeDesignPool
#from thelma.interfaces import IRackShape
#from thelma.interfaces import IUser
#from thelma.models.container import TubeSpecs
#from thelma.models.container import WellSpecs
#from thelma.models.iso import Iso
#from thelma.models.iso import IsoRequest
#from thelma.models.rack import PlateSpecs
#from thelma.models.rack import TubeRackSpecs
#from thelma.models.racklayout import RackLayout
#from thelma.models.sample import Molecule
#from thelma.models.sample import Sample
#from thelma.oldtests.tools.tooltestingutils import ToolsAndUtilsTestCase
#
#
#class VerifierTestCase(ToolsAndUtilsTestCase):
#
#    count_gen = id_generator()
#
#    def set_up(self):
#        ToolsAndUtilsTestCase.set_up(self)
#        self.expected_layout = None
#        self.shape = get_96_rack_shape()
#        self.user = self._get_entity(IUser, 'it')
#        self.status = get_item_status_managed()
#        self.record_success = True
#        self.pos_data = None
#        self.rack = None
#        self.tube_specs = TubeSpecs(label='tube_specs', max_volume=0.000100,
#                                    dead_volume=0.000100)
#
#    def tear_down(self):
#        ToolsAndUtilsTestCase.tear_down(self)
#        del self.expected_layout
#        del self.shape
#        del self.status
#        del self.record_success
#        del self.pos_data
#        del self.rack
#        del self.tube_specs
#
#    def _get_test_tube_rack(self):
#        count = self.count_gen.next()
#        tube_rack_specs = TubeRackSpecs(label='tube_rack_specs%d' % count,
#                                        shape=self.shape)
#        rack = tube_rack_specs.create_rack(label='test_rack%d' % count,
#                                           status=self.status)
#        rack.barcode = '0999999%d' % (count + 2)
#        return rack
#
#    def _get_test_plate_rack(self):
#        count = self.count_gen.next()
#        well_specs = WellSpecs(label='well_specs%d' % count,
#                               max_volume=0.000300,
#                               dead_volume=0.000005, plate_specs=None)
#        plate_specs = PlateSpecs(label='test_plate_specs%d' % count,
#                                 shape=self.shape,
#                                 well_specs=well_specs)
#        plate = plate_specs.create_rack(label='test_rack', status=self.status)
#        plate.barcode = '0999999%d' % (count + 2)
#        return plate
#
#    def _create_tool(self):
#        raise NotImplementedError('Abstract method.')
#
#    def _test_and_expect_compliance(self):
#        result = self.tool.get_result()
#        self.assert_is_not_none(result)
#        self.assert_true(result)
#        self._check_warning_messages('complies with the expected layout')
#        self.assert_equal(self.tool.get_expected_layout(),
#                          self.expected_layout)
#
#    def _test_success_without_record(self):
#        self.record_success = False
#        self._create_tool()
#        result = self.tool.get_result()
#        self.assert_is_not_none(result)
#        self.assert_true(result)
#        warnings = self.tool.get_messages()
#        self.assert_equal(len(warnings), 0)
#        self.assert_equal(self.tool.get_expected_layout(),
#                          self.expected_layout)
#
#    def _test_and_expect_errors(self, msg=None):
#        ToolsAndUtilsTestCase._test_and_expect_errors(self, msg)
#        self.assert_is_none(self.tool.get_expected_layout())
#
#    def _test_and_expect_mismatch(self, error_msg_fragment):
#        self._create_tool()
#        result = self.tool.get_result()
#        self.assert_false(result)
#        self._check_error_messages(error_msg_fragment)
#        self.assert_is_none(self.tool.get_expected_layout())
#
#    def _test_and_expect_missing_tubes(self):
#        self._test_and_expect_mismatch('expected molecule designs are missing')
#
#    def _test_and_expect_additional_tubes(self):
#        self._test_and_expect_mismatch('Some positions in the rack contain ' \
#                               'molecule designs although they should be empty')
#
#    def _test_and_expect_mismatching_tubes(self):
#        self._test_and_expect_mismatch('molecule designs of the following ' \
#                                        'positions do not match')
#
#    def _test_and_expect_rack_shape_mismatch(self):
#        self._test_and_expect_mismatch('The rack shapes of')
#
#
#class IsoRackVerifierTestCase(VerifierTestCase):
#
#    def set_up(self):
#        VerifierTestCase.set_up(self)
#        self.iso_request = None
#        self.iso = None
#        self.iso_rack_layout = None
#        self.prep_rack_layout = None
#        # (molecule design pool ID, iso conc, parent_well)
#        self.pos_data = dict(A1=(205200, 20, None), A2=(205200, 10, 'A1'),
#                             B1=(1056000, 20, None), B2=(1056000, 10, 'B1'),
#                             C1=(205201, 20, None), C2=(205201, 10, 'C1'),
#                             D1=('mock', None, None))
#        # molecule design pool IDs, placeholder
#        self.floating_map = {205200 : 'md_1', 1056000 : 'md_2'}
#
#    def tear_down(self):
#        VerifierTestCase.tear_down(self)
#        del self.iso_request
#        del self.iso
#        del self.iso_rack_layout
#        del self.prep_rack_layout
#        del self.floating_map
#
#    def __continue_setup(self, with_floatings=False):
#        self.__create_iso_layout(with_floatings=with_floatings)
#        self.__create_test_plate()
#        if with_floatings: self.__create_prep_layout()
#        self.__create_iso_request()
#        self.__create_iso()
#        self._create_tool()
#
#    def __create_iso_layout(self, with_floatings=False):
#        iso_layout = IsoLayout(shape=self.shape)
#        for rack_pos in get_positions_for_shape(self.shape):
#            pos_label = rack_pos.label
#            if not self.pos_data.has_key(pos_label): continue
#            data_tuple = self.pos_data[pos_label]
#            pool_id = data_tuple[0]
#            pool = self._get_pool(pool_id)
#            if with_floatings and self.floating_map.has_key(pool_id):
#                pool = self.floating_map[pool_id]
#            iso_conc = data_tuple[1]
#            iso_pos = IsoPosition(rack_position=rack_pos,
#                                  molecule_design_pool=pool,
#                                  iso_concentration=iso_conc,
#                                  iso_volume=5)
#            iso_layout.add_position(iso_pos)
#        self.expected_layout = iso_layout
#        self.iso_rack_layout = iso_layout.create_rack_layout()
#
#    def __create_prep_layout(self):
#        prep_layout = PrepIsoLayout(shape=self.shape)
#        for pos_label, data_tuple in self.pos_data.iteritems():
#            pool_id = data_tuple[0]
#            pool = self._get_pool(pool_id)
#            prep_conc = data_tuple[1]
#            rack_pos = get_rack_position_from_label(pos_label)
#            tt = TransferTarget(rack_position=rack_pos, transfer_volume=5)
#            parent_well = data_tuple[2]
#            if not parent_well is None:
#                parent_well = get_rack_position_from_label(parent_well)
#            pos_type = IsoParameters.FIXED_TYPE_VALUE
#            if pool_id == IsoParameters.MOCK_TYPE_VALUE:
#                pos_type = IsoParameters.MOCK_TYPE_VALUE
#            prep_pos = PrepIsoPosition(rack_position=rack_pos,
#                                       molecule_design_pool=pool,
#                                       position_type=pos_type,
#                                       prep_concentration=prep_conc,
#                                       required_volume=20,
#                                       transfer_targets=[tt],
#                                       parent_well=parent_well,
#                                       stock_tube_barcode=str(pool_id))
#            prep_layout.add_position(prep_pos)
#        self.prep_rack_layout = prep_layout.create_rack_layout()
#
#    def __create_iso_request(self):
#        self.iso_request = IsoRequest(requester=self.user,
#                                plate_set_label='verification test request',
#                                iso_layout=self.iso_rack_layout)
#
#    def __create_iso(self):
#        self.iso = Iso(label='verification test ISO',
#                       rack_layout=self.prep_rack_layout,
#                       iso_request=self.iso_request)
#
#    def __create_test_plate(self):
#        self.rack = self._get_test_plate_rack()
#        for container in self.rack.containers:
#            pos_label = container.location.position.label
#            if not self.pos_data.has_key(pos_label): continue
#            data_tuple = self.pos_data[pos_label]
#            sample = Sample(5, container)
#            pool_id = data_tuple[0]
#            if pool_id == IsoParameters.MOCK_TYPE_VALUE: continue
#            md_pool = self.pool_map[pool_id]
#            for md in md_pool:
#                mol = Molecule(molecule_design=md, supplier=None)
#                sample.make_sample_molecule(mol, 0.000100)
#
#    def _create_tool(self):
#        self.tool = IsoRackVerifier(self.rack, elf.iso,
#                                    record_success=self.record_success)
#
#    def test_compliant_without_floatings(self):
#        self.__continue_setup(with_floatings=False)
#        self._test_and_expect_compliance()
#
#    def test_compliant_with_floatings(self):
#        self.__continue_setup(with_floatings=True)
#        self._test_and_expect_compliance()
#
#    def test_compatibility_without_record(self):
#        self.__continue_setup()
#        self._test_success_without_record()
#
#    def test_invalid_iso(self):
#        self.__continue_setup()
#        self.iso = self.iso.label
#        self._test_and_expect_errors('ISO must be a Iso object')
#
#    def test_invalid_record_flag(self):
#        self.record_success = 1
#        self.__continue_setup()
#        self._test_and_expect_errors('record success flag must be a bool')
#
#    def test_invalid_plate(self):
#        self.__continue_setup()
#        self.rack = self._get_test_tube_rack()
#        self._test_and_expect_errors('rack must be a Plate')
#
#    def test_mismatching_rack_shapes(self):
#        self.__continue_setup()
#        self.shape = self._get_entity(IRackShape, '16x24')
#        self.__create_test_plate()
#        self._test_and_expect_rack_shape_mismatch()
#
#    def test_invalid_iso_layout(self):
#        self.__continue_setup()
#        self.iso_request.iso_layout = None
#        self._test_and_expect_errors('Error when trying to convert ISO layout')
#
#    def test_missing_prep_layout(self):
#        self.__continue_setup(with_floatings=True)
#        self.iso.rack_layout = None
#        self._test_and_expect_errors('Error when trying to convert ' \
#                                     'preparation plate layout')
#        self.__continue_setup(with_floatings=False)
#        self.iso.rack_layout = None
#        self._test_and_expect_compliance()
#
#    def test_invalid_prep_layout(self):
#        self.__continue_setup(with_floatings=True)
#        self.iso.rack_layout = RackLayout()
#        self._test_and_expect_errors('Error when trying to convert ' \
#                                     'preparation plate layout')
#        self.__continue_setup(with_floatings=False)
#        self.iso.rack_layout = RackLayout()
#        self._test_and_expect_compliance()
#
#    def test_missing_tubes_without_floatings(self):
#        self.__continue_setup(with_floatings=False)
#        del self.pos_data['A1']
#        del self.pos_data['B1']
#        self.__create_test_plate()
#        self._test_and_expect_missing_tubes()
#
#    def test_missing_tubes_with_floatings(self):
#        self.__continue_setup(with_floatings=True)
#        del self.pos_data['A1']
#        del self.pos_data['B1']
#        self.__create_test_plate()
#        self._test_and_expect_missing_tubes()
#
#    def test_additional_tubes_without_floatings(self):
#        a1_data = self.pos_data['A1']
#        b1_data = self.pos_data['B1']
#        del self.pos_data['A1']
#        del self.pos_data['B1']
#        self.__continue_setup(with_floatings=False)
#        self.pos_data['A1'] = a1_data
#        self.pos_data['B1'] = b1_data
#        self.__create_test_plate()
#        self._test_and_expect_additional_tubes()
#
#    def test_additional_tubes_with_floatings(self):
#        a1_data = self.pos_data['A1']
#        b1_data = self.pos_data['B1']
#        del self.pos_data['A1']
#        del self.pos_data['B1']
#        self.__continue_setup(with_floatings=True)
#        self.pos_data['A1'] = a1_data
#        self.pos_data['B1'] = b1_data
#        self.__create_test_plate()
#        self._test_and_expect_additional_tubes()
#
#    def test_mismatching_tubes_without_floatings(self):
#        self.__continue_setup(with_floatings=False)
#        a1_data = self.pos_data['A1']
#        b1_data = self.pos_data['B1']
#        self.pos_data['A1'] = b1_data
#        self.pos_data['B1'] = a1_data
#        self.__create_test_plate()
#        self._test_and_expect_mismatching_tubes()
#
#    def test_mismatching_tubes_with_floatings(self):
#        self.__continue_setup(with_floatings=True)
#        a1_data = self.pos_data['A1']
#        b1_data = self.pos_data['B1']
#        self.pos_data['A1'] = b1_data
#        self.pos_data['B1'] = a1_data
#        self.__create_test_plate()
#        self._test_and_expect_mismatching_tubes()
#
#
#class SourceRackVerifierTestCase(VerifierTestCase):
#
#    def set_up(self):
#        VerifierTestCase.set_up(self)
#        self.iso_rack_layout = None
#        self.iso_request = None
#        self.pool_map[205204] = self._get_entity(IMoleculeDesignPool, '205204')
#        self.pool_map[205207] = self._get_entity(IMoleculeDesignPool, '205207')
#        self.pool_map[205208] = self._get_entity(IMoleculeDesignPool, '205208')
#        # (molecule design pool ID, iso conc, parent_well)
#        self.pos_data1 = dict(A1=(205200, 20, None), A2=(205200, 10, 'A1'),
#                              B1=(1056000, 20, None), B2=(1056000, 10, 'B1'),
#                              C1=(205201, 20, None), C2=(205201, 10, 'C1'))
#        self.pos_data2 = dict(A1=(205204, 20, None), A2=(205204, 10, 'A1'),
#                              B1=(205207, 20, None), B2=(205207, 10, 'B1'),
#                              C1=(205201, 20, None), C2=(205201, 10, 'C1'))
#        self.pos_data3 = dict(A1=(205208, 20, None), A2=(205208, 10, 'A1'),
#                              C1=(205201, 20, None), C2=(205201, 10, 'C1'))
#        # placeholder, molecule design IDs
#        self.floating_map = {205200 : 'md_1', 1056000 : 'md_2', 205204 : 'md_1',
#                             205207 : 'md_2', 205208 : 'md_3'}
#
#    def tear_down(self):
#        VerifierTestCase.tear_down(self)
#        del self.iso_rack_layout
#        del self.iso_request
#        del self.pos_data1
#        del self.pos_data2
#        del self.pos_data3
#        del self.floating_map
#
#    def __continue_setup(self, with_floatings=False):
#        self.__create_test_plate(self.pos_data1)
#        self.__create_iso_layout(with_floatings=with_floatings)
#        self.__create_iso_request()
#        self.__create_isos(with_floatings=with_floatings)
#        self._create_tool()
#
#    def __create_test_plate(self, pos_data):
#        self.rack = self._get_test_plate_rack()
#        for container in self.rack.containers:
#            pos_label = container.location.position.label
#            if not pos_data.has_key(pos_label): continue
#            sample = Sample(5, container)
#            data_tuple = pos_data[pos_label]
#            pool_id = data_tuple[0]
#            md_pool = self._get_pool(pool_id)
#            for md in md_pool:
#                mol = Molecule(molecule_design=md, supplier=None)
#                sample.make_sample_molecule(mol, 0.000050)
#
#    def __create_iso_layout(self, with_floatings=False):
#        iso_layout = IsoLayout(shape=self.shape)
#        for rack_pos in get_positions_for_shape(self.shape):
#            pos_label = rack_pos.label
#            if not self.pos_data1.has_key(pos_label):
#                iso_pos = IsoPosition(rack_position=rack_pos)
#                iso_layout.add_position(iso_pos)
#                continue
#            data_tuple = self.pos_data1[pos_label]
#            pool_id = data_tuple[0]
#            iso_conc = data_tuple[1]
#            if with_floatings and self.floating_map.has_key(pool_id):
#                md_pool = self.floating_map[pool_id]
#            else:
#                md_pool = self.pool_map[pool_id]
#            iso_pos = IsoPosition(rack_position=rack_pos,
#                                  molecule_design_pool=md_pool,
#                                  iso_concentration=iso_conc,
#                                  iso_volume=5)
#            iso_layout.add_position(iso_pos)
#        self.expected_layout = iso_layout
#        self.iso_rack_layout = iso_layout.create_rack_layout()
#
#    def __create_iso_request(self):
#        self.iso_request = IsoRequest(iso_layout=self.iso_rack_layout,
#                                plate_set_label='test verification request',
#                                requester=self.user)
#
#    def __create_isos(self, with_floatings=False):
#        rl1 = self.__create_prep_layout_for_pos_data(self.pos_data1,
#                                    IsoParameters.FIXED_TYPE_VALUE)
#        Iso(rack_layout=rl1, iso_request=self.iso_request, label='iso1')
#        if with_floatings:
#            rl2 = self.__create_prep_layout_for_pos_data(self.pos_data2,
#                                            IsoParameters.FLOATING_TYPE_VALUE)
#            Iso(rack_layout=rl2, iso_request=self.iso_request, label='iso2')
#            rl3 = self.__create_prep_layout_for_pos_data(self.pos_data3,
#                                            IsoParameters.FLOATING_TYPE_VALUE)
#            Iso(rack_layout=rl3, iso_request=self.iso_request, label='iso3')
#
#    def __create_prep_layout_for_pos_data(self, pos_data, pos_type):
#        prep_layout = PrepIsoLayout(shape=self.shape)
#        for pos_label, data_tuple in pos_data.iteritems():
#            rack_pos = get_rack_position_from_label(pos_label)
#            pool_id = data_tuple[0]
#            pool = self._get_pool(pool_id)
#            prep_conc = data_tuple[1]
#            tt = TransferTarget(rack_position=rack_pos, transfer_volume=5)
#            parent_well = data_tuple[2]
#            if not parent_well is None:
#                parent_well = get_rack_position_from_label(parent_well)
#            prep_pos = PrepIsoPosition(rack_position=rack_pos,
#                                molecule_design_pool=pool,
#                                position_type=pos_type,
#                                prep_concentration=prep_conc,
#                                required_volume=20,
#                                parent_well=parent_well,
#                                transfer_targets=[tt],
#                                stock_tube_barcode=str(pool_id))
#            prep_layout.add_position(prep_pos)
#        return prep_layout.create_rack_layout()
#
#    def _create_tool(self):
#        self.tool = SourceRackVerifier(self.rack, self.iso_request)
#
#    def test_compliance_without_floatings(self):
#        self.__continue_setup(with_floatings=False)
#        self._test_and_expect_compliance()
#        self.__create_test_plate(self.pos_data2)
#        self._test_and_expect_compliance()
#        self.__create_test_plate(self.pos_data3)
#        self._test_and_expect_compliance()
#
#    def test_compliance_with_floatings(self):
#        self.__continue_setup(with_floatings=True)
#        self._test_and_expect_compliance()
#        self.__create_test_plate(self.pos_data2)
#        self._test_and_expect_compliance()
#        self.__create_test_plate(self.pos_data3)
#        self._test_and_expect_compliance()
#
#    def test_compatibility_without_record(self):
#        self.__continue_setup()
#        self._test_success_without_record()
#
#    def test_invalid_iso_request(self):
#        self.__continue_setup(with_floatings=False)
#        self.iso_request = None
#        self._test_and_expect_errors('ISO request must be a IsoRequest')
#
#    def test_invalid_record_flag(self):
#        self.record_success = 1
#        self.__continue_setup()
#        self._test_and_expect_errors('record success flag must be a bool')
#
#    def test_invalid_rack(self):
#        self.__continue_setup(with_floatings=False)
#        self.rack = self._get_test_tube_rack()
#        self._test_and_expect_errors('rack must be a Plate')
#
#    def test_mismatching_rack_shape(self):
#        self.__continue_setup(with_floatings=False)
#        self.shape = self._get_entity(IRackShape, '16x24')
#        self.__create_test_plate(self.pos_data1)
#        self._test_and_expect_rack_shape_mismatch()
#
#    def test_invalid_iso_layout(self):
#        self.__continue_setup(with_floatings=False)
#        self.iso_request.iso_layout = RackLayout()
#        self._test_and_expect_errors('Error when trying to convert ISO layout')
#
#    def test_invalid_prep_layout(self):
#        self.__continue_setup(with_floatings=False)
#        self.iso_request.isos[0].rack_layout = RackLayout()
#        self._test_and_expect_compliance()
#        self.__continue_setup(with_floatings=True)
#        self.iso_request.isos[0].rack_layout = RackLayout()
#        self._test_and_expect_errors('Error when trying to convert ' \
#                                     'preparation plate layout')
#
#    def test_mix_molecule_designs_between_isos(self):
#        self.__continue_setup(with_floatings=True)
#        data1 = self.pos_data1['A1']
#        data2 = self.pos_data2['A1']
#        self.pos_data1['A1'] = data2
#        self.pos_data2['A1'] = data1
#        self.__create_test_plate(self.pos_data1)
#        self._test_and_expect_mismatching_tubes()
#
#    def test_missing_tubes_without_floatings(self):
#        self.__continue_setup(with_floatings=False)
#        del self.pos_data1['A1']
#        del self.pos_data1['B1']
#        self.__create_test_plate(self.pos_data1)
#        self._test_and_expect_missing_tubes()
#
#    def test_missing_tubes_with_floatings(self):
#        self.__continue_setup(with_floatings=True)
#        del self.pos_data1['A1']
#        del self.pos_data1['B1']
#        self.__create_test_plate(self.pos_data1)
#        self._test_and_expect_missing_tubes()
#
#    def test_additional_tubes_without_floatings(self):
#        a1_data = self.pos_data1['A1']
#        b1_data = self.pos_data1['B1']
#        del self.pos_data1['A1']
#        del self.pos_data1['B1']
#        self.__continue_setup(with_floatings=False)
#        self.pos_data1['A1'] = a1_data
#        self.pos_data1['B1'] = b1_data
#        self.__create_test_plate(self.pos_data1)
#        self._test_and_expect_additional_tubes()
#
#    def test_additional_tubes_with_floatings(self):
#        a1_data = self.pos_data1['A1']
#        b1_data = self.pos_data1['B1']
#        del self.pos_data1['A1']
#        del self.pos_data1['B1']
#        self.__continue_setup(with_floatings=True)
#        self.pos_data1['A1'] = a1_data
#        self.pos_data1['B1'] = b1_data
#        self.__create_test_plate(self.pos_data1)
#        self._test_and_expect_additional_tubes()
#
#    def test_mismatching_tubes_without_floatings(self):
#        self.__continue_setup(with_floatings=False)
#        a1_data = self.pos_data1['A1']
#        b1_data = self.pos_data1['B1']
#        self.pos_data1['A1'] = b1_data
#        self.pos_data1['B1'] = a1_data
#        self.__create_test_plate(self.pos_data1)
#        self._test_and_expect_mismatching_tubes()
#
#    def test_mismatching_tubes_with_floatings(self):
#        self.__continue_setup(with_floatings=True)
#        a1_data = self.pos_data1['A1']
#        b1_data = self.pos_data1['B1']
#        self.pos_data1['A1'] = b1_data
#        self.pos_data1['B1'] = a1_data
#        self.__create_test_plate(self.pos_data1)
#        self._test_and_expect_mismatching_tubes()
