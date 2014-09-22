"""
Tests for custom liquid transfer plan tools.

AAB
"""
from everest.entities.utils import get_root_aggregate
from thelma.automation.semiconstants import RESERVOIR_SPECS_NAMES
from thelma.automation.semiconstants import get_item_status_future
from thelma.automation.semiconstants import get_rack_specs_from_reservoir_specs
from thelma.automation.semiconstants import get_reservoir_spec
from thelma.automation.tools.worklists.custom import CustomLiquidTransferTool
from thelma.automation.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.interfaces import IMoleculeDesign
from thelma.interfaces import IOrganization
from thelma.interfaces import IPlate
from thelma.interfaces import IUser
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.sample import Molecule
from thelma.oldtests.tools.tooltestingutils import FileCreatorTestCase
from thelma.oldtests.tools.tooltestingutils import FileReadingTestCase


class _CustomLiquidTransferPlanToolTestCase(FileReadingTestCase):

    TEST_CLS = CustomLiquidTransferTool

    def set_up(self):
        FileReadingTestCase.set_up(self)
        self.VALID_FILE = 'valid_file.xls'
        self.TEST_FILE_PATH = 'thelma:tests/tools/worklists/custom/'
        self.mode = None
        self.plates = dict(int=None, t1=None, t2=None)
        self.md_map = {11 : self._get_entity(IMoleculeDesign, '11'),
                       12 : self._get_entity(IMoleculeDesign, '12'),
                       13 : self._get_entity(IMoleculeDesign, '13')}
        self.start_vols = dict(int=25, t1=2, t2=0)
        self.rs_names = dict(int=RESERVOIR_SPECS_NAMES.STANDARD_96,
                             t1=RESERVOIR_SPECS_NAMES.STANDARD_384,
                             t2=RESERVOIR_SPECS_NAMES.STANDARD_384)
        self.barcodes = dict(int='09999990', t1='09999998', t2='09999999')
        # transfer data for each worklist: source well - target wells, volumes
        self.transfer_data = {
                1 : dict(A1=dict(B2=25, B3=25)),
                2 : dict(A1=dict(B2=2, B3=2, E2=2, E3=2)),
                3 : dict(B2=dict(B2=2, B3=2), B3=dict(E2=4, E3=4))}

        # for each plate: pos label - md ID, starting conc
        self.start_data = {
            'int' : dict(B2=[11, 24], B3=[11, 48]),
            't1' : dict(B2=[12, 12], B3=[13, 12], E2=[12, 24], E3=[13, 24]),
            't2' : dict()}
        # for each plate: pos label - vol, mdIDs, conc
        self.result_data = {
            'int' : dict(B2=[42, {11 : 12}], B3=[34, {11 : 24}]),
            't1' : dict(B2=[6, {11 : 4, 12 : 4}], B3=[6, {11 : 4, 13 : 4}],
                        E2=[8, {11 : 12, 12 : 6}], E3=[8, {11 : 12, 13 : 6}]),
            't2' : dict(B2=[4, {11 : 6}], B3=[4, {11 : 6}],
                        E2=[6, {11 : 16}], E3=[6, {11 : 16}])}

    def tear_down(self):
        FileReadingTestCase.tear_down(self)
        del self.plates
        del self.md_map
        del self.barcodes
        del self.start_vols
        del self.rs_names
        del self.transfer_data
        del self.start_data
        del self.result_data

    def _create_tool(self):
        self.tool = CustomLiquidTransferTool(stream=self.stream,
                                             mode=self.mode,
                                             user=self.executor_user)

    def _continue_setup(self, file_name=None):
        FileReadingTestCase._continue_setup(self, file_name=file_name)
        self.__create_plates()
        self._create_tool()

    def __create_plates(self):
        plate_agg = get_root_aggregate(IPlate)
        supplier = self._get_entity(IOrganization)
        for name, start_vol in self.start_vols.iteritems():
            rs = get_reservoir_spec(self.rs_names[name])
            ps = get_rack_specs_from_reservoir_specs(rs)
            plate = ps.create_rack(label=name, status=get_item_status_future())
            barcode = self.barcodes[name]
            if not barcode is None:
                plate.barcode = barcode
                plate_agg.add(plate)
            start_map = self.start_data[name]
            vol = start_vol / VOLUME_CONVERSION_FACTOR
            for well in plate.containers:
                pos_label = well.location.position.label
                if not start_map.has_key(pos_label): continue
                pos_data = start_map[pos_label]
                sample = well.make_sample(vol)
                md = self.md_map[pos_data[0]]
                mol = Molecule(molecule_design=md, supplier=supplier)
                conc = pos_data[1] / CONCENTRATION_CONVERSION_FACTOR
                sample.make_sample_molecule(molecule=mol, concentration=conc)
            self.plates[name] = plate

    def _test_invalid_input_values(self):
        self._continue_setup()
        ori_stream = self.stream
        self.stream = None
        self._test_and_expect_errors('The stream must not be None!')
        self.stream = ori_stream
        self.mode = None
        self._test_and_expect_errors('The mode must be a str')
        self.mode = 'invalid'
        self._test_and_expect_errors('Unexpected mode: invalid.')
        self.mode = self.TEST_CLS.MODE_EXECUTE

    def _test_parsing_error(self):
        self._continue_setup('parsing_error.xls')
        self._test_and_expect_errors('Error when trying to parse file')

    def _test_series_tool_error(self, msg):
        self.start_vols['int'] = 0
        self._continue_setup()
        self._test_and_expect_errors(msg)


