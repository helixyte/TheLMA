"""
Tests for the re-use of prepared stock racks in lab ISOs.

AAB
"""
from thelma.automation.semiconstants import get_pipetting_specs_biomek_stock
from thelma.automation.semiconstants import get_pipetting_specs_cybio
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.tools.iso.lab.base import LABELS
from thelma.automation.tools.iso.lab.stockrack.recycling \
    import StockRackRecyclerLabIso
from thelma.automation.tools.iso.lab.stockrack.recycling \
    import StockRackRecyclerIsoJob
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.oldtests.tools.iso.lab.stockrack.utils import LabIsoStockRackTestCase
from thelma.oldtests.tools.iso.lab.utils import LAB_ISO_TEST_CASES
from thelma.oldtests.tools.iso.lab.utils import TestTubeGenerator


class _StockRackRecyclerTestCase(LabIsoStockRackTestCase):

    def set_up(self):
        LabIsoStockRackTestCase.set_up(self)
        # tube barcode - pos label
        self.alt_tube_position_map = None
        self.starting_vol = 100 / VOLUME_CONVERSION_FACTOR
        self.tube_generator = None
        self.tube_map = dict()
        self.alt_layout_data = None
        self.alt_worklist_details = None
        self.exp_pipetting_specs = None

    def tear_down(self):
        LabIsoStockRackTestCase.tear_down(self)
        del self.alt_tube_position_map
        del self.starting_vol
        del self.tube_generator
        del self.tube_map
        del self.alt_layout_data
        del self.alt_worklist_details
        del self.exp_pipetting_specs

    def _continue_setup(self, file_name=None):
        LabIsoStockRackTestCase._continue_setup(self, file_name=file_name)
        self.__fill_destination_racks()
        self._create_tool()

    def __fill_destination_racks(self):
        sr_map = LAB_ISO_TEST_CASES.get_stock_rack_labels(self.case)
        layout_data = LAB_ISO_TEST_CASES.get_stock_rack_layout_data(self.case)
        for rack_labels in sr_map.values():
            for rack_label in rack_labels:
                rack = self.rack_generator.get_tube_rack(rack_label)
                if self.filter_destination_racks:
                    if not rack.barcode in self.rack_barcodes: continue
                if not rack.barcode in self.rack_barcodes: continue
                tube_specs = rack.specs.tube_specs[0]
                if self.tube_generator is None:
                    self.tube_generator = TestTubeGenerator(tube_specs)
                # pos_label - pool, tube barcode, transfer_targets
                layout_details = layout_data[rack_label]
                for pos_label, pos_data in layout_details.iteritems():
                    tube_barcode = pos_data[1]
                    if self.alt_tube_position_map is not None:
                        use_pos = self.alt_tube_position_map[tube_barcode]
                    else:
                        use_pos = pos_label
                    rack_pos = get_rack_position_from_label(use_pos)
                    pool = self._get_pool(pos_data[0])
                    if self.tube_map.has_key(tube_barcode):
                        tube_barcode += 'b' # happens with case_association_96
                    tube = self.tube_generator.create_tube(rack, rack_pos, pool,
                                                tube_barcode, self.starting_vol)
                    self.tube_map[tube_barcode] = tube

    def _test_and_expect_success(self, case_name):
        self._load_iso_request(case_name)
        self._check_result()

    def _check_result(self):
        stock_racks = self._get_entity_stock_racks()
        self.assert_equal(len(stock_racks), 0)
        updated_entity = self.tool.get_result()
        self.assert_is_not_none(updated_entity)
        self._check_stock_racks()

    def _get_entity_stock_racks(self):
        raise NotImplementedError('Abstract method.')

    def _check_stock_racks(self):
        raise NotImplementedError('Abstract method.')

    def _compare_alt_worklist_series(self, stock_rack):
        worklist_series = stock_rack.worklist_series
        self.assert_true(len(worklist_series) > 0)
        worklists = dict()
        for wl_label, wl_data in self.alt_worklist_details.iteritems():
            value_parts = LABELS.parse_rack_label(stock_rack.label)
            rack_marker = value_parts[LABELS.MARKER_RACK_MARKER]
            if not rack_marker in wl_label: continue
            worklists[wl_label] = wl_data
        self.assert_equal(len(worklist_series), len(worklists))
        found_labels = []
        for worklist in worklist_series:
            wl_label = worklist.label
            found_labels.append(wl_label)
            value_parts = LABELS.parse_worklist_label(wl_label)
            exp_index = value_parts[LABELS.MARKER_WORKLIST_NUM] - 1
            self.assert_equal(worklist.index, exp_index)
            details = worklists[wl_label]
            if not worklist.transfer_type == TRANSFER_TYPES.SAMPLE_TRANSFER:
                msg = 'The transfer types for worklist %s differ.\n' \
                     'Expected: %s\nFound: %s' % (worklist.label,
                      TRANSFER_TYPES.SAMPLE_TRANSFER, worklist.transfer_type)
                raise AssertionError(msg)
            if not worklist.pipetting_specs == self.exp_pipetting_specs:
                msg = 'The pipetting specs for worklist %s differ.\n' \
                      'Expected: %s\nFound: %s' % (worklist.label,
                       self.exp_pipetting_specs.name,
                       worklist.pipetting_specs.name)
                raise AssertionError(msg)
            self._compare_worklist_details(worklist, details)
        self.assert_equal(sorted(found_labels),
                          sorted(worklists.keys()))

    def _test_invalid_input_values(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
        self._test_invalid_input_value_entity()
        self._test_invalid_input_value_rack_barcodes()

    def _test_empty_tubes(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
        rack = self.rack_generator.barcode_map[self.rack_barcodes[0]]
        rack_pos = get_rack_position_from_label('g8')
        self.tube_generator.create_tube(rack=rack, rack_pos=rack_pos, pool=None,
                                        tube_barcode='99998764', volume=None)
        exp_msg = 'In some racks there are empty tubes: %s (99998764 (G8)). ' \
                  'Please remove them and try again.' % (rack.barcode)
        self._test_and_expect_errors(exp_msg)

    def _test_no_stock_sample(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
        rack = self.rack_generator.barcode_map[self.rack_barcodes[0]]
        rack_pos = get_rack_position_from_label('g8')
        tube = self.tube_generator.create_tube(rack=rack, rack_pos=rack_pos,
                               pool=None, tube_barcode='99998764', volume=None)
        tube.make_sample(0.005)
        exp_msg = 'The tubes in some of the racks you have specified contain ' \
              'normal samples instead of stock samples. Talk to the IT ' \
              'department, please. Details: %s (99998764 (G8)).' % (rack.barcode)
        self._test_and_expect_errors(exp_msg)

    def _test_unexpected_tubes(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
        rack = self.rack_generator.barcode_map[self.rack_barcodes[0]]
        rack_pos = get_rack_position_from_label('g8')
        pool = self._get_pool(205215)
        self.tube_generator.create_tube(rack, rack_pos, pool,
                                        tube_barcode='99998764', volume=0.0001)
        # for this case we expect 3 tubes for both lab ISO and job, that's
        # why we can use the same error message
        exp_msg = 'The number of tubes in the racks you have specified (4) ' \
            'is different from the expected one (3). Remove all tubes that ' \
            'are not required and add the missing ones or try the generate ' \
            'a new stock rack.'
        self._test_and_expect_errors(exp_msg)

    def _test_missing_pools(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
        rack = self.rack_generator.barcode_map[self.rack_barcodes[0]]
        for tube in rack.containers:
            tube.sample.molecule_design_pool = self._get_pool(205215)
            break
        self._test_and_expect_errors('Could not find tubes for the ' \
                                     'following pools:')

    def _test_invalid_concentration(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
        rack = self.rack_generator.barcode_map[self.rack_barcodes[0]]
        for tube in rack.containers:
            tube.sample.concentration = (2 * tube.sample.concentration)
            break
        self._test_and_expect_errors('The concentrations in some tubes do ' \
                                     'not match the expected ones:')

    def _test_insufficient_volume(self, details_msg):
        self.starting_vol = 5 / VOLUME_CONVERSION_FACTOR
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SIMPLE)
        exp_msg = 'The volumes in some tubes (dead volume included) are ' \
                  'not sufficient: ' + details_msg
        self._test_and_expect_errors(exp_msg)


class StockRackRecyclerLabIsoTestCase(_StockRackRecyclerTestCase):

    FOR_JOB = False

    def _create_tool(self):
        self.tool = StockRackRecyclerLabIso(self.entity, self.rack_barcodes)

    def _get_entity_stock_racks(self):
        return self.entity.iso_stock_racks + self.entity.iso_sector_stock_racks

    def _check_stock_racks(self):
        exp_num_sr = LAB_ISO_TEST_CASES.get_number_iso_stock_racks(self.case)\
                                                        [self._USED_ISO_LABEL]
        iso_sr = self.entity.iso_stock_racks
        sector_sr = self.entity.iso_sector_stock_racks
        all_sr = sector_sr + iso_sr
        self.assert_equal(len(all_sr), exp_num_sr)
        # check sectors
        sector_racks = dict()
        for sr in sector_sr:
            sector_racks[sr.sector_index] = sr
        sector_data = LAB_ISO_TEST_CASES.get_sectors_for_iso_stock_racks(
                                                                    self.case)
        num_sector_racks = 0
        for rack_marker, sector_index in sector_data.iteritems():
            if sector_index is None: continue
            num_sector_racks += 1
            sr = sector_racks[sector_index]
            value_parts = LABELS.parse_rack_label(sr.label)
            self.assert_equal(rack_marker,
                              value_parts[LABELS.MARKER_RACK_MARKER])
        self.assert_equal(num_sector_racks, len(sector_sr))
        # check layouts and worklist series
        for sr in all_sr:
            label = sr.label
            if self.alt_layout_data is None:
                layout_data = LAB_ISO_TEST_CASES.get_stock_rack_layout_data(
                                                            self.case)[label]
                self._compare_stock_rack_worklist_series(sr)
            else:
                layout_data = self.alt_layout_data[label]
                self._compare_alt_worklist_series(sr)
            self._compare_stock_rack_layout(layout_data, sr.rack_layout, label)

    def test_result_case_order_only(self):
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_ORDER_ONLY)

    def test_case_no_job_direct(self):
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_NO_JOB_DIRECT)

    def test_case_no_job_1_prep(self):
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_NO_JOB_1_PREP)

    def test_case_no_job_complex(self):
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_NO_JOB_COMPLEX)

    def test_case_association_direct(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)

    def test_case_association_96(self):
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_96)

    def test_case_association_simple(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SIMPLE)

    def test_case_association_no_cybio(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_NO_CYBIO)

    def test_case_association_2_aliquots(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_2_ALIQUOTS)

    def test_case_association_job_last(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_JOB_LAST)

    def test_case_association_several_conc(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SEVERAL_CONC)

    def test_case_library_simple(self):
        self.filter_destination_racks = False
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_LIBRARY_SIMPLE)
        self._test_and_expect_errors('The lab ISO does not need to be ' \
                'processed. Please proceed with the lab ISO job processing.')

    def test_case_library_2_aliquots(self):
        self.filter_destination_racks = False
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_LIBRARY_2_ALIQUOTS)
        self._test_and_expect_errors('The lab ISO does not need to be ' \
                'processed. Please proceed with the lab ISO job processing.')

    def test_result_altered_tube_order(self):
        case_name = LAB_ISO_TEST_CASES.CASE_ORDER_ONLY
        self.alt_tube_position_map = {
                  '1000205201' : 'g1', # otherwise b2
                  '1000330001' : 'g2', # otherwise b4
                  '1000333803' : 'g3', # otherwise b6
                  '1001056000' : 'g4', # otherwise b8
                  '1000180005' : 'g5'} # otherwise b10
        sr_label = '123_iso_01_s#1'
        layout_data = LAB_ISO_TEST_CASES.get_stock_rack_layout_data(
                                                case_name)[sr_label]
        alt_layout_data = dict(
                    g1=layout_data['b2'],
                    g2=layout_data['b4'],
                    g3=layout_data['b6'],
                    g4=layout_data['b8'],
                    g5=layout_data['b10'])
        self.alt_layout_data = {sr_label : alt_layout_data}
        self.exp_pipetting_specs = get_pipetting_specs_biomek_stock()
        alt_worklist = dict(b2=[2, 'g1'], b4=[2, 'g2'], b6=[2, 'g3'],
                            b8=[2, 'g4'], b10=[2, 'g5'])
        self.alt_worklist_details = {'123_1_s#1_to_a' :  alt_worklist}
        self._test_and_expect_success(case_name)

    def test_result_altered_racks(self):
        case_name = LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT
        self.alt_tube_position_map = {
                '1000205206' : 'b2', # stays the same, just other marker
                '1000205205' : 'b1', # stays the same, just other marker
                '1000205027' : 'b2'} # stays the same, just other marker
        layout_data_sets = LAB_ISO_TEST_CASES.get_stock_rack_layout_data(
                                                                    case_name)
        self.alt_layout_data = {
                '123_iso_01_s#2' : layout_data_sets['123_iso_01_s#2'],
                '123_iso_01_s#3' : layout_data_sets['123_iso_01_s#3']}
        self.exp_pipetting_specs = get_pipetting_specs_cybio()
        worklist_details_s2 = LAB_ISO_TEST_CASES.\
                    get_stock_rack_worklist_details(case_name, '123_1_s#2_to_a')
        worklist_details_s3 = LAB_ISO_TEST_CASES.\
                    get_stock_rack_worklist_details(case_name, '123_1_s#3_to_a')
        self.alt_worklist_details = {
                '123_1_s#2_to_a' : worklist_details_s2,
                '123_1_s#3_to_a' : worklist_details_s3}
        self._test_and_expect_success(case_name)

    def test_invalid_input_values(self):
        self._test_invalid_input_values()

    def test_unknown_rack_barcodes(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
        self._test_unknown_rack_barcodes()

    def test_not_enough_rack_barcodes_iso(self):
        self._test_not_enough_rack_barcodes_iso()

    def test_final_layout_conversion_error(self):
        self._test_final_layout_conversion_error()

    def test_iso_preparation_layout_conversion_error(self):
        self._test_iso_preparation_layout_conversion_error()

    def test_empty_tubes(self):
        self._test_empty_tubes()

    def test_no_stock_sample(self):
        self._test_no_stock_sample()

    def test_unexpected_tubes(self):
        self._test_unexpected_tubes()

    def test_missing_pools(self):
        self._test_missing_pools()

    def test_invalid_concentration(self):
        self._test_invalid_concentration()

    def test_insufficient_volume(self):
        self._test_insufficient_volume('1000205205 (pool: 205205, required: ' \
            '6 ul, found: 5 ul), 1000205206 (pool: 205206, required: 6 ul, ' \
            'found: 5 ul), 1000205207 (pool: 205207, required: 6 ul, ' \
            'found: 5 ul)')

    def test_layout_none_sectors(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
        layout = self._get_layout_from_iso()
        rack_pos = get_rack_position_from_label('c2')
        fp = layout.get_working_position(rack_pos)
        fp.sector_index = None
        self.entity.rack_layout = layout.create_rack_layout()
        self._test_and_expect_errors('The sector data for the layouts are ' \
                    'inconsistent - some sector indices for samples are None!')

    def test_inconsistent_layout_sectors(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
        layout = self._get_layout_from_iso()
        rack_pos = get_rack_position_from_label('c2')
        fp = layout.get_working_position(rack_pos)
        fp.sector_index = 3
        self.entity.rack_layout = layout.create_rack_layout()
        self._test_and_expect_errors('he sector for the following pools are ' \
                                     'inconsistent in the layouts: 205205.')

    def test_tube_for_sectors_spread(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
        rack_s2 = self.rack_generator.label_map['123_iso_01_s#2']
        rack_s3 = self.rack_generator.label_map['123_iso_01_s#3']
        for tube in rack_s3.containers:
            if tube.sample.molecule_design_pool.id == 205207:
                rack_s3.remove_tube(tube)
                rack_s3.containers.remove(tube)
                new_pos = get_rack_position_from_label('b3')
                rack_s2.add_tube(tube, new_pos)
                rack_s2.containers.append(tube)
                break
        self._test_and_expect_errors('The pools for the following sectors ' \
                                     'are spread over several racks: 1!')

    def test_sector_tube_in_wrong_position(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
        rack_s3 = self.rack_generator.label_map['123_iso_01_s#3']
        for tube in rack_s3.containers:
            if tube.sample.molecule_design_pool.id == 205205:
                rack_s3.move_tube(tube.location.position,
                                  get_rack_position_from_label('b3'))
                break
        self._test_and_expect_errors('The following tubes scheduled for the ' \
            'CyBio are located in wrong positions: tube 1000205205 in rack ' \
            '09999013 (exp: B1, found: B3)')


class StockRackRecyclerIsoJobTestCase(_StockRackRecyclerTestCase):

    FOR_JOB = True

    def _create_tool(self):
        self.tool = StockRackRecyclerIsoJob(self.entity, self.rack_barcodes)

    def _get_entity_stock_racks(self):
        return self.entity.iso_job_stock_racks

    def _check_stock_racks(self):
        self.assert_is_not_none(self.iso_job)
        exp_num_sr = LAB_ISO_TEST_CASES.get_number_job_stock_racks(self.case)
        stock_racks = self.iso_job.iso_job_stock_racks
        self.assert_equal(len(stock_racks), exp_num_sr)
        for sr in stock_racks:
            label = sr.label
            exp_barcode = self.rack_generator.STOCK_RACK_BARCODES[label]
            self.assert_equal(sr.rack.barcode, exp_barcode)
            if self.alt_layout_data is None:
                layout_data = LAB_ISO_TEST_CASES.get_stock_rack_layout_data(
                                                            self.case)[label]
                self._compare_stock_rack_worklist_series(sr)
            else:
                layout_data = self.alt_layout_data[label]
                self._compare_alt_worklist_series(sr)
            self._compare_stock_rack_layout(layout_data, sr.rack_layout, label)

    def test_result_case_order_only(self):
        self.filter_destination_racks = False
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ORDER_ONLY)
        self._test_and_expect_errors('The lab ISO job does not need ' \
                'to be processed. Please proceed with the lab ISO processing.')

    def test_case_no_job_direct(self):
        self.filter_destination_racks = False
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_NO_JOB_DIRECT)
        self._test_and_expect_errors('The lab ISO job does not need ' \
                'to be processed. Please proceed with the lab ISO processing.')

    def test_case_no_job_1_prep(self):
        self.filter_destination_racks = False
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_NO_JOB_1_PREP)
        self._test_and_expect_errors('The lab ISO job does not need ' \
                'to be processed. Please proceed with the lab ISO processing.')

    def test_case_no_job_complex(self):
        self.filter_destination_racks = False
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_NO_JOB_COMPLEX)
        self._test_and_expect_errors('The lab ISO job does not need ' \
                'to be processed. Please proceed with the lab ISO processing.')

    def test_case_association_direct(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)

    def test_case_association_96(self):
        self.filter_destination_racks = False
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_96)
        self._test_and_expect_errors('The lab ISO job does not need ' \
                'to be processed. Please proceed with the lab ISO processing.')

    def test_case_association_simple(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SIMPLE)

    def test_case_association_no_cybio(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_NO_CYBIO)

    def test_case_association_2_aliquots(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_2_ALIQUOTS)

    def test_case_association_job_last(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_JOB_LAST)

    def test_case_association_several_conc(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SEVERAL_CONC)

    def test_case_library_simple(self):
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_LIBRARY_SIMPLE)

    def test_case_library_2_aliquots(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_LIBRARY_2_ALIQUOTS)

    def test_result_altered_tube_order(self):
        case_name = LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SIMPLE
        self.alt_tube_position_map = {
                  '1000205201' : 'g1', # otherwise a1
                  '1000205202' : 'g2', # otherwise b1
                  '1000205200' : 'g3'} # otherwise c1
        sr_label = '123_job_01_s#1'
        layout_data = LAB_ISO_TEST_CASES.get_stock_rack_layout_data(
                                                case_name)[sr_label]
        alt_layout_data = dict(
                    g1=layout_data['a1'],
                    g2=layout_data['b1'],
                    g3=layout_data['c1'])
        self.alt_layout_data = {sr_label : alt_layout_data}
        self.exp_pipetting_specs = get_pipetting_specs_biomek_stock()
        alt_worklist = dict(b2=[1, 'g1'], d2=[1, 'g1'],
                b3=[1, 'g2'], d3=[1, 'g2'], b4=[1, 'g3'], d4=[1, 'g3'])
        self.alt_worklist_details = {'123_1_s#1_to_p' :  alt_worklist}
        self._test_and_expect_success(case_name)

    def test_invalid_input_values(self):
        self._test_invalid_input_values()

    def test_unknown_rack_barcodes(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
        self._test_unknown_rack_barcodes()

    def test_final_layout_conversion_error(self):
        self._test_final_layout_conversion_error()

    def test_iso_preparation_layout_conversion_error(self):
        self._test_iso_preparation_layout_conversion_error()

    def test_job_preparation_layout_conversion_error(self):
        self._test_job_preparation_layout_conversion_error()

    def test_job_different_iso_preparation_positions(self):
        self._test_job_different_iso_preparation_positions()

    def test_job_no_starting_wells(self):
        self._test_job_no_starting_wells()

    def test_empty_tubes(self):
        self._test_empty_tubes()

    def test_no_stock_sample(self):
        self._test_no_stock_sample()

    def test_unexpected_tubes(self):
        self._test_unexpected_tubes()

    def test_missing_pools(self):
        self._test_missing_pools()

    def test_invalid_concentration(self):
        self._test_invalid_concentration()

    def test_insufficient_volume(self):
        self._test_insufficient_volume('1000205200 (pool: 205200, required: ' \
                '9 ul, found: 5 ul), 1000205201 (pool: 205201, required: ' \
                '9 ul, found: 5 ul), 1000205202 (pool: 205202, required: ' \
                '9 ul, found: 5 ul).')
