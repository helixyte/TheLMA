"""
Base classes for lab ISO testing.
"""
from thelma.tests.tools.tooltestingutils import ExperimentMetadataReadingTestCase
from thelma.automation.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.semiconstants import get_experiment_metadata_type
from thelma.models.experiment import ExperimentMetadata
from thelma.interfaces import ISubproject
from thelma.automation.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.utils.iso import IsoRequestPosition
from thelma.automation.utils.iso import IsoRequestLayout
from thelma.automation.tools.iso.lab.base import LabIsoPrepLayoutConverter
from thelma.tests.tools.tooltestingutils import SilentLog
from thelma.automation.tools.iso.lab.base import FinalLabIsoLayoutConverter
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.automation.semiconstants import get_pipetting_specs_biomek
from thelma.automation.semiconstants import get_pipetting_specs_cybio
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.utils.base import are_equal_values
from thelma.automation.utils.base import get_trimmed_string
from thelma.automation.tools.iso.lab.base import DILUENT_INFO
from thelma.automation.utils.layouts import TransferTarget

class LAB_ISO_TEST_CASES(object):

    #: no job preparation step (no floatings), all samples are transferred
    #: directly to the aliquot plate, no dilutions with buffer (all pools
    #: in stock concentration)
    CASE_ORDER_ONLY = 'order_only'
    #: no job preparation step (no floatings), all samples are transferred
    #: directly to the aliquot plate
    CASE_NO_JOB_DIRECT = 'no_job_direct'
    #: no job step (no floatings), 1 intermediate preparation step for
    #: all samples
    CASE_NO_JOB_1_PREP = 'no_job_one_prep'
    #: no job step, 1 intermediate preparation step for some samples,
    #: large variations in target volume and concentration, incl.
    #: one dilution series in the aliquot plate
    CASE_NO_JOB_COMPLEX = 'no_job_complex'

    #: 96-well layout that can be transferred with the CyBio
    CASE_ASSOCIATION_96 = 'association_96'
    #: 384-well association layout with job processing first, one concentration
    #: for all samples
    CASE_ASSOCIATION_SIMPLE = 'association_simple'
    #: 384-well association layout with job processing first with 2 target
    #: aliquot plates, one concentration for all samples
    CASE_ASSOCIATION_2_ALIQUOTS = 'association_2_aliquots'
    #: 384-well association layout with job processing coming second, one
    #: concentration for all samples
    CASE_ASSOCIATION_JOB_LAST = 'association_job_last'
    #: 384-well association layout with job processing first, two concentrations
    #: for each samples
    CASE_ASSOCIATION_SEVERAL_CONC = 'association_several_conc'

    #: Standard library case with controls one conc and one target aliquot
    CASE_LIBRARY = 'library'
    #: Standard library case with controls in different concentrations and
    #: one target aliquot
    CASE_LIBRARY_SEVERAL_CONC = 'library_several_conc'
    #: Library case with with controls in different concentrations and
    #: 2 target aliquot
    CASE_LIBRARY_2_ALIQUOTS = 'library_2_aliquots'

    NON_LIBRARY_CASES = [CASE_ORDER_ONLY, CASE_NO_JOB_DIRECT, CASE_NO_JOB_1_PREP,
             CASE_NO_JOB_COMPLEX, CASE_ASSOCIATION_SIMPLE, CASE_ASSOCIATION_96,
             CASE_ASSOCIATION_2_ALIQUOTS, CASE_ASSOCIATION_JOB_LAST,
             CASE_ASSOCIATION_SEVERAL_CONC]
    LIBRARY_CASES = [CASE_LIBRARY, CASE_LIBRARY_2_ALIQUOTS,
                     CASE_LIBRARY_SEVERAL_CONC]
    ALL_CASES = NON_LIBRARY_CASES + LIBRARY_CASES

    __EXPERIMENT_SCENARIOS = {
            CASE_ORDER_ONLY : EXPERIMENT_SCENARIOS.ORDER_ONLY,
            CASE_NO_JOB_DIRECT : EXPERIMENT_SCENARIOS.MANUAL,
            CASE_NO_JOB_1_PREP : EXPERIMENT_SCENARIOS.MANUAL,
            CASE_NO_JOB_COMPLEX : EXPERIMENT_SCENARIOS.MANUAL,
            CASE_ASSOCIATION_SIMPLE : EXPERIMENT_SCENARIOS.SCREENING,
            CASE_ASSOCIATION_96 : EXPERIMENT_SCENARIOS.SCREENING,
            CASE_ASSOCIATION_2_ALIQUOTS : EXPERIMENT_SCENARIOS.SCREENING,
            CASE_ASSOCIATION_JOB_LAST : EXPERIMENT_SCENARIOS.SCREENING,
            CASE_ASSOCIATION_SEVERAL_CONC : EXPERIMENT_SCENARIOS.SCREENING,
            CASE_LIBRARY : EXPERIMENT_SCENARIOS.LIBRARY,
            CASE_LIBRARY_2_ALIQUOTS : EXPERIMENT_SCENARIOS.LIBRARY,
            CASE_LIBRARY_SEVERAL_CONC : EXPERIMENT_SCENARIOS.LIBRARY}

    __ALIQUOT_PLATE_SHAPE = {
            CASE_ORDER_ONLY : RACK_SHAPE_NAMES.SHAPE_96,
            CASE_NO_JOB_DIRECT : RACK_SHAPE_NAMES.SHAPE_96,
            CASE_NO_JOB_1_PREP : RACK_SHAPE_NAMES.SHAPE_96,
            CASE_NO_JOB_COMPLEX : RACK_SHAPE_NAMES.SHAPE_96,
            CASE_ASSOCIATION_SIMPLE : RACK_SHAPE_NAMES.SHAPE_384,
            CASE_ASSOCIATION_96 : RACK_SHAPE_NAMES.SHAPE_96,
            CASE_ASSOCIATION_2_ALIQUOTS : RACK_SHAPE_NAMES.SHAPE_384,
            CASE_ASSOCIATION_JOB_LAST : RACK_SHAPE_NAMES.SHAPE_384,
            CASE_ASSOCIATION_SEVERAL_CONC : RACK_SHAPE_NAMES.SHAPE_384,
            CASE_LIBRARY : None,
            CASE_LIBRARY_2_ALIQUOTS : None,
            CASE_LIBRARY_SEVERAL_CONC : None}

    __LIBRARY_PLATE_SHAPE = {
            CASE_ORDER_ONLY : None,
            CASE_NO_JOB_DIRECT : None,
            CASE_NO_JOB_1_PREP : None,
            CASE_NO_JOB_COMPLEX : None,
            CASE_ASSOCIATION_SIMPLE : None,
            CASE_ASSOCIATION_96 : None,
            CASE_ASSOCIATION_2_ALIQUOTS : None,
            CASE_ASSOCIATION_JOB_LAST : None,
            CASE_ASSOCIATION_SEVERAL_CONC : None,
            CASE_LIBRARY : RACK_SHAPE_NAMES.SHAPE_384,
            CASE_LIBRARY_2_ALIQUOTS : RACK_SHAPE_NAMES.SHAPE_384,
            CASE_LIBRARY_SEVERAL_CONC : RACK_SHAPE_NAMES.SHAPE_384}

    # assuming the first 2 ISOs (job size 2)
    ISO_LABELS = {
            CASE_ORDER_ONLY : ['123_iso_01'],
            CASE_NO_JOB_DIRECT : ['123_iso_01'],
            CASE_NO_JOB_1_PREP : ['123_iso_01'],
                    }

    TEST_FILE_PATH = 'thelma:tests/tools/iso/lab/cases/'

    @classmethod
    def get_xls_file_name(cls, case_name):
        return '%s.xls' % (case_name)

    @classmethod
    def get_experiment_scenario(cls, case_name):
        type_id = cls.__EXPERIMENT_SCENARIOS[case_name]
        return get_experiment_metadata_type(type_id)

    @classmethod
    def get_iso_request_layout_data(cls, case_name):
        #pos_label - pool_id, pos_type, iso vol, iso conc
        if case_name == cls.CASE_ORDER_ONLY:
            return dict(
                b2=[205201, 'fixed', 2, 50000], # siRNA
                b4=[330001, 'fixed', 2, 10000], # miRNA
                b6=[333803, 'fixed', 2, 5000000], # compound
                b8=[1056000, 'fixed', 2, 10000], # siRNA pool
                b10=[180005, 'fixed', 2, 50000]) # ssDNA (primer)
        elif case_name == cls.CASE_NO_JOB_DIRECT:
            return dict(
                b2=[205201, 'fixed', 2, 50000], # siRNA
                d2=[205201, 'fixed', 10, 10000], # siRNA
                b4=[330001, 'fixed', 2, 10000], # miRNA
                d4=[330001, 'fixed', 10, 2000], # miRNA
                b6=[333803, 'fixed', 2, 5000000], # compound
                d6=[333803, 'fixed', 20, 500000], # compound
                b8=[1056000, 'fixed', 2, 10000], # siRNA pool
                d8=[1056000, 'fixed', 10, 20000], # siRNA pool
                b10=[180005, 'fixed', 2, 50000], # ssDNA (primer)
                d10=[180005, 'fixed', 10, 10000]) # ssDNA (primer)
        elif case_name == cls.CASE_NO_JOB_1_PREP:
            return dict(
                b2=[205201, 'fixed', 2, 50000], # siRNA
                d2=[205201, 'fixed', 2, 10000], # siRNA
                b4=[330001, 'fixed', 2, 10000], # miRNA
                d4=[330001, 'fixed', 2, 2000], # miRNA
                b6=[333803, 'fixed', 2, 5000000], # compound
                d6=[333803, 'fixed', 2, 500000], # compound
                b8=[1056000, 'fixed', 2, 10000], # siRNA pool
                d8=[1056000, 'fixed', 2, 20000], # siRNA pool
                b10=[180005, 'fixed', 2, 50000], # ssDNA (primer)
                d10=[180005, 'fixed', 2, 10000]) # ssDNA (primer)
        raise NotImplementedError('The value for this case is missing.')

    @classmethod
    def get_aliquot_plate_shape(cls, case_name):
        return cls.__ALIQUOT_PLATE_SHAPE[case_name]

    @classmethod
    def get_library_plate_shape(cls, case_name):
        return cls.__LIBRARY_PLATE_SHAPE[case_name]

    @classmethod
    def get_final_plate_labels(cls, case_name):
        iso_labels = cls.ISO_LABELS[case_name]
        if case_name == cls.CASE_ORDER_ONLY:
            return {iso_labels[0] : ['123_iso_01_a']}
        elif case_name == cls.CASE_NO_JOB_DIRECT:
            return {iso_labels[0] : ['123_iso_01_a']}
        elif case_name == cls.CASE_NO_JOB_1_PREP:
            return {iso_labels[0] : ['123_iso_01_a']}
        raise NotImplementedError('The value for this case is missing.')

    @classmethod
    def get_final_plate_layout_data(cls, case_name):
        iso_labels = cls.ISO_LABELS[case_name]
        # pos_label - pool_id, pos_type, vol, concentration, from_job,
        # transfer_targets, sector_index, stock_rack_marker
        if case_name == cls.CASE_ORDER_ONLY:
            f1 = dict(
                b2=[205201, 'fixed', 2, 50000, False, [], None, 's#1'], # siRNA
                b4=[330001, 'fixed', 2, 10000, False, [], None, 's#1'], # miRNA
                b6=[333803, 'fixed', 2, 5000000, False, [], None, 's#1'], # compound
                b8=[1056000, 'fixed', 2, 10000, False, [], None, 's#1'], # siRNA pool
                b10=[180005, 'fixed', 2, 50000, False, [], None, 's#1']) # ssDNA (primer)
            return {iso_labels[0] : f1}
        elif case_name == cls.CASE_NO_JOB_DIRECT:
            f1 = dict(
                b2=[205201, 'fixed', 2, 50000, False, [], None, 's#1'], # siRNA
                d2=[205201, 'fixed', 10, 10000, False, [], None, 's#1'], # siRNA
                b4=[330001, 'fixed', 2, 10000, False, [], None, 's#1'], # miRNA
                d4=[330001, 'fixed', 10, 2000, False, [], None, 's#1'], # miRNA
                b6=[333803, 'fixed', 2, 5000000, False, [], None, 's#1'], # compound
                d6=[333803, 'fixed', 20, 500000, False, [], None, 's#1'], # compound
                b8=[1056000, 'fixed', 2, 10000, False, [], None, 's#1'], # siRNA pool
                d8=[1056000, 'fixed', 10, 2000, False, [], None, 's#1'], # siRNA pool
                b10=[180005, 'fixed', 2, 50000, False, [], None, 's#1'], # ssDNA (primer)
                d10=[180005, 'fixed', 10, 10000, False, [], None, 's#1']) # ssDNA (primer)
            return {iso_labels[0] : f1}
        elif case_name == cls.CASE_NO_JOB_1_PREP:
            f1 = dict(
                b2=[205201, 'fixed', 2, 50000, False, [], None, 's#1'], # siRNA
                d2=[205201, 'fixed', 2, 10000, False, [], None, None], # siRNA
                b4=[330001, 'fixed', 2, 10000, False, [], None, 's#1'], # miRNA
                d4=[330001, 'fixed', 2, 2000, False, [], None, None], # miRNA
                b6=[333803, 'fixed', 2, 5000000, False, [], None, 's#1'], # compound
                d6=[333803, 'fixed', 2, 500000, False, [], None, None], # compound
                b8=[1056000, 'fixed', 4, 10000, False, [], None, 's#1'], # siRNA pool
                d8=[1056000, 'fixed', 4, 2000, False, [], None, None], # siRNA pool
                b10=[180005, 'fixed', 4, 50000, False, [], None, 's#1'], # ssDNA (primer)
                d10=[180005, 'fixed', 4, 10000, False, [], None, None]) # ssDNA (primer)
            return {iso_labels[0] : f1}
        raise NotImplementedError('The value for this case is missing.')

    @classmethod
    def get_final_iso_layout_shape(cls, case_name):
        if case_name in cls.LIBRARY_CASES:
            return cls.get_library_plate_shape(case_name)
        else:
            return cls.get_aliquot_plate_shape(case_name)

    @classmethod
    def get_prep_plate_layout_data(cls, case_name):
        # pos_label - pool_id, pos_type, vol, concentration, transfer_targets,
        # external_targets, sector_index, stock_rack_marker
        if case_name == cls.CASE_ORDER_ONLY:
            return {}
        elif case_name == cls.CASE_NO_JOB_DIRECT:
            return {}
        elif case_name == cls.CASE_NO_JOB_1_PREP:
            p1 = dict(d2=[205201, 'fixed', 12, 10000, [],
                          [TransferTarget('d2', 2, 'a')], None, 's#1'],
                      d4=[330001, 'fixed', 12, 2000, [],
                          [TransferTarget('d4', 2, 'a')], None, 's#1'],
                      d6=[333803, 'fixed', 12, 500000, [],
                          [TransferTarget('d6', 12, 'a')], None, 's#1'],
                      d8=[1056000, 'fixed', 12, 4000, [],
                          [TransferTarget('d8', 12, 'a')], None, 's#1'],
                      d10=[180005, 'fixed', 12, 20000, [],
                          [TransferTarget('d10', 12, 'a')], None, 's#1'])
            return {'123_iso_01_p' : p1}
        raise NotImplementedError('The value for this case is missing.')

    @classmethod
    def get_preparation_plate_layout_shape(cls, case_name):
        if case_name == cls.CASE_NO_JOB_1_PREP:
            return RACK_SHAPE_NAMES.SHAPE_96
        raise NotImplementedError('The value for this case is missing.')

    @classmethod
    def get_job_plate_layout_data(cls, case_name):
        # pos_label - pool_id, pos_type, vol, concentration, transfer_targets,
        # external_targets, sector_index, stock_rack_marker
        if case_name == cls.CASE_ORDER_ONLY:
            return {}
        elif case_name == cls.CASE_NO_JOB_DIRECT:
            return {}
        elif case_name == cls.CASE_NO_JOB_1_PREP:
            return {}
        raise NotImplementedError('The value for this case is missing.')

    @classmethod
    def get_job_plate_layout_shape(cls, case_name):
        raise NotImplementedError('The value for this case is missing.')

    @classmethod
    def get_number_job_stock_racks(cls, case_name):
        if case_name == cls.CASE_ORDER_ONLY:
            return 0
        elif case_name == cls.CASE_NO_JOB_DIRECT:
            return 0
        elif case_name == cls.CASE_NO_JOB_1_PREP:
            return 0
        raise NotImplementedError('The value for this case is missing.')

    @classmethod
    def get_number_iso_stock_racks(cls, case_name):
        iso_labels = cls.ISO_LABELS[case_name]
        if case_name == cls.CASE_ORDER_ONLY:
            return {iso_labels[0] : 1}
        elif case_name == cls.CASE_NO_JOB_DIRECT:
            return {iso_labels[0] : 1}
        elif case_name == cls.CASE_NO_JOB_1_PREP:
            return {iso_labels[0] : 1}
        raise NotImplementedError('The value for this case is missing.')

    @classmethod
    def get_worklist_data(cls, case_name):
        type_dil = TRANSFER_TYPES.SAMPLE_DILUTION
        type_trans = TRANSFER_TYPES.SAMPLE_TRANSFER
        type_rack = TRANSFER_TYPES.RACK_SAMPLE_TRANSFER
        ps_biomek = get_pipetting_specs_biomek()
        ps_cybio = get_pipetting_specs_cybio()
        #: worklist label - type, pipetting specs name
        if case_name == cls.CASE_ORDER_ONLY:
            return {}
        elif case_name == cls.CASE_NO_JOB_DIRECT:
            return {'123_1_a_buffer' : [type_dil, ps_biomek]}
        elif case_name == cls.CASE_NO_JOB_1_PREP:
            return {'123_1_p_buffer' : [type_dil, ps_biomek],
                    '123_2_a_buffer' : [type_dil, ps_biomek],
                    '123_3_p_to_a' : [type_trans, ps_biomek]}
        raise NotImplementedError('The value for this case is missing.')

    @classmethod
    def get_worklist_details(cls, case_name, worklist_label):
        # for dilutions: target_pos - vol
        # for transfers: trg_pos - vol, target_pos
        # for rack_transfers: target index - vol, source, num sectors
        if case_name == cls.CASE_ORDER_ONLY:
            return dict()
        elif case_name == cls.CASE_NO_JOB_DIRECT:
            if worklist_label == '123_1_a_buffer':
                return dict(d2=8, d4=8, d6=18, d8=8, d10=8)
        elif case_name == cls.CASE_NO_JOB_1_PREP:
            if worklist_label == '123_1_p_buffer':
                return dict(d2=9.6, d4=9.6, d6=10.8, d8=7.2, d10=7.2)
            elif worklist_label == '123_2_a_buffer':
                return dict(d8=2, d10=2)
            elif worklist_label == '123_3_p_to_a':
                return dict(d2=[2, 'd2'], d4=[2, 'd4'], d6=[2, 'd6'],
                            d8=[2, 'd8'], d10=[2, 'd10'])
        raise NotImplementedError('The value for this case or worklist (%s) ' \
                                  'is missing.' % (worklist_label))


