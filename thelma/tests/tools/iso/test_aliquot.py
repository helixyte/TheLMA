"""
Tests for tools involved in additinal ISO aliquot plates.

AAB
"""
from thelma.automation.tools.iso.aliquot import IsoAliquotCreator
from thelma.automation.tools.iso.aliquot import IsoAliquotExecutor
from thelma.automation.tools.iso.aliquot import IsoAliquotWorklistWriter
from thelma.automation.tools.iso.isoprocessing import IsoProcessingExecutor
from thelma.automation.tools.semiconstants \
    import get_reservoir_specs_standard_96
from thelma.automation.tools.semiconstants import ITEM_STATUS_NAMES
from thelma.automation.tools.semiconstants import PLATE_SPECS_NAMES
from thelma.automation.tools.semiconstants import RESERVOIR_SPECS_NAMES
from thelma.automation.tools.semiconstants import get_384_rack_shape
from thelma.automation.tools.semiconstants import get_item_status_managed
from thelma.automation.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.models.container import WellSpecs
from thelma.models.iso import ISO_STATUS
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.rack import PlateSpecs
from thelma.tests.tools.iso.test_isoprocessing import IsoProcessing384TestCase
from thelma.tests.tools.iso.test_isoprocessing import IsoProcessing96TestCase
from thelma.tests.tools.tooltestingutils import FileCreatorTestCase


class IsoAliquotCreator96TestCase(IsoProcessing96TestCase):

    def _create_tool(self):
        self.tool = IsoAliquotCreator(iso=self.iso)

    def test_not_supported(self):
        self._continue_setup()
        self.assert_equal(len(self.iso.iso_aliquot_plates), 1)
        self._test_and_expect_errors('Aliquots can only be created for ' \
                                     '384-well screening ISOs!')

    def test_invalid_iso(self):
        self._test_invalid_iso()


class IsoAliquotToolTestCase(IsoProcessing384TestCase):

    def set_up(self):
        IsoProcessing384TestCase.set_up(self)
        self.setup_includes_stock_transfer = True
        self.new_aliqout_label = 'iso_processing_request#1_a3'
        self.new_aliquot_barcode = '09999933'

    def tear_down(self):
        IsoProcessing384TestCase.tear_down(self)
        del self.new_aliqout_label
        del self.new_aliquot_barcode

    def _continue_setup(self):
        IsoProcessing384TestCase._continue_setup(self)
        self._add_process_dilution_series()
        self._create_new_aliquot_plate()
        self._create_tool()

    def _continue_setup_empty_floatings(self):
        del self.float_map['md_010']
        IsoProcessing384TestCase._continue_setup(self)
        del self.position_data['D2']
        self.expected_transfers_per_stock_transfer = [2, 3]
        self.expected_buffer_transfers = len(self.position_data) - 2 # 2 mocks
        self._add_process_dilution_series()
        self._create_new_aliquot_plate()
        self._create_tool()

    def _add_process_dilution_series(self):
        executor = IsoProcessingExecutor(iso=self.iso,
                                         user=self.executor_user)
        updated_iso = executor.get_result()
        if updated_iso is None: raise ValueError('Series executed failed.')
        # we double the preparation plate volume to have enough
        for well in self.preparation_plate.containers:
            if not well.sample is None:
                well.sample.volume = (well.sample.volume * 2)

    def _create_new_aliquot_plate(self):
        aliquot_creator = IsoAliquotCreator(iso=self.iso)
        updated_iso = aliquot_creator.get_result()
        if updated_iso is None:
            raise ValueError('Aliquot plate creation failed.')
        for iap in updated_iso.iso_aliquot_plates:
            if iap.plate.label == self.new_aliqout_label:
                iap.plate.barcode = self.new_aliquot_barcode
                break

    def _test_invalid_barcode(self):
        self._continue_setup()
        self.new_aliquot_barcode = 123
        self._test_and_expect_errors('The barcode must be a basestring object')
        self.new_aliquot_barcode = '099999999'
        self._test_and_expect_errors('There is no aliquot plate with ' \
                                     'the barcode')


