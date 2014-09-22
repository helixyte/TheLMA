"""
Base classes for lab ISO testing.
"""
from everest.entities.utils import get_root_aggregate
from thelma.automation.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.semiconstants import RACK_SPECS_NAMES
from thelma.automation.semiconstants import get_384_rack_shape
from thelma.automation.semiconstants import get_experiment_metadata_type
from thelma.automation.semiconstants import get_item_status_future
from thelma.automation.semiconstants import get_item_status_managed
from thelma.automation.semiconstants import get_pipetting_specs_biomek
from thelma.automation.semiconstants import get_pipetting_specs_biomek_stock
from thelma.automation.semiconstants import get_pipetting_specs_cybio
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.tools.iso.base import StockRackLayout
from thelma.automation.tools.iso.base import StockRackLayoutConverter
from thelma.automation.tools.iso.base import StockRackPosition
from thelma.automation.tools.iso.lab.base import DILUENT_INFO
from thelma.automation.tools.iso.lab.base import FinalLabIsoLayout
from thelma.automation.tools.iso.lab.base import FinalLabIsoLayoutConverter
from thelma.automation.tools.iso.lab.base import FinalLabIsoPosition
from thelma.automation.tools.iso.lab.base import LAB_ISO_ORDERS
from thelma.automation.tools.iso.lab.base import LabIsoPrepLayout
from thelma.automation.tools.iso.lab.base import LabIsoPrepLayoutConverter
from thelma.automation.tools.iso.lab.base import LabIsoPrepPosition
from thelma.automation.tools.stock.tubepicking import TubeCandidate
from thelma.automation.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.utils.base import are_equal_values
from thelma.automation.utils.base import get_trimmed_string
from thelma.automation.utils.iso import IsoRequestLayout
from thelma.automation.utils.iso import IsoRequestLayoutConverter
from thelma.automation.utils.iso import IsoRequestPosition
from thelma.automation.utils.layouts import LibraryBaseLayout
from thelma.automation.utils.layouts import LibraryBaseLayoutPosition
from thelma.automation.utils.layouts import MOCK_POSITION_TYPE
from thelma.automation.utils.layouts import TransferTarget
from thelma.interfaces import IMoleculeDesignLibrary
from thelma.interfaces import IMoleculeDesignPool
from thelma.interfaces import ISubproject
from thelma.interfaces import IUser
from thelma.models.container import Tube
from thelma.models.experiment import ExperimentMetadata
from thelma.models.job import IsoJob
from thelma.models.library import LibraryPlate
from thelma.models.library import MoleculeDesignLibrary
from thelma.models.liquidtransfer import PlannedRackSampleTransfer
from thelma.models.liquidtransfer import PlannedSampleDilution
from thelma.models.liquidtransfer import PlannedSampleTransfer
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.moleculedesign import MoleculeDesignPoolSet
from thelma.models.organization import Organization
from thelma.models.sample import StockSample
from thelma.oldtests.tools.tooltestingutils \
    import ExperimentMetadataReadingTestCase


#: This pool ID is used for tests in which we do not want to find an
#: appropriate stock sample.
POOL_WITHOUT_STOCK_SAMPLE = 689600