class CustomLiquidTransferWorklistWriterTestCase(
                                    _CustomLiquidTransferPlanToolTestCase,
                                    FileCreatorTestCase):

    def set_up(self):
        _CustomLiquidTransferPlanToolTestCase.set_up(self)
        self.WL_PATH = self.TEST_FILE_PATH
        self.mode = CustomLiquidTransferTool.MODE_PRINT_WORKLISTS

    def tear_down(self):
        _CustomLiquidTransferPlanToolTestCase.tear_down(self)
        del self.WL_PATH

    def test_result(self):
        self._continue_setup()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        zip_archive = self._get_zip_archive(zip_stream)
        self.assert_equal(len(zip_archive.namelist()), 3)
        for fn in zip_archive.namelist():
            tool_content = zip_archive.read(fn)
            self._compare_csv_file_content(tool_content, fn)

    def test_invalid_input_values(self):
        self._test_invalid_input_values()

    def test_parsing_error(self):
        self._test_parsing_error()

    def test_serial_writer_error(self):
        self._test_series_tool_error('Error when running serial worklist ' \
                                     'printer')


class CustomLiquidTransferExecutorTestCase(
                                    _CustomLiquidTransferPlanToolTestCase):

    def set_up(self):
        _CustomLiquidTransferPlanToolTestCase.set_up(self)
        self.executor_user = self._get_entity(IUser, 'it')
        self.mode = CustomLiquidTransferTool.MODE_EXECUTE

    def test_result(self):
        self._continue_setup()
        executed_worklists = self.tool.get_result()
        self.assert_is_not_none(executed_worklists)
        self.__check_executed_worklists(executed_worklists)
        self.__check_plates()

    def __check_executed_worklists(self, executed_worklists):
        self.assert_equal(len(executed_worklists), 5)
        for ew in executed_worklists:
            pw = ew.planned_worklist
            num = int(pw.label[-1:])
            transfer_items = self.transfer_data[num]
            num_transfers = 0
            for transfers in transfer_items.values():
                num_transfers += len(transfers)
            self.assert_equal(len(pw.planned_liquid_transfers), num_transfers)
            elts = ew.executed_liquid_transfers
            self.assert_equal(len(elts), num_transfers)
            if num == 1 or num == 2:
                transfer_type = TRANSFER_TYPES.SAMPLE_DILUTION
                if num == 1:
                    diluent = 'buffer'
                    vol = 25
                else:
                    diluent = 'medium'
                    vol = 2
                trg_labels = []
                for elt in elts:
                    self._check_executed_transfer(elt, transfer_type)
                    plt = elt.planned_liquid_transfer
                    self.assert_equal(plt.diluent_info, diluent)
                    plt_vol = plt.volume * VOLUME_CONVERSION_FACTOR
                    self.assert_equal(plt_vol, vol)
                    trg_labels.append(plt.target_position.label)
                dilutions = transfer_items['A1']
                self.assert_equal(sorted(dilutions.keys()),
                                  sorted(trg_labels))
            elif num == 3:
                values = dict()
                for elt in elts:
                    plt = elt.planned_liquid_transfer
                    self._check_executed_transfer(elt,
                                                TRANSFER_TYPES.SAMPLE_TRANSFER)
                    src_label = plt.source_position.label
                    if values.has_key(src_label):
                        transfer_map = values[src_label]
                    else:
                        transfer_map = dict()
                        values[src_label] = transfer_map
                    trg_label = plt.target_position.label
                    vol = plt.volume * VOLUME_CONVERSION_FACTOR
                    transfer_map[trg_label] = vol
                self.assert_equal(values, transfer_items)
            else:
                raise ValueError('Unknown worklist number: %i' % num)

    def __check_plates(self):
        for name, well_data in self.result_data.iteritems():
            plate = self.plates[name]
            for well in plate.containers:
                pos_label = well.location.position.label
                if not well_data.has_key(pos_label):
                    self.assert_is_none(well.sample)
                    continue
                sample = well.sample
                self._compare_sample_volume(sample, well_data[pos_label][0])
                exp_sms = well_data[pos_label][1]
                sms = dict()
                for sm in sample.sample_molecules:
                    sms[sm.molecule.molecule_design.id] = \
                            sm.concentration * CONCENTRATION_CONVERSION_FACTOR
                self.assert_equal(sms, exp_sms)

    def test_invalid_input_values(self):
        self._test_invalid_input_values()
        self.executor_user = None
        self._test_and_expect_errors('The user must be a User object')

    def test_parsing_error(self):
        self._test_parsing_error()

    def test_serial_writer_error(self):
        self._test_series_tool_error('Error when running serial worklist ' \
                                     'executor!')