class IsoAliquotCreator384TestCase(IsoAliquotToolTestCase):

    def set_up(self):
        IsoAliquotToolTestCase.set_up(self)
        self.exp_plate_label = 'iso_processing_request#1_a3'

    def tear_down(self):
        IsoAliquotToolTestCase.tear_down(self)
        del self.exp_plate_label

    def _create_tool(self):
        self.tool = IsoAliquotCreator(iso=self.iso)

    def _continue_setup(self):
        IsoProcessing384TestCase._continue_setup(self) #pylint: disable=W0212
        self._add_process_dilution_series()

    def __check_result(self):
        aliquot_plates = self.iso.iso_aliquot_plates
        self.assert_equal(len(aliquot_plates), 2)
        plate_specs = aliquot_plates[0].plate.specs
        original_labels = []
        for iap in aliquot_plates: original_labels.append(iap.plate.label)
        updated_iso = self.tool.get_result()
        self.assert_is_not_none(updated_iso)
        self.assert_equal(updated_iso.status, ISO_STATUS.REOPENED)
        self.assert_equal(len(updated_iso.iso_aliquot_plates), 3)
        for iap in updated_iso.iso_aliquot_plates:
            self.assert_equal(iap.plate.specs, plate_specs)
            plate_label = iap.plate.label
            if not plate_label in original_labels:
                self.assert_equal(plate_label, self.exp_plate_label)

    def test_result(self):
        self._continue_setup()
        self.__check_result()

    def test_result_empty_floatings(self):
        del self.float_map['md_010']
        self._continue_setup()
        self.__check_result()

    def test_result_inactivated_position(self):
        self.inactivated_positions = ['A1']
        self._continue_setup()
        self.__check_result()

    def test_invalid_iso(self):
        self._test_invalid_iso()

    def test_missing_sample(self):
        self._continue_setup()
        for well in self.preparation_plate.containers:
            rack_pos = well.location.position
            prep_pos = self.preparation_layout.get_working_position(rack_pos)
            if prep_pos is None: continue
            well.sample = None
            break
        self._test_and_expect_errors('Some wells in the preparation plate ' \
                    'do not contain a sample although there should be one')

    def test_not_enough_preparation_volume(self):
        self._continue_setup()
        # revert doubling of preparation volume
        for well in self.preparation_plate.containers:
            if well.sample is None: continue
            well.sample.volume = (well.sample.volume / 2)
        self._test_and_expect_errors('The following well do not contain ' \
                        'enough volume for another aliquot plate anymore')

    def test_different_specs(self):
        self._continue_setup()
        specs_96 = PLATE_SPECS_NAMES.from_reservoir_specs(
                                        get_reservoir_specs_standard_96())
        for iap in self.iso.iso_aliquot_plates:
            iap.plate.specs = specs_96
            break
        self._test_and_expect_errors('The existing aliquot plates have ' \
                                     'different plate specs:')

    def test_missing_series_execution(self):
        self.setup_includes_stock_transfer = False
        IsoProcessing384TestCase._continue_setup(self) #pylint: disable=W0212
        self._test_and_expect_errors('You cannot create an additional ' \
                'aliquot plates as long as you have not executed the ISO ' \
                'processing series for all other aliquot plates!')