#: The name of the test ISO job.
TEST_ISO_JOB_NAME = '123_job_01'

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

    #: 384-well layout, 1 conc (stock concentration), controls in sector,
    #: no preparation plates
    CASE_ASSOCIATION_DIRECT = 'association_direct'
    #: 96-well layout that can be transferred with the CyBio
    CASE_ASSOCIATION_96 = 'association_96'
    #: 384-well association layout with job processing first, one concentration
    #: for all samples
    CASE_ASSOCIATION_SIMPLE = 'association_simple'
    #: 384-well with association that is not transferred with the Cybio due to
    #: too less transfers. All pools in stock concentrations.
    CASE_ASSOCIATION_NO_CYBIO = 'association_no_cybio'
    #: 384-well association layout with job processing first with 2 target
    #: aliquot plates, one concentration for all samples
    CASE_ASSOCIATION_2_ALIQUOTS = 'association_2_aliquots'
    #: 384-well association layout with job processing coming second, one
    #: concentration for samples, 2 for controls (transfer within final plate)
    CASE_ASSOCIATION_JOB_LAST = 'association_job_last'
    #: 384-well association layout with job processing second,
    #: two concentrations for each samples
    CASE_ASSOCIATION_SEVERAL_CONC = 'association_several_conc'

    #: Standard library case with controls one conc and one target aliquot
    CASE_LIBRARY_SIMPLE = 'library_simple'
    #: Library case with with controls in different concentrations and
    #: 2 target aliquot
    CASE_LIBRARY_2_ALIQUOTS = 'library_2_aliquots'

    NON_LIBRARY_CASES = [CASE_ORDER_ONLY, CASE_NO_JOB_DIRECT, CASE_NO_JOB_1_PREP,
             CASE_NO_JOB_COMPLEX, CASE_ASSOCIATION_DIRECT,
             CASE_ASSOCIATION_NO_CYBIO, CASE_ASSOCIATION_SIMPLE,
             CASE_ASSOCIATION_96, CASE_ASSOCIATION_2_ALIQUOTS,
             CASE_ASSOCIATION_JOB_LAST, CASE_ASSOCIATION_SEVERAL_CONC]
    LIBRARY_CASES = [CASE_LIBRARY_SIMPLE, CASE_LIBRARY_2_ALIQUOTS]
    ALL_CASES = NON_LIBRARY_CASES + LIBRARY_CASES

    __EXPERIMENT_SCENARIOS = {
            CASE_ORDER_ONLY : EXPERIMENT_SCENARIOS.ORDER_ONLY,
            CASE_NO_JOB_DIRECT : EXPERIMENT_SCENARIOS.MANUAL,
            CASE_NO_JOB_1_PREP : EXPERIMENT_SCENARIOS.MANUAL,
            CASE_NO_JOB_COMPLEX : EXPERIMENT_SCENARIOS.MANUAL,
            CASE_ASSOCIATION_DIRECT : EXPERIMENT_SCENARIOS.SCREENING,
            CASE_ASSOCIATION_NO_CYBIO : EXPERIMENT_SCENARIOS.SCREENING,
            CASE_ASSOCIATION_SIMPLE : EXPERIMENT_SCENARIOS.SCREENING,
            CASE_ASSOCIATION_96 : EXPERIMENT_SCENARIOS.SCREENING,
            CASE_ASSOCIATION_2_ALIQUOTS : EXPERIMENT_SCENARIOS.SCREENING,
            CASE_ASSOCIATION_JOB_LAST : EXPERIMENT_SCENARIOS.SCREENING,
            CASE_ASSOCIATION_SEVERAL_CONC : EXPERIMENT_SCENARIOS.SCREENING,
            CASE_LIBRARY_SIMPLE : EXPERIMENT_SCENARIOS.LIBRARY,
            CASE_LIBRARY_2_ALIQUOTS : EXPERIMENT_SCENARIOS.LIBRARY}

    __ALIQUOT_PLATE_SHAPE = {
            CASE_ORDER_ONLY : RACK_SHAPE_NAMES.SHAPE_96,
            CASE_NO_JOB_DIRECT : RACK_SHAPE_NAMES.SHAPE_96,
            CASE_NO_JOB_1_PREP : RACK_SHAPE_NAMES.SHAPE_96,
            CASE_NO_JOB_COMPLEX : RACK_SHAPE_NAMES.SHAPE_96,
            CASE_ASSOCIATION_DIRECT : RACK_SHAPE_NAMES.SHAPE_384,
            CASE_ASSOCIATION_SIMPLE : RACK_SHAPE_NAMES.SHAPE_384,
            CASE_ASSOCIATION_NO_CYBIO : RACK_SHAPE_NAMES.SHAPE_384,
            CASE_ASSOCIATION_96 : RACK_SHAPE_NAMES.SHAPE_96,
            CASE_ASSOCIATION_2_ALIQUOTS : RACK_SHAPE_NAMES.SHAPE_384,
            CASE_ASSOCIATION_JOB_LAST : RACK_SHAPE_NAMES.SHAPE_384,
            CASE_ASSOCIATION_SEVERAL_CONC : RACK_SHAPE_NAMES.SHAPE_384}

    __LIBRARY_PLATE_SHAPE = {
            CASE_LIBRARY_SIMPLE : RACK_SHAPE_NAMES.SHAPE_384,
            CASE_LIBRARY_2_ALIQUOTS : RACK_SHAPE_NAMES.SHAPE_384}

    # assuming the first 2 ISOs (job size 2)
    ISO_LABELS = {
            CASE_ORDER_ONLY : ['123_iso_01'],
            CASE_NO_JOB_DIRECT : ['123_iso_01'],
            CASE_NO_JOB_1_PREP : ['123_iso_01'],
            CASE_NO_JOB_COMPLEX : ['123_iso_01'],
            CASE_ASSOCIATION_DIRECT : ['123_iso_01', '123_iso_02'],
            CASE_ASSOCIATION_96 : ['123_iso_01', '123_iso_02'],
            CASE_ASSOCIATION_SIMPLE : ['123_iso_01', '123_iso_02'],
            CASE_ASSOCIATION_NO_CYBIO : ['123_iso_01', '123_iso_02'],
            CASE_ASSOCIATION_2_ALIQUOTS : ['123_iso_01', '123_iso_02'],
            CASE_ASSOCIATION_JOB_LAST : ['123_iso_01', '123_iso_02'],
            CASE_ASSOCIATION_SEVERAL_CONC : ['123_iso_01', '123_iso_02'],
            CASE_LIBRARY_SIMPLE : ['123_iso_01', '123_iso_02'],
            CASE_LIBRARY_2_ALIQUOTS : ['123_iso_01', '123_iso_02']}

    TEST_FILE_PATH = 'thelma:tests/tools/iso/lab/cases/'
    INSTRUCTIONS_FILE_PATH = 'thelma:tests/tools/iso/lab/instructionfiles/'
    WORKLIST_FILE_PATH_PATTERN = 'thelma:tests/tools/iso/lab/processing/%s/'
    TRAC_FILE_PATH = 'thelma:tests/tools/iso/lab/tracreporting/'

    @classmethod
    def get_xls_file_name(cls, case_name):
        return '%s.xls' % (case_name)

    @classmethod
    def get_experiment_scenario(cls, case_name):
        type_id = cls.__EXPERIMENT_SCENARIOS[case_name]
        return get_experiment_metadata_type(type_id)

    @classmethod
    def get_instruction_file(cls, case_name, for_job):
        if for_job:
            pat = '%s_job_instructions.txt'
        else:
            pat = '%s_iso_instructions.txt'
        return pat % (case_name)

    @classmethod
    def get_worklist_file_dir(cls, case_name):
        return cls.WORKLIST_FILE_PATH_PATTERN % (case_name)

    @classmethod
    def get_trac_log_file_name(cls, case_name, for_job):
        if for_job:
            pat = '%s_trac_log_job.txt'
        else:
            pat = '%s_trac_log_iso.txt'
        return pat % (case_name)

    @classmethod
    def is_library_case(cls, case_name):
        return case_name in cls.LIBRARY_CASES

    @classmethod
    def get_iso_request_layout_data(cls, case_name):
        #pos_label - pool_id, pos_type, iso vol, iso conc
        if case_name == cls.CASE_ORDER_ONLY:
            return dict(
                b2=[205201, 'fixed', 2, 50000], # siRNA
                b4=[330001, 'fixed', 2, 10000], # miRNA
                b6=[333803, 'fixed', 2, 5000000], # compound
                b8=[1056000, 'fixed', 2, 10000], # siRNA pool
                b10=[180005, 'fixed', 2, 100000]) # ssDNA (primer)
        elif case_name == cls.CASE_NO_JOB_DIRECT:
            return dict(
                b2=[205201, 'fixed', 2, 50000], # siRNA
                d2=[205201, 'fixed', 10, 10000], # siRNA
                b4=[330001, 'fixed', 2, 10000], # miRNA
                d4=[330001, 'fixed', 10, 2000], # miRNA
                b6=[333803, 'fixed', 2, 5000000], # compound
                d6=[333803, 'fixed', 20, 500000], # compound
                b8=[1056000, 'fixed', 2, 10000], # siRNA pool
                d8=[1056000, 'fixed', 10, 2000], # siRNA pool
                b10=[180005, 'fixed', 2, 100000], # ssDNA (primer)
                d10=[180005, 'fixed', 10, 20000]) # ssDNA (primer)
        elif case_name == cls.CASE_NO_JOB_1_PREP:
            return dict(
                b2=[205201, 'fixed', 2, 50000], # siRNA
                d2=[205201, 'fixed', 2, 10000], # siRNA
                b4=[330001, 'fixed', 2, 10000], # miRNA
                d4=[330001, 'fixed', 2, 2000], # miRNA
                b6=[333803, 'fixed', 2, 5000000], # compound
                d6=[333803, 'fixed', 2, 500000], # compound
                b8=[1056000, 'fixed', 4, 10000], # siRNA pool
                d8=[1056000, 'fixed', 4, 2000], # siRNA pool
                b10=[180005, 'fixed', 4, 100000], # ssDNA (primer)
                d10=[180005, 'fixed', 4, 20000]) # ssDNA (primer)
        elif case_name == cls.CASE_NO_JOB_COMPLEX:
            return dict(
                b2=[205201, 'fixed', 20, 50000],
                b3=[205201, 'fixed', 20, 25000],
                b4=[205201, 'fixed', 20, 10000],
                c2=[330001, 'fixed', 3, 10000],
                d2=[333803, 'fixed', 3, 5000000],
                d3=[333803, 'fixed', 3, 1],
                d4=[333803, 'fixed', 3, 1],
                e2=[1056000, 'fixed', 3, 10000],
                f2=[180005, 'fixed', 3, 100000],
                f3=[180005, 'fixed', 3, 96000])
        elif case_name == cls.CASE_ASSOCIATION_DIRECT:
            return dict(
                b2=[205201, 'fixed', 4, 50000],
                b3=[205202, 'fixed', 4, 50000],
                b4=[180005, 'fixed', 4, 50000],
                c2=['md_001', 'floating', 4, 50000],
                c3=['md_002', 'floating', 4, 50000],
                c4=['md_003', 'floating', 4, 50000],
                d2=[205201, 'fixed', 4, 50000],
                d3=[205202, 'fixed', 4, 50000],
                d4=[180005, 'fixed', 4, 50000],
                e2=['mock', 'mock', 4, 'mock'],
                e3=['mock', 'mock', 4, 'mock'])
        elif case_name == cls.CASE_ASSOCIATION_96:
            return dict(
                b2=[205201, 'fixed', 5, 50],
                c2=[205202, 'fixed', 5, 50],
                b4=[205203, 'fixed', 5, 50],
                c4=[205200, 'fixed', 5, 50],
                b6=['md_001', 'floating', 5, 50],
                c6=['md_002', 'floating', 5, 50],
                b8=['mock', 'mock', 5, 'mock'],
                c8=['mock', 'mock', 5, 'mock'],
                b3=['untransfected', 'untransfected', 'untransfected',
                    'untransfected'],
                c3=['untransfected', 'untransfected', 'untransfected',
                    'untransfected'])
        elif case_name == cls.CASE_ASSOCIATION_SIMPLE:
            return dict(
                b2=[205201, 'fixed', 10, 50],
                b3=[205202, 'fixed', 10, 50],
                b4=[205200, 'fixed', 10, 50],
                c2=['md_001', 'floating', 10, 50],
                c3=['md_002', 'floating', 10, 50],
                c4=['md_003', 'floating', 10, 50],
                d2=[205201, 'fixed', 10, 50],
                d3=[205202, 'fixed', 10, 50],
                d4=[205200, 'fixed', 10, 50],
                e2=['mock', 'mock', 10, 'mock'],
                e3=['mock', 'mock', 10, 'mock'],
                e4=['untransfected', 'untransfected', 'untransfected',
                    'untransfected'])
        elif case_name == cls.CASE_ASSOCIATION_NO_CYBIO:
            return dict(
                c3=[205201, 'fixed', 10, 100],
                c4=[205201, 'fixed', 10, 50],
                c5=[180005, 'fixed', 10, 100],
                c6=[180005, 'fixed', 10, 50],
                d3=['md_001', 'floating', 10, 100],
                d4=['md_001', 'floating', 10, 50],
                d5=['md_002', 'floating', 10, 100],
                d6=['md_002', 'floating', 10, 50],
                e3=[205201, 'fixed', 10, 100],
                e4=[205201, 'fixed', 10, 50],
                e5=[180005, 'fixed', 10, 100],
                e6=[180005, 'fixed', 10, 50],
                f3=['mock', 'mock', 10, 'mock'])
        elif case_name == cls.CASE_ASSOCIATION_2_ALIQUOTS:
            return dict(
                b2=[205201, 'fixed', 10, 50],
                b3=[205202, 'fixed', 10, 50],
                b4=[205200, 'fixed', 10, 50],
                c2=['md_001', 'floating', 10, 50],
                c3=['md_002', 'floating', 10, 50],
                c4=['md_003', 'floating', 10, 50],
                d2=[205201, 'fixed', 10, 50],
                d3=[205202, 'fixed', 10, 50],
                d4=[205200, 'fixed', 10, 50],
                e2=['mock', 'mock', 10, 'mock'],
                e3=['mock', 'mock', 10, 'mock'],
                e4=['untransfected', 'untransfected', 'untransfected',
                    'untransfected'])
        elif case_name == cls.CASE_ASSOCIATION_JOB_LAST:
            return dict(
                b2=[205201, 'fixed', 10, 50],
                b3=[330001, 'fixed', 10, 50],
                b4=[205200, 'fixed', 10, 50],
                c2=['md_001', 'floating', 10, 50],
                c3=['md_002', 'floating', 10, 50],
                c4=['md_003', 'floating', 10, 50],
                d2=['md_004', 'floating', 10, 50],
                d3=['md_005', 'floating', 10, 50],
                d4=['md_006', 'floating', 10, 50],
                e2=[205201, 'fixed', 10, 100],
                e3=[330001, 'fixed', 10, 100],
                e4=[205200, 'fixed', 10, 100],
                f2=['mock', 'mock', 10, 'mock'],
                f3=['mock', 'mock', 10, 'mock'],
                f4=['untransfected', 'untransfected', 'untransfected',
                    'untransfected'])
        elif case_name == cls.CASE_ASSOCIATION_SEVERAL_CONC:
            return dict(
                b3=[205201, 'fixed', 10, 50],
                b5=[330001, 'fixed', 10, 50],
                b7=[205200, 'fixed', 10, 50],
                c3=['md_001', 'floating', 10, 50],
                c5=['md_002', 'floating', 10, 50],
                c7=['md_003', 'floating', 10, 50],
                d3=['md_001', 'floating', 10, 100],
                d5=['md_002', 'floating', 10, 100],
                d7=['md_002', 'floating', 10, 100],
                e3=['mock', 'mock', 10, 'mock'],
                e5=['mock', 'mock', 10, 'mock'],
                e7=['mock', 'mock', 10, 'mock'],
                f3=[205201, 'fixed', 10, 100],
                f5=[330001, 'fixed', 10, 100],
                f7=[205200, 'fixed', 10, 100],
                g3=['md_004', 'floating', 10, 50],
                g5=['md_005', 'floating', 10, 50],
                g7=['md_006', 'floating', 10, 50],
                h3=['md_004', 'floating', 10, 100],
                h5=['md_005', 'floating', 10, 100],
                h7=['md_006', 'floating', 10, 100],
                i3=['untransfected', 'untransfected', 'untransfected',
                    'untransfected'])
        elif case_name == cls.CASE_LIBRARY_SIMPLE:
            return dict(
                b2=[205201, 'fixed', 4, 1270],
                d2=[330001, 'fixed', 4, 1270],
                f2=[1056000, 'fixed', 4, 1270],
                h2=['mock', 'mock', 4, 'mock'],
                i10=[205201, 'fixed', 4, 1270],
                k10=[330001, 'fixed', 4, 1270],
                m10=[1056000, 'fixed', 4, 1270],
                o10=['mock', 'mock', 4, 'mock'])
        elif case_name == cls.CASE_LIBRARY_2_ALIQUOTS:
            return dict(
                b2=[205201, 'fixed', 4, 1270],
                d2=[330001, 'fixed', 4, 1270],
                f2=[1056000, 'fixed', 4, 1270],
                h2=['mock', 'mock', 4, 'mock'],
                i10=[205201, 'fixed', 4, 1270],
                k10=[330001, 'fixed', 4, 1270],
                m10=[1056000, 'fixed', 4, 1270],
                o10=['mock', 'mock', 4, 'mock'])
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
        elif case_name == cls.CASE_NO_JOB_COMPLEX:
            return {iso_labels[0] : ['123_iso_01_a']}
        elif case_name == cls.CASE_ASSOCIATION_DIRECT:
            return {iso_labels[0] : ['123_iso_01_a'],
                    iso_labels[1] : ['123_iso_02_a']}
        elif case_name == cls.CASE_ASSOCIATION_NO_CYBIO:
            return {iso_labels[0] : ['123_iso_01_a'],
                    iso_labels[1] : ['123_iso_02_a']}
        elif case_name == cls.CASE_ASSOCIATION_96:
            return {iso_labels[0] : ['123_iso_01_a'],
                    iso_labels[1] : ['123_iso_02_a']}
        elif case_name == cls.CASE_ASSOCIATION_SIMPLE:
            return {iso_labels[0] : ['123_iso_01_a'],
                    iso_labels[1] : ['123_iso_02_a']}
        elif case_name == cls.CASE_ASSOCIATION_2_ALIQUOTS:
            return {iso_labels[0] : ['123_iso_01_a#1', '123_iso_01_a#2'],
                    iso_labels[1] : ['123_iso_02_a#1', '123_iso_02_a#2']}
        elif case_name == cls.CASE_ASSOCIATION_JOB_LAST:
            return {iso_labels[0] : ['123_iso_01_a'],
                    iso_labels[1] : ['123_iso_02_a']}
        elif case_name == cls.CASE_ASSOCIATION_SEVERAL_CONC:
            return {iso_labels[0] : ['123_iso_01_a'],
                    iso_labels[1] : ['123_iso_02_a']}
        elif case_name == cls.CASE_LIBRARY_SIMPLE:
            return {iso_labels[0] : ['testlib_l1_r2'],
                    iso_labels[1] : ['testlib_l2_r2']}
        elif case_name == cls.CASE_LIBRARY_2_ALIQUOTS:
            return {iso_labels[0] : ['testlib_l1_r2', 'testlib_l1_r3'],
                    iso_labels[1] : ['testlib_l2_r2', 'testlib_l2_r3']}
        raise NotImplementedError('The value for this case is missing.')

    @classmethod
    def get_final_plate_layout_data(cls, case_name):
        iso_labels = cls.ISO_LABELS[case_name]
        # pos_label - pool_id, pos_type, vol, concentration, from_job,
        # transfer_targets, sector_index, stock_rack_marker
        if case_name == cls.CASE_ORDER_ONLY:
            f = dict(
                b2=[205201, 'fixed', 2, 50000, False, [], None, 's#1'], # siRNA
                b4=[330001, 'fixed', 2, 10000, False, [], None, 's#1'], # miRNA
                b6=[333803, 'fixed', 2, 5000000, False, [], None, 's#1'], # compound
                b8=[1056000, 'fixed', 2, 10000, False, [], None, 's#1'], # siRNA pool
                b10=[180005, 'fixed', 2, 100000, False, [], None, 's#1']) # ssDNA (primer)
            return {iso_labels[0] : f}
        elif case_name == cls.CASE_NO_JOB_DIRECT:
            f = dict(
                b2=[205201, 'fixed', 2, 50000, False, [], None, 's#1'], # siRNA
                d2=[205201, 'fixed', 10, 10000, False, [], None, 's#1'], # siRNA
                b4=[330001, 'fixed', 2, 10000, False, [], None, 's#1'], # miRNA
                d4=[330001, 'fixed', 10, 2000, False, [], None, 's#1'], # miRNA
                b6=[333803, 'fixed', 2, 5000000, False, [], None, 's#1'], # compound
                d6=[333803, 'fixed', 20, 500000, False, [], None, 's#1'], # compound
                b8=[1056000, 'fixed', 2, 10000, False, [], None, 's#1'], # siRNA pool
                d8=[1056000, 'fixed', 10, 2000, False, [], None, 's#1'], # siRNA pool
                b10=[180005, 'fixed', 2, 100000, False, [], None, 's#1'], # ssDNA (primer)
                d10=[180005, 'fixed', 10, 20000, False, [], None, 's#1']) # ssDNA (primer)
            return {iso_labels[0] : f}
        elif case_name == cls.CASE_NO_JOB_1_PREP:
            f = dict(
                b2=[205201, 'fixed', 2, 50000, False, [], None, 's#1'], # siRNA
                d2=[205201, 'fixed', 2, 10000, False, [], None, None], # siRNA
                b4=[330001, 'fixed', 2, 10000, False, [], None, 's#1'], # miRNA
                d4=[330001, 'fixed', 2, 2000, False, [], None, None], # miRNA
                b6=[333803, 'fixed', 2, 5000000, False, [], None, 's#1'], # compound
                d6=[333803, 'fixed', 2, 500000, False, [], None, None], # compound
                b8=[1056000, 'fixed', 4, 10000, False, [], None, 's#1'], # siRNA pool
                d8=[1056000, 'fixed', 4, 2000, False, [], None, None], # siRNA pool
                b10=[180005, 'fixed', 4, 100000, False, [], None, 's#1'], # ssDNA (primer)
                d10=[180005, 'fixed', 4, 20000, False, [], None, None]) # ssDNA (primer)
            return {iso_labels[0] : f}
        elif case_name == cls.CASE_NO_JOB_COMPLEX:
            f = dict(
                b2=[205201, 'fixed', 34, 50000, False,
                    [TransferTarget('b3', 10, 'a'),
                     TransferTarget('b4', 4, 'a')], None, 's#1'],
                b3=[205201, 'fixed', 20, 25000, False, [], None, None],
                b4=[205201, 'fixed', 20, 10000, False, [], None, None],
                c2=[330001, 'fixed', 3, 10000, False, [], None, 's#1'],
                d2=[333803, 'fixed', 3, 5000000, False, [], None, 's#1'],
                d3=[333803, 'fixed', 3, 1, False, [], None, None],
                d4=[333803, 'fixed', 3, 1, False, [], None, None],
                e2=[1056000, 'fixed', 3, 10000, False, [], None, 's#1'],
                f2=[180005, 'fixed', 3, 100000, False, [], None, 's#1'],
                f3=[180005, 'fixed', 3, 96000, False, [], None, None])
            return {iso_labels[0] : f}
        elif case_name == cls.CASE_ASSOCIATION_DIRECT:
            f = dict(
                b2=[205201, 'fixed', 4, 50000, True, [], 3, 's#1'],
                b3=[205202, 'fixed', 4, 50000, True, [], 2, 's#1'],
                b4=[180005, 'fixed', 4, 50000, True, [], 3, 's#1'],
                d2=[205201, 'fixed', 4, 50000, True, [], 3, 's#1'],
                d3=[205202, 'fixed', 4, 50000, True, [], 2, 's#1'],
                d4=[180005, 'fixed', 4, 50000, True, [], 3, 's#1'],
                e2=['mock', 'mock', 4, None, False, [], None, None],
                e3=['mock', 'mock', 4, None, False, [], None, None])
            f1 = dict(f, **dict(
                    c2=[205205, 'floating', 4, 50000, False, [], 1, 's#3'],
                    c3=[205206, 'floating', 4, 50000, False, [], 0, 's#2'],
                    c4=[205207, 'floating', 4, 50000, False, [], 1, 's#3']))
            f2 = dict(f, **dict(
                    c2=[205208, 'floating', 4, 50000, False, [], 1, 's#3'],
                    c3=[205209, 'floating', 4, 50000, False, [], 0, 's#2'],
                    c4=[205210, 'floating', 4, 50000, False, [], 1, 's#3']))
            return {iso_labels[0] : f1, iso_labels[1] : f2}
        elif case_name == cls.CASE_ASSOCIATION_96:
            f = dict(
                b2=[205201, 'fixed', 5, 50, False, [], 0, None],
                c2=[205202, 'fixed', 5, 50, False, [], 0, None],
                b4=[205203, 'fixed', 5, 50, False, [], 0, None],
                c4=[205200, 'fixed', 5, 50, False, [], 0, None],
                b8=['mock', 'mock', 5, None, False, [], None, None],
                c8=['mock', 'mock', 5, None, False, [], None, None])
            f1 = dict(f, **dict(
                        b6=[205205, 'floating', 5, 50, False, [], 0, None],
                        c6=[205206, 'floating', 5, 50, False, [], 0, None]))
            f2 = dict(f, **dict(
                        b6=[205207, 'floating', 5, 50, False, [], 0, None],
                        c6=[205208, 'floating', 5, 50, False, [], 0, None]))
            return {iso_labels[0] : f1, iso_labels[1] : f2}
        elif case_name == cls.CASE_ASSOCIATION_SIMPLE:
            f = dict(
                b2=[205201, 'fixed', 10, 50, False, [], 3, None],
                b3=[205202, 'fixed', 10, 50, False, [], 2, None],
                b4=[205200, 'fixed', 10, 50, False, [], 3, None],
                d2=[205201, 'fixed', 10, 50, False, [], 3, None],
                d3=[205202, 'fixed', 10, 50, False, [], 2, None],
                d4=[205200, 'fixed', 10, 50, False, [], 3, None],
                e2=['mock', 'mock', 10, None, False, [], None, None],
                e3=['mock', 'mock', 10, None, False, [], None, None])
            f1 = dict(f, **dict(
                    c2=[205205, 'floating', 10, 50, False, [], 1, None],
                    c3=[205206, 'floating', 10, 50, False, [], 0, None],
                    c4=[205207, 'floating', 10, 50, False, [], 1, None]))
            f2 = dict(f, **dict(
                    c2=[205208, 'floating', 10, 50, False, [], 1, None],
                    c3=[205209, 'floating', 10, 50, False, [], 0, None],
                    c4=[205210, 'floating', 10, 50, False, [], 1, None]))
            return {iso_labels[0] : f1, iso_labels[1] : f2}
        elif case_name == cls.CASE_ASSOCIATION_NO_CYBIO:
            f = dict(
                c3=[205201, 'fixed', 20, 100, True,
                    [TransferTarget('c4', 5, 'a'),
                     TransferTarget('e4', 5, 'a')], None, None],
                c4=[205201, 'fixed', 10, 50, True, [], None, None],
                c5=[180005, 'fixed', 20, 100, True,
                    [TransferTarget('c6', 5, 'a'),
                     TransferTarget('e6', 5, 'a')], None, None],
                c6=[180005, 'fixed', 10, 50, True, [], None, None],
                e3=[205201, 'fixed', 10, 100, True, [], None, None],
                e4=[205201, 'fixed', 10, 50, True, [], None, None],
                e5=[180005, 'fixed', 10, 100, True, [], None, None],
                e6=[180005, 'fixed', 10, 50, True, [], None, None],
                f3=['mock', 'mock', 10, None, False, [], None, None])
            f1 = dict(f, **dict(
                d3=[205202, 'floating', 15, 100, False,
                    [TransferTarget('d4', 5, 'a')], None, None],
                d4=[205202, 'floating', 10, 50, False, [], None, None],
                d5=[205203, 'floating', 15, 100, False,
                    [TransferTarget('d6', 5, 'a')], None, None],
                d6=[205203, 'floating', 10, 50, False, [], None, None]))
            f2 = dict(f, **dict(
                d3=[205204, 'floating', 15, 100, False,
                    [TransferTarget('d4', 5, 'a')], None, None],
                d4=[205204, 'floating', 10, 50, False, [], None, None],
                d5=[205205, 'floating', 15, 100, False,
                    [TransferTarget('d6', 5, 'a')], None, None],
                d6=[205205, 'floating', 10, 50, False, [], None, None]))
            return {iso_labels[0] : f1, iso_labels[1] : f2}
        elif case_name == cls.CASE_ASSOCIATION_2_ALIQUOTS:
            f = dict(
                b2=[205201, 'fixed', 10, 50, False, [], 3, None],
                b3=[205202, 'fixed', 10, 50, False, [], 2, None],
                b4=[205200, 'fixed', 10, 50, False, [], 3, None],
                d2=[205201, 'fixed', 10, 50, False, [], 3, None],
                d3=[205202, 'fixed', 10, 50, False, [], 2, None],
                d4=[205200, 'fixed', 10, 50, False, [], 3, None],
                e2=['mock', 'mock', 10, None, False, [], None, None],
                e3=['mock', 'mock', 10, None, False, [], None, None])
            f1 = dict(f, **dict(
                    c2=[205205, 'floating', 10, 50, False, [], 1, None],
                    c3=[205206, 'floating', 10, 50, False, [], 0, None],
                    c4=[205207, 'floating', 10, 50, False, [], 1, None]))
            f2 = dict(f, **dict(
                    c2=[205208, 'floating', 10, 50, False, [], 1, None],
                    c3=[205209, 'floating', 10, 50, False, [], 0, None],
                    c4=[205210, 'floating', 10, 50, False, [], 1, None]))
            return {iso_labels[0] : f1, iso_labels[1] : f2}
        elif case_name == cls.CASE_ASSOCIATION_JOB_LAST:
            f = dict(
                b2=[205201, 'fixed', 10, 50, True, [], None, None],
                b3=[330001, 'fixed', 10, 50, True, [], None, None],
                b4=[205200, 'fixed', 10, 50, True, [], None, None],
                e2=[205201, 'fixed', 15, 100, True,
                    [TransferTarget('b2', 5, 'a')], None, None],
                e3=[330001, 'fixed', 15, 100, True,
                    [TransferTarget('b3', 5, 'a')], None, None],
                e4=[205200, 'fixed', 15, 100, True,
                    [TransferTarget('b4', 5, 'a')], None, None],
                f2=['mock', 'mock', 10, None, False, [], None, None],
                f3=['mock', 'mock', 10, None, False, [], None, None])
            f1 = dict(f, **dict(
                c2=[205202, 'floating', 10, 50, False, [], 1, None],
                c3=[205203, 'floating', 10, 50, False, [], 0, None],
                c4=[205204, 'floating', 10, 50, False, [], 1, None],
                d2=[205205, 'floating', 10, 50, False, [], 3, None],
                d3=[205206, 'floating', 10, 50, False, [], 2, None],
                d4=[205207, 'floating', 10, 50, False, [], 3, None]))
            f2 = dict(f, **dict(
                c2=[205208, 'floating', 10, 50, False, [], 1, None],
                c3=[205209, 'floating', 10, 50, False, [], 0, None],
                c4=[205210, 'floating', 10, 50, False, [], 1, None],
                d2=[205212, 'floating', 10, 50, False, [], 3, None],
                d3=[205214, 'floating', 10, 50, False, [], 2, None],
                d4=[205215, 'floating', 10, 50, False, [], 3, None]))
            return {iso_labels[0] : f1, iso_labels[1] : f2}
        elif case_name == cls.CASE_ASSOCIATION_SEVERAL_CONC:
            f = dict(
                b3=[205201, 'fixed', 10, 50, True, [], None, None],
                b5=[330001, 'fixed', 10, 50, True, [], None, None],
                b7=[205200, 'fixed', 10, 50, True, [], None, None],
                e3=['mock', 'mock', 10, None, False, [], None, None],
                e5=['mock', 'mock', 10, None, False, [], None, None],
                e7=['mock', 'mock', 10, None, False, [], None, None],
                f3=[205201, 'fixed', 15, 100, True,
                    [TransferTarget('b3', 5, 'a')], None, None],
                f5=[330001, 'fixed', 15, 100, True,
                    [TransferTarget('b5', 5, 'a')], None, None],
                f7=[205200, 'fixed', 15, 100, True,
                    [TransferTarget('b7', 5, 'a')], None, None])
            f1 = dict(f, **dict(
                c3=[205202, 'floating', 10, 50, False, [], 0, None],
                c5=[205203, 'floating', 10, 50, False, [], 0, None],
                c7=[205204, 'floating', 10, 50, False, [], 0, None],
                d3=[205202, 'floating', 15, 100, False,
                    [TransferTarget('c3', 5, 'a')], 2, None],
                d5=[205203, 'floating', 15, 100, False,
                    [TransferTarget('c5', 5, 'a')], 2, None],
                d7=[205204, 'floating', 15, 100, False,
                    [TransferTarget('c7', 5, 'a')], 2, None],
                g3=[205205, 'floating', 10, 50, False, [], 0, None],
                g5=[205206, 'floating', 10, 50, False, [], 0, None],
                g7=[205207, 'floating', 10, 50, False, [], 0, None],
                h3=[205205, 'floating', 15, 100, False,
                    [TransferTarget('g3', 5, 'a')], 2, None],
                h5=[205206, 'floating', 15, 100, False,
                    [TransferTarget('g5', 5, 'a')], 2, None],
                h7=[205207, 'floating', 15, 100, False,
                    [TransferTarget('g7', 5, 'a')], 2, None]))
            f2 = dict(f, **dict(
                c3=[205208, 'floating', 10, 50, False, [], 0, None],
                c5=[205209, 'floating', 10, 50, False, [], 0, None],
                c7=[205210, 'floating', 10, 50, False, [], 0, None],
                d3=[205208, 'floating', 15, 100, False,
                    [TransferTarget('c3', 5, 'a')], 2, None],
                d5=[205209, 'floating', 15, 100, False,
                    [TransferTarget('c5', 5, 'a')], 2, None],
                d7=[205210, 'floating', 15, 100, False,
                    [TransferTarget('c7', 5, 'a')], 2, None],
                g3=[205212, 'floating', 10, 50, False, [], 0, None],
                g5=[205214, 'floating', 10, 50, False, [], 0, None],
                g7=[205215, 'floating', 10, 50, False, [], 0, None],
                h3=[205212, 'floating', 15, 100, False,
                    [TransferTarget('g3', 5, 'a')], 2, None],
                h5=[205214, 'floating', 15, 100, False,
                    [TransferTarget('g5', 5, 'a')], 2, None],
                h7=[205215, 'floating', 15, 100, False,
                    [TransferTarget('g7', 5, 'a')], 2, None]))
            return {iso_labels[0] : f1, iso_labels[1] : f2}
        elif case_name == cls.CASE_LIBRARY_SIMPLE:
            f = dict(
                b2=[205201, 'fixed', 4, 1270, True, [], None, None],
                d2=[330001, 'fixed', 4, 1270, True, [], None, None],
                f2=[1056000, 'fixed', 4, 1270, True, [], None, None],
                h2=['mock', 'mock', 4, None, False, [], None, None],
                i10=[205201, 'fixed', 4, 1270, True, [], None, None],
                k10=[330001, 'fixed', 4, 1270, True, [], None, None],
                m10=[1056000, 'fixed', 4, 1270, True, [], None, None],
                o10=['mock', 'mock', 4, None, False, [], None, None],
                b3=['library', 'library', 4, 1270, False, [], None, None],
                b4=['library', 'library', 4, 1270, False, [], None, None],
                c3=['library', 'library', 4, 1270, False, [], None, None],
                c4=['library', 'library', 4, 1270, False, [], None, None]
                )
            return {iso_labels[0] : f, iso_labels[1] : f}
        elif case_name == cls.CASE_LIBRARY_2_ALIQUOTS:
            f = dict(
                b2=[205201, 'fixed', 4, 1270, True, [], None, None],
                d2=[330001, 'fixed', 4, 1270, True, [], None, None],
                f2=[1056000, 'fixed', 4, 1270, True, [], None, None],
                h2=['mock', 'mock', 4, None, False, [], None, None],
                i10=[205201, 'fixed', 4, 1270, True, [], None, None],
                k10=[330001, 'fixed', 4, 1270, True, [], None, None],
                m10=[1056000, 'fixed', 4, 1270, True, [], None, None],
                o10=['mock', 'mock', 4, None, False, [], None, None],
                b3=['library', 'library', 4, 1270, False, [], None, None],
                b4=['library', 'library', 4, 1270, False, [], None, None],
                c3=['library', 'library', 4, 1270, False, [], None, None],
                c4=['library', 'library', 4, 1270, False, [], None, None]
                )
            return {iso_labels[0] : f, iso_labels[1] : f}
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
            p1 = dict(d1=[205201, 'fixed', 12, 10000, [],
                          [TransferTarget('d2', 2, 'a')], None, 's#1'],
                      d2=[330001, 'fixed', 12, 2000, [],
                          [TransferTarget('d4', 2, 'a')], None, 's#1'],
                      d3=[333803, 'fixed', 12, 500000, [],
                          [TransferTarget('d6', 2, 'a')], None, 's#1'],
                      d4=[1056000, 'fixed', 12, 4000, [],
                          [TransferTarget('d8', 2, 'a')], None, 's#1'],
                      d5=[180005, 'fixed', 12, 40000, [],
                          [TransferTarget('d10', 2, 'a')], None, 's#1'])
            return {'123_iso_01_p' : p1}
        elif case_name == cls.CASE_NO_JOB_COMPLEX:
            p1 = dict(
                d1=[333803, 'fixed', 12, 1953125,
                    [TransferTarget('d2', 2, 'p#1')], [], None, 's#1'],
                d2=[333803, 'fixed', 250, 15625,
                    [TransferTarget('d3', 2, 'p#1')], [], None, None],
                d3=[333803, 'fixed', 250, 125, [TransferTarget('d4', 2, 'p#1')],
                    [], None, None],
                d4=[333803, 'fixed', 250, 1, [],
                    [TransferTarget('d3', 3, 'a'), TransferTarget('d4', 3, 'a')],
                    None, None],
                f1=[180005, 'fixed', 50, 96000, [],
                    [TransferTarget('f3', 3, 'a')], None, 's#1'])
            return {'123_iso_01_p' : p1}
        elif case_name == cls.CASE_ASSOCIATION_DIRECT:
            return {}
        elif case_name == cls.CASE_ASSOCIATION_96:
            p = dict(
                c3=[205201, 'fixed', 11, 25000,
                    [TransferTarget('c4', 1, 'p#1')], [], 0, 's#1'],
                c4=[205201, 'fixed', 100, 250,
                    [], [TransferTarget('b2', 1, 'a')], 1, None],
                e3=[205202, 'fixed', 11, 25000,
                    [TransferTarget('e4', 1, 'p#1')], [], 0, 's#1'],
                e4=[205202, 'fixed', 100, 250,
                    [], [TransferTarget('c2', 1, 'a')], 1, None],
                c7=[205203, 'fixed', 11, 25000,
                    [TransferTarget('c8', 1, 'p#1')], [], 0, 's#1'],
                c8=[205203, 'fixed', 100, 250,
                    [], [TransferTarget('b4', 1, 'a')], 1, None],
                e7=[205200, 'fixed', 11, 25000,
                    [TransferTarget('e8', 1, 'p#1')], [], 0, 's#1'],
                e8=[205200, 'fixed', 100, 250,
                    [], [TransferTarget('c4', 1, 'a')], 1, None])
            p1 = dict(p, **dict(
                c11=[205205, 'floating', 11, 25000,
                    [TransferTarget('c12', 1, 'p#1')], [], 0, 's#1'],
                c12=[205205, 'floating', 100, 250,
                     [], [TransferTarget('b6', 1, 'a')], 1, None],
                e11=[205206, 'floating', 11, 25000,
                    [TransferTarget('e12', 1, 'p#1')], [], 0, 's#1'],
                e12=[205206, 'floating', 100, 250,
                     [], [TransferTarget('c6', 1, 'a')], 1, None]))
            p2 = dict(p, **dict(
                c11=[205207, 'floating', 11, 25000,
                    [TransferTarget('c12', 1, 'p#1')], [], 0, 's#1'],
                c12=[205207, 'floating', 100, 250,
                     [], [TransferTarget('b6', 1, 'a')], 1, None],
                e11=[205208, 'floating', 11, 25000,
                    [TransferTarget('e12', 1, 'p#1')], [], 0, 's#1'],
                e12=[205209, 'floating', 100, 250,
                     [], [TransferTarget('c6', 1, 'a')], 1, None]))
            return {'123_iso_01_p' : p1, '123_iso_02_p' : p2}
        elif case_name == cls.CASE_ASSOCIATION_SIMPLE:
            p = dict(
                b2=[205201, 'fixed', 100, 500, [],
                    [TransferTarget('b2', 1, 'a')], 3, 's#1'],
                b3=[205202, 'fixed', 100, 500, [],
                    [TransferTarget('b3', 1, 'a')], 2, 's#1'],
                b4=[205200, 'fixed', 100, 500, [],
                    [TransferTarget('b4', 1, 'a')], 3, 's#1'],
                d2=[205201, 'fixed', 100, 500, [],
                    [TransferTarget('d2', 1, 'a')], 3, 's#1'],
                d3=[205202, 'fixed', 100, 500, [],
                    [TransferTarget('d3', 1, 'a')], 2, 's#1'],
                d4=[205200, 'fixed', 100, 500, [],
                    [TransferTarget('d4', 1, 'a')], 3, 's#1'])
            p1 = dict(p, **dict(
                c2=[205205, 'floating', 100, 500, [],
                    [TransferTarget('c2', 1, 'a')], 1, 's#3'],
                c3=[205206, 'floating', 100, 500, [],
                    [TransferTarget('c3', 1, 'a')], 0, 's#2'],
                c4=[205207, 'floating', 100, 500, [],
                    [TransferTarget('c4', 1, 'a')], 1, 's#3']))
            p2 = dict(p, **dict(
                c2=[205208, 'floating', 100, 500, [],
                    [TransferTarget('c2', 1, 'a')], 1, 's#3'],
                c3=[205209, 'floating', 100, 500, [],
                    [TransferTarget('c3', 1, 'a')], 0, 's#2'],
                c4=[205210, 'floating', 100, 500, [],
                    [TransferTarget('c4', 1, 'a')], 1, 's#3']))
            return {'123_iso_01_p' : p1, '123_iso_02_p' : p2}
        elif case_name == cls.CASE_ASSOCIATION_NO_CYBIO:
            p1 = dict(
                d1=[205202, 'floating', 66.7, 750, [],
                    [TransferTarget('d3', 2, 'a')], None, 's#2'],
                d2=[205203, 'floating', 66.7, 750, [],
                    [TransferTarget('d5', 2, 'a')], None, 's#2'])
            p2 = dict(
                d1=[205204, 'floating', 66.7, 750, [],
                    [TransferTarget('d3', 2, 'a')], None, 's#2'],
                d2=[205205, 'floating', 66.7, 750, [],
                    [TransferTarget('d5', 2, 'a')], None, 's#2'])
            return {'123_iso_01_p' : p1, '123_iso_02_p' : p2}
        elif case_name == cls.CASE_ASSOCIATION_2_ALIQUOTS:
            p = dict(
                b2=[205201, 'fixed', 100, 500, [],
                    [TransferTarget('b2', 1, 'a')], 3, 's#1'],
                b3=[205202, 'fixed', 100, 500, [],
                    [TransferTarget('b3', 1, 'a')], 2, 's#1'],
                b4=[205200, 'fixed', 100, 500, [],
                    [TransferTarget('b4', 1, 'a')], 3, 's#1'],
                d2=[205201, 'fixed', 100, 500, [],
                    [TransferTarget('d2', 1, 'a')], 3, 's#1'],
                d3=[205202, 'fixed', 100, 500, [],
                    [TransferTarget('d3', 1, 'a')], 2, 's#1'],
                d4=[205200, 'fixed', 100, 500, [],
                    [TransferTarget('d4', 1, 'a')], 3, 's#1'])
            p1 = dict(p, **dict(
                c2=[205205, 'floating', 100, 500, [],
                    [TransferTarget('c2', 1, 'a')], 1, 's#3'],
                c3=[205206, 'floating', 100, 500, [],
                    [TransferTarget('c3', 1, 'a')], 0, 's#2'],
                c4=[205207, 'floating', 100, 500, [],
                    [TransferTarget('c4', 1, 'a')], 1, 's#3']))
            p2 = dict(p, **dict(
                c2=[205208, 'floating', 100, 500, [],
                    [TransferTarget('c2', 1, 'a')], 1, 's#3'],
                c3=[205209, 'floating', 100, 500, [],
                    [TransferTarget('c3', 1, 'a')], 0, 's#2'],
                c4=[205210, 'floating', 100, 500, [],
                    [TransferTarget('c4', 1, 'a')], 1, 's#3']))
            return {'123_iso_01_p' : p1, '123_iso_02_p' : p2}
        elif case_name == cls.CASE_ASSOCIATION_JOB_LAST:
            p1 = dict(
                c2=[205202, 'floating', 100, 500, [],
                    [TransferTarget('c2', 1, 'a')], 1, 's#3'],
                c3=[205203, 'floating', 100, 500, [],
                    [TransferTarget('c3', 1, 'a')], 0, 's#2'],
                c4=[205204, 'floating', 100, 500, [],
                    [TransferTarget('c4', 1, 'a')], 1, 's#3'],
                d2=[205205, 'floating', 100, 500, [],
                    [TransferTarget('d2', 1, 'a')], 3, 's#5'],
                d3=[205206, 'floating', 100, 500, [],
                    [TransferTarget('d3', 1, 'a')], 2, 's#4'],
                d4=[205207, 'floating', 100, 500, [],
                    [TransferTarget('d4', 1, 'a')], 3, 's#5'])
            p2 = dict(
                c2=[205208, 'floating', 100, 500, [],
                    [TransferTarget('c2', 1, 'a')], 1, 's#3'],
                c3=[205209, 'floating', 100, 500, [],
                    [TransferTarget('c3', 1, 'a')], 0, 's#2'],
                c4=[205210, 'floating', 100, 500, [],
                    [TransferTarget('c4', 1, 'a')], 1, 's#3'],
                d2=[205212, 'floating', 100, 500, [],
                    [TransferTarget('d2', 1, 'a')], 3, 's#5'],
                d3=[205214, 'floating', 100, 500, [],
                    [TransferTarget('d3', 1, 'a')], 2, 's#4'],
                d4=[205215, 'floating', 100, 500, [],
                    [TransferTarget('d4', 1, 'a')], 3, 's#5'])
            return {'123_iso_01_p' : p1, '123_iso_02_p' : p2}
        elif case_name == cls.CASE_ASSOCIATION_SEVERAL_CONC:
            p1 = dict(
                b2=[205202, 'floating', 33.3, 1500, [],
                    [TransferTarget('d3', 1, 'a')], 0, 's#2'],
                b3=[205203, 'floating', 33.3, 1500, [],
                    [TransferTarget('d5', 1, 'a')], 0, 's#2'],
                b4=[205204, 'floating', 33.3, 1500, [],
                    [TransferTarget('d7', 1, 'a')], 0, 's#2'],
                d2=[205205, 'floating', 33.3, 1500, [],
                    [TransferTarget('h3', 1, 'a')], 0, 's#2'],
                d3=[205206, 'floating', 33.3, 1500, [],
                    [TransferTarget('h5', 1, 'a')], 0, 's#2'],
                d4=[205207, 'floating', 33.3, 1500, [],
                    [TransferTarget('h7', 1, 'a')], 0, 's#2'])
            p2 = dict(
                b2=[205208, 'floating', 33.3, 1500, [],
                    [TransferTarget('d3', 1, 'a')], 0, 's#2'],
                b3=[205209, 'floating', 33.3, 1500, [],
                    [TransferTarget('d5', 1, 'a')], 0, 's#2'],
                b4=[205210, 'floating', 33.3, 1500, [],
                    [TransferTarget('d7', 1, 'a')], 0, 's#2'],
                d2=[205212, 'floating', 33.3, 1500, [],
                    [TransferTarget('h3', 1, 'a')], 0, 's#2'],
                d3=[205214, 'floating', 33.3, 1500, [],
                    [TransferTarget('h5', 1, 'a')], 0, 's#2'],
                d4=[205215, 'floating', 33.3, 1500, [],
                    [TransferTarget('h7', 1, 'a')], 0, 's#2'])
            return {'123_iso_01_p' : p1, '123_iso_02_p' : p2}
        elif case_name == cls.CASE_LIBRARY_SIMPLE:
            return dict()
        elif case_name == cls.CASE_LIBRARY_2_ALIQUOTS:
            return dict()
        raise NotImplementedError('The value for this case is missing.')

    @classmethod
    def get_preparation_plate_layout_shape(cls, case_name):
        if case_name == cls.CASE_NO_JOB_1_PREP:
            return RACK_SHAPE_NAMES.SHAPE_96
        elif case_name == cls.CASE_NO_JOB_COMPLEX:
            return RACK_SHAPE_NAMES.SHAPE_96
        elif case_name == cls.CASE_ASSOCIATION_96:
            return RACK_SHAPE_NAMES.SHAPE_384
        elif case_name == cls.CASE_ASSOCIATION_SIMPLE:
            return RACK_SHAPE_NAMES.SHAPE_384
        elif case_name == cls.CASE_ASSOCIATION_NO_CYBIO:
            return RACK_SHAPE_NAMES.SHAPE_96
        elif case_name == cls.CASE_ASSOCIATION_2_ALIQUOTS:
            return RACK_SHAPE_NAMES.SHAPE_384
        elif case_name == cls.CASE_ASSOCIATION_JOB_LAST:
            return RACK_SHAPE_NAMES.SHAPE_384
        elif case_name == cls.CASE_ASSOCIATION_SEVERAL_CONC:
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
        elif case_name == cls.CASE_NO_JOB_COMPLEX:
            return {}
        elif case_name == cls.CASE_ASSOCIATION_DIRECT:
            return {}
        elif case_name == cls.CASE_ASSOCIATION_96:
            return {}
        elif case_name == cls.CASE_ASSOCIATION_SIMPLE:
            return {}
        elif case_name == cls.CASE_ASSOCIATION_NO_CYBIO:
            jp = dict(
                 c1=[205201, 'fixed', 100, 500, [],
                     [TransferTarget('c3', 4, 'a'),
                      TransferTarget('e3', 2, 'a')], None, 's#1'],
                 c2=[180005, 'fixed', 200, 500, [],
                     [TransferTarget('c5', 4, 'a'),
                      TransferTarget('e5', 2, 'a')], None, 's#1'])
            return {'123_job_01_jp' : jp}
        elif case_name == cls.CASE_ASSOCIATION_2_ALIQUOTS:
            return {}
        elif case_name == cls.CASE_ASSOCIATION_JOB_LAST:
            jp = dict(
                 e1=[205201, 'fixed', 66.7, 750, [],
                     [TransferTarget('e2', 2, 'a')], None, 's#1'],
                 e2=[330001, 'fixed', 14.7, 750, [],
                     [TransferTarget('e3', 2, 'a')], None, 's#1'],
                 e3=[205200, 'fixed', 66.7, 750, [],
                     [TransferTarget('e4', 2, 'a')], None, 's#1'])
            return {'123_job_01_jp' : jp}
        elif case_name == cls.CASE_ASSOCIATION_SEVERAL_CONC:
            jp = dict(
                 f1=[205201, 'fixed', 66.7, 750, [],
                     [TransferTarget('f3', 2, 'a')], None, 's#1'],
                 f2=[330001, 'fixed', 14.7, 750, [],
                     [TransferTarget('f5', 2, 'a')], None, 's#1'],
                 f3=[205200, 'fixed', 66.7, 750, [],
                     [TransferTarget('f7', 2, 'a')], None, 's#1'])
            return {'123_job_01_jp' : jp}
        elif case_name == cls.CASE_LIBRARY_SIMPLE:
            jp = dict(
                 b1=[205201, 'fixed', 19.7, 2540, [],
                     [TransferTarget('b2', 2, 'a'),
                      TransferTarget('i10', 2, 'a')], None, 's#1'],
                 d1=[330001, 'fixed', 18.1, 2540, [],
                     [TransferTarget('d2', 2, 'a'),
                      TransferTarget('k10', 2, 'a')], None, 's#1'],
                 f1=[1056000, 'fixed', 18.1, 2540, [],
                     [TransferTarget('f2', 2, 'a'),
                      TransferTarget('m10', 2, 'a')], None, 's#1'])
            return {'123_job_01_jp' : jp}
        elif case_name == cls.CASE_LIBRARY_2_ALIQUOTS:
            jp = dict(
                 b1=[205201, 'fixed', 27.6, 2540, [],
                     [TransferTarget('b2', 2, 'a'),
                      TransferTarget('i10', 2, 'a')], None, 's#1'],
                 d1=[330001, 'fixed', 26.4, 2540, [],
                     [TransferTarget('d2', 2, 'a'),
                      TransferTarget('k10', 2, 'a')], None, 's#1'],
                 f1=[1056000, 'fixed', 26.4, 2540, [],
                     [TransferTarget('f2', 2, 'a'),
                      TransferTarget('m10', 2, 'a')], None, 's#1'])
            return {'123_job_01_jp' : jp}
        raise NotImplementedError('The value for this case is missing.')

    @classmethod
    def get_job_plate_layout_shape(cls, case_name):
        if case_name == cls.CASE_ASSOCIATION_NO_CYBIO:
            return RACK_SHAPE_NAMES.SHAPE_96
        elif case_name == cls.CASE_ASSOCIATION_JOB_LAST:
            return RACK_SHAPE_NAMES.SHAPE_96
        elif case_name == cls.CASE_ASSOCIATION_SEVERAL_CONC:
            return RACK_SHAPE_NAMES.SHAPE_96
        elif case_name == cls.CASE_LIBRARY_SIMPLE:
            return RACK_SHAPE_NAMES.SHAPE_96
        elif case_name == cls.CASE_LIBRARY_2_ALIQUOTS:
            return RACK_SHAPE_NAMES.SHAPE_96
        raise NotImplementedError('The value for this case is missing.')

    @classmethod
    def get_number_job_stock_racks(cls, case_name):
        if case_name == cls.CASE_ORDER_ONLY:
            return 0
        elif case_name == cls.CASE_NO_JOB_DIRECT:
            return 0
        elif case_name == cls.CASE_NO_JOB_1_PREP:
            return 0
        elif case_name == cls.CASE_NO_JOB_COMPLEX:
            return 0
        elif case_name == cls.CASE_ASSOCIATION_DIRECT:
            return 1
        elif case_name == cls.CASE_ASSOCIATION_96:
            return 0
        elif case_name == cls.CASE_ASSOCIATION_SIMPLE:
            return 1
        elif case_name == cls.CASE_ASSOCIATION_NO_CYBIO:
            return 1
        elif case_name == cls.CASE_ASSOCIATION_2_ALIQUOTS:
            return 1
        elif case_name == cls.CASE_ASSOCIATION_JOB_LAST:
            return 1
        elif case_name == cls.CASE_ASSOCIATION_SEVERAL_CONC:
            return 1
        elif case_name == cls.CASE_LIBRARY_SIMPLE:
            return 1
        elif case_name == cls.CASE_LIBRARY_2_ALIQUOTS:
            return 1
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
        elif case_name == cls.CASE_NO_JOB_COMPLEX:
            return {iso_labels[0] : 1}
        elif case_name == cls.CASE_ASSOCIATION_DIRECT:
            return {iso_labels[0] : 2, iso_labels[1] : 2}
        elif case_name == cls.CASE_ASSOCIATION_96:
            return {iso_labels[0] : 1, iso_labels[1] : 1}
        elif case_name == cls.CASE_ASSOCIATION_SIMPLE:
            return {iso_labels[0] : 2, iso_labels[1] : 2}
        elif case_name == cls.CASE_ASSOCIATION_NO_CYBIO:
            return {iso_labels[0] : 1, iso_labels[1] : 1}
        elif case_name == cls.CASE_ASSOCIATION_2_ALIQUOTS:
            return {iso_labels[0] : 2, iso_labels[1] : 2}
        elif case_name == cls.CASE_ASSOCIATION_JOB_LAST:
            return {iso_labels[0] : 4, iso_labels[1] : 4}
        elif case_name == cls.CASE_ASSOCIATION_SEVERAL_CONC:
            return {iso_labels[0] : 1, iso_labels[1] : 1}
        elif case_name == cls.CASE_LIBRARY_SIMPLE:
            return {iso_labels[0] : 0, iso_labels[1] : 0}
        elif case_name == cls.CASE_LIBRARY_2_ALIQUOTS:
            return {iso_labels[0] : 0, iso_labels[1] : 0}
        raise NotImplementedError('The value for this case is missing.')

    @classmethod
    def get_iso_worklist_data(cls, case_name):
        type_dil = TRANSFER_TYPES.SAMPLE_DILUTION
        type_trans = TRANSFER_TYPES.SAMPLE_TRANSFER
        type_rack = TRANSFER_TYPES.RACK_SAMPLE_TRANSFER
        ps_biomek = get_pipetting_specs_biomek()
        ps_cybio = get_pipetting_specs_cybio()
        #: worklist label - type, pipetting specs, worklist index
        if case_name == cls.CASE_ORDER_ONLY:
            return {}
        elif case_name == cls.CASE_NO_JOB_DIRECT:
            return {'123_1_a_buffer' : [type_dil, ps_biomek, 1]}
        elif case_name == cls.CASE_NO_JOB_1_PREP:
            return {'123_1_p_buffer' : [type_dil, ps_biomek, 1],
                    '123_2_a_buffer' : [type_dil, ps_biomek, 2],
                    '123_3_p_to_a' : [type_trans, ps_biomek, 3]}
        elif case_name == cls.CASE_NO_JOB_COMPLEX:
            return {'123_1_p_buffer' : [type_dil, ps_biomek, 1],
                    '123_2_a_buffer' : [type_dil, ps_biomek, 2],
                    '123_3_p_to_p' : [type_trans, ps_biomek, 3],
                    '123_4_p_to_p' : [type_trans, ps_biomek, 4],
                    '123_5_p_to_p' : [type_trans, ps_biomek, 5],
                    '123_6_p_to_a' : [type_trans, ps_biomek, 6],
                    '123_7_a_to_a' : [type_trans, ps_biomek, 7]}
        elif case_name == cls.CASE_ASSOCIATION_DIRECT:
            return {'123_1_a_buffer' : [type_dil, ps_biomek, 1]}
        elif case_name == cls.CASE_ASSOCIATION_96:
            return {'123_1_p_buffer' : [type_dil, ps_cybio, 1],
                    '123_2_a_buffer' : [type_dil, ps_biomek, 2],
                    '123_3_p_to_p' : [type_rack, ps_cybio, 3],
                    '123_4_p_to_a' : [type_rack, ps_cybio, 4]}
        elif case_name == cls.CASE_ASSOCIATION_SIMPLE:
            return {'123_1_p_buffer' : [type_dil, ps_cybio, 1],
                    '123_2_a_buffer' : [type_dil, ps_biomek, 2],
                    '123_3_p_to_a' : [type_rack, ps_cybio, 3]}
        elif case_name == cls.CASE_ASSOCIATION_NO_CYBIO:
            return {'123_2_p_buffer' : [type_dil, ps_biomek, 2],
                    '123_3_a_buffer' : [type_dil, ps_biomek, 3],
                    '123_5_p_to_a' : [type_trans, ps_biomek, 5],
                    '123_6_a_to_a' : [type_trans, ps_biomek, 6]}
        elif case_name == cls.CASE_ASSOCIATION_2_ALIQUOTS:
            return {'123_1_p_buffer' : [type_dil, ps_cybio, 1],
                    '123_2_a_buffer' : [type_dil, ps_biomek, 2],
                    '123_3_p_to_a' : [type_rack, ps_cybio, 3]}
        elif case_name == cls.CASE_ASSOCIATION_JOB_LAST:
            return {'123_1_p_buffer' : [type_dil, ps_cybio, 1],
                    '123_2_a_buffer' : [type_dil, ps_biomek, 2],
                    '123_4_p_to_a' : [type_rack, ps_cybio, 4]}
        elif case_name == cls.CASE_ASSOCIATION_SEVERAL_CONC:
            return {'123_1_p_buffer' : [type_dil, ps_cybio, 1],
                    '123_2_a_buffer' : [type_dil, ps_biomek, 2],
                    '123_5_p_to_a' : [type_rack, ps_cybio, 4],
                    '123_6_a_to_a' : [type_rack, ps_cybio, 5]}
        elif case_name == cls.CASE_LIBRARY_SIMPLE:
            return {'123_2_a_buffer' : [type_dil, ps_biomek, 2]}
        elif case_name == cls.CASE_LIBRARY_2_ALIQUOTS:
            return {'123_2_a_buffer' : [type_dil, ps_biomek, 2]}
        raise NotImplementedError('The value for this case is missing.')

    @classmethod
    def get_job_worklist_data(cls, case_name):
        type_dil = TRANSFER_TYPES.SAMPLE_DILUTION
        type_trans = TRANSFER_TYPES.SAMPLE_TRANSFER
        ps_biomek = get_pipetting_specs_biomek()
        #: worklist label - type, pipetting specs, worklist index
        if case_name == cls.CASE_ORDER_ONLY:
            return dict()
        elif case_name == cls.CASE_NO_JOB_DIRECT:
            return dict()
        elif case_name == cls.CASE_NO_JOB_1_PREP:
            return dict()
        elif case_name == cls.CASE_NO_JOB_COMPLEX:
            return dict()
        elif case_name == cls.CASE_ASSOCIATION_DIRECT:
            return dict()
        elif case_name == cls.CASE_ASSOCIATION_96:
            return dict()
        elif case_name == cls.CASE_ASSOCIATION_SIMPLE:
            return dict()
        elif case_name == cls.CASE_ASSOCIATION_NO_CYBIO:
            return {'123_1_jp_buffer' : [type_dil, ps_biomek, 1],
                    '123_4_jp_to_a' : [type_trans, ps_biomek, 4]}
        elif case_name == cls.CASE_ASSOCIATION_2_ALIQUOTS:
            return dict()
        elif case_name == cls.CASE_ASSOCIATION_JOB_LAST:
            return {'123_3_jp_buffer' : [type_dil, ps_biomek, 3],
                    '123_5_jp_to_a' : [type_trans, ps_biomek, 5],
                    '123_6_a_to_a' : [type_trans, ps_biomek, 6]}
        elif case_name == cls.CASE_ASSOCIATION_SEVERAL_CONC:
            return {'123_3_a_buffer' : [type_dil, ps_biomek, 3],
                    '123_4_jp_buffer' : [type_dil, ps_biomek, 4],
                    '123_7_jp_to_a' : [type_trans, ps_biomek, 6],
                    '123_8_a_to_a' : [type_trans, ps_biomek, 7]}
        elif case_name == cls.CASE_LIBRARY_SIMPLE:
            return {'123_1_jp_buffer' : [type_dil, ps_biomek, 1],
                    '123_3_jp_to_a' : [type_trans, ps_biomek, 3]}
        elif case_name == cls.CASE_LIBRARY_2_ALIQUOTS:
            return {'123_1_jp_buffer' : [type_dil, ps_biomek, 1],
                    '123_3_jp_to_a' : [type_trans, ps_biomek, 3]}
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
                return dict(d1=9.6, d2=9.6, d3=10.8, d4=7.2, d5=7.2)
            elif worklist_label == '123_2_a_buffer':
                return dict(d8=2, d10=2)
            elif worklist_label == '123_3_p_to_a':
                return dict(d2=[2, 'd1'], d4=[2, 'd2'], d6=[2, 'd3'],
                            d8=[2, 'd4'], d10=[2, 'd5'])
        elif case_name == cls.CASE_NO_JOB_COMPLEX:
            if worklist_label == '123_1_p_buffer':
                return dict(d1=7.3, d2=248, d3=248, d4=248, f1=2)
            elif worklist_label == '123_2_a_buffer':
                return dict(b3=10, b4=16)
            elif worklist_label == '123_3_p_to_p':
                return  dict(d2=[2, 'd1'])
            elif worklist_label == '123_4_p_to_p':
                return  dict(d3=[2, 'd2'])
            elif worklist_label == '123_5_p_to_p':
                return dict(d4=[2, 'd3'])
            elif worklist_label == '123_6_p_to_a':
                return dict(d3=[3, 'd4'], d4=[3, 'd4'],
                            f3=[3, 'f1'])
            elif worklist_label == '123_7_a_to_a':
                return dict(b3=[10, 'b2'], b4=[4, 'b2'])
        elif case_name == cls.CASE_ASSOCIATION_DIRECT:
            if worklist_label == '123_1_a_buffer':
                return dict(e2=4, e3=4, b4=2, d4=2)
        elif case_name == cls.CASE_ASSOCIATION_96:
            if worklist_label == '123_1_p_buffer':
                return dict(c3=5.5, c4=99, e3=5.5, e4=99, c7=5.5, c8=99,
                            e7=5.5, e8=99, c11=5.5, c12=99, e11=5.5, e12=99)
            elif worklist_label == '123_2_a_buffer':
                return dict(b2=4, c2=4, b4=4, c4=4, b6=4, c6=4, b8=5, c8=5)
            elif worklist_label == '123_3_p_to_p':
                return {1 : [1, 0, 4]}
            elif worklist_label == '123_4_p_to_a':
                return {0 : [1, 1, 4]}
        elif case_name == cls.CASE_ASSOCIATION_SIMPLE:
            if worklist_label == '123_1_p_buffer':
                return dict(b2=99, b3=99, b4=99, c2=99, c3=99, c4=99,
                             d2=99, d3=99, d4=99)
            elif worklist_label == '123_2_a_buffer':
                return dict(b2=9, b3=9, b4=9, c2=9, c3=9, c4=9,
                            d2=9, d3=9, d4=9, e2=10, e3=10)
            elif worklist_label == '123_3_p_to_a':
                return {0 : [1, 0, 4], 1 : [1, 1, 4], 2 : [1, 2, 4],
                        3 : [1, 3, 4]}
        elif case_name == cls.CASE_ASSOCIATION_NO_CYBIO:
            if worklist_label == '123_1_jp_buffer':
                return dict(c1=99, c2=199)
            elif worklist_label == '123_2_p_buffer':
                return dict(d1=65.7, d2=65.7)
            elif worklist_label == '123_3_a_buffer':
                return dict(c3=16, c4=5, c5=16, c6=5,
                            d3=13, d4=5, d5=13, d6=5,
                            e3=8, e4=5, e5=8, e6=5, f3=10)
            elif worklist_label == '123_4_jp_to_a':
                return dict(c3=[4, 'c1'], c5=[4, 'c2'],
                            e3=[2, 'c1'], e5=[2, 'c2'])
            elif worklist_label == '123_5_p_to_a':
                return dict(d3=[2, 'd1'], d5=[2, 'd2'])
            elif worklist_label == '123_6_a_to_a':
                return dict(c4=[5, 'c3'], e4=[5, 'c3'],
                            c6=[5, 'c5'], e6=[5, 'c5'],
                            d4=[5, 'd3'], d6=[5, 'd5'])
        elif case_name == cls.CASE_ASSOCIATION_2_ALIQUOTS:
            if worklist_label == '123_1_p_buffer':
                return dict(b2=99, b3=99, b4=99, c2=99, c3=99, c4=99,
                            d2=99, d3=99, d4=99)
            elif worklist_label == '123_2_a_buffer':
                return dict(b2=9, b3=9, b4=9, c2=9, c3=9, c4=9,
                            d2=9, d3=9, d4=9, e2=10, e3=10)
            elif worklist_label == '123_3_p_to_a':
                return {0 : [1, 0, 4], 1 : [1, 1, 4], 2 : [1, 2, 4],
                        3 : [1, 3, 4]}
        elif case_name == cls.CASE_ASSOCIATION_JOB_LAST:
            if worklist_label == '123_1_p_buffer':
                return dict(c2=99, c3=99, c4=99, d2=99, d3=99, d4=99)
            elif worklist_label == '123_2_a_buffer':
                return dict(b2=5, b3=5, b4=5, c2=9, c3=9, c4=9,
                            d2=9, d3=9, d4=9, e2=13, e3=13, e4=13,
                            f2=10, f3=10)
            elif worklist_label == '123_3_jp_buffer':
                return dict(e1=65.7, e2=13.6, e3=65.7)
            elif worklist_label == '123_4_p_to_a':
                return {0 : [1, 0, 4], 1 : [1, 1, 4], 2 : [1, 2, 4],
                        3 : [1, 3, 4]}
            elif worklist_label == '123_5_jp_to_a':
                return dict(e2=[2, 'e1'], e3=[2, 'e2'], e4=[2, 'e3'])
            elif worklist_label == '123_6_a_to_a':
                return dict(b2=[5, 'e2'], b3=[5, 'e3'], b4=[5, 'e4'])
        elif case_name == cls.CASE_ASSOCIATION_SEVERAL_CONC:
            if worklist_label == '123_1_p_buffer':
                return dict(b2=32.3, b3=32.3, b4=32.3, d2=32.3, d3=32.3, d4=32.3)
            elif worklist_label == '123_2_a_buffer':
                return dict(c3=5, c5=5, c7=5, d3=14, d5=14, d7=14,
                            g3=5, g5=5, g7=5, h3=14, h5=14, h7=14)
            elif worklist_label == '123_3_a_buffer':
                return dict(b3=5, b5=5, b7=5, f3=13, f5=13, f7=13,
                            e3=10, e5=10, e7=10)
            elif worklist_label == '123_4_jp_buffer':
                return dict(f1=65.7, f2=13.6, f3=65.7)
            elif worklist_label == '123_5_p_to_a':
                return {2 : [1, 0, 4]}
            elif worklist_label == '123_6_a_to_a':
                return {0 : [5, 2, 4]}
            elif worklist_label == '123_7_jp_to_a':
                return dict(f3=[2, 'f1'], f5=[2, 'f2'], f7=[2, 'f3'])
            elif worklist_label == '123_8_a_to_a':
                return dict(b3=[5, 'f3'], b5=[5, 'f5'], b7=[5, 'f7'])
        elif case_name == cls.CASE_LIBRARY_SIMPLE:
            if worklist_label == '123_1_jp_buffer':
                return dict(b1=18.7, d1=13.5, f1=13.5)
            elif worklist_label == '123_2_a_buffer':
                return dict(b2=2, i10=2, d2=2, k10=2, f2=2, m10=2,
                            h2=4, o10=4)
            elif worklist_label == '123_3_jp_to_a':
                return dict(b2=[2, 'b1'], i10=[2, 'b1'], d2=[2, 'd1'],
                            k10=[2, 'd1'], f2=[2, 'f1'], m10=[2, 'f1'])
        elif case_name == cls.CASE_LIBRARY_2_ALIQUOTS:
            if worklist_label == '123_1_jp_buffer':
                return dict(b1=26.2, d1=19.7, f1=19.7)
            elif worklist_label == '123_2_a_buffer':
                return dict(b2=2, i10=2, d2=2, k10=2, f2=2, m10=2,
                            h2=4, o10=4)
            elif worklist_label == '123_3_jp_to_a':
                return dict(b2=[2, 'b1'], i10=[2, 'b1'], d2=[2, 'd1'],
                            k10=[2, 'd1'], f2=[2, 'f1'], m10=[2, 'f1'])
        raise NotImplementedError('The value for this case or worklist (%s) ' \
                                  'is missing.' % (worklist_label))

    @classmethod
    def get_pool_set_data(cls, case_name):
        if case_name == cls.CASE_ORDER_ONLY:
            return None
        elif case_name == cls.CASE_NO_JOB_DIRECT:
            return None
        elif case_name == cls.CASE_NO_JOB_1_PREP:
            return None
        elif case_name == cls.CASE_NO_JOB_COMPLEX:
            return None
        elif case_name == cls.CASE_ASSOCIATION_DIRECT:
            return {'123_iso_01' : [205205, 205206, 205207],
                    '123_iso_02' : [205208, 205209, 205210]}
        elif case_name == cls.CASE_ASSOCIATION_96:
            return {'123_iso_01' : [205205, 205206],
                    '123_iso_02' : [205207, 205208]}
        elif case_name == cls.CASE_ASSOCIATION_SIMPLE:
            return {'123_iso_01' : [205205, 205206, 205207],
                    '123_iso_02' : [205208, 205209, 205210]}
        elif case_name == cls.CASE_ASSOCIATION_NO_CYBIO:
            return {'123_iso_01' : [205202, 205203],
                    '123_iso_02' : [205204, 205205]}
        elif case_name == cls.CASE_ASSOCIATION_2_ALIQUOTS:
            return {'123_iso_01' : [205205, 205206, 205207],
                    '123_iso_02' : [205208, 205209, 205210]}
        elif case_name == cls.CASE_ASSOCIATION_JOB_LAST:
            return {'123_iso_01' : [205205, 205203, 205204, 205205, 205206,
                                    205207],
                    '123_iso_02' : [205208, 205209, 205210, 205212, 205214,
                                    205215]}
        elif case_name == cls.CASE_ASSOCIATION_SEVERAL_CONC:
            return {'123_iso_01' : [205205, 205203, 205204, 205205, 205206,
                                    205207],
                    '123_iso_02' : [205208, 205209, 205210, 205212, 205214,
                                    205215]}
        elif case_name == cls.CASE_LIBRARY_SIMPLE:
            return None
        elif case_name == cls.CASE_LIBRARY_2_ALIQUOTS:
            return None
        raise NotImplementedError('The value for this case is missing.')

    @classmethod
    def get_iso_order(cls, case_name):
        if case_name == cls.CASE_ORDER_ONLY:
            return LAB_ISO_ORDERS.NO_JOB
        elif case_name == cls.CASE_NO_JOB_DIRECT:
            return LAB_ISO_ORDERS.NO_JOB
        elif case_name == cls.CASE_NO_JOB_1_PREP:
            return LAB_ISO_ORDERS.NO_JOB
        elif case_name == cls.CASE_NO_JOB_COMPLEX:
            return LAB_ISO_ORDERS.NO_JOB
        elif case_name == cls.CASE_ASSOCIATION_DIRECT:
            return LAB_ISO_ORDERS.JOB_FIRST
        elif case_name == cls.CASE_ASSOCIATION_96:
            return LAB_ISO_ORDERS.NO_JOB
        elif case_name == cls.CASE_ASSOCIATION_SIMPLE:
            return LAB_ISO_ORDERS.JOB_FIRST
        elif case_name == cls.CASE_ASSOCIATION_NO_CYBIO:
            return LAB_ISO_ORDERS.JOB_FIRST
        elif case_name == cls.CASE_ASSOCIATION_2_ALIQUOTS:
            return LAB_ISO_ORDERS.JOB_FIRST
        elif case_name == cls.CASE_ASSOCIATION_JOB_LAST:
            return LAB_ISO_ORDERS.ISO_FIRST
        elif case_name == cls.CASE_ASSOCIATION_SEVERAL_CONC:
            return LAB_ISO_ORDERS.ISO_FIRST
        elif case_name == cls.CASE_LIBRARY_SIMPLE:
            return LAB_ISO_ORDERS.NO_ISO
        elif case_name == cls.CASE_LIBRARY_2_ALIQUOTS:
            return LAB_ISO_ORDERS.NO_ISO
        raise NotImplementedError('The value for this case is missing.')

    @classmethod
    def get_stock_takeout_volumes(cls, case_name):
        # pool_id - stock take out volume in ul
        if case_name == cls.CASE_ORDER_ONLY:
            return {205201 : 2, 330001 : 2, 333803 : 2, 1056000 : 2, 180005 : 2}
        elif case_name == cls.CASE_NO_JOB_DIRECT:
            return {205201 : (2 + 2), 330001 : (2 + 2), 333803 : (2 + 2),
                    1056000 : (2 + 2), 180005 : (2 + 2)}
        elif case_name == cls.CASE_NO_JOB_1_PREP:
            return {205201 : (2 + 2.4), 330001 : (2 + 2.4), 333803 : (2 + 1.2),
                    1056000 : (4 + 4.8), 180005 : (2 + 4.8)}
        elif case_name == cls.CASE_NO_JOB_COMPLEX:
            return {205201 : 34, 330001 : 2, 333803 : (2 + 4.7), 1056000 : 4,
                    180005 : (4 + 48)}
        elif case_name == cls.CASE_ASSOCIATION_DIRECT:
            return {205201 : (8 * 2), 205202 : (8 * 2), 180005 : (4 * 2),
                    205205 : 4, 205206 : 4, 205207 : 4,
                    205208 : 4, 205209 : 4, 205210 : 4}
        elif case_name == cls.CASE_ASSOCIATION_96:
            return {205201 : (5.5 * 2), 205202 : (5.5 * 2), 205203 : (5.5 * 2),
                    205200 : (5.5 * 2), 205205 : 5.5, 205206: 5.5,
                    205207 : 5.5, 205208 : 5.5}
        elif case_name == cls.CASE_ASSOCIATION_SIMPLE:
            return {205201 : 2, 205202 : 2, 205200 : 2,
                    205205 : 1, 205206 : 1, 205207 : 1,
                    205208 : 1, 205209 : 1, 205210 : 1}
        elif case_name == cls.CASE_ASSOCIATION_NO_CYBIO:
            return {205201 : 1, 180005 : 1,
                    205202 : 1, 205203 : 1, 205204 : 1, 205205 : 1}
        elif case_name == cls.CASE_ASSOCIATION_2_ALIQUOTS:
            return {205201 : 2, 205202 : 2, 205200 : 2,
                    205205 : 1, 205206 : 1, 205207 : 1,
                    205208 : 1, 205209 : 1, 205210 : 1}
        elif case_name == cls.CASE_ASSOCIATION_JOB_LAST:
            return {205201 : 1, 330001 : 1.1, 205200 : 1,
                    205202 : 1, 205203 : 1, 205204 : 1, 205205 : 1, 205206 : 1,
                    205207 : 1,
                    205208 : 1, 205209 : 1, 205210 : 1, 205212 : 1, 205214 : 1,
                    205215 : 1}
        elif case_name == cls.CASE_ASSOCIATION_SEVERAL_CONC:
            return {205201 : 1, 330001 : 1, 205200 : 1,
                    205202 : 1, 205203 : 1, 205204 : 1, 205205 : 1,
                    205206 : 1, 205207 : 1,
                    205208 : 1, 205209 : 1, 205210 : 1, 205212 : 1,
                    205214 : 1, 205215 : 1}
        elif case_name == cls.CASE_LIBRARY_SIMPLE:
            return {205201 : 1, 330001 : 4.6, 1056000 : 4.6}
        elif case_name == cls.CASE_LIBRARY_2_ALIQUOTS:
            return {205201 : 1.4, 330001 : 6.7, 1056000 : 6.7}
        raise NotImplementedError('The value for this case is missing.')

    @classmethod
    def get_stock_rack_layout_data(cls, case_name):
        # pos_label - pool, tube barcode, transfer_targets
        if case_name == cls.CASE_ORDER_ONLY:
            s1 = dict(
                b2=[205201, '1000205201', [TransferTarget('b2', 2, 'a')]],
                b4=[330001, '1000330001', [TransferTarget('b4', 2, 'a')]],
                b6=[333803, '1000333803', [TransferTarget('b6', 2, 'a')]],
                b8=[1056000, '1001056000', [TransferTarget('b8', 2, 'a')]],
                b10=[180005, '1000180005', [TransferTarget('b10', 2, 'a')]])
            return {'123_iso_01_s#1' : s1}
        elif case_name == cls.CASE_NO_JOB_DIRECT:
            s1 = dict(
                a1=[205201, '1000205201', [TransferTarget('b2', 2, 'a'),
                                           TransferTarget('d2', 2, 'a')]],
                b1=[330001, '1000330001', [TransferTarget('b4', 2, 'a'),
                                           TransferTarget('d4', 2, 'a')]],
                c1=[333803, '1000333803', [TransferTarget('b6', 2, 'a'),
                                           TransferTarget('d6', 2, 'a')]],
                d1=[1056000, '1001056000', [TransferTarget('b8', 2, 'a'),
                                           TransferTarget('d8', 2, 'a')]],
                e1=[180005, '1000180005', [TransferTarget('b10', 2, 'a'),
                                            TransferTarget('d10', 2, 'a')]])
            return {'123_iso_01_s#1' : s1}
        elif case_name == cls.CASE_NO_JOB_1_PREP:
            s1 = dict(
                a1=[205201, '1000205201', [TransferTarget('b2', 2, 'a'),
                                           TransferTarget('d1', 2.4, 'p')]],
                b1=[330001, '1000330001', [TransferTarget('b4', 2, 'a'),
                                           TransferTarget('d2', 2.4, 'p')]],
                c1=[333803, '1000333803', [TransferTarget('b6', 2, 'a'),
                                           TransferTarget('d3', 1.2, 'p')]],
                d1=[1056000, '1001056000', [TransferTarget('b8', 4, 'a'),
                                           TransferTarget('d4', 4.8, 'p')]],
                e1=[180005, '1000180005', [TransferTarget('b10', 4, 'a'),
                                           TransferTarget('d5', 4.8, 'p')]])
            return {'123_iso_01_s#1' : s1}
        elif case_name == cls.CASE_NO_JOB_COMPLEX:
            s1 = dict(
                a1=[205201, '1000205201', [TransferTarget('b2', 34, 'a')]],
                b1=[330001, '1000330001', [TransferTarget('c2', 3, 'a')]],
                c1=[333803, '1000333803', [TransferTarget('d2', 3, 'a'),
                                           TransferTarget('d1', 4.7, 'p')]],
                d1=[1056000, '1001056000', [TransferTarget('e2', 3, 'a')]],
                e1=[180005, '1000180005', [TransferTarget('f2', 3, 'a'),
                                           TransferTarget('f1', 48, 'p')]])
            return {'123_iso_01_s#1' : s1}
        elif case_name == cls.CASE_ASSOCIATION_DIRECT:
            s1 = dict(
                a1=[205201, '1000205201', [TransferTarget('b2', 4, 'a'),
                                           TransferTarget('d2', 4, 'a')]],
                b1=[205202, '1000205202', [TransferTarget('b3', 4, 'a'),
                                           TransferTarget('d3', 4, 'a')]],
                c1=[180005, '1000180005', [TransferTarget('b4', 2, 'a'),
                                           TransferTarget('d4', 2, 'a')]])
            s21 = dict(
                b2=[205206, '1000205206', [TransferTarget('c3', 4, 'a')]])
            s22 = dict(
                b2=[205209, '1000205206', [TransferTarget('c3', 4, 'a')]])
            s31 = dict(
                b1=[205205, '1000205205', [TransferTarget('c2', 4, 'a')]],
                b2=[205207, '1000205027', [TransferTarget('c4', 4, 'a')]])
            s32 = dict(
                b1=[205208, '1000205208', [TransferTarget('c2', 4, 'a')]],
                b2=[205210, '1000205010', [TransferTarget('c4', 4, 'a')]])
            return {'123_job_01_s#1' : s1,
                    '123_iso_01_s#2' : s21, '123_iso_02_s#2' : s22,
                    '123_iso_01_s#3' : s31, '123_iso_02_s#3' : s32}
        elif case_name == cls.CASE_ASSOCIATION_96:
            s11 = dict(
                b2=[205201, '1000205201', [TransferTarget('c3', 5.5, 'p')]],
                c2=[205202, '1000205202', [TransferTarget('e3', 5.5, 'p')]],
                b4=[205203, '1000205203', [TransferTarget('c7', 5.5, 'p')]],
                c4=[205200, '1000205200', [TransferTarget('e7', 5.5, 'p')]],
                b6=[205205, '1000205205', [TransferTarget('c11', 5.5, 'p')]],
                c6=[205206, '1000205206', [TransferTarget('e11', 5.5, 'p')]])
            s12 = dict(
                b2=[205201, '1000205201', [TransferTarget('c3', 5.5, 'p')]],
                c2=[205202, '1000205202', [TransferTarget('e3', 5.5, 'p')]],
                b4=[205203, '1000205203', [TransferTarget('c7', 5.5, 'p')]],
                c4=[205200, '1000205200', [TransferTarget('e7', 5.5, 'p')]],
                b6=[205207, '1000205207', [TransferTarget('c11', 5.5, 'p')]],
                c6=[205208, '1000205208', [TransferTarget('e11', 5.5, 'p')]])
            return {'123_iso_01_s#1' : s11, '123_iso_02_s#1' : s12}
        elif case_name == cls.CASE_ASSOCIATION_SIMPLE:
            s1 = dict(
                a1=[205201, '1000205201', [TransferTarget('b2', 1, 'p'),
                                           TransferTarget('d2', 1, 'p')]],
                b1=[205202, '1000205202', [TransferTarget('b3', 1, 'p'),
                                           TransferTarget('d3', 1, 'p')]],
                c1=[205200, '1000205200', [TransferTarget('b4', 1, 'p'),
                                           TransferTarget('d4', 1, 'p')]])
            s21 = dict(
                b2=[205206, '1000205206', [TransferTarget('c3', 1, 'p')]])
            s22 = dict(
                b2=[205209, '1000205209', [TransferTarget('c3', 1, 'p')]])
            s31 = dict(
                b1=[205205, '1000205205', [TransferTarget('c2', 1, 'p')]],
                b2=[205207, '1000205207', [TransferTarget('c4', 1, 'p')]])
            s32 = dict(
                b1=[205208, '1000205208', [TransferTarget('c2', 1, 'p')]],
                b2=[205210, '1000205210', [TransferTarget('c4', 1, 'p')]])
            return {'123_job_01_s#1' : s1,
                    '123_iso_01_s#2' : s21, '123_iso_02_s#2' : s22,
                    '123_iso_01_s#3' : s31, '123_iso_02_s#3' : s32}
        elif case_name == cls.CASE_ASSOCIATION_NO_CYBIO:
            s1 = dict(
                c1=[205201, '1000205201', [TransferTarget('c1', 1, 'jp')]],
                c2=[180005, '1000180005', [TransferTarget('c2', 1, 'jp')]])
            s21 = dict(
                d1=[205202, '1000205202', [TransferTarget('d1', 1, 'p')]],
                d2=[205203, '1000205203', [TransferTarget('d2', 1, 'p')]])
            s22 = dict(
                d1=[205204, '1000205204', [TransferTarget('d1', 1, 'p')]],
                d2=[205205, '1000205205', [TransferTarget('d2', 1, 'p')]])
            return {'123_job_01_s#1' : s1,
                    '123_iso_01_s#2' : s21, '123_iso_02_s#2' : s22}
        elif case_name == cls.CASE_ASSOCIATION_2_ALIQUOTS:
            s1 = dict(
                a1=[205201, '1000205201', [TransferTarget('b2', 1, 'p'),
                                           TransferTarget('d2', 1, 'p')]],
                b1=[205202, '1000205202', [TransferTarget('b3', 1, 'p'),
                                           TransferTarget('d3', 1, 'p')]],
                c1=[205200, '1000205200', [TransferTarget('b4', 1, 'p'),
                                           TransferTarget('d4', 1, 'p')]])
            s21 = dict(
                b2=[205206, '1000205206', [TransferTarget('c3', 1, 'p')]])
            s22 = dict(
                b2=[205209, '1000205209', [TransferTarget('c3', 1, 'p')]])
            s31 = dict(
                b1=[205205, '1000205205', [TransferTarget('c2', 1, 'p')]],
                b2=[205207, '1000205207', [TransferTarget('c4', 1, 'p')]])
            s32 = dict(
                b1=[205208, '1000205208', [TransferTarget('c2', 1, 'p')]],
                b2=[205210, '1000205210', [TransferTarget('c4', 1, 'p')]])
            return {'123_job_01_s#1' : s1,
                    '123_iso_01_s#2' : s21, '123_iso_02_s#2' : s22,
                    '123_iso_01_s#3' : s31, '123_iso_02_s#3' : s32}
        elif case_name == cls.CASE_ASSOCIATION_JOB_LAST:
            s1 = dict(
                e1=[205201, '1000205201', [TransferTarget('e1', 1, 'jp')]],
                e2=[330001, '1000330001', [TransferTarget('e2', 1.1, 'jp')]],
                e3=[205200, '1000205200', [TransferTarget('e3', 1, 'jp')]])
            s21 = dict(
                b2=[205203, '1000205203', [TransferTarget('c3', 1, 'p')]])
            s22 = dict(
                b2=[205209, '1000205203', [TransferTarget('c3', 1, 'p')]])
            s31 = dict(
                b1=[205202, '1000205202', [TransferTarget('c2', 1, 'p')]],
                b2=[205204, '1000205204', [TransferTarget('c4', 1, 'p')]])
            s32 = dict(
                b1=[205208, '1000205208', [TransferTarget('c2', 1, 'p')]],
                b2=[205210, '1000205210', [TransferTarget('c4', 1, 'p')]])
            s41 = dict(
                b2=[205206, '1000205206', [TransferTarget('d3', 1, 'p')]])
            s42 = dict(
                b2=[205214, '1000205206', [TransferTarget('d3', 1, 'p')]])
            s51 = dict(
                b1=[205205, '1000205205', [TransferTarget('d2', 1, 'p')]],
                b2=[205207, '1000205207', [TransferTarget('d4', 1, 'p')]])
            s52 = dict(
                b1=[205212, '1000205205', [TransferTarget('d2', 1, 'p')]],
                b2=[205215, '1000205215', [TransferTarget('d4', 1, 'p')]])
            return {'123_job_01_s#1' : s1,
                    '123_iso_01_s#2' : s21, '123_iso_02_s#2' : s22,
                    '123_iso_01_s#3' : s31, '123_iso_02_s#3' : s32,
                    '123_iso_01_s#4' : s41, '123_iso_02_s#4' : s42,
                    '123_iso_01_s#5' : s51, '123_iso_02_s#5' : s52}
        elif case_name == cls.CASE_ASSOCIATION_SEVERAL_CONC:
            s1 = dict(
                f1=[205201, '1000205201', [TransferTarget('f1', 1, 'jp')]],
                f2=[330001, '1000330001', [TransferTarget('f2', 1.1, 'jp')]],
                f3=[205200, '1000205200', [TransferTarget('f3', 1, 'jp')]])
            s21 = dict(
                b2=[205202, '1000205202', [TransferTarget('b2', 1, 'p')]],
                b3=[205203, '1000205203', [TransferTarget('b3', 1, 'p')]],
                b4=[205204, '1000205204', [TransferTarget('b4', 1, 'p')]],
                d2=[205205, '1000205205', [TransferTarget('d2', 1, 'p')]],
                d3=[205206, '1000205206', [TransferTarget('d3', 1, 'p')]],
                d4=[205207, '1000205207', [TransferTarget('d4', 1, 'p')]])
            s22 = dict(
                b2=[205208, '1000205208', [TransferTarget('b2', 1, 'p')]],
                b3=[205209, '1000205209', [TransferTarget('b3', 1, 'p')]],
                b4=[205210, '1000205210', [TransferTarget('b4', 1, 'p')]],
                d2=[205212, '1000205212', [TransferTarget('d2', 1, 'p')]],
                d3=[205214, '1000205214', [TransferTarget('d3', 1, 'p')]],
                d4=[205215, '1000205215', [TransferTarget('d4', 1, 'p')]])
            return {'123_job_01_s#1' : s1,
                    '123_iso_01_s#2' : s21, '123_iso_02_s#2' : s22}
        elif case_name == cls.CASE_LIBRARY_SIMPLE:
            s1 = dict(
                b1=[205201, '1000205201', [TransferTarget('b1', 1, 'jp')]],
                d1=[330001, '1000330001', [TransferTarget('d1', 4.6, 'jp')]],
                f1=[1056000, '1001056000', [TransferTarget('f1', 4.6, 'jp')]])
            return {'123_job_01_s#1' : s1}
        elif case_name == cls.CASE_LIBRARY_2_ALIQUOTS:
            s1 = dict(
                b1=[205201, '1000205201', [TransferTarget('b1', 1.4, 'jp')]],
                d1=[330001, '1000330001', [TransferTarget('d1', 6.7, 'jp')]],
                f1=[1056000, '1001056000', [TransferTarget('f1', 6.7, 'jp')]])
            return {'123_job_01_s#1' : s1}
        raise NotImplementedError('The value for this case is missing.')

    @classmethod
    def get_stock_rack_labels(cls, case_name):
        if case_name == cls.CASE_ORDER_ONLY:
            return {'s#1' : ['123_iso_01_s#1']}
        elif case_name == cls.CASE_NO_JOB_DIRECT:
            return {'s#1' : ['123_iso_01_s#1']}
        elif case_name == cls.CASE_NO_JOB_1_PREP:
            return {'s#1' : ['123_iso_01_s#1']}
        elif case_name == cls.CASE_NO_JOB_COMPLEX:
            return {'s#1' : ['123_iso_01_s#1']}
        elif case_name == cls.CASE_ASSOCIATION_DIRECT:
            return {'s#1' : ['123_job_01_s#1'],
                    's#2' : ['123_iso_01_s#2', '123_iso_02_s#2'],
                    's#3' : ['123_iso_01_s#3', '123_iso_02_s#3']}
        elif case_name == cls.CASE_ASSOCIATION_96:
            return {'s#1' : ['123_iso_01_s#1', '123_iso_02_s#1']}
        elif case_name == cls.CASE_ASSOCIATION_SIMPLE:
            return {'s#1' : ['123_job_01_s#1'],
                    's#2' : ['123_iso_01_s#2', '123_iso_02_s#2'],
                    's#3' : ['123_iso_01_s#3', '123_iso_02_s#3']}
        elif case_name == cls.CASE_ASSOCIATION_NO_CYBIO:
            return {'s#1' : ['123_job_01_s#1'],
                    's#2' : ['123_iso_01_s#2', '123_iso_02_s#2']}
        elif case_name == cls.CASE_ASSOCIATION_2_ALIQUOTS:
            return {'s#1' : ['123_job_01_s#1'],
                    's#2' : ['123_iso_01_s#2', '123_iso_02_s#2'],
                    's#3' : ['123_iso_01_s#3', '123_iso_02_s#3']}
        elif case_name == cls.CASE_ASSOCIATION_JOB_LAST:
            return {'s#1' : ['123_job_01_s#1'],
                    's#2' : ['123_iso_01_s#2', '123_iso_02_s#2'],
                    's#3' : ['123_iso_01_s#3', '123_iso_02_s#3'],
                    's#4' : ['123_iso_01_s#4', '123_iso_02_s#4'],
                    's#5' : ['123_iso_01_s#5', '123_iso_02_s#5']}
        elif case_name == cls.CASE_ASSOCIATION_SEVERAL_CONC:
            return {'s#1' : ['123_job_01_s#1'],
                    's#2' : ['123_iso_01_s#2', '123_iso_02_s#2']}
        elif case_name == cls.CASE_LIBRARY_SIMPLE:
            return {'s#1' : ['123_job_01_s#1']}
        elif case_name == cls.CASE_LIBRARY_2_ALIQUOTS:
            return {'s#1' : ['123_job_01_s#1']}
        raise NotImplementedError('The value for this case is missing.')

    @classmethod
    def get_sectors_for_iso_stock_racks(cls, case_name):
        if case_name == cls.CASE_ORDER_ONLY:
            return {'s#1' : None}
        elif case_name == cls.CASE_NO_JOB_DIRECT:
            return {'s#1' : None}
        elif case_name == cls.CASE_NO_JOB_1_PREP:
            return {'s#1' : None}
        elif case_name == cls.CASE_NO_JOB_COMPLEX:
            return {'s#1' : None}
        elif case_name == cls.CASE_ASSOCIATION_DIRECT:
            return {'s#2' : 0, 's#3' : 1}
        elif case_name == cls.CASE_ASSOCIATION_96:
            return {'s#1' : 0}
        elif case_name == cls.CASE_ASSOCIATION_SIMPLE:
            return {'s#2' : 0, 's#3' : 1}
        elif case_name == cls.CASE_ASSOCIATION_NO_CYBIO:
            return {'s#2' : None}
        elif case_name == cls.CASE_ASSOCIATION_2_ALIQUOTS:
            return {'s#2' : 0, 's#3' : 1}
        elif case_name == cls.CASE_ASSOCIATION_JOB_LAST:
            return {'s#2' : 0, 's#3' : 1, 's#4' : 2, 's#5' : 3}
        elif case_name == cls.CASE_ASSOCIATION_SEVERAL_CONC:
            return {'s#2' : 0}
        raise NotImplementedError('The value for this case is missing.')

    @classmethod
    def get_stock_rack_worklist_series_for_job(cls, case_name):
        ps_biomek_stock = get_pipetting_specs_biomek_stock()
        #: worklist label - worklist index
        # all stock rack worklists have SAMPLE_TRANSFER as transfer type
        if case_name == cls.CASE_ASSOCIATION_DIRECT:
            return {'123_1_s#1_to_a' : [0, ps_biomek_stock]}
        elif case_name == cls.CASE_ASSOCIATION_SIMPLE:
            return {'123_1_s#1_to_p' : [0, ps_biomek_stock]}
        elif case_name == cls.CASE_ASSOCIATION_NO_CYBIO:
            return {'123_1_s#1_to_jp' : [0, ps_biomek_stock]}
        elif case_name == cls.CASE_ASSOCIATION_2_ALIQUOTS:
            return {'123_1_s#1_to_p' : [0, ps_biomek_stock]}
        elif case_name == cls.CASE_ASSOCIATION_JOB_LAST:
            return {'123_1_s#1_to_jp' : [0, ps_biomek_stock]}
        elif case_name == cls.CASE_ASSOCIATION_SEVERAL_CONC:
            return {'123_1_s#1_to_jp' : [0, ps_biomek_stock]}
        elif case_name == cls.CASE_LIBRARY_SIMPLE:
            return {'123_1_s#1_to_jp' : [0, ps_biomek_stock]}
        elif case_name == cls.CASE_LIBRARY_2_ALIQUOTS:
            return {'123_1_s#1_to_jp' : [0, ps_biomek_stock]}
        raise NotImplementedError('The value for this case is missing.')

    @classmethod
    def get_stock_rack_worklist_series_for_iso(cls, case_name):
        ps_biomek_stock = get_pipetting_specs_biomek_stock()
        ps_cybio = get_pipetting_specs_cybio()
        #: worklist label - worklist index, pipetting specs
        # all stock rack worklists have SAMPLE_TRANSFER as transfer type
        if case_name == cls.CASE_ORDER_ONLY:
            return {'123_1_s#1_to_a' : [0, ps_biomek_stock]}
        elif case_name == cls.CASE_NO_JOB_DIRECT:
            return {'123_1_s#1_to_a' : [0, ps_biomek_stock]}
        elif case_name == cls.CASE_NO_JOB_1_PREP:
            return {'123_1_s#1_to_p' : [0, ps_biomek_stock],
                    '123_2_s#1_to_a' : [1, ps_biomek_stock]}
        elif case_name == cls.CASE_NO_JOB_COMPLEX:
            return {'123_1_s#1_to_p' : [0, ps_biomek_stock],
                    '123_2_s#1_to_a' : [1, ps_biomek_stock]}
        elif case_name == cls.CASE_ASSOCIATION_DIRECT:
            return {'123_1_s#2_to_a' : [0, ps_cybio],
                    '123_1_s#3_to_a' : [0, ps_cybio]}
        elif case_name == cls.CASE_ASSOCIATION_96:
            return {'123_1_s#1_to_p' : [0, ps_cybio]}
        elif case_name == cls.CASE_ASSOCIATION_SIMPLE:
            return {'123_1_s#2_to_p' : [0, ps_cybio],
                    '123_1_s#3_to_p' : [0, ps_cybio]}
        elif case_name == cls.CASE_ASSOCIATION_NO_CYBIO:
            return {'123_1_s#2_to_p' : [0, ps_biomek_stock]}
        elif case_name == cls.CASE_ASSOCIATION_2_ALIQUOTS:
            return {'123_1_s#2_to_p' : [0, ps_cybio],
                    '123_1_s#3_to_p' : [0, ps_cybio]}
        elif case_name == cls.CASE_ASSOCIATION_JOB_LAST:
            return {'123_1_s#2_to_p' : [0, ps_cybio],
                    '123_1_s#3_to_p' : [0, ps_cybio],
                    '123_1_s#4_to_p' : [0, ps_cybio],
                    '123_1_s#5_to_p' : [0, ps_cybio]}
        elif case_name == cls.CASE_ASSOCIATION_SEVERAL_CONC:
            return {'123_1_s#2_to_p' : [0, ps_cybio]}
        elif case_name == cls.CASE_LIBRARY_SIMPLE:
            return dict()
        elif case_name == cls.CASE_LIBRARY_2_ALIQUOTS:
            return dict()
        raise NotImplementedError('The value for this case is missing.')

    @classmethod
    def get_stock_rack_worklist_details(cls, case_name, worklist_label):
        # trg_pos - vol, target_pos
        if case_name == cls.CASE_ORDER_ONLY:
            if worklist_label == '123_1_s#1_to_a':
                return dict(b2=[2, 'b2'], b4=[2, 'b4'], b6=[2, 'b6'],
                            b8=[2, 'b8'], b10=[2, 'b10'])
        elif case_name == cls.CASE_NO_JOB_DIRECT:
            if worklist_label == '123_1_s#1_to_a':
                return dict(b2=[2, 'a1'], d2=[2, 'a1'],
                    b4=[2, 'b1'], d4=[2, 'b1'], b6=[2, 'c1'], d6=[2, 'c1'],
                    b8=[2, 'd1'], d8=[2, 'd1'], b10=[2, 'e1'], d10=[2, 'e1'])
        elif case_name == cls.CASE_NO_JOB_1_PREP:
            if worklist_label == '123_1_s#1_to_p':
                return dict(d1=[2.4, 'a1'], d2=[2.4, 'b1'], d3=[1.2, 'c1'],
                            d4=[4.8, 'd1'], d5=[4.8, 'e1'])
            elif worklist_label == '123_2_s#1_to_a':
                return  dict(b2=[2, 'a1'], b4=[2, 'b1'], b6=[2, 'c1'],
                             b8=[4, 'd1'], b10=[4, 'e1'])
        elif case_name == cls.CASE_NO_JOB_COMPLEX:
            if worklist_label == '123_1_s#1_to_p':
                return dict(d1=[4.7, 'c1'], f1=[48, 'e1'])
            elif worklist_label == '123_2_s#1_to_a':
                return  dict(b2=[34, 'a1'], c2=[3, 'b1'], d2=[3, 'c1'],
                             e2=[3, 'd1'], f2=[3, 'e1'])
        elif case_name == cls.CASE_ASSOCIATION_DIRECT:
            if worklist_label == '123_1_s#1_to_a':
                return dict(b2=[4, 'a1'], d2=[4, 'a1'],
                    b3=[4, 'b1'], d3=[4, 'b1'], b4=[2, 'c1'], d4=[2, 'c1'])
            elif worklist_label == '123_1_s#2_to_a':
                return dict(c3=[4, 'b2'])
            elif worklist_label == '123_1_s#3_to_a':
                return dict(c2=[4, 'b1'], c4=[4, 'b2'])
        elif case_name == cls.CASE_ASSOCIATION_96:
            if worklist_label == '123_1_s#1_to_p':
                return dict(c3=[5.5, 'b2'], e3=[5.5, 'c2'], c7=[5.5, 'b4'],
                    e7=[5.5, 'c4'], c11=[5.5, 'b6'], e11=[5.5, 'c6'])
        elif case_name == cls.CASE_ASSOCIATION_SIMPLE:
            if worklist_label == '123_1_s#1_to_p':
                return dict(b2=[1, 'a1'], d2=[1, 'a1'],
                    b3=[1, 'b1'], d3=[1, 'b1'], b4=[1, 'c1'], d4=[1, 'c1'])
            elif worklist_label == '123_1_s#2_to_p':
                return dict(c3=[1, 'b2'])
            elif worklist_label == '123_1_s#3_to_p':
                return dict(c2=[1, 'b1'], c4=[1, 'b2'])
        elif case_name == cls.CASE_ASSOCIATION_NO_CYBIO:
            if worklist_label == '123_1_s#1_to_jp':
                return dict(c1=[1, 'c1'], c2=[1, 'c2'])
            elif worklist_label == '123_1_s#2_to_p':
                return dict(d1=[1, 'd1'], d2=[1, 'd2'])
        elif case_name == cls.CASE_ASSOCIATION_2_ALIQUOTS:
            if worklist_label == '123_1_s#1_to_p':
                return dict(b2=[1, 'a1'], d2=[1, 'a1'],
                    b3=[1, 'b1'], d3=[1, 'b1'], b4=[1, 'c1'], d4=[1, 'c1'])
            elif worklist_label == '123_1_s#2_to_p':
                return dict(c3=[1, 'b2'])
            elif worklist_label == '123_1_s#3_to_p':
                return dict(c2=[1, 'b1'], c4=[1, 'b2'])
        elif case_name == cls.CASE_ASSOCIATION_JOB_LAST:
            if worklist_label == '123_1_s#2_to_p':
                return dict(c3=[1, 'b2'])
            elif worklist_label == '123_1_s#3_to_p':
                return dict(c2=[1, 'b1'], c4=[1, 'b2'])
            elif worklist_label == '123_1_s#4_to_p':
                return dict(d3=[1, 'b2'])
            elif worklist_label == '123_1_s#5_to_p':
                return dict(d2=[1, 'b1'], d4=[1, 'b2'])
            elif worklist_label == '123_1_s#1_to_jp':
                return dict(e1=[1, 'e1'], e2=[1.1, 'e2'], e3=[1, 'e3'])
        elif case_name == cls.CASE_ASSOCIATION_SEVERAL_CONC:
            if worklist_label == '123_1_s#2_to_p':
                return dict(b2=[1, 'b2'], b3=[1, 'b3'], b4=[1, 'b4'],
                            d2=[1, 'd2'], d3=[1, 'd3'], d4=[1, 'd4'])
            elif worklist_label == '123_1_s#1_to_jp':
                return dict(f1=[1, 'f1'], f2=[1.1, 'f2'], f3=[1, 'f3'])
        elif case_name == cls.CASE_LIBRARY_SIMPLE:
            if worklist_label == '123_1_s#1_to_jp':
                return dict(b1=[1, 'b1'], d1=[4.6, 'd1'], f1=[4.6, 'f1'])
        elif case_name == cls.CASE_LIBRARY_2_ALIQUOTS:
            if worklist_label == '123_1_s#1_to_jp':
                return dict(b1=[1.4, 'b1'], d1=[6.7, 'd1'], f1=[6.7, 'f1'])
        raise NotImplementedError('The value for this case or worklist (%s) ' \
                                  'is missing.' % (worklist_label))

    @classmethod
    def get_stock_tube_number(cls, case_name, for_job):
        if case_name == cls.CASE_ORDER_ONLY:
            if for_job:
                return 0
            else:
                return 5
        elif case_name == cls.CASE_NO_JOB_DIRECT:
            if for_job:
                return 0
            else:
                return 5
        elif case_name == cls.CASE_NO_JOB_1_PREP:
            if for_job:
                return 0
            else:
                return 5
        elif case_name == cls.CASE_NO_JOB_COMPLEX:
            if for_job:
                return 0
            else:
                return 5
        elif case_name == cls.CASE_ASSOCIATION_DIRECT:
            if for_job:
                return 3
            else:
                return 3
        elif case_name == cls.CASE_ASSOCIATION_96:
            if for_job:
                return 0
            else:
                return 6
        elif case_name == cls.CASE_ASSOCIATION_SIMPLE:
            if for_job:
                return 3
            else:
                return 3
        elif case_name == cls.CASE_ASSOCIATION_NO_CYBIO:
            if for_job:
                return 2
            else:
                return 2
        elif case_name == cls.CASE_ASSOCIATION_2_ALIQUOTS:
            if for_job:
                return 3
            else:
                return 3
        elif case_name == cls.CASE_ASSOCIATION_JOB_LAST:
            if for_job:
                return 3
            else:
                return 6
        elif case_name == cls.CASE_ASSOCIATION_SEVERAL_CONC:
            if for_job:
                return 3
            else:
                return 6
        elif case_name == cls.CASE_LIBRARY_SIMPLE:
            if for_job:
                return 3
            else:
                return 0
        elif case_name == cls.CASE_LIBRARY_2_ALIQUOTS:
            if for_job:
                return 3
            else:
                return 0
        raise NotImplementedError('The value for this case is missing.')

    @classmethod
    def get_plate_intermediate_data(cls, case_name):
        # plate label - pos_label: pool (or None for buffer only), volume, conc
        if case_name == cls.CASE_ASSOCIATION_DIRECT:
            f = dict(b2=[205201, 4, 50000],
                     b3=[205202, 4, 50000],
                     b4=[180005, 4, 50000],
                     d2=[205201, 4, 50000],
                     d3=[205202, 4, 50000],
                     d4=[180005, 4, 50000],
                     e2=[None, 4, None],
                     e3=[None, 4, None])
            return {'123_iso_01_a' : f, '123_iso_02_a' : f}
        elif case_name == cls.CASE_ASSOCIATION_SIMPLE:
            f = dict(b2=[None, 9, None],
                     b3=[None, 9, None],
                     b4=[None, 9, None],
                     c2=[None, 9, None],
                     c3=[None, 9, None],
                     c4=[None, 9, None],
                     d2=[None, 9, None],
                     d3=[None, 9, None],
                     d4=[None, 9, None],
                     e2=[None, 10, None],
                     e3=[None, 10, None])
            p = dict(b2=[205201, 100, 500],
                     b3=[205202, 100, 500],
                     b4=[205200, 100, 500],
                     c2=[None, 99, None],
                     c3=[None, 99, None],
                     c4=[None, 99, None],
                     d2=[205201, 100, 500],
                     d3=[205202, 100, 500],
                     d4=[205200, 100, 500])
            return {'123_iso_01_a' : f, '123_iso_01_p' : p,
                    '123_iso_02_a' : f, '123_iso_02_p' : p}
        elif case_name == cls.CASE_ASSOCIATION_NO_CYBIO:
            jp = dict(c1=[205201, 88, 500],
                      c2=[180005, 188, 500])
            p = dict(d1=[None, 65.7, None],
                     d2=[None, 65.7, None])
            f = dict(c3=[205201, 20, 100],
                     c4=[None, 5, None],
                     c5=[180005, 20, 100],
                     c6=[None, 5, None],
                     d3=[None, 13, None],
                     d4=[None, 5, None],
                     d5=[None, 13, None],
                     d6=[None, 5, None],
                     e3=[205201, 10, 100],
                     e4=[None, 5, None],
                     e5=[180005, 10, 100],
                     e6=[None, 5, None],
                     f3=[None, 10, None])
            return {'123_job_01_jp' : jp,
                    '123_iso_01_a' : f, '123_iso_01_p' : p,
                    '123_iso_02_a' : f, '123_iso_02_p' : p}
        elif case_name == cls.CASE_ASSOCIATION_2_ALIQUOTS:
            p = dict(b2=[205201, 100, 500],
                     b3=[205202, 100, 500],
                     b4=[205200, 100, 500],
                     c2=[None, 99, None],
                     c3=[None, 99, None],
                     c4=[None, 99, None],
                     d2=[205201, 100, 500],
                     d3=[205202, 100, 500],
                     d4=[205200, 100, 500])
            f = dict(b2=[None, 9, None],
                     b3=[None, 9, None],
                     b4=[None, 9, None],
                     c2=[None, 9, None],
                     c3=[None, 9, None],
                     c4=[None, 9, None],
                     d2=[None, 9, None],
                     d3=[None, 9, None],
                     d4=[None, 9, None],
                     e2=[None, 10, None],
                     e3=[None, 10, None])
            return {'123_iso_01_a#1' : f, '123_iso_01_a#2' : f,
                    '123_iso_01_p' : p,
                    '123_iso_02_a#1' : f, '123_iso_02_a#2' : f,
                    '123_iso_02_p' : p}
        elif case_name == cls.CASE_ASSOCIATION_JOB_LAST:
            p1 = dict(c2=[205202, 99, 500],
                      c3=[205203, 99, 500],
                      c4=[205204, 99, 500],
                      d2=[205205, 99, 500],
                      d3=[205206, 99, 500],
                      d4=[205207, 99, 500])
            p2 = dict(c2=[205208, 99, 500],
                      c3=[205209, 99, 500],
                      c4=[205210, 99, 500],
                      d2=[205212, 99, 500],
                      d3=[205214, 99, 500],
                      d4=[205215, 99, 500])
            f = dict(b2=[None, 5, None],
                     b3=[None, 5, None],
                     b4=[None, 5, None],
                     e2=[None, 13, None],
                     e3=[None, 13, None],
                     e4=[None, 13, None],
                     f2=[None, 10, None],
                     f3=[None, 10, None],)
            f1 = dict(f, **dict(c2=[205202, 10, 50],
                      c3=[205203, 10, 50],
                      c4=[205204, 10, 50],
                      d2=[205205, 10, 50],
                      d3=[205206, 10, 50],
                      d4=[205207, 10, 50]))
            f2 = dict(f, **dict(c2=[205208, 10, 50],
                      c3=[205209, 10, 50],
                      c4=[205210, 10, 50],
                      d2=[205212, 10, 50],
                      d3=[205214, 10, 50],
                      d4=[205215, 10, 50]))
            return {'123_iso_01_p' : p1, '123_iso_02_p' : p2,
                    '123_iso_01_a' : f1, '123_iso_02_a' : f2}
        elif case_name == cls.CASE_ASSOCIATION_SEVERAL_CONC:
            p1 = dict(b2=[205202, 32.3, 1500],
                      b3=[205203, 32.3, 1500],
                      b4=[205204, 32.3, 1500],
                      d2=[205205, 32.3, 1500],
                      d3=[205206, 32.3, 1500],
                      d4=[205207, 32.3, 1500])
            p2 = dict(b2=[205208, 32.3, 1500],
                      b3=[205209, 32.3, 1500],
                      b4=[205210, 32.3, 1500],
                      d2=[205212, 32.3, 1500],
                      d3=[205214, 32.3, 1500],
                      d4=[205215, 32.3, 1500])
            f1 = dict(c3=[205202, 10, 50],
                      c5=[205203, 10, 50],
                      c7=[205204, 10, 50],
                      d3=[205202, 10, 100],
                      d5=[205203, 10, 100],
                      d7=[205204, 10, 100],
                      g3=[205205, 10, 50],
                      g5=[205206, 10, 50],
                      g7=[205207, 10, 50],
                      h3=[205205, 10, 100],
                      h5=[205206, 10, 100],
                      h7=[205207, 10, 100])
            f2 = dict(c3=[205208, 10, 50],
                      c5=[205209, 10, 50],
                      c7=[205210, 10, 50],
                      d3=[205208, 10, 100],
                      d5=[205209, 10, 100],
                      d7=[205210, 10, 100],
                      g3=[205212, 10, 50],
                      g5=[205214, 10, 50],
                      g7=[205215, 10, 50],
                      h3=[205212, 10, 100],
                      h5=[205214, 10, 100],
                      h7=[205215, 10, 100])
            return {'123_iso_01_p' : p1, '123_iso_02_p' : p2,
                    '123_iso_01_a' : f1, '123_iso_02_a' : f2}
        raise NotImplementedError('The value for this case is missing.')

    @classmethod
    def get_final_plate_labels_after_completion(cls, case_name):
        iso_labels = cls.ISO_LABELS[case_name]
        if case_name == cls.CASE_ORDER_ONLY:
            return {iso_labels[0] : ['order_only']}
        elif case_name == cls.CASE_NO_JOB_DIRECT:
            return {iso_labels[0] : ['no_job_direct']}
        elif case_name == cls.CASE_NO_JOB_1_PREP:
            return {iso_labels[0] : ['no_job_one_prep']}
        elif case_name == cls.CASE_NO_JOB_COMPLEX:
            return {iso_labels[0] : ['no_job_complex']}
        elif case_name == cls.CASE_ASSOCIATION_DIRECT:
            return {iso_labels[0] : ['ass_direct_1'],
                    iso_labels[1] : ['ass_direct_2']}
        elif case_name == cls.CASE_ASSOCIATION_96:
            return {iso_labels[0] : ['asso96_1'],
                    iso_labels[1] : ['asso96_2']}
        elif case_name == cls.CASE_ASSOCIATION_SIMPLE:
            return {iso_labels[0] : ['asso_simple_1'],
                    iso_labels[1] : ['asso_simple_2']}
        elif case_name == cls.CASE_ASSOCIATION_NO_CYBIO:
            return {iso_labels[0] : ['ass_biomek_1'],
                    iso_labels[1] : ['ass_biomek_2']}
        elif case_name == cls.CASE_ASSOCIATION_2_ALIQUOTS:
            return {iso_labels[0] : ['ass_2ali_1_a#1', 'ass_2ali_1_a#2'],
                    iso_labels[1] : ['ass_2ali_2_a#2', 'ass_2ali_2_a#2']}
        elif case_name == cls.CASE_ASSOCIATION_JOB_LAST:
            return {iso_labels[0] : ['ass_job_last_1'],
                    iso_labels[1] : ['ass_job_last_2']}
        elif case_name == cls.CASE_ASSOCIATION_SEVERAL_CONC:
            return {iso_labels[0] : ['ass_sev_conc_1'],
                    iso_labels[1] : ['ass_sev_conc_2']}
        elif case_name == cls.CASE_LIBRARY_SIMPLE:
            return cls.get_final_plate_labels(case_name)
        elif case_name == cls.CASE_LIBRARY_2_ALIQUOTS:
            return cls.get_final_plate_labels(case_name)
        raise NotImplementedError('The value for this case is missing.')


