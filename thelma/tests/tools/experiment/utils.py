"""
Base classes for experiment tests.

AAB
"""
from everest.entities.utils import get_root_aggregate
from thelma.automation.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.semiconstants import ITEM_STATUS_NAMES
from thelma.automation.semiconstants import RACK_SPECS_NAMES
from thelma.automation.semiconstants import get_384_rack_shape
from thelma.automation.semiconstants import get_96_rack_shape
from thelma.automation.semiconstants import get_experiment_metadata_type
from thelma.automation.semiconstants import get_experiment_type_order
from thelma.automation.semiconstants import get_item_status_future
from thelma.automation.semiconstants import get_item_status_managed
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.semiconstants import get_rack_specs_from_reservoir_specs
from thelma.automation.tools.iso.lab.base import FinalLabIsoLayout
from thelma.automation.tools.iso.lab.base import FinalLabIsoPosition
from thelma.automation.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.utils.layouts import LibraryLayout
from thelma.automation.utils.layouts import LibraryLayoutPosition
from thelma.interfaces import IMoleculeDesignLibrary
from thelma.interfaces import IMoleculeDesignPool
from thelma.models.library import LibraryPlate
from thelma.models.library import MoleculeDesignLibrary
from thelma.models.moleculedesign import MoleculeDesignPoolSet
from thelma.models.racklayout import RackLayout
from thelma.automation.semiconstants import PIPETTING_SPECS_NAMES
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.tests.tools.tooltestingutils \
    import ExperimentMetadataReadingTestCase
from thelma.tests.tools.tooltestingutils import FileCreatorTestCase