class IsoAliquotWorklistWriterTestCase(IsoAliquotToolTestCase,
                                       FileCreatorTestCase):

    def set_up(self):
        IsoAliquotToolTestCase.set_up(self)
        self.WL_PATH = 'thelma:tests/tools/iso/csv_files/'

    def _create_tool(self):
        self.tool = IsoAliquotWorklistWriter(iso=self.iso,
                                             barcode=self.new_aliquot_barcode)

    def __check_result(self):
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        zip_archive = self._get_zip_archive(zip_stream)
        self.assert_equal(len(zip_archive.namelist()), 1)
        for fil in zip_archive.namelist():
            tool_content = zip_archive.read(fil)
            self._compare_txt_file_content(tool_content,
                                           'additional_aliquot_transfer.txt')

    def test_result(self):
        self._continue_setup()
        self.__check_result()

    def test_result_aliquot_dilutions(self):
        self.position_data = self.position_data_aliquot_buffer
        self._continue_setup()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        self._check_warning_messages('Attention! The transfer from the ' \
            'preparation plate to the aliquot plates includes a dilution. ' \
            'You have to add buffer to the aliquot plates')
        zip_archive = self._get_zip_archive(zip_stream)
        self.assert_equal(len(zip_archive.namelist()), 2)
        for fil in zip_archive.namelist():
            tool_content = zip_archive.read(fil)
            if self.tool.CYBIO_FILE_SUFFIX[2:] in fil:
                self._compare_txt_file_content(tool_content,
                                'additional_aliquot_transfer_with_dil.txt')
            else:
                self._compare_csv_file_content(tool_content,
                                'buffer_additional_aliquot.csv')

    def test_result_empty_floatings(self):
        self._continue_setup_empty_floatings()
        self.__check_result()

    def test_result_inactivated_positions(self):
        self.inactivated_positions = ['A1']
        self.setup_includes_stock_transfer = True
        self._continue_setup()
        self.__check_result()

    def test_invalid_iso(self):
        self._test_invalid_iso()

    def test_invalid_barcode(self):
        self._test_invalid_barcode()

    def test_serial_worklist_creation_failure(self):
        self.setup_includes_stock_transfer = True
        self.position_data = self.position_data_aliquot_buffer
        self._continue_setup()
        new_well_specs = WellSpecs(label='invalid',
                                   max_volume=5 / VOLUME_CONVERSION_FACTOR,
                                   dead_volume=4 / VOLUME_CONVERSION_FACTOR,
                                   plate_specs=None)
        new_plate_specs = PlateSpecs(label='invalid',
                                     shape=get_384_rack_shape(),
                                     well_specs=new_well_specs)
        for iap in self.iso.iso_aliquot_plates:
            plate = iap.plate
            if plate.barcode == self.new_aliquot_barcode:
                plate.specs = new_plate_specs
                break
        self._test_and_expect_errors('Error during serial worklist ' \
                                     'file generation.')