class LabIsoTestCase1(ExperimentMetadataReadingTestCase):

    def set_up(self):
        ExperimentMetadataReadingTestCase.set_up(self)
        self.TEST_FILE_PATH = LAB_ISO_TEST_CASES.TEST_FILE_PATH
        self.case = None
        self.iso_request = None
        self.number_isos = 2
        self.compare_floating_pools = True
        self.library_generator = None

    def tear_down(self):
        ExperimentMetadataReadingTestCase.tear_down(self)
        del self.case
        del self.iso_request
        del self.number_isos
        del self.compare_floating_pools
        del self.library_generator

    def _load_iso_request(self, case_name=None):
        if not case_name is None:
            self.case = case_name
        self._continue_setup()

    def _continue_setup(self, file_name=None):
        if LAB_ISO_TEST_CASES.is_library_case(self.case):
            self.library_generator = TestLibraryGenerator()
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
        converter = LabIsoPrepLayoutConverter(rack_layout)
        layout = converter.get_result()
        if layout is None:
            raise AssertionError('Unable to convert layout for ' \
                                 'preparation plate "%s".' % (rack_label))
        if is_job:
            exp_shape = LAB_ISO_TEST_CASES.get_job_plate_layout_shape(self.case)
        else:
            exp_shape = LAB_ISO_TEST_CASES.get_preparation_plate_layout_shape(
                                                                    self.case)
        self.assert_equal(layout.shape.name, exp_shape)
        self.assert_equal(len(layout), len(layout_data))
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
        converter = FinalLabIsoLayoutConverter(rack_layout)
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
        for rack_pos, plate_pos in layout.iterpositions():
            pos_label = rack_pos.label.lower()
            tested_labels.append(pos_label)
            pos_data = layout_data[pos_label]
            self._compare_layout_value(pos_data[1], 'position_type',
                                        plate_pos, layout_name)
            if plate_pos.is_floating and not self.compare_floating_pools:
                self.assert_is_not_none(plate_pos.molecule_design_pool)
            else:
                self._compare_layout_value(pos_data[0], 'molecule_design_pool',
                                           plate_pos, layout_name)
            self._compare_layout_value(pos_data[2], 'volume',
                                        plate_pos, layout_name)
            self._compare_layout_value(pos_data[3], 'concentration',
                                        plate_pos, layout_name)
            self._compare_layout_value(pos_data[4], 'from_job',
                                        plate_pos, layout_name)
            self._compare_layout_value(pos_data[5], 'transfer_targets',
                                        plate_pos, layout_name)
            self._compare_layout_value(pos_data[6], 'sector_index',
                                        plate_pos, layout_name)
            self._compare_layout_value(pos_data[7], 'stock_rack_marker',
                                        plate_pos, layout_name)
            if plate_pos.stock_rack_marker is None:
                self.assert_is_none(plate_pos.stock_tube_barcode)
                self.assert_is_none(plate_pos.stock_rack_barcode)
            else:
                self.assert_is_not_none(plate_pos.stock_tube_barcode)
                self.assert_is_not_none(plate_pos.stock_rack_barcode)
        self.assert_equal(sorted(tested_labels), sorted(layout_data.keys()))

    def _compare_worklist_series(self, iso_job=None):
        if iso_job is None: # check ISO request series
            exp_data = LAB_ISO_TEST_CASES.get_iso_worklist_data(self.case)
            worklist_series = self.iso_request.worklist_series
        else:
            exp_data = LAB_ISO_TEST_CASES.get_job_worklist_data(self.case)
            worklist_series = iso_job.worklist_series
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
                if not wl_data[0] == worklist.transfer_type:
                    msg = 'The transfer types for worklist %s differ.\n' \
                          'Expected: %s\nFound: %s' % (worklist.label,
                           wl_data[0], worklist.transfer_type)
                    raise AssertionError(msg)
                if not wl_data[1] == worklist.pipetting_specs:
                    msg = 'The pipetting specs for worklist %s differ.\n' \
                          'Expected: %s\nFound: %s' % (worklist.label,
                           wl_data[1], worklist.pipetting_specs)
                    raise AssertionError(msg)
                self._compare_worklist_details(worklist)
            self.assert_equal(sorted(found_labels), sorted(exp_data.keys()))

    def _compare_worklist_details(self, worklist, wl_data=None):
        wl_label = worklist.label
        if wl_data is None:
            wl_data = LAB_ISO_TEST_CASES.get_worklist_details(self.case,
                                                              wl_label)
        plts = worklist.planned_liquid_transfers
        if not len(wl_data) == len(plts):
            msg = 'Worklist "%s" has an unexpected number of transfers.\n' \
                  'Expected: %i, found: %i.' % (wl_label, len(wl_data),
                                                len(plts))
            raise AssertionError(msg)
        transfer_type = worklist.transfer_type
        missing_template = 'Unexpected target %s in worklist "%s".'
        for plt in plts:
            if transfer_type == TRANSFER_TYPES.SAMPLE_DILUTION:
                trg_label = plt.target_position.label.lower()
                if not wl_data.has_key(trg_label):
                    raise AssertionError(missing_template % (trg_label,
                                                             wl_label))
                exp_vol = wl_data[trg_label]
                self.__compare_volume(plt, exp_vol, trg_label, wl_label)
                self.assert_equal(plt.diluent_info, DILUENT_INFO)
            elif transfer_type == TRANSFER_TYPES.SAMPLE_TRANSFER:
                trg_label = plt.target_position.label.lower()
                if not wl_data.has_key(trg_label):
                    raise AssertionError(missing_template % (trg_label,
                                                             wl_label))
                plt_data = wl_data[trg_label]
                self.__compare_volume(plt, plt_data[0], trg_label, wl_label)
                src_label = plt.source_position.label.lower()
                if not src_label == plt_data[1]:
                    msg = 'The source position for transfer %s of worklist ' \
                          '"%s" differ:\nExpected: %s\nFound: %s.' \
                          % (trg_label, wl_label, plt_data[1], src_label)
                    raise AssertionError(msg)
            else:
                src_index = plt.source_sector_index
                trg_index = plt.target_sector_index
                plt_data = wl_data[trg_index]
                self.__compare_volume(plt, plt_data[0],
                                      'sector %i' % (trg_index), wl_label)
                src_index = plt.source_sector_index
                if not src_index == plt_data[1]:
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

    def _get_layout_from_iso_request(self):
        converter = IsoRequestLayoutConverter(self.iso_request.rack_layout)
        return converter.get_result()