class LabIsoTestCase(ExperimentMetadataReadingTestCase):

    def set_up(self):
        ExperimentMetadataReadingTestCase.set_up(self)
        self.TEST_FILE_PATH = LAB_ISO_TEST_CASES.TEST_FILE_PATH
        self.case = None
        self.iso_request = None
        self.number_isos = 2
        self.compare_floating_pools = True

    def tear_down(self):
        ExperimentMetadataReadingTestCase.tear_down(self)
        del self.case
        del self.iso_request
        del self.number_isos
        del self.compare_floating_pools

    def _load_iso_request(self, case_name=None):
        if not case_name is None:
            self.case = case_name
        self._continue_setup()

    def _continue_setup(self, file_name=None):
        if file_name is None:
            file_name = LAB_ISO_TEST_CASES.get_xls_file_name(self.case)
        ExperimentMetadataReadingTestCase._continue_setup(self, file_name)
        self.iso_request = self.experiment_metadata.lab_iso_request

    def _set_experiment_metadadata(self):
        em_type = LAB_ISO_TEST_CASES.get_experiment_scenario(self.case)
        self.experiment_metadata = ExperimentMetadata(label=self.case,
                    subproject=self._get_entity(ISubproject),
                    number_replicates=1,
                    experiment_metadata_type=em_type,
                    ticket_number=123)

    def _get_iso_request_layout(self, case_name=None):
        if case_name is None: case_name = self.case
        shape_name = LAB_ISO_TEST_CASES.get_aliquot_plate_shape(case_name)
        shape = RACK_SHAPE_NAMES.from_name(shape_name)
        layout_data = LAB_ISO_TEST_CASES.get_iso_request_layout_data(case_name)
        layout = IsoRequestLayout(shape)
        for pos_label, pos_data in layout_data.iteritems():
            rack_pos = get_rack_position_from_label(pos_label)
            pool = self._get_pool(pos_data[0])
            ir_pos = IsoRequestPosition(rack_position=rack_pos,
                    molecule_design_pool=pool,
                    position_type=pos_data[1],
                    iso_volume=pos_data[2],
                    iso_concentration=pos_data[3])
            layout.add_position(ir_pos)
        return layout

    def _compare_preparation_layout(self, layout_data, rack_layout, rack_label,
                                    is_job=False):
        converter = LabIsoPrepLayoutConverter(log=SilentLog(),
                                              rack_layout=rack_layout)
        layout = converter.get_result()
        if layout is None:
            raise AssertionError('Unable to convert layout for %s ' \
                                 'preparation plate "%s".' % (rack_label))
        if is_job:
            exp_shape = LAB_ISO_TEST_CASES.get_job_plate_layout_shape(self.case)
        else:
            exp_shape = LAB_ISO_TEST_CASES.get_preparation_plate_layout_shape(
                                                                    self.case)
        self.assert_equal(layout.shape.name, exp_shape)
        layout_name = 'preparation plate layout for rack "%s"' % (rack_label)
        if is_job: layout_name = 'job ' + layout_name
        tested_labels = []
        # pos_label - pool_id, pos_type, vol, concentration, transfer_targets,
        # external_targets, sector_index, stock_rack_marker
        for rack_pos, prep_pos in layout.iterpositions():
            pos_label = rack_pos.label.lower()
            tested_labels.append(pos_label)
            pos_data = layout_data[pos_label]
            self._compare_layout_value(pos_data[1], 'position_type',
                                        prep_pos, layout_name)
            if prep_pos.is_floating and not self.compare_floating_pools:
                self.assert_is_not_none(prep_pos.molecule_design_pool)
            else:
                self._compare_layout_value(pos_data[0], 'molecule_design_pool',
                                           prep_pos, layout_name)
            self._compare_layout_value(pos_data[2], 'volume',
                                        prep_pos, layout_name)
            self._compare_layout_value(pos_data[3], 'concentration',
                                        prep_pos, layout_name)
            self._compare_layout_value(pos_data[4], 'transfer_targets',
                                        prep_pos, layout_name)
            self._compare_layout_value(pos_data[5], 'external_targets',
                                        prep_pos, layout_name)
            self._compare_layout_value(pos_data[6], 'sector_index',
                                        prep_pos, layout_name)
            self._compare_layout_value(pos_data[7], 'stock_rack_marker',
                                        prep_pos, layout_name)
            if prep_pos.stock_rack_marker is None:
                self.assert_is_none(prep_pos.stock_tube_barcode)
                self.assert_is_none(prep_pos.stock_rack_barcode)
            else:
                self.assert_is_not_none(prep_pos.stock_tube_barcode)
                self.assert_is_not_none(prep_pos.stock_rack_barcode)
        self.assert_equal(sorted(tested_labels), sorted(layout_data.keys()))

    def _compare_final_iso_layout(self, layout_data, rack_layout, iso_label):
        converter = FinalLabIsoLayoutConverter(rack_layout=rack_layout,
                                               log=SilentLog())
        layout = converter.get_result()
        if layout is None:
            raise AssertionError('Unable to convert final ISO layout for ISO ' \
                                 '"%s".' % (iso_label))
        self.assert_equal(layout.shape.name,
                      LAB_ISO_TEST_CASES.get_final_iso_layout_shape(self.case))
        layout_name = 'final layout for ISO "%s"' % (iso_label)
        tested_labels = []
        # pos_label - pool_id, pos_type, vol, concentration, from_job,
        # transfer_targets, sector_index, stock_rack_marker
        for rack_pos, prep_pos in layout.iterpositions():
            pos_label = rack_pos.label.lower()
            tested_labels.append(pos_label)
            pos_data = layout_data[pos_label]
            self._compare_layout_value(pos_data[1], 'position_type',
                                        prep_pos, layout_name)
            if prep_pos.is_floating and not self.compare_floating_pools:
                self.assert_is_not_none(prep_pos.molecule_design_pool)
            else:
                self._compare_layout_value(pos_data[0], 'molecule_design_pool',
                                           prep_pos, layout_name)
            self._compare_layout_value(pos_data[2], 'volume',
                                        prep_pos, layout_name)
            self._compare_layout_value(pos_data[3], 'concentration',
                                        prep_pos, layout_name)
            self._compare_layout_value(pos_data[4], 'from_job',
                                        prep_pos, layout_name)
            self._compare_layout_value(pos_data[5], 'transfer_targets',
                                        prep_pos, layout_name)
            self._compare_layout_value(pos_data[6], 'sector_index',
                                        prep_pos, layout_name)
            self._compare_layout_value(pos_data[7], 'stock_rack_marker',
                                        prep_pos, layout_name)
            if prep_pos.stock_rack_marker is None:
                self.assert_is_none(prep_pos.stock_tube_barcode)
                self.assert_is_none(prep_pos.stock_rack_barcode)
            else:
                self.assert_is_not_none(prep_pos.stock_tube_barcode)
                self.assert_is_not_none(prep_pos.stock_rack_barcode)
        self.assert_equal(sorted(tested_labels), sorted(layout_data.keys()))

    def _compare_layout_value(self, exp_value, attr_name, pool_pos,
                               layout_name):
        found_value = getattr(pool_pos, attr_name)
        pos_label = pool_pos.rack_position.label
        if attr_name == 'molecule_design_pool':
            exp_value = self._get_pool(exp_value)
        if not exp_value == found_value:
            msg = 'The values for the %s attribute of position %s in ' \
                  'layout %s are not equal.\nExpected: %s.\nFound: %s.' \
                  % (attr_name, pos_label, layout_name, exp_value, found_value)
            raise AssertionError(msg)

    def _compare_worklist_series(self):
        exp_data = LAB_ISO_TEST_CASES.get_worklist_data(self.case)
        worklist_series = self.iso_request.worklist_series
        if len(exp_data) == 0:
            self.assert_is_none(worklist_series)
        else:
            self.assert_is_not_none(worklist_series)
            self.assert_equal(len(worklist_series), len(exp_data))
            found_labels = []
            for worklist in worklist_series:
                label = worklist.label
                found_labels.append(label)
                #: worklist label - type, pipetting specs name, num transfers
                wl_data = exp_data[label]
                self.assert_equal(wl_data[0], worklist.transfer_type)
                self.assert_equal(wl_data[1], worklist.pipetting_specs)
                self._compare_worklist_details(worklist)
            self.assert_equal(sorted(found_labels), sorted(exp_data.keys()))

    def _compare_worklist_details(self, worklist):
        wl_label = worklist.label
        wl_data = LAB_ISO_TEST_CASES.get_worklist_details(self.case, wl_label)
        plts = worklist.planned_liquid_transfers
        self.assert_equal(len(wl_data), len(plts))
        transfer_type = worklist.transfer_type
        for plt in plts:
            if transfer_type == TRANSFER_TYPES.SAMPLE_DILUTION:
                trg_label = plt.target_position.label.lower()
                exp_vol = wl_data[trg_label]
                self.__compare_volume(plt, exp_vol, trg_label, wl_label)
                self.assert_equal(plt.diluent_info, DILUENT_INFO)
            elif transfer_type == TRANSFER_TYPES.SAMPLE_TRANSFER:
                trg_label = plt.target_position.label.lower()
                plt_data = wl_data[trg_label]
                self.__compare_volume(plt, plt_data[0], trg_label, wl_label)
                src_label = plt.source_position.label.lower()
                if not src_label == plt_data[1]:
                    msg = 'The source position for transfer %s of worklist ' \
                          '"%s" differ:\nExpected: %s\nFound: %s.' \
                          % (trg_label, wl_data, plt_data[1], src_label)
                    raise AssertionError(msg)
            else:
                trg_index = plt.target_sector_index
                plt_data = wl_data[trg_index]
                self.__compare_volume(plt, plt_data[0],
                                      'sector %i' % (trg_index), wl_label)
                src_index = plt.source_sector_index
                if not src_label == plt_data[1]:
                    msg = 'The source sector index for target sector %s of ' \
                          'worklist "%s" differ:\nExpected: %s\nFound: %s.' \
                          % (trg_index, wl_data, plt_data[1], src_index)
                    raise AssertionError(msg)
                if not plt.number_sectors == plt_data[2]:
                    msg = 'The sector number for target sector %s of ' \
                          'worklist "%s" differ:\nExpected: %s\nFound: %s.' \
                          % (trg_index, wl_data, plt_data[2],
                             plt.number_sectors)
                    raise AssertionError(msg)

    def __compare_volume(self, plt, exp_vol, transfer_name, wl_label):
        vol = round(plt.volume * VOLUME_CONVERSION_FACTOR, 1)
        if not are_equal_values(vol, exp_vol):
            msg = 'The volume for transfer %s of worklist "%s" differ.\n' \
                  'Expected: %s ul, found: %s ul.' % (transfer_name, wl_label,
                   get_trimmed_string(exp_vol), get_trimmed_string(vol))
            raise AssertionError(msg)