class IsoAliquotPlateExecutorTestCase(IsoAliquotToolTestCase):

    def _create_tool(self):
        self.tool = IsoAliquotExecutor(iso=self.iso,
                                       barcode=self.new_aliquot_barcode,
                                       user=self.executor_user)


    def __check_result(self):
        updated_iso = self.tool.get_result()
        self.assert_is_not_none(updated_iso.status, ISO_STATUS.DONE)
        self.__check_executed_worklists(updated_iso)
        self.__check_aliquot_plate(updated_iso)

    def __check_executed_worklists(self, updated_iso):
        worklist_series = updated_iso.iso_request.worklist_series
        worklist_map = dict()
        for wl in worklist_series:
            worklist_map[wl.index] = wl
        last_index = max(worklist_map.keys())
        transfer_worklist = worklist_map[last_index]
        self.assert_equal(len(transfer_worklist.executed_worklists), 2)
        num_ets = []
        for transfer_ew in transfer_worklist.executed_worklists:
            num_ets.append(len(transfer_ew.executed_transfers))
            ert = transfer_ew.executed_transfers[0]
            self._check_executed_transfer(ert, TRANSFER_TYPES.RACK_TRANSFER)
            self.assert_equal(ert.source_rack.barcode, self.prep_plate_barcode)
            target_barcode = ert.target_rack.barcode
            if not target_barcode == self.new_aliquot_barcode:
                self.assert_true(target_barcode in self.aliquot_plate_barcodes)
        self.assert_equal(sorted(num_ets), [1, 2])
        if self.position_data == self.position_data_aliquot_buffer:
            buffer_worklist = worklist_map[last_index - 1]
            self.assert_equal(len(buffer_worklist.executed_worklists), 3)
            quarter_rs_name = RESERVOIR_SPECS_NAMES.QUARTER_MODULAR
            for buffer_ew in buffer_worklist.executed_worklists:
                for et in buffer_ew.executed_transfers:
                    self._check_executed_transfer(et,
                                            TRANSFER_TYPES.CONTAINER_DILUTION)
                    target_pos = et.target_container.location.position
                    iso_pos = self.iso_layout.get_working_position(target_pos)
                    self.assert_is_not_none(iso_pos)
                    self.assert_equal(et.reservoir_specs.name, quarter_rs_name)

    def __check_aliquot_plate(self, updated_iso):
        plate = None
        for iap in updated_iso.iso_aliquot_plates:
            if iap.plate.barcode == self.new_aliquot_barcode:
                plate = iap.plate
                break
        self.assert_equal(plate.status.name, ITEM_STATUS_NAMES.MANAGED)
        for container in plate.containers:
            rack_pos = container.location.position
            iso_pos = self.iso_layout.get_working_position(rack_pos)
            sample = container.sample
            if iso_pos is None or rack_pos.label in self.inactivated_positions:
                self.assert_is_none(sample)
                continue
            elif iso_pos.is_mock:
                self.assert_is_none(sample)
                continue
            elif iso_pos.is_floating and \
                    not self.float_map.has_key(iso_pos.molecule_design_pool):
                self.assert_is_none(sample)
                continue
            expected_volume = iso_pos.iso_volume
            self._compare_sample_volume(sample, expected_volume)
            pool_id = iso_pos.molecule_design_pool_id
            if not isinstance(pool_id, int):
                pool_id = self.float_map[pool_id]
            pool = self._get_pool(pool_id)
            expected_conc = iso_pos.iso_concentration / len(pool)
            self._compare_sample_and_pool(sample, pool, expected_conc)

    def test_result(self):
        self._continue_setup()
        self.__check_result()

    def test_result_aliquot_dilutions(self):
        self.position_data = self.position_data_aliquot_buffer
        self._continue_setup()
        self.__check_result()
        self.assert_equal(len(self.tool.get_messages()), 0)

    def test_result_empty_floatings(self):
        self._continue_setup_empty_floatings()
        self.__check_result()

    def test_result_inactivated_positions(self):
        self.inactivated_positions = ['A1']
        self._continue_setup()
        self.__check_result()

    def test_invalid_iso(self):
        self._test_invalid_iso()

    def test_invalid_barcode(self):
        self._test_invalid_barcode()

    def test_invalid_user(self):
        self._test_invalid_user()

    def test_serial_worklist_creation_failure(self):
        self.setup_includes_stock_transfer = True
        self.position_data = self.position_data_aliquot_buffer
        self._continue_setup()
        new_well_specs = WellSpecs(label='invalid',
                                   max_volume=5 / VOLUME_CONVERSION_FACTOR,
                                   dead_volume=4 / VOLUME_CONVERSION_FACTOR,
                                   plate_specs=None)
        new_plate_specs = PlateSpecs(label='invalid',
                                     shape=get_384_rack_shape(),
                                     well_specs=new_well_specs)
        for iap in self.iso.iso_aliquot_plates:
            plate = iap.plate
            if plate.barcode == self.new_aliquot_barcode:
                plate.specs = new_plate_specs
                break
        self._test_and_expect_errors('Error during serial transfer execution.')

    def test_check_previous_execution(self):
        self._continue_setup()
        for iap in self.iso.iso_aliquot_plates:
            if iap.plate.barcode == self.new_aliquot_barcode:
                iap.plate.status = get_item_status_managed()
                break
        self._test_and_expect_errors('The transfer for this aliquot plate ' \
                                     'has already been executed before!')

    def test_unexpected_status(self):
        self._test_unexpected_status(iso_status=ISO_STATUS.IN_PROGRESS,
                                     include_stock_transfer=True)