class TestLibraryGenerator(object):
    """
    A smaller version of the poollib library that is faster to load
    and easier to handle during testing.
    """

    LIB_NAME = 'testlib'
    VOLUME_IN_UL = 4 # equal to poollib
    CONC_IN_UL = 1270 # equal to poollib

    # 11 pool = 3 layouts
    POOL_IDS = {1 : [1068472, 1068473, 1068474, 1068475],
                2 : [1068476, 1068477, 1068478, 1068479],
                3 : [1068480, 1068481, 1068482]}
    # The barcodes for the library plates.
    PLATE_BARCODES = {1 : ['08888811', '08888812', '08888813'],
                      2 : ['08888821', '08888822', '08888823'],
                      3 : ['08888831', '08888832', '08888833']}

    #: The number of library plates for each layout - the first layout plate
    #: will be set to has_been_used = True.
    NUM_LIBRARY_PLATES = 3

    def __init__(self):
        self.library = None
        self.library_plates = {1 : [], 2 : [], 3 : []}
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
            final_concentration=conc, number_layouts=3,
            rack_layout=layout.create_rack_layout())
        return lib

    @classmethod
    def get_library_layout(cls):
        layout = LibraryBaseLayout(shape=get_384_rack_shape())
        for pos_label in ('b3', 'b4', 'c3', 'c4'):
            rack_pos = get_rack_position_from_label(pos_label)
            lib_pos = LibraryBaseLayoutPosition(rack_position=rack_pos)
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
        for layout_num in (1, 2, 3):
            for i in range(self.NUM_LIBRARY_PLATES):
                has_been_used = False
                if i == 0: has_been_used = True
                rack_num = i + 1
                rack_label = '%s_l%i_r%i' % (self.LIB_NAME, layout_num,
                                             rack_num)
                barcode = self.PLATE_BARCODES[layout_num][i]
                plate = plate_specs.create_rack(label=rack_label,
                                                barcode=barcode, status=status)
                lib_plate = LibraryPlate(molecule_design_library=lib,
                            rack=plate, layout_number=layout_num,
                            has_been_used=has_been_used)
                self.library_plates[layout_num].append(lib_plate)

    def get_library(self):
        return self.library