class EXPERIMENT_TEST_DATA(object):

    TEST_FILE_PATH = 'thelma:tests/tools/experiment/cases/'
    WORKLIST_FILE_PATH = 'thelma:tests/tools/experiment/worklists/'

    CASE_ORDER = 'order'
    CASE_MANUAL = 'manual'
    CASE_OPTI_MM = 'opti_mm' # with mastermix support
    CASE_OPTI_NO = 'opti_no' # opti without mastermix support
    CASE_SCREEN_MM = 'screen_mm' # with mastermix support
    CASE_SCREEN_NO = 'screen_no' # without mastermix support
    CASE_LIBRARY_MM = 'lib_mm' # with mastermix support
    CASE_LIBRARY_NO = 'lib_no' # without mastermix support
    CASE_ISOLESS = 'isoless'

    EXPERIMENT_METADATA_TYPES = {
            CASE_ORDER : EXPERIMENT_SCENARIOS.ORDER_ONLY,
            CASE_MANUAL : EXPERIMENT_SCENARIOS.MANUAL,
            CASE_OPTI_MM : EXPERIMENT_SCENARIOS.OPTIMISATION,
            CASE_OPTI_NO : EXPERIMENT_SCENARIOS.OPTIMISATION,
            CASE_SCREEN_MM : EXPERIMENT_SCENARIOS.SCREENING,
            CASE_SCREEN_NO : EXPERIMENT_SCENARIOS.SCREENING,
            CASE_LIBRARY_MM : EXPERIMENT_SCENARIOS.LIBRARY,
            CASE_LIBRARY_NO : EXPERIMENT_SCENARIOS.LIBRARY,
            CASE_ISOLESS : EXPERIMENT_SCENARIOS.ISO_LESS}

    @classmethod
    def supports_mastermixes(cls, case_name):
        return case_name in (cls.CASE_OPTI_MM, cls.CASE_SCREEN_MM,
                             cls.CASE_LIBRARY_MM)

    @classmethod
    def is_library_testcase(cls, case_name):
        return case_name in (cls.CASE_LIBRARY_MM, cls.CASE_LIBRARY_NO)

    @classmethod
    def get_xls_file_name(cls, case_name):
        return '%s.xls' % (case_name)

    @classmethod
    def get_experiment_metadata_label(cls, case_name):
        return '%s_em' % (case_name)

    @classmethod
    def has_source_plate(cls, case_name):
        return not (case_name == cls.CASE_ISOLESS)

    @classmethod
    def has_experiments(cls, case_name):
        return not (case_name == cls.CASE_ORDER)

    NUMBER_REPLICATES = 2
    DESIGN_RACK_LABELS = ['1', '2']

    FLOATING_MAP = {'md_001' : 205205, 'md_002' : 205206,
                    'md_003' : 205207, 'md_004' : 205208}

    ISO_LABEL = 'testiso1'
    ISO_PLATE_BARCODE = '09999999'
    ISO_PLATE_BARCODE_LIBRARY = '07777711'
    ISO_PLATE_LABEL = ISO_LABEL + '_plate'

    @classmethod
    def get_experiment_label(cls, case_name):
        return '%s_exp' % (case_name)

    EXPERIMENT_PLATE_SPECS = {
            CASE_ORDER : RACK_SPECS_NAMES.STANDARD_96,
            CASE_MANUAL : RACK_SPECS_NAMES.STANDARD_96,
            CASE_OPTI_MM : RACK_SPECS_NAMES.STANDARD_96,
            CASE_OPTI_NO : RACK_SPECS_NAMES.STANDARD_96,
            CASE_SCREEN_MM : RACK_SPECS_NAMES.STANDARD_384,
            CASE_SCREEN_NO : RACK_SPECS_NAMES.STANDARD_384,
            CASE_LIBRARY_MM : RACK_SPECS_NAMES.STANDARD_384,
            CASE_LIBRARY_NO : RACK_SPECS_NAMES.STANDARD_384,
            CASE_ISOLESS : RACK_SPECS_NAMES.STANDARD_384}

    # design rack label - barcode - rack label
    EXPERIMENT_PLATES = {
                '1' : {'08880011' : 'exp1_ds1_c1', '08880012' : 'exp1_ds1_c2'},
                '2' : {'08880021' : 'exp1_ds2_c1', '08880022' : 'exp1_ds1_c2'}}
    FINAL_VOLUME = 35 # ul

    # layout num - pos label - pool ID,
    LIBRARY_POS_DATA = {
                1 : dict(b3=1068472, b4=1068473, c3=1068474, c4=1068475),
                2 : dict(b3=1068480, b4=1068481, c3=1068482)}

    @classmethod
    def get_experiment_plate_final_state_data(cls, case_name):
        # pos label - pool ID, final concentration
        if case_name == cls.CASE_MANUAL:
            fd = dict(b2=[205200, 10], b3=[205200, 20],
                      d2=[205201, 10], d3=[205201, 20],
                      f2=[1056000, 10], f3=[1056000, 20])
            return {'1' : fd, '2' : fd}
        elif case_name == cls.CASE_OPTI_MM:
            fd = dict(b2=[205200, 10], b3=[205200, 20],
                      b4=[205200, 30], b5=[205200, 30],
                      c2=[330001, 10], c3=[330001, 20],
                      c4=[330001, 30], c5=[330001, 30],
                      d2=[None, None], d3=[None, None],
                      d4=[None, None], d5=[None, None])
            return {'1' : fd, '2' : fd}
        elif case_name == cls.CASE_OPTI_NO:
            fd = dict(d2=[None, None], d3=[None, None],
                      d4=[None, None], d5=[None, None])
            fd1 = dict(fd, **dict(b2=[205200, 10], b3=[205200, 20],
                                  b4=[205200, 30], b5=[205200, 30]))
            fd2 = dict(fd, **dict(b2=[1056000, 10], b3=[1056000, 20],
                                  b4=[1056000, 30], b5=[1056000, 30]))
            return {'1' : fd1, '2' : fd2}

        elif case_name == cls.CASE_SCREEN_MM:
            fd = dict(b3=[205200, 10], b4=[205200, 20],
                      c3=[205201, 10], c4=[205201, 20],
                      d3=[205200, 10], d4=[205200, 20],
                      e3=[205201, 10], e4=[205201, 20],
                      f3=[None, None], f4=[None, None],
                      b5=[205205, 10], b6=[205205, 20],
                      c5=[205206, 10], c6=[205206, 20],
                      d5=[205207, 10], d6=[205207, 20],
                      e5=[205208, 10], e6=[205208, 20])
            return {'1' : fd, '2' : fd}
        elif case_name == cls.CASE_SCREEN_NO:
            fd = dict(b3=[205200, 10], b4=[205200, 20],
                      c3=[205201, 10], c4=[205201, 20],
                      d3=[205200, 10], d4=[205200, 20],
                      e3=[205201, 10], e4=[205201, 20],
                      f3=[None, None], f4=[None, None],
                      b5=[205205, 10], b6=[205205, 20],
                      c5=[205206, 10], c6=[205206, 20],
                      d5=[205207, 10], d6=[205207, 20],
                      e5=[205208, 10], e6=[205208, 20])
            return {'1' : fd, '2' : fd}
        elif case_name == cls.CASE_LIBRARY_MM:
            fd = dict(b2=[205201, 10], i10=[205201, 10],
                      d2=[330001, 10], k10=[330001, 10],
                      f2=[1056000, 10], m10=[1056000, 10],
                      h2=[None, None], o10=[None, None],
                      b3=[1068472, 10], b4=[1068473, 10],
                      c3=[1068474, 10], c4=[1068475, 10])
            return {'1' : fd, '2' : fd}
        elif case_name == cls.CASE_LIBRARY_NO:
            fd = dict(b2=[205201, 30], i10=[205201, 30],
                      d2=[330001, 30], k10=[330001, 30],
                      f2=[1056000, 30], m10=[1056000, 30],
                      h2=[None, None], o10=[None, None],
                      b3=[1068472, 30], b4=[1068473, 30],
                      c3=[1068474, 30], c4=[1068475, 30])
            return {'1' : fd, '2' : fd}
        elif case_name == cls.CASE_ISOLESS:
            fd = dict(b2=[None, None], b3=[None, None],
                      c2=[None, None], c3=[None, None],
                      d2=[None, None], d3=[None, None])
            return {'1' : fd, '2' : fd}
        raise NotImplementedError('The values for this case are missing!')

    @classmethod
    def get_source_plate_final_plate_data(cls, case_name):
        # pos label - pool ID, concentration, volume
        if case_name == cls.CASE_OPTI_MM:
            return dict(b2=[205200, 70, 11.2], # ISO conc 560, ISO vol 3.9
                        b3=[205200, 140, 11.2], # ISO conc 1120, ISO vol 3.9,
                        b4=[205200, 210, 15.2], # ISO conc 1680, ISO vol 6.9,
                        c2=[330001, 70, 11.2], # ISO conc 420, ISO vol 5.2,
                        c3=[330001, 140, 11.2], # ISO conc 840, ISO vol 5.2,
                        c4=[330001, 210, 15.2], # ISO conc 1260, ISO vol 9.2,
                        d2=[None, None, 15.2], # ISO vol 6.9,
                        d4=[None, None, 15.2]) # ISO vol 6.9)
        elif case_name == cls.CASE_SCREEN_MM: # ISO volume is always 3.8
            return dict(b3=[205200, 70, 10.4], # ISO conc 560
                        b4=[205200, 140, 10.4], # ISO conc 1120
                        c3=[205201, 70, 10.4], # ISO conc 560
                        c4=[205201, 140, 10.4], # ISO conc 1120
                        d3=[205200, 70, 10.4], # ISO conc 560
                        d4=[205200, 140, 10.4], # ISO conc 1120
                        e3=[205201, 70, 10.4], # ISO conc 560
                        e4=[205201, 140, 10.4], # ISO conc 1120
                        f3=[None, None, 10.4],
                        f4=[None, None, 10.4],
                        b5=[205205, 70, 10.4], # ISO conc 560
                        b6=[205205, 140, 10.4], # ISO conc 1120
                        c5=[205206, 70, 10.4], # ISO conc 560
                        c6=[205206, 140, 10.4], # ISO conc 1120
                        d5=[205207, 70, 10.4], # ISO conc 560
                        d6=[205207, 140, 10.4], # ISO conc 1120
                        e5=[205208, 70, 10.4], # ISO conc 560
                        e6=[205208, 140, 10.4]) # ISO conc 1120
        elif case_name == cls.CASE_LIBRARY_MM:
            # ISO volume is always 4, ISO conc is always 1270 (1269) nM
            return dict(b2=[205201, 69.8, 52.8],
                        d2=[330001, 69.8, 52.8],
                        f2=[1056000, 69.8, 52.8],
                        h2=[None, None, 52.8],
                        i10=[205201, 69.8, 52.8],
                        k10=[330001, 69.8, 52.8],
                        m10=[1056000, 69.8, 52.8],
                        o10=[None, None, 52.8],
                        b3=[1068472, 69.8, 52.8],
                        b4=[1068473, 69.8, 52.8],
                        c3=[1068474, 69.8, 52.8],
                        c4=[1068475, 69.8, 52.8])
        raise NotImplementedError('The values for this case are missing!')

    @classmethod
    def get_number_executed_worklists(cls, case_name):
        if case_name == cls.CASE_OPTI_MM:
            # optimem, reagent, 4 x transfer, 4x cell suspension
            return 1 + 1 + 8
        elif case_name == cls.CASE_SCREEN_MM:
            # optimem, reagent, transfer (cybio), 4x cell suspension
            return 1 + 1 + 1 + 4
        elif case_name == cls.CASE_LIBRARY_MM:
            # optimem, reagent, transfer (cybio), 4x cell suspension
            return 1 + 1 + 1 + 4
        raise NotImplementedError('The values for this case are missing!')

    # case name - list with file names
    WORKLIST_FILES = {
            CASE_OPTI_MM : ['opti_mm_exp_biomek_optimem.csv',
                            'opti_mm_exp_biomek_reagent.csv',
                            'opti_mm_exp_biomek_transfer.csv',
                            'opti_mm_exp_reagent_instructions.csv'],
            CASE_SCREEN_MM : ['screen_mm_exp_biomek_optimem.csv',
                              'screen_mm_exp_biomek_reagent.csv',
                              'screen_mm_exp_cybio_transfers.txt',
                              'screen_mm_exp_reagent_instructions.csv'],
            CASE_LIBRARY_MM : ['lib_mm_exp_biomek_optimem.csv',
                               'lib_mm_exp_biomek_reagent.csv',
                               'lib_mm_exp_cybio_transfers.txt',
                               'lib_mm_exp_reagent_instructions.csv']}

    @classmethod
    def get_worklist_details(cls, case_name):
        ps_biomek = PIPETTING_SPECS_NAMES.BIOMEK
        ps_cybio = PIPETTING_SPECS_NAMES.CYBIO
        type_dil = TRANSFER_TYPES.SAMPLE_DILUTION
        type_trans = TRANSFER_TYPES.SAMPLE_TRANSFER
        type_rack = TRANSFER_TYPES.RACK_SAMPLE_TRANSFER
        # worklist label - pipetting specs, transfer type, num planned transfers,
        # num executed transfers
        if case_name == cls.CASE_OPTI_MM:
            return {'opti_mm_em_optimem' : [ps_biomek, type_dil, 8, 8],
            'opti_mm_em_reagent' : [ps_biomek, type_dil, 8, 8],
            'opti_mm_em-1_biomek_transfer' : [ps_biomek, type_trans, 12, 12],
            'opti_mm_em-1_cellsuspension' : [ps_biomek, type_dil, 12, 12],
            'opti_mm_em-2_biomek_transfer' : [ps_biomek, type_trans, 12, 12],
            'opti_mm_em-2_cellsuspension' : [ps_biomek, type_dil, 12, 12]}
        elif case_name == cls.CASE_SCREEN_MM:
            return {'screen_mm_em_optimem' : [ps_biomek, type_dil, 18, 18],
            'screen_mm_em_reagent' : [ps_biomek, type_dil, 18, 18],
            'screen_mm_em_cybio_transfer' : [ps_cybio, type_rack, 1, 4],
            'screen_mm_em_cellsuspension' : [ps_biomek, type_dil, 18, 18]}
        elif case_name == cls.CASE_LIBRARY_MM:
            return {'lib_mm_em_optimem' : [ps_biomek, type_dil, 12, 12],
            'lib_mm_em_reagent' : [ps_biomek, type_dil, 12, 12],
            'lib_mm_em_cybio_transfer' : [ps_cybio, type_rack, 1, 4],
            'lib_mm_em_cellsuspension' : [ps_biomek, type_dil, 12, 12]}
        raise NotImplementedError('The values for this case are missing!')

    WORKLIST_MARKER_OPTIMEM = 'optimem'
    WORKLIST_MARKER_REAGENT = 'reagent'
    WORKLIST_MARKER_TRANSFER = 'transfer'
    WORKLIST_MARKER_CELLS = 'cellsuspension'


