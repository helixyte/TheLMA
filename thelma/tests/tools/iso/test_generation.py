"""
Tests the ISO generator tool
AAB, Jan 2012
"""


from everest.repositories.rdb.testing import RdbContextManager
from thelma.automation.tools.iso.generation import IsoGenerator
from thelma.automation.tools.iso.generation import IsoRescheduler
from thelma.automation.tools.iso.optimizer import IsoOptimizer
from thelma.automation.tools.iso.preplayoutfinder import PrepLayoutFinder96
from thelma.automation.tools.semiconstants \
    import get_reservoir_specs_standard_384
from thelma.automation.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.semiconstants import RACK_SPECS_NAMES
from thelma.automation.tools.semiconstants import get_experiment_metadata_type
from thelma.automation.tools.semiconstants import get_experiment_type_isoless
from thelma.automation.tools.semiconstants import get_experiment_type_screening
from thelma.automation.tools.stock.base import STOCK_ITEM_STATUS
from thelma.automation.tools.utils.iso import IsoLayoutConverter
from thelma.automation.tools.utils.iso import IsoParameters
from thelma.interfaces import IRackShape
from thelma.interfaces import ISubproject
from thelma.models.experiment import ExperimentMetadata
from thelma.models.iso import ISO_STATUS
from thelma.models.iso import Iso
from thelma.models.moleculedesign import MoleculeDesignPoolSet
from thelma.models.racklayout import RackLayout
from thelma.models.utils import get_user
from thelma.tests.tools.tooltestingutils \
    import ExperimentMetadataReadingTestCase
from thelma.tests.tools.tooltestingutils import SilentLog


class IsoCreatorTestCase(ExperimentMetadataReadingTestCase):

    def set_up(self):
        ExperimentMetadataReadingTestCase.set_up(self)
        self.TEST_FILE_PATH = 'thelma:tests/tools/iso/iso_generator/'
        self.VALID_FILE = 'valid_file_96.xls'
        self.user = get_user('it')
        self.number_of_isos = 2
        self.excluded_racks = None
        self.requested_tubes = None
        self.iso_request = None
        self.experiment_metadata = None
        self.source = None
        self.experiment_type_id = EXPERIMENT_SCENARIOS.OPTIMISATION
        self.expected_prep_plate_specs_name = RACK_SPECS_NAMES.STANDARD_96
        self.pool_id = None
        self.expected_iso_labels = None

    def tear_down(self):
        ExperimentMetadataReadingTestCase.tear_down(self)
        del self.number_of_isos
        del self.excluded_racks
        del self.requested_tubes
        del self.iso_request
        del self.source
        del self.experiment_type_id
        del self.expected_prep_plate_specs_name
        del self.pool_id
        del self.expected_iso_labels

    def _continue_setup(self, file_name=None):
        ExperimentMetadataReadingTestCase._continue_setup(self, file_name)
        self.iso_request = self.experiment_metadata.iso_request
        self._create_tool()

    def _set_experiment_metadadata(self):
        if self.experiment_metadata is None:
            em_type = get_experiment_metadata_type(self.experiment_type_id)
            self.experiment_metadata = ExperimentMetadata(number_replicates=3,
                                    label='ISO Creation Test',
                                    subproject=self._get_entity(ISubproject),
                                    experiment_metadata_type=em_type,
                                    ticket_number=123)

    def _check_result(self, file_name=None):
        self._continue_setup(file_name)
        original_isos = len(self.iso_request.isos)
        isos = self.tool.get_result()
        self.assert_is_not_none(isos)
        self.assert_true(len(isos) > 0)
        new_length = original_isos + len(isos)
        self.assert_equal(len(self.iso_request.isos), new_length)
        for iso in isos:
            self.assert_is_not_none(iso.rack_layout)
        fixed_cand, iso_cands, prep_layout_map = self.tool.get_report_data()
        used_pools = set()
        found_iso_labels = []
        for iso in isos:
            found_iso_labels.append(iso.label)
            prep_layout = prep_layout_map[iso.label]
            self.assert_false(prep_layout.has_unconverted_floatings())
            floating_cands = iso_cands[iso.label]
            all_set_pools = []
            if not iso.molecule_design_pool_set is None:
                for md_pool in iso.molecule_design_pool_set:
                    all_set_pools.append(md_pool.id)
            self.assert_equal(len(all_set_pools), len(floating_cands))
            for pool_id in floating_cands.keys():
                self.assert_true(pool_id in all_set_pools)
                self.assert_false(pool_id in used_pools)
                used_pools.add(pool_id)
            for prep_pos in prep_layout.working_positions():
                if prep_pos.is_mock: continue
                pool_id = prep_pos.molecule_design_pool_id
                if not fixed_cand.has_key(pool_id):
                    self.assert_true(pool_id in all_set_pools)
            self.assert_equal(len(iso.iso_sample_stock_racks), 0)
            self.assert_equal(len(iso.iso_aliquot_plates), 0)
            prep_plate = iso.preparation_plate
            self.assert_is_not_none(prep_plate)
            if self.experiment_type_id in self.tool.ONE_PLATE_TYPES:
                self.assert_equal(prep_plate.label,
                                  self.iso_request.plate_set_label)
            else:
                self.assert_true(iso.label in prep_plate.label)
            self.assert_equal(self.expected_prep_plate_specs_name,
                              prep_plate.specs.name)
        if self.pool_id is not None:
            req_cand = fixed_cand[self.pool_id]
            self.assert_is_not_none(req_cand)
            self.assert_equal(req_cand.container_barcode,
                              self.requested_tubes[0])
        if self.expected_iso_labels is None:
            self.expected_iso_labels = []
            for i in range(self.number_of_isos):
                label = '123_iso%i' % (i + 1)
                self.expected_iso_labels.append(label)
        self.assert_equal(sorted(found_iso_labels),
                          sorted(self.expected_iso_labels))