class _TestRackGenerator(object):

    # The barcodes for the racks mapped onto rack markers.
    STOCK_RACK_BARCODES = {
            '123_job_01_s#1' : '09999001',
            '123_iso_01_s#1' : '09999011', '123_iso_02_s#1' : '09999021',
            '123_iso_01_s#2' : '09999012', '123_iso_02_s#2' : '09999022',
            '123_iso_01_s#3' : '09999013', '123_iso_02_s#3' : '09999023',
            '123_iso_01_s#4' : '09999014', '123_iso_02_s#4' : '09999024',
            '123_iso_01_s#5' : '09999015', '123_iso_02_s#5' : '09999025'}

    #: The barcodes for the preparation plate mapped onto rack label.
    PREP_PLATE_BARCODES = {
            '123_iso_01_p' : '09999911', '123_iso_02_p' : '09999912',
            '123_job_01_jp' : '09999900'}
    #: The barcodes for the aliquot plates mapped onto rack label.
    ALIQUOT_PLATE_BARCODES = {
            '123_iso_01_a' : '09999210', '123_iso_02_a' : '09999220',
            '123_iso_01_a#1' : '09999211', '123_iso_01_a#2' : '09999212',
            '123_iso_02_a#1' : '09999221', '123_iso_02_a#2' : '09999210'}

    def __init__(self):
        self.barcode_map = dict()
        self.label_map = dict()
        self.__status_future = get_item_status_future()
        self.__status_managed = get_item_status_managed()
        self.tube_rack_specs = None

    def reset_session(self):
        self.__status_future = get_item_status_future()
        self.__status_managed = get_item_status_managed()

    def get_tube_rack(self, rack_label):
        if not self.label_map.has_key(rack_label):
            self.__create_tube_rack(rack_label)
        return self.label_map[rack_label]

    def __create_tube_rack(self, rack_label):
        if self.tube_rack_specs is None:
            self.tube_rack_specs = RACK_SPECS_NAMES.from_name(
                                                  RACK_SPECS_NAMES.STOCK_RACK)
        barcode = self.STOCK_RACK_BARCODES[rack_label]
        rack = self.__create_rack(self.tube_rack_specs, None, barcode,
                                  self.__status_managed)
        self.label_map[rack_label] = rack
        return rack

    def get_plate(self, specs, label):
        if not self.label_map.has_key(label):
            self.__create_plate(specs, label)
        return self.label_map[label]

    def __create_plate(self, specs, label):
        if isinstance(specs, str):
            specs = RACK_SPECS_NAMES.from_name(specs)
        if self.PREP_PLATE_BARCODES.has_key(label):
            barcode = self.PREP_PLATE_BARCODES[label]
        else:
            barcode = self.ALIQUOT_PLATE_BARCODES[label]
        rack = self.__create_rack(specs, label, barcode)
        self.label_map[rack.label] = rack
        return rack

    def __create_rack(self, specs, label, barcode, status=None):
        if status is None: status = self.__status_future
        rack = specs.create_rack(status=status, label=label, barcode=barcode)
        self.barcode_map[rack.barcode] = rack
        return rack