class ExperimentTestCase(ExperimentMetadataReadingTestCase,
                         FileCreatorTestCase):

    def set_up(self):
        ExperimentMetadataReadingTestCase.set_up(self)
        self.TEST_FILE_PATH = EXPERIMENT_TEST_DATA.TEST_FILE_PATH
        self.WL_PATH = EXPERIMENT_TEST_DATA.WORKLIST_FILE_PATH
        self.case = None
        self.library_generator = None
        self.transfection_layout = None
        self.experiment = None
        self.iso_plate = None
        self.exp_plate_map = dict()
        self.missing_floating_placeholder = None
        self.missing_floating_pool_id = None

    def tear_down(self):
        ExperimentMetadataReadingTestCase.tear_down(self)
        del self.WL_PATH
        del self.case
        del self.library_generator
        del self.transfection_layout
        del self.experiment
        del self.iso_plate
        del self.exp_plate_map
        del self.missing_floating_placeholder
        del self.missing_floating_pool_id

    def _load_scenario(self, case_name):
        self.case = case_name
        if EXPERIMENT_TEST_DATA.is_library_testcase(case_name):
            self.library_generator = TestLibraryGenerator()
        self._continue_setup()

    def _continue_setup(self, file_name=None):
        if file_name is None:
            file_name = EXPERIMENT_TEST_DATA.get_xls_file_name(self.case)
        generator = ExperimentMetadataReadingTestCase._continue_setup(self,
                                                  file_name=file_name)
        self.transfection_layout = generator.get_source_layout()
        if EXPERIMENT_TEST_DATA.has_source_plate(self.case):
            self.__create_iso_and_plate()
        if EXPERIMENT_TEST_DATA.has_experiments(self.case):
            self.__create_experiment_and_plates()
        self._create_tool()

    def _set_experiment_metadadata(self):
        em_type = get_experiment_metadata_type(
                    EXPERIMENT_TEST_DATA.EXPERIMENT_METADATA_TYPES[self.case])
        self.experiment_metadata = self._create_experiment_metadata(
            label=EXPERIMENT_TEST_DATA.get_experiment_metadata_label(self.case),
            experiment_metadata_type=em_type, ticket_number=123,
            number_replicates=EXPERIMENT_TEST_DATA.NUMBER_REPLICATES)

    def __create_iso_and_plate(self):
        layout = self._generate_iso_layout(EXPERIMENT_TEST_DATA.FLOATING_MAP)
        pool_set = self._generate_pool_set_from_iso_layout(layout)
        iso = self._create_lab_iso(label=EXPERIMENT_TEST_DATA.ISO_LABEL,
                        rack_layout=layout.create_rack_layout(),
                        molecule_design_pool_set=pool_set,
                        iso_request=self.experiment_metadata.lab_iso_request)
        if self.library_generator is not None:
            self.__fill_library_plates_and_set_iso_plate(iso)
        else:
            self.iso_plate = self._generate_iso_plate(layout, iso)

    def _generate_iso_layout(self, floating_map):
        layout = FinalLabIsoLayout(shape=self.transfection_layout.shape)
        for rack_pos, ir_pos in self.transfection_layout.iterpositions():
            if ir_pos.is_untreated_type or ir_pos.is_library: continue
            pool = ir_pos.molecule_design_pool
            if floating_map.has_key(pool):
                if pool == self.missing_floating_placeholder: continue
                pool_id = floating_map[pool]
                pool = self._get_pool(pool_id)
            if ir_pos.is_mock:
                conc = None
            else:
                conc = ir_pos.iso_concentration
            fp = FinalLabIsoPosition(rack_position=rack_pos,
                        molecule_design_pool=pool, volume=ir_pos.iso_volume,
                        concentration=conc, position_type=ir_pos.position_type)
            layout.add_position(fp)
        return layout

    def _generate_pool_set_from_iso_layout(self, layout):
        pools = set()
        for fp in layout.working_positions():
            if fp.is_floating:
                pools.add(fp.molecule_design_pool)
        if len(pools) < 1: return None
        return self._create_molecule_design_pool_set(
                                    molecule_type=list(pools)[0].molecule_type,
                                    molecule_design_pools=pools)

    def __fill_library_plates_and_set_iso_plate(self, iso):
        source_vol = float(self.library_generator.VOLUME_IN_UL)
        source_conc = float(self.library_generator.CONC_IN_UL)
        for layout_num, lib_plate in self.library_generator.\
                                      library_plates.iteritems():
            pool_data = EXPERIMENT_TEST_DATA.LIBRARY_POS_DATA[layout_num]
            plate = lib_plate.rack
            for well in plate.containers:
                rack_pos = well.location.position
                ir_pos = self.transfection_layout.get_working_position(rack_pos)
                if ir_pos is not None and ir_pos.is_mock:
                    self._create_test_sample(container=well, pool=None,
                                 volume=source_vol, target_conc=None)
                    continue
                elif ir_pos is not None and ir_pos.is_fixed:
                    self._create_test_sample(container=well,
                                pool=ir_pos.molecule_design_pool,
                                volume=source_vol, target_conc=source_conc)
                    continue
                pos_label = rack_pos.label.lower()
                if not pool_data.has_key(pos_label): continue
                pool_id = pool_data[pos_label]
                pool = self._get_pool(pool_id)
                self._create_test_sample(container=well, pool=pool,
                                volume=source_vol, target_conc=source_conc)

        lib_plate = self.library_generator.library_plates[1]
        self.iso_plate = lib_plate.rack
        lib_plate.lab_iso = iso

    def _generate_iso_plate(self, layout, iso):
        rs = self.experiment_metadata.lab_iso_request.iso_plate_reservoir_specs
        ps = get_rack_specs_from_reservoir_specs(rs)
        plate = ps.create_rack(status=get_item_status_managed(),
                            label=EXPERIMENT_TEST_DATA.ISO_PLATE_LABEL,
                            barcode=EXPERIMENT_TEST_DATA.ISO_PLATE_BARCODE)
        for well in plate.containers:
            rack_pos = well.location.position
            fp = layout.get_working_position(rack_pos)
            if fp is None: continue
            pool = fp.molecule_design_pool
            conc = fp.concentration
            if fp.is_mock:
                pool = None
                conc = None
            self._create_test_sample(well, pool, fp.volume, conc)
        iso.add_aliquot_plate(plate)
        return plate

    def __create_experiment_and_plates(self):
        ps_name = EXPERIMENT_TEST_DATA.EXPERIMENT_PLATE_SPECS[self.case]
        plate_specs = RACK_SPECS_NAMES.from_name(ps_name)
        exp_label = EXPERIMENT_TEST_DATA.get_experiment_label(self.case)
        self.experiment = self._create_experiment(label=exp_label,
                destination_rack_specs=plate_specs, source_rack=self.iso_plate,
                experiment_design=self.experiment_metadata.experiment_design)
        self._generate_experiment_plates(plate_specs,
                                         EXPERIMENT_TEST_DATA.EXPERIMENT_PLATES)

    def _generate_experiment_plates(self, plate_specs, plate_map,
                                    experiment=None):
        if experiment is None: experiment = self.experiment
        drs = self.experiment_metadata.experiment_design.experiment_design_racks
        status = get_item_status_future()
        for design_rack in drs:
            labels = plate_map[design_rack.label]
            for barcode, label in labels.iteritems():
                plate = plate_specs.create_rack(label=label, status=status,
                                                barcode=barcode)
                self._create_experiment_rack(design_rack=design_rack,
                                         rack=plate, experiment=experiment)
                self.exp_plate_map[plate.barcode] = plate

    def _check_no_worklist_executions(self):
        em_series = self.experiment_metadata.experiment_design.worklist_series
        self.__check_no_execution_in_worklist_series(em_series)
        for dr in self.experiment_metadata.experiment_design.\
                                                experiment_design_racks:
            self.__check_no_execution_in_worklist_series(dr.worklist_series)

    def __check_no_execution_in_worklist_series(self, worklist_series):
        if worklist_series is not None:
            for worklist in worklist_series:
                self.assert_equal(len(worklist.executed_worklists), 0)

    def _check_iso_aliquot_plate_update(self, source_plate_barcodes=None):
        if source_plate_barcodes is None:
            source_plate_barcodes = {EXPERIMENT_TEST_DATA.ISO_PLATE_BARCODE}
        ir = self.experiment_metadata.lab_iso_request
        if ir is not None:
            for iso in ir.isos:
                for iap in iso.iso_aliquot_plates:
                    if iap.rack.barcode in source_plate_barcodes:
                        self.assert_true(iap.has_been_used)
                    else:
                        self.assert_false(iap.has_been_used)

    def _check_final_plates_final_state(self, final_plate_data=None,
                                        experiment_racks=None):
        if experiment_racks is None:
            experiment_racks = self.experiment.experiment_racks
        self.assert_equal(len(experiment_racks), 4)
        if final_plate_data is None:
            final_plate_data = EXPERIMENT_TEST_DATA.\
                       get_experiment_plate_final_state_data(self.case)
        for edr in experiment_racks:
            layout_data = final_plate_data[edr.design_rack.label]
            plate = edr.rack
            self.assert_equal(plate.status.name, ITEM_STATUS_NAMES.MANAGED)
            for well in plate.containers:
                pos_label = well.location.position.label.lower()
                sample_info = '%s in plate %s' % (pos_label, plate.label)
                if not layout_data.has_key(pos_label):
                    if not well.sample is None:
                        raise AssertionError('Unexpected position in %s!' \
                                             % (sample_info))
                    continue
                # pos label - pool ID, final concentration
                pos_data = layout_data[pos_label]
                pool_id = pos_data[0]
                sample = well.sample
                if pool_id is not None and \
                                    pool_id == self.missing_floating_pool_id:
                    if not sample is None:
                        msg = 'Unexpected sample for missing floating in %s.' \
                              % (sample_info)
                        raise AssertionError(msg)
                    continue
                self._compare_sample_volume(sample,
                            EXPERIMENT_TEST_DATA.FINAL_VOLUME, sample_info)
                if pool_id is None or pool_id == self.missing_floating_pool_id:
                    self.assert_equal(len(sample.sample_molecules), 0)
                    continue
                pool = self._get_pool(pool_id)
                conc = round((float(pos_data[1]) / pool.number_designs), 1)
                self._compare_sample_and_pool(sample, pool, conc, sample_info)

    def _check_source_plate_unaltered(self, iso_plate=None, floating_map=None):
        if EXPERIMENT_TEST_DATA.has_source_plate(self.case):
            self.__check_source_plate_unaltered(iso_plate, floating_map)
        else:
            self.assert_is_none(self.experiment.source_rack)

    def __check_source_plate_unaltered(self, iso_plate=None, floating_map=None):
        if iso_plate is None:
            iso_plate = self.iso_plate
            layout_num = 1
        else:
            layout_num = 2
        if floating_map is None:
            floating_map = EXPERIMENT_TEST_DATA.FLOATING_MAP
        self.assert_equal(iso_plate.status.name, ITEM_STATUS_NAMES.MANAGED)
        for well in iso_plate.containers:
            rack_pos = well.location.position
            pos_label = rack_pos.label.lower()
            sample_info = '%s in plate source plate' % (pos_label)
            ir_pos = self.transfection_layout.get_working_position(rack_pos)
            if ir_pos is None or ir_pos.is_untreated_type:
                if not well.sample is None:
                    raise AssertionError('Unexpected position in %s!' \
                                         % (sample_info))
                continue
            sample = well.sample
            if ir_pos.is_mock:
                self.assert_equal(len(sample.sample_molecules), 0)
                continue
            elif ir_pos.is_library:
                lookup = EXPERIMENT_TEST_DATA.LIBRARY_POS_DATA[layout_num]
                if lookup.has_key(pos_label):
                    pool = self._get_pool(lookup[pos_label])
                else:
                    if not sample is None:
                        msg = 'Unexpected missing library sample %s' \
                              % (sample_info)
                        raise AssertionError(msg)
                    continue
            elif ir_pos.is_floating:
                placeholder = ir_pos.molecule_design_pool
                if placeholder == self.missing_floating_placeholder:
                    if sample is not None:
                        raise AssertionError('Unexpected pool for missing ' \
                                             'floating in %s.' % (sample_info))
                    continue
                pool_id = floating_map[placeholder]
                pool = self._get_pool(pool_id)
            else:
                pool = ir_pos.molecule_design_pool
            conc = round(float(ir_pos.iso_concentration) / pool.number_designs,
                         1)
            self._compare_sample_volume(sample, ir_pos.iso_volume, sample_info)
            self._compare_sample_and_pool(sample, pool, conc, sample_info)

    def _test_case_order(self):
        self._load_scenario(EXPERIMENT_TEST_DATA.CASE_ORDER)
        self._test_and_expect_errors('The experiment must be a Experiment ' \
                                     'object (obtained: NoneType).')
        ed = self._create_experiment_design(rack_shape=get_96_rack_shape(),
                            experiment_metadata=self.experiment_metadata)
        self.experiment = self._create_experiment(experiment_design=ed)
        self._test_and_expect_errors('The type of this experiment is not ' \
                                     'supported by this tool')

    def _set_up_missing_floating(self):
        self.missing_floating_placeholder = 'md_004'
        self.missing_floating_pool_id = 205208
        self.case = EXPERIMENT_TEST_DATA.CASE_SCREEN_MM

    def _check_worklist_files(self, exp_file_names=None):
        if exp_file_names is None:
            exp_file_names = EXPERIMENT_TEST_DATA.WORKLIST_FILES[self.case]
        zip_stream = self.tool.get_result()
        archive = self._get_zip_archive(zip_stream)
        namelist = archive.namelist()
        self.assert_equal(sorted(namelist), sorted(exp_file_names))
        for fn in exp_file_names:
            tool_content = archive.read(fn)
            if fn.endswith('.csv'):
                try:
                    self._compare_csv_file_content(tool_content, fn)
                except AssertionError as e:
                    raise AssertionError('Error in file "%s": %s' % (fn, e))
            else:
                try:
                    self._compare_txt_file_content(tool_content, fn)
                except AssertionError as e:
                    raise AssertionError('Error in file "%s": %s' % (fn, e))

    def _test_invalid_input_values(self):
        if self.case is None: self.case = EXPERIMENT_TEST_DATA.CASE_MANUAL
        self._load_scenario(self.case)
        ori_exp = self.experiment
        self.experiment = None
        self._test_and_expect_errors('The experiment must be a Experiment ' \
                                     'object (obtained: NoneType).')
        self.experiment = ori_exp


    def _test_invalid_experiment_type(self):
        if self.case is None: self.case = EXPERIMENT_TEST_DATA.CASE_MANUAL
        self._load_scenario(self.case)
        self.experiment_metadata.experiment_metadata_type = \
                                             get_experiment_type_order()
        self._test_and_expect_errors('The type of this experiment is not ' \
            'supported by this tool (given: ISO without experiment')

    def _test_unknown_design_rack(self):
        if self.case is None: self.case = EXPERIMENT_TEST_DATA.CASE_MANUAL
        self._load_scenario(self.case)
        for edr in self.experiment.experiment_racks:
            if not edr.rack.barcode == '08880011': continue
            dr = self._create_experiment_design_rack(label='3')
            edr.design_rack = dr
            break
        self._test_and_expect_errors('Unknown design rack "3" for experiment ' \
                                     'rack "08880011"!')

    def _test_previous_executor_with_source_plate(self):
        if self.case is None: self.case = EXPERIMENT_TEST_DATA.CASE_MANUAL
        self._load_scenario(self.case)
        for edr in self.experiment.experiment_racks:
            if not edr.rack.barcode == '08880011': continue
            edr.rack.status = get_item_status_managed()
            break
        self._test_and_expect_errors('The database update for source plate ' \
                                     '09999999 has already been made before!')

    def _test_previous_execution_without_source_plate(self):
        self._load_scenario(EXPERIMENT_TEST_DATA.CASE_ISOLESS)
        for edr in self.experiment.experiment_racks:
            if not edr.rack.barcode == '08880011': continue
            edr.rack.status = get_item_status_managed()
            break
        self._test_and_expect_errors('The database update for experiment ' \
                            '"isoless_exp" has already been made before!')

    def _test_verification_error(self):
        if self.case is None: self.case = EXPERIMENT_TEST_DATA.CASE_MANUAL
        self._load_scenario(self.case)
        self.experiment_metadata.lab_iso_request.rack_layout = RackLayout()
        self._test_and_expect_errors('Error when trying to verify source rack!')

    def _test_no_verification(self):
        if self.case is None: self.case = EXPERIMENT_TEST_DATA.CASE_MANUAL
        self._load_scenario(self.case)
        for well in self.iso_plate.containers:
            if well.sample is None:
                pool = self._get_pool(205215)
                self._create_test_sample(well, pool, 1, 10)
                break
        self._test_and_expect_errors('The source rack does not match the ' \
                                     'ISO request layout!')

    def _check_source_plate_final_state(self, source_plate_data=None,
                                        iso_plate=None):
        if iso_plate is None: iso_plate = self.iso_plate
        self.assert_equal(iso_plate.status.name, ITEM_STATUS_NAMES.MANAGED)
        # pos label - pool ID, concentration, volume
        if source_plate_data is None:
            source_plate_data = EXPERIMENT_TEST_DATA.\
                                get_source_plate_final_plate_data(self.case)
        for well in iso_plate.containers:
            pos_label = well.location.position.label.lower()
            sample_info = '%s in source plate' % (pos_label)
            if not source_plate_data.has_key(pos_label):
                if not well.sample is None:
                    raise AssertionError('Unexpected position in %s!' \
                                             % (sample_info))
                continue
            pos_data = source_plate_data[pos_label]
            sample = well.sample
            pool_id = pos_data[0]
            if pool_id is not None and pool_id == self.missing_floating_pool_id:
                if sample is not None:
                    raise AssertionError('Unexpected pool for missing ' \
                                         'floating in %s.' % (sample_info))
                continue
            exp_vol = pos_data[2]
            self._compare_sample_volume(sample, exp_vol, sample_info)
            if pool_id is None:
                self.assert_equal(len(sample.sample_molecules), 0)
                continue
            pool = self._get_pool(pool_id)
            conc = round(float(pos_data[1]) / pool.number_designs, 1)
            self._compare_sample_and_pool(sample, pool, conc, sample_info)