class IsoGeneratorTestCase(IsoCreatorTestCase):

    def _create_tool(self):
        self.tool = IsoGenerator(iso_request=self.iso_request,
                                 number_isos=self.number_of_isos,
                                 excluded_racks=self.excluded_racks,
                                 requested_tubes=self.requested_tubes)

    def test_result_96(self):
        self._check_result()
        self.assert_equal(len(self.tool.return_value), self.number_of_isos)
        self._check_warning_messages('Did not find candidates for the ' \
                                     'following sample molecule design pools')

    def test_result_96_deep_well(self):
        self.number_of_isos = 1
        self.expected_prep_plate_specs_name = RACK_SPECS_NAMES.DEEP_96
        self._check_result('valid_file_96_deep.xls')

    def test_result_384_opti(self):
        self.expected_prep_plate_specs_name = RACK_SPECS_NAMES.STANDARD_384
        self.expected_iso_labels = ['123_iso1']
        self._check_result('valid_file_384_opti.xls')
        self._check_warning_messages('The system will only generate 1 ISO ' \
                                     'though, because there are no floating ' \
                                     'positions for this ISO request')

    def test_result_384_opti_floats(self):
        self.expected_prep_plate_specs_name = RACK_SPECS_NAMES.STANDARD_384
        self.expected_iso_labels = ['123_iso1']
        self._check_result('valid_file_384_opti_floats.xls')
        new_iso = self.tool.return_value[0]
        self.assert_equal(len(new_iso.molecule_design_pool_set), 2)

    def test_result_96_screen(self):
        # has exactly enough floatings positions for 2 plates
        self.expected_prep_plate_specs_name = RACK_SPECS_NAMES.STANDARD_96
        self.experiment_type_id = EXPERIMENT_SCENARIOS.SCREENING
        self._check_result('valid_screen_96.xls')
        warnings = self.tool.get_messages()
        self.assert_equal(len(warnings), 0)

    def test_result_384_screen(self):
        self.expected_prep_plate_specs_name = RACK_SPECS_NAMES.STANDARD_384
        self.experiment_type_id = EXPERIMENT_SCENARIOS.SCREENING
        self._check_result('valid_file_384_screen.xls')

    def test_result_manual_with_buffer(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.MANUAL
        self.expected_prep_plate_specs_name = RACK_SPECS_NAMES.STANDARD_96
        self.number_of_isos = 1
        self._check_result('valid_manual.xls')
        ws = self.iso_request.worklist_series
        self.assert_is_not_none(ws)
        self.assert_equal(len(ws), 1)

    def test_result_manual_stock_concentration_only(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.MANUAL
        self.expected_prep_plate_specs_name = RACK_SPECS_NAMES.STANDARD_96
        self.number_of_isos = 1
        self._check_result('valid_manual_stock_conc_only.xls')
        ws = self.iso_request.worklist_series
        self.assert_is_none(ws)

    def test_result_order_only(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.ORDER_ONLY
        self.expected_prep_plate_specs_name = RACK_SPECS_NAMES.STANDARD_96
        self.number_of_isos = 1
        self._check_result('valid_order.xls')
        self.assert_is_none(self.iso_request.worklist_series)

    def test_with_compounds(self):
        self.number_of_isos = 1
        self.expected_prep_plate_specs_name = RACK_SPECS_NAMES.DEEP_96
        self._check_result('with_compound.xls')
        self._check_warning_messages('Attention! There are compound pools ' \
             'among the molecule design pools for the floating positions. ' \
             'For these compounds positions, we assume a stock concentration ' \
             'of 5,000,000 nM. Some floating pools have different ' \
             'concentrations: 277700 (11,603,070.7)')
        # If there is no stock sample use this part:
#        self._continue_setup()
#        self._test_and_expect_errors('Could not find valid stock tubes for ' \
#                    'the following fixed molecule design pool IDs: [277700]')

    def test_invalid_iso_request(self):
        self._continue_setup()
        self.iso_request = None
        self._test_and_expect_errors('The ISO request must be a IsoRequest ' \
                                     'object')

    def test_invalid_number_isos(self):
        self._continue_setup()
        self.number_of_isos = 3.4
        self._test_and_expect_errors('The number of ISOs order must be a ' \
                                     'positive integer')

    def test_invalid_excluded_racks(self):
        self._continue_setup()
        self.excluded_racks = dict()
        self._test_and_expect_errors('The excluded racks list must be a ' \
                                     'list object')
        self.excluded_racks = [13, 12]
        self._test_and_expect_errors('The excluded rack barcode must be a ' \
                                     'basestring object')

    def test_invalid_requested_tube(self):
        self._continue_setup()
        self.requested_tubes = dict()
        self._test_and_expect_errors('The requested tubes list must be a list')
        self.requested_tubes = [12, 13]
        self._test_and_expect_errors('The requested tube barcode must be a ' \
                                     'basestring object')

    def test_iso_layout_conversion_error(self):
        self._continue_setup()
        self.iso_request.iso_layout = RackLayout()
        self._test_and_expect_errors('Error when trying to convert ISO layout.')

    def test_unknown_experiment_type(self):
        self._continue_setup()
        self.experiment_metadata.experiment_metadata_type = \
                                                get_experiment_type_isoless()
        self._test_and_expect_errors('Unsupported experiment type')

    def test_unsupported_rack_shape(self):
        self._continue_setup()
        rack_shape = self._get_entity(IRackShape, '1x4')
        self.assert_is_not_none(rack_shape)
        self.iso_request.iso_layout.shape = rack_shape
        self._test_and_expect_errors('Unknown rack shape name')

    def test_preparation_layout_finding_failure(self):
        self._continue_setup('valid_file_384_opti.xls')
        self.experiment_metadata.experiment_metadata_type = \
                                            get_experiment_type_screening()
        self._test_and_expect_errors('Error when trying to find ' \
                                     'preparation plate layout')

    def test_wrong_supplier(self):
        self._continue_setup('wrong_supplier.xls')
        self._test_and_expect_errors('Could not find valid stock tubes for ' \
                                'the following fixed molecule design pool IDs')

    def test_not_enough_floatings(self):
        self.number_of_isos = 6
        self.expected_iso_labels = ['123_iso1', '123_iso2', '123_iso3']
        self._check_result()
        self.assert_equal(len(self.iso_request.isos),
                          len(self.expected_iso_labels))
        self._check_warning_messages('Some positions of the last ISO will ' \
                    'be empty because there are not enough molecule design ' \
                    'pools left in the queue to fill all positions. Number ' \
                    'of generated ISOs: 3')

    def test_queued_molecules(self):
        self._continue_setup()
        md_pools = set()
        for md_pool in self.experiment_metadata.molecule_design_pool_set:
            md_pools.add(md_pool)
        md_type = self.experiment_metadata \
                      .molecule_design_pool_set.molecule_type
        pool_set = MoleculeDesignPoolSet(molecule_type=md_type,
                                         molecule_design_pools=md_pools)
        iso = Iso(label='test_iso', iso_request=self.iso_request,
                  molecule_design_pool_set=pool_set)
        self.assert_equal(len(self.iso_request.isos), 1)
        self._test_and_expect_errors('There are no unused molecule design ' \
                                     'pools left for the floating positions!')
        iso.status = ISO_STATUS.CANCELLED
        self._create_tool()
        isos = self.tool.get_result()
        self.assert_is_not_none(isos)
        self.assert_equal(len(isos), self.number_of_isos)
        self.assert_equal(len(self.iso_request.isos), 3)

    def test_optimizer_failure(self):
        self._continue_setup('optimizer_failure.xls')
        self._test_and_expect_errors('Error when trying to find ISO candidates')

    def test_missing_fixed_candidates(self):
        self._continue_setup()
        converter = IsoLayoutConverter(rack_layout=self.iso_request.iso_layout,
                                       log=SilentLog())
        iso_layout = converter.get_result()
        for iso_pos in iso_layout.working_positions():
            if iso_pos.is_fixed:
                # set to a pool we do not have a stock sample for
                iso_pos.molecule_design_pool = 205205
                break
        self.iso_request.iso_layout = iso_layout.create_rack_layout()
        self._test_and_expect_errors('Could not find valid stock tubes for ' \
                                'the following fixed molecule design pool IDs')

    def test_requested_tubes(self):
        # use test pool we have at least 2 stock samples for, make sure you
        # find it in the file
        test_pool_id = 205230
        self._check_result()
        fixed_candidates = self.tool.get_report_data()[0]
        first_tube = fixed_candidates[test_pool_id].container_barcode
        # get tubes barcode
        silent_log = SilentLog()
        converter = IsoLayoutConverter(rack_layout=self.iso_request.iso_layout,
                                       log=silent_log)
        iso_layout = converter.get_result()
        finder = PrepLayoutFinder96(iso_layout=iso_layout,
                                    iso_request=self.iso_request,
                                    log=silent_log)
        prep_layout = finder.get_result()
        for prep_pos in prep_layout.working_positions():
            if prep_pos.is_fixed:
                prep_layout.set_floating_stock_concentration(
                                                prep_pos.stock_concentration)
                break
        optimizer = IsoOptimizer(molecule_design_pools=set([test_pool_id]),
                                 preparation_layout=prep_layout,
                                 log=silent_log)
        candidates = optimizer.get_result()
        self.assert_true(len(candidates) > 1)
        for candidate in candidates:
            if not candidate.container_barcode == first_tube:
                self.requested_tubes = [candidate.container_barcode]
                break
        self.assert_is_not_none(self.requested_tubes)
        self._create_tool()
        isos = self.tool.get_result()
        self.assert_is_not_none(isos)
        fixed_candidates = self.tool.get_report_data()[0]
        candidate = fixed_candidates[test_pool_id]
        self.assert_not_equal(first_tube, candidate.container_barcode)

    def test_requested_tubes2(self):
        # use test pool we have at least 2 stock samples for, make sure you
        # find it in the file
        test_pool_id = 205230
        with RdbContextManager() as session:
            self.pool_id = test_pool_id
            query = 'SELECT cb.barcode AS tube_barcode ' \
                    'FROM container_barcode cb, sample s, stock_sample ss, ' \
                        'container c ' \
                    'WHERE cb.container_id = c.container_id ' \
                    'AND c.item_status = \'%s\' ' \
                    'AND c.container_id = s.container_id ' \
                    'AND ss.sample_id = s.sample_id ' \
                    'AND ss.molecule_design_set_id = %i' \
                    % (STOCK_ITEM_STATUS, self.pool_id)
            result = session.query('tube_barcode').from_statement(query).all()
            self.assert_true(len(result) > 1)
            self.requested_tubes = [result[0][0]]
            self._check_result()

    def test_more_requested_tubes_than_controls(self):
        self.requested_tubes = ['1', '2', '3', '4', '5', '6', '7']
        self._check_result()
        self._check_warning_messages('There are more requested control tubes ' \
                                '(7) than control molecule design pools (3)')
        self._check_warning_messages('The following tube barcodes you have ' \
                                     'requested could not be found')

    def test_requested_tube_not_found(self):
        self.requested_tubes = ['1']
        self._check_result()
        self._check_warning_messages('The following tube barcodes you have ' \
                                     'requested could not be found')

    def test_empty_molecule_design_pool_set(self):
        # Note: might fail if some molecule design lack a suitable candidate
        self.number_of_isos = 4
        self._continue_setup()
        new_isos = self.tool.get_result()
        self.assert_is_not_none(new_isos)
        pool_set = self.experiment_metadata.molecule_design_pool_set
        # remove pools we do not have a stock sample for
        pool_set.remove_pool(205205)
        pool_set.remove_pool(205210)
        pool_set.remove_pool(205216)
        self._test_and_expect_errors('There are no unused molecule design ' \
                                     'pools left for the floating positions')

    def test_no_fixed_positions(self):
        self._continue_setup()
        converter = IsoLayoutConverter(rack_layout=self.iso_request.iso_layout,
                                       log=SilentLog())
        iso_layout = converter.get_result()
        for iso_pos in iso_layout.working_positions():
            if iso_pos.is_fixed:
                iso_pos.molecule_design = IsoParameters.MOCK_TYPE_VALUE
                iso_pos.iso_concentration = None
                iso_pos.position_type = IsoParameters.MOCK_TYPE_VALUE
        self.iso_request.iso_layout = iso_layout.create_rack_layout()
        self._test_and_expect_errors('There are no fixed molecule design ' \
                                     'pools in this ISO layout!')


class IsoReschedulerTestCase(IsoCreatorTestCase):

    def set_up(self):
        IsoCreatorTestCase.set_up(self)
        self.isos = None
        self.all_old_mdps = set()
        self.expected_mdps = set()
        self.number_of_isos = 3

    def tear_down(self):
        IsoCreatorTestCase.tear_down(self)
        del self.isos
        del self.all_old_mdps
        del self.expected_mdps

    def _continue_setup(self, file_name=None):
        IsoCreatorTestCase._continue_setup(self, file_name)
        self.__create_isos()
        self._create_tool()

    def __create_isos(self):
        generator = IsoGenerator(iso_request=self.iso_request,
                                 number_isos=self.number_of_isos,
                                 excluded_racks=self.excluded_racks,
                                 requested_tubes=self.requested_tubes)
        isos = generator.get_result()
        self.isos = isos[:2]
        for iso in isos:
            pool_set = iso.molecule_design_pool_set
            for md_pool in pool_set: self.all_old_mdps.add(md_pool)
            if iso in self.isos:
                for md_pool in pool_set: self.expected_mdps.add(md_pool)

    def _create_tool(self):
        self.tool = IsoRescheduler(iso_request=self.iso_request,
                                   isos_to_copy=self.isos,
                                   excluded_racks=self.excluded_racks,
                                   requested_tubes=self.requested_tubes)

    def test_result(self):
        self.expected_iso_labels = ['123_iso4_copy', '123_iso5_copy']
        self._check_result()
        new_isos = self.tool.return_value
        self.assert_is_not_none(new_isos)
        self.assert_equal(len(new_isos), len(self.isos))
        self.assert_equal(len(self.iso_request.isos), 5)
        new_mdps = set()
        for iso in new_isos:
            for md_pool in iso.molecule_design_pool_set:
                self.assert_true(md_pool in self.expected_mdps)
                new_mdps.add(md_pool)
        self.assert_equal(len(self.expected_mdps), len(new_mdps))

    def test_invalid_isos_list(self):
        self._continue_setup()
        self.isos = dict()
        self._test_and_expect_errors('The ISO list must be a list object')
        self.isos = [1, 2]
        self._test_and_expect_errors('The ISO must be a Iso object')

    def test_twice_the_same(self):
        # there is a duplicate ISO among the isos passed to the tool
        self.number_of_isos = 1
        self._continue_setup()
        self.iso_request.isos[0].status = ISO_STATUS.CANCELLED
        self.__create_isos()
        self.assert_equal(len(self.iso_request.isos), 2)
        self.isos = self.iso_request.isos
        self.assert_equal(len(self.isos), 2)
        self._create_tool()
        isos = self.tool.get_result()
        self.assert_is_not_none(isos)
        self.assert_equal(len(isos), 1)
        self._check_warning_messages('There is not enough molecule design ' \
                'pools left in the queue to generate the requested number ' \
                'of ISOs. Number of generated ISOs: 1')

    def test_no_preparation_plate(self):
        self._continue_setup()
        for iso in self.isos:
            iso.iso_preparation_plate = None
            break
        self._test_and_expect_errors('Some of the ISOs to copy to not have ' \
                                     'a preparation plate!')

    def test_differing_plate_specs(self):
        self._continue_setup()
        plate_specs_384 = RACK_SPECS_NAMES.from_reservoir_specs(
                                           get_reservoir_specs_standard_384())
        for iso in self.isos:
            #pylint: disable=E1101
            iso.iso_preparation_plate.plate.specs = plate_specs_384
            #pylint: enable=E1101
            break
        self._test_and_expect_errors('The ISOs to copy have different ' \
                                     'preparation plate specs:')