class TestTubeGenerator(object):
    """
    This class contains the data for the stock tubes before tube handling.
    """
    #: pool_id = pos label, tube barcode, rack barcode
    CANDIDATE_DATA = {205200 : ['f1', '1000205200', '07777777'],
                      205201 : ['g1', '1000205201', '07777777'],
                      205202 : ['c1', '1000205202', '07777777'],
                      205203 : ['c2', '1000205203', '07777777'],
                      205204 : ['c3', '1000205204', '07777777'],
                      205205 : ['c4', '1000205205', '07777777'],
                      205206 : ['c5', '1000205206', '07777777'],
                      205207 : ['c6', '1000205207', '07777777'],
                      205208 : ['c7', '1000205208', '07777777'],
                      205209 : ['c8', '1000205209', '07777777'],
                      205210 : ['d1', '1000205210', '07777777'],
                      205212 : ['d2', '1000205212', '07777777'],
                      205214 : ['d3', '1000205214', '07777777'],
                      205215 : ['d4', '1000205215', '07777777'],
                      330001 : ['c1', '1000330001', '07777778'],
                      333803 : ['a3', '1000333803', '07777773'],
                      1056000 : ['g2', '1001056000', '07777778'],
                      180005 : ['g6', '1000180005', '07777778']}

    #: rack_barcode = location string
    RACK_LOCATIONS = {'07777777' : 'freezer 1 (index 2)',
                      '07777773' : 'freezer 2',
                      '07777778' : 'unknown location'}

    def __init__(self, tube_specs):
        self.__tube_specs = tube_specs
        self.__status_managed = get_item_status_managed()
        self.__supplier = Organization('testvendor')

    @classmethod
    def create_tube_candidate(cls, pool):
        tc_data = cls.CANDIDATE_DATA[pool.id]
        rack_pos = get_rack_position_from_label(tc_data[0])
        tc = TubeCandidate(pool_id=pool.id, rack_barcode=tc_data[2],
                rack_position=rack_pos, tube_barcode=tc_data[1],
                concentration=pool.default_stock_concentration,
                volume=100 / VOLUME_CONVERSION_FACTOR)
        return tc

    def create_tube(self, rack, rack_pos, pool, tube_barcode, volume):
        tube = Tube(specs=self.__tube_specs, status=self.__status_managed,
                    barcode=tube_barcode, location=None)
        rack.add_tube(tube, rack_pos)
        rack.containers.append(tube)
        if pool is not None:
            self.create_sample(tube, pool, volume)
        return tube

    def create_sample(self, tube, pool, volume):
        conc = pool.default_stock_concentration
        sample = StockSample(volume=volume, container=tube,
                             molecule_design_pool=pool,
                             supplier=self.__supplier,
                             molecule_type=pool.molecule_type,
                             concentration=conc)
        tube.sample = sample
        return sample