class TestLibraryGenerator(object):
    """
    A smaller version of the poollib library that is faster to load
    and easier to handle during testing.
    """

    LIB_NAME = 'testlib'
    VOLUME_IN_UL = 4 # equal to poollib
    CONC_IN_UL = 1270 # equal to poollib

    # 7 pool = 2 layouts
    POOL_IDS = {1 : [1068472, 1068473, 1068474, 1068475],
                2 : [1068480, 1068481, 1068482]}
    # The barcodes for the library plates.
    PLATE_BARCODES = {1 : '07777711', 2 : '07777721'}

    #: The number of library plates for each layout.
    NUM_LIBRARY_PLATES = 2

    def __init__(self):
        self.library = None
        self.library_plates = {1 : None, 2 : None}
        self.__create_and_store()

    def __create_and_store(self):
        lib = self.__create_library()
        self.__create_library_plates(lib)
        lib_agg = get_root_aggregate(IMoleculeDesignLibrary)
        lib_agg.add(lib)
        self.library = lib

    def __create_library(self):
        layout = self.get_library_layout()
        pool_set = self.get_pool_set()
        vol = self.VOLUME_IN_UL / VOLUME_CONVERSION_FACTOR
        conc = self.CONC_IN_UL / CONCENTRATION_CONVERSION_FACTOR
        lib = MoleculeDesignLibrary(molecule_design_pool_set=pool_set,
            label=self.LIB_NAME, final_volume=vol,
            final_concentration=conc, number_layouts=2,
            rack_layout=layout.create_rack_layout())
        return lib

    @classmethod
    def get_library_layout(cls):
        layout = LibraryLayout(shape=get_384_rack_shape())
        for pos_label in ('b3', 'b4', 'c3', 'c4'):
            rack_pos = get_rack_position_from_label(pos_label)
            lib_pos = LibraryLayoutPosition(rack_position=rack_pos)
            layout.add_position(lib_pos)
        return layout

    @classmethod
    def get_pool_set(cls, layout_number=None):
        pool_ids = []
        if layout_number is None:
            for pids in cls.POOL_IDS.values():
                pool_ids.extend(pids)
        else:
            pool_ids = cls.POOL_IDS[layout_number]
        mt = None
        pool_agg = get_root_aggregate(IMoleculeDesignPool)
        pools = set()
        for pool_id in pool_ids:
            pool = pool_agg.get_by_id(pool_id)
            if mt is None: mt = pool.molecule_type
            pools.add(pool)
        return MoleculeDesignPoolSet(molecule_type=mt,
                                     molecule_design_pools=pools)

    def __create_library_plates(self, lib):
        plate_specs = RACK_SPECS_NAMES.from_name(RACK_SPECS_NAMES.STANDARD_384)
        status = get_item_status_managed()
        for layout_num in (1, 2):
            rack_label = '%s_l%i_r%i' % (self.LIB_NAME, layout_num, 1)
            barcode = self.PLATE_BARCODES[layout_num]
            plate = plate_specs.create_rack(label=rack_label,
                                            barcode=barcode, status=status)
            lib_plate = LibraryPlate(molecule_design_library=lib,
                        rack=plate, layout_number=layout_num,
                        has_been_used=True)
            self.library_plates[layout_num] = lib_plate

    def get_library(self):
        return self.library