class LabIsoTestCase2(LabIsoTestCase1):
    """
    This class generates test ISOs from the data in :class:`LAB_ISO_TEST_CASES`
    """
    FOR_JOB = None
    _USED_ISO_LABEL = '123_iso_01'

    def set_up(self):
        LabIsoTestCase1.set_up(self)
        self.user = self._get_entity(IUser, 'it')
        self.rack_generator = _TestRackGenerator()
        self.entity = None # ISO or ISO job
        self.isos = dict()
        self.iso_job = None
        self.iso_layouts = dict()
        self.prep_layouts = dict()
        self.job_layouts = dict()
        self.stock_racks = dict() # mapped onto stock rack labels
        self.stock_rack_layouts = dict()
        self.compare_stock_tube_barcode = True

    def tear_down(self):
        LabIsoTestCase1.tear_down(self)
        del self.entity
        del self.isos
        del self.iso_job
        del self.rack_generator
        del self.iso_layouts
        del self.prep_layouts
        del self.job_layouts
        del self.stock_racks
        del self.stock_rack_layouts
        del self.compare_stock_tube_barcode

    def _continue_setup(self, file_name=None):
        LabIsoTestCase1._continue_setup(self, file_name=file_name)
        self.__adjust_process_job_first_flag()
        self.__generate_layouts()
        self.__generate_isos()
        self.__generate_iso_plates()
        self.__generate_iso_request_worklist_series()
        self.__generate_iso_job()
        self.__set_entity()

    def __set_entity(self):
        if self.FOR_JOB:
            self.entity = self.iso_job
        else:
            self.entity = self.isos[self._USED_ISO_LABEL]

    def __adjust_process_job_first_flag(self):
        """
        This is a fix, since the recognition during metadata upload is not
        error-proof yet. Recognition during ISO planning is working, but the
        ISO-planning step is not done by a tool byut manually here to save
        processing time.
        """
        order = LAB_ISO_TEST_CASES.get_iso_order(self.case)
        process_first = True
        if order == LAB_ISO_ORDERS.ISO_FIRST:
            process_first = False
        self.iso_request.process_job_first = process_first

    def __generate_layouts(self):
        iso_labels = LAB_ISO_TEST_CASES.ISO_LABELS[self.case]
        for iso_label in iso_labels:
            final_layout = self.__create_iso_layout(iso_label)
            self.iso_layouts[iso_label] = final_layout
        prep_layouts = LAB_ISO_TEST_CASES.get_prep_plate_layout_data(self.case)
        for plate_label in prep_layouts.keys():
            layout = self.__create_prep_layout(plate_label, for_job=False)
            self.prep_layouts[plate_label] = layout
        job_layouts = LAB_ISO_TEST_CASES.get_job_plate_layout_data(self.case)
        for plate_label in job_layouts.keys():
            layout = self.__create_prep_layout(plate_label, for_job=True)
            self.job_layouts[plate_label] = layout

    def __create_iso_layout(self, iso_label):
        layout_map = LAB_ISO_TEST_CASES.get_final_plate_layout_data(self.case)
        layout_data = layout_map[iso_label]
        shape_name = LAB_ISO_TEST_CASES.get_final_iso_layout_shape(self.case)
        shape = RACK_SHAPE_NAMES.from_name(shape_name)
        layout = FinalLabIsoLayout(shape)
        # pos_label - pool_id, pos_type, vol, concentration, from_job,
        # transfer_targets, sector_index, stock_rack_marker
        for pos_label, pos_data in layout_data.iteritems():
            rack_pos = get_rack_position_from_label(pos_label)
            pos_type = pos_data[1]
            stock_rack_marker = pos_data[7]
            if pos_type == MOCK_POSITION_TYPE:
                pool = MOCK_POSITION_TYPE
            else:
                pool = self._get_pool(pos_data[0])
            stock_tube_barcode, stock_rack_barcode = \
                self._get_original_stock_data(pos_data[0], stock_rack_marker)
            fp = FinalLabIsoPosition(rack_position=rack_pos,
                    molecule_design_pool=pool, position_type=pos_type,
                    volume=pos_data[2], concentration=pos_data[3],
                    from_job=pos_data[4],
                    transfer_targets=pos_data[5],
                    sector_index=pos_data[6],
                    stock_rack_marker=stock_rack_marker,
                    stock_tube_barcode=stock_tube_barcode,
                    stock_rack_barcode=stock_rack_barcode)
            layout.add_position(fp)
        return layout

    def __create_prep_layout(self, rack_label, for_job):
        if for_job:
            layout_map = LAB_ISO_TEST_CASES.get_job_plate_layout_data(self.case)
            shape_name = LAB_ISO_TEST_CASES.get_job_plate_layout_shape(self.case)
        else:
            layout_map = LAB_ISO_TEST_CASES.get_prep_plate_layout_data(self.case)
            shape_name = LAB_ISO_TEST_CASES.get_preparation_plate_layout_shape(
                                                                    self.case)
        shape = RACK_SHAPE_NAMES.from_name(shape_name)
        layout = LabIsoPrepLayout(shape)
        layout_data = layout_map[rack_label]
        # pos_label - pool_id, pos_type, vol, concentration, transfer_targets,
        # external_targets, sector_index, stock_rack_marker
        for pos_label, pos_data in layout_data.iteritems():
            rack_pos = get_rack_position_from_label(pos_label)
            pos_type = pos_data[1]
            stock_rack_marker = pos_data[7]
            if pos_type == MOCK_POSITION_TYPE:
                pool = MOCK_POSITION_TYPE
            else:
                pool = self._get_pool(pos_data[0])
            stock_tube_barcode, stock_rack_barcode = \
                self._get_original_stock_data(pos_data[0], stock_rack_marker)
            pp = LabIsoPrepPosition(rack_position=rack_pos,
                    molecule_design_pool=pool, position_type=pos_type,
                    volume=pos_data[2], concentration=pos_data[3],
                    transfer_targets=pos_data[4], external_targets=pos_data[5],
                    sector_index=pos_data[6],
                    stock_rack_marker=stock_rack_marker,
                    stock_tube_barcode=stock_tube_barcode,
                    stock_rack_barcode=stock_rack_barcode)
            layout.add_position(pp)
        return layout

    def _get_original_stock_data(self, pool_id, stock_rack_marker):
        if pool_id == MOCK_POSITION_TYPE or stock_rack_marker is None:
            return (None, None)
        tube_data = TestTubeGenerator.CANDIDATE_DATA[pool_id]
        tube_barcode = tube_data[1]
        rack_barcode = tube_data[2]
        return (tube_barcode, rack_barcode)

    def _get_plate_specs_name_for_shape(self, shape):
        if shape.name == RACK_SHAPE_NAMES.SHAPE_96:
            return RACK_SPECS_NAMES.STANDARD_96
        else:
            return RACK_SPECS_NAMES.STANDARD_384

    def __generate_isos(self):
        for iso_label, iso_layout in self.iso_layouts.iteritems():
            num_stock_racks = LAB_ISO_TEST_CASES.get_number_iso_stock_racks(
                                                        self.case)[iso_label]
            pool_set = self.__generate_pool_set(iso_label)
            iso = self._create_lab_iso(
                        label=iso_label, iso_request=self.iso_request,
                        number_stock_racks=num_stock_racks,
                        rack_layout=iso_layout.create_rack_layout(),
                        molecule_design_pool_set=pool_set)
            self.isos[iso_label] = iso

    def __generate_iso_plates(self):
        rs = self.iso_request.iso_plate_reservoir_specs
        ps = RACK_SPECS_NAMES.from_reservoir_specs(rs)
        for iso_label, iso in self.isos.iteritems():
            final_plate_labels = LAB_ISO_TEST_CASES.get_final_plate_labels(
                                                        self.case)[iso_label]
            if LAB_ISO_TEST_CASES.is_library_case(self.case):
                for lib_plates in self.library_generator.library_plates.values():
                    for lib_plate in lib_plates:
                        if lib_plate.rack.label in final_plate_labels:
                            lib_plate.lab_iso = iso
                            lib_plate.has_been_used = True
            else:
                for label in final_plate_labels:
                    plate = self.rack_generator.get_plate(ps, label)
                    iso.add_aliquot_plate(plate)
            for plate_label, layout in self.prep_layouts.iteritems():
                if not iso_label in plate_label: continue
                specs_name = self._get_plate_specs_name_for_shape(layout.shape)
                plate = self.rack_generator.get_plate(specs_name, plate_label)
                iso.add_preparation_plate(plate,
                                          layout.create_rack_layout())

    def __generate_pool_set(self, iso_label):
        set_data = LAB_ISO_TEST_CASES.get_pool_set_data(self.case)
        if set_data is None: return None
        pool_ids = set_data[iso_label]
        pools = []
        for pool_id in pool_ids:
            pools.append(self._get_pool(pool_id))
        mt = pools[0].molecule_type
        return self._create_molecule_design_pool_set(molecule_type=mt,
                                     molecule_design_pools=set(pools))

    def __generate_iso_request_worklist_series(self):
        worklist_data = LAB_ISO_TEST_CASES.get_iso_worklist_data(self.case)
        ws = self.__generate_worklist_series(worklist_data)
        self.iso_request.worklist_series = ws

    def __generate_iso_job(self):
        num_stock_racks = LAB_ISO_TEST_CASES.get_number_job_stock_racks(
                                                                    self.case)
        worklist_data = LAB_ISO_TEST_CASES.get_job_worklist_data(self.case)
        worklist_series = self.__generate_worklist_series(worklist_data)
        self.iso_job = self._create_iso_job(number_stock_racks=num_stock_racks,
                       isos=self.isos.values(), label=TEST_ISO_JOB_NAME,
                       worklist_series=worklist_series, user=self.user)
        for plate_label, layout in self.job_layouts.iteritems():
            specs = self._get_plate_specs_name_for_shape(layout.shape)
            plate = self.rack_generator.get_plate(specs, plate_label)
            self.iso_job.add_preparation_plate(plate,
                                               layout.create_rack_layout())

    def __generate_worklist_series(self, worklist_data):
        if len(worklist_data) < 1: return None
        worklist_series = self._create_worklist_series()
        for wl_label, wl_info in worklist_data.iteritems():
            transfer_type = wl_info[0]
            pipetting_specs = wl_info[1]
            wl_index = wl_info[2]
            plts = []
            plt_data = LAB_ISO_TEST_CASES.get_worklist_details(self.case,
                                                               wl_label)
            # for dilutions: target_pos - vol
            # for transfers: trg_pos - vol, target_pos
            # for rack_transfers: target index - vol, source, num sectors
            for trg, plt_info in plt_data.iteritems():
                if transfer_type == TRANSFER_TYPES.SAMPLE_DILUTION:
                    trg_pos = get_rack_position_from_label(trg)
                    vol = plt_info / VOLUME_CONVERSION_FACTOR
                    plt = PlannedSampleDilution.get_entity(volume=vol,
                          diluent_info=DILUENT_INFO, target_position=trg_pos)
                elif transfer_type == TRANSFER_TYPES.SAMPLE_TRANSFER:
                    trg_pos = get_rack_position_from_label(trg)
                    vol = plt_info[0] / VOLUME_CONVERSION_FACTOR
                    src_pos = get_rack_position_from_label(plt_info[1])
                    plt = PlannedSampleTransfer.get_entity(volume=vol,
                          source_position=src_pos, target_position=trg_pos)
                else:
                    vol = plt_info[0] / VOLUME_CONVERSION_FACTOR
                    plt = PlannedRackSampleTransfer.get_entity(vol,
                                                               plt_info[2],
                                                               plt_info[1],
                                                               trg)
                plts.append(plt)
            wl = self._create_planned_worklist(label=wl_label,
                transfer_type=transfer_type, pipetting_specs=pipetting_specs,
                planned_liquid_transfers=plts)
            worklist_series.add_worklist(index=wl_index, worklist=wl)
        return worklist_series

    def _generate_stock_rack_layout(self, stock_rack_label):
        layout_map = LAB_ISO_TEST_CASES.get_stock_rack_layout_data(self.case)
        layout_data = layout_map[stock_rack_label]
        layout = StockRackLayout()
        for pos_label, pos_data in layout_data.iteritems():
            rack_pos = get_rack_position_from_label(pos_label)
            pool = self._get_pool(pos_data[0])
            sr_pos = StockRackPosition(rack_position=rack_pos,
                    molecule_design_pool=pool, tube_barcode=pos_data[1],
                    transfer_targets=pos_data[2])
            layout.add_position(sr_pos)
        return layout

    def __generate_stock_rack_worklist_series(self, stock_rack_marker,
                                              iso_label):
        if iso_label is None: # for job
            num_stock_racks = LAB_ISO_TEST_CASES.get_number_job_stock_racks(
                                                                    self.case)
        else:
            num_stock_racks = LAB_ISO_TEST_CASES.get_number_iso_stock_racks(
                                                        self.case)[iso_label]
        if num_stock_racks == 0: return None
        if iso_label is None: # for job
            worklist_data = LAB_ISO_TEST_CASES.\
                            get_stock_rack_worklist_series_for_job(self.case)
        else:
            worklist_data = LAB_ISO_TEST_CASES.\
                            get_stock_rack_worklist_series_for_iso(self.case)
        worklist_series = self._create_worklist_series()
        for wl_label, wl_details in worklist_data.iteritems():
            if not stock_rack_marker in wl_label: continue
            pipetting_specs = wl_details[1]
            wl_index = wl_details[0]
            plts = []
            plt_data = LAB_ISO_TEST_CASES.get_stock_rack_worklist_details(
                                                        self.case, wl_label)
            for trg, plt_info in plt_data.iteritems():
                trg_pos = get_rack_position_from_label(trg)
                vol = plt_info[0] / VOLUME_CONVERSION_FACTOR
                src_pos = get_rack_position_from_label(plt_info[1])
                plt = PlannedSampleTransfer.get_entity(volume=vol,
                      source_position=src_pos, target_position=trg_pos)
                plts.append(plt)
            wl = self._create_planned_worklist(label=wl_label,
                transfer_type=TRANSFER_TYPES.SAMPLE_TRANSFER,
                pipetting_specs=pipetting_specs, planned_liquid_transfers=plts)
            worklist_series.add_worklist(index=wl_index, worklist=wl)
        return worklist_series

    def _generate_stock_racks(self, entity):
        if isinstance(entity, IsoJob):
            iso_label = None
        else:
            iso_label = entity.label
        sr_map = LAB_ISO_TEST_CASES.get_stock_rack_labels(self.case)
        for rack_marker, rack_labels in sr_map.iteritems():
            for rack_label in rack_labels:
                if not entity.label in rack_label: continue
                worklist_series = self.__generate_stock_rack_worklist_series(
                                                        rack_marker, iso_label)
                layout = self._generate_stock_rack_layout(rack_label)
                rack = self.rack_generator.get_tube_rack(rack_label)
                if iso_label is None: # for job
                    stock_rack = self._create_iso_job_stock_rack(iso_job=entity,
                                 label=rack_label, rack=rack,
                                 rack_layout=layout.create_rack_layout(),
                                 worklist_series=worklist_series)
                else:
                    sector_index = LAB_ISO_TEST_CASES.\
                        get_sectors_for_iso_stock_racks(self.case)[rack_marker]
                    kw = dict(iso=entity, label=rack_label, rack=rack,
                              rack_layout=layout.create_rack_layout(),
                              worklist_series=worklist_series)
                    if sector_index is None:
                        meth = self._create_iso_stock_rack
                    else:
                        meth = self._create_iso_sector_stock_rack
                        kw['sector_index'] = sector_index
                    stock_rack = meth(**kw)
                self.stock_racks[rack_label] = stock_rack
                self.stock_rack_layouts[rack_label] = layout

    def _compare_stock_rack_layout(self, layout_data, rack_layout, rack_label):
        converter = StockRackLayoutConverter(rack_layout)
        layout = converter.get_result()
        if layout is None:
            raise AssertionError('Unable to convert rack layout for stock ' \
                                 'rack "%s".' % (rack_label))
        self.assert_equal(layout.shape.name, RACK_SHAPE_NAMES.SHAPE_96)
        layout_name = 'rack layout for stock rack "%s"' % (rack_label)
        tested_labels = []
        # pos_label - pool, tube barcode, transfer_targets
        for rack_pos, plate_pos in layout.iterpositions():
            pos_label = rack_pos.label.lower()
            tested_labels.append(pos_label)
            if not layout_data.has_key(pos_label):
                msg = 'Unexpected position %s in layout for stock rack "%s"!' \
                      % (pos_label, rack_label)
                raise AssertionError(msg)
            pos_data = layout_data[pos_label]
            self._compare_layout_value(pos_data[0], 'molecule_design_pool',
                                       plate_pos, layout_name)
            if self.compare_stock_tube_barcode:
                self._compare_layout_value(pos_data[1], 'tube_barcode',
                                           plate_pos, layout_name)
            else:
                self.assert_is_not_none(plate_pos.tube_barcode)
            self._compare_layout_value(pos_data[2], 'transfer_targets',
                                        plate_pos, layout_name)
        self.assert_equal(sorted(tested_labels), sorted(layout_data.keys()))

    def _compare_stock_rack_worklist_series(self, stock_rack):
        worklist_series = stock_rack.worklist_series
        self.assert_true(len(worklist_series) > 0)
        if self.FOR_JOB:
            sr_data = LAB_ISO_TEST_CASES.\
                       get_stock_rack_worklist_series_for_job(self.case)
        else:
            sr_data = LAB_ISO_TEST_CASES.\
                       get_stock_rack_worklist_series_for_iso(self.case)
        rack_marker = None
        stock_rack_labels = LAB_ISO_TEST_CASES.get_stock_rack_labels(self.case)
        for marker, labels in stock_rack_labels.iteritems():
            if stock_rack.label in labels:
                rack_marker = marker
                break
        exp_data = dict()
        for sr_label, wl_data in sr_data.iteritems():
            if rack_marker in sr_label: exp_data[sr_label] = wl_data
        self.assert_is_not_none(worklist_series)
        self.assert_equal(len(worklist_series), len(exp_data))
        found_labels = []
        for worklist in worklist_series:
            label = worklist.label
            found_labels.append(label)
            #: worklist label - type, pipetting specs name, num transfers
            wl_data = exp_data[label]
            wl_index = wl_data[0]
            ps = wl_data[1]
            self.assert_equal(worklist.index, wl_index)
            if not worklist.transfer_type == TRANSFER_TYPES.SAMPLE_TRANSFER:
                msg = 'The transfer types for worklist %s differ.\n' \
                      'Expected: %s\nFound: %s' % (worklist.label,
                       TRANSFER_TYPES.SAMPLE_TRANSFER, worklist.transfer_type)
                raise AssertionError(msg)
            if not worklist.pipetting_specs == ps:
                msg = 'The pipetting specs for worklist %s differ.\n' \
                      'Expected: %s\nFound: %s' % (worklist.label, ps.name,
                       worklist.pipetting_specs.name)
                raise AssertionError(msg)
            details = LAB_ISO_TEST_CASES.get_stock_rack_worklist_details(
                                                            self.case, label)
            self._compare_worklist_details(worklist, details)
        self.assert_equal(sorted(found_labels), sorted(exp_data.keys()))

    def _get_layout_from_iso(self, iso=None):
        if iso is None:
            iso = self.isos[self._USED_ISO_LABEL]
        converter = FinalLabIsoLayoutConverter(iso.rack_layout)
        return converter.get_result()

    def _get_layout_from_preparation_plate(self, prep_plate):
        converter = LabIsoPrepLayoutConverter(prep_plate.rack_layout)
        return converter.get_result()

