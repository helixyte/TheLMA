"""
Base classes for lab ISO testing.
"""
from everest.entities.utils import get_root_aggregate
from thelma.automation.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.semiconstants import RACK_SPECS_NAMES
from thelma.automation.semiconstants import get_384_rack_shape
from thelma.automation.semiconstants import get_experiment_metadata_type
from thelma.automation.semiconstants import get_item_status_managed
from thelma.automation.semiconstants import get_pipetting_specs_biomek
from thelma.automation.semiconstants import get_pipetting_specs_cybio
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.tools.iso.lab.base import DILUENT_INFO
from thelma.automation.tools.iso.lab.base import FinalLabIsoLayoutConverter
from thelma.automation.tools.iso.lab.base import LabIsoPrepLayoutConverter
from thelma.automation.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.utils.base import are_equal_values
from thelma.automation.utils.base import get_trimmed_string
from thelma.automation.utils.iso import IsoRequestLayout
from thelma.automation.utils.iso import IsoRequestLayoutConverter
from thelma.automation.utils.iso import IsoRequestPosition
from thelma.automation.utils.layouts import LibraryLayout
from thelma.automation.utils.layouts import LibraryLayoutPosition
from thelma.automation.utils.layouts import TransferTarget
from thelma.interfaces import IMoleculeDesignLibrary
from thelma.interfaces import IMoleculeDesignPool
from thelma.interfaces import ISubproject
from thelma.models.experiment import ExperimentMetadata
from thelma.models.library import LibraryPlate
from thelma.models.library import MoleculeDesignLibrary
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.moleculedesign import MoleculeDesignPoolSet
from thelma.tests.tools.tooltestingutils \
    import ExperimentMetadataReadingTestCase
from thelma.tests.tools.tooltestingutils import SilentLog
from thelma.tests.tools.tooltestingutils import TestingLog

#: This pool ID is used for tests in which we do not want to find an
#: appropriate stock sample.
POOL_WITHOUT_STOCK_SAMPLE = 689600

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

    @classmethod
    def get_xls_file_name(cls, case_name):
        return '%s.xls' % (case_name)

    @classmethod
    def get_experiment_scenario(cls, case_name):
        type_id = cls.__EXPERIMENT_SCENARIOS[case_name]
        return get_experiment_metadata_type(type_id)

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
                f2=[180005, 'fixed', 3, 50000],
                f3=[180005, 'fixed', 3, 49500])
        elif case_name == cls.CASE_ASSOCIATION_DIRECT:
            return dict(
                b2=[205201, 'fixed', 2, 50000],
                b3=[205202, 'fixed', 2, 50000],
                b4=[180005, 'fixed', 2, 50000],
                c2=['md_001', 'floating', 2, 50000],
                c3=['md_002', 'floating', 2, 50000],
                c4=['md_003', 'floating', 2, 50000],
                d2=[205201, 'fixed', 2, 50000],
                d3=[205202, 'fixed', 2, 50000],
                d4=[180005, 'fixed', 2, 50000],
                e2=['mock', 'mock', 2, 'mock'],
                e3=['mock', 'mock', 2, 'mock'])
        elif case_name == cls.CASE_ASSOCIATION_96:
            return dict(
                b2=[205201, 'fixed', 5, 50],
                c2=[205202, 'fixed', 5, 50],
                b4=[205203, 'fixed', 5, 50],
                c4=[180005, 'fixed', 5, 50],
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
                b4=[180005, 'fixed', 10, 50],
                c2=['md_001', 'floating', 10, 50],
                c3=['md_002', 'floating', 10, 50],
                c4=['md_003', 'floating', 10, 50],
                d2=[205201, 'fixed', 10, 50],
                d3=[205202, 'fixed', 10, 50],
                d4=[180005, 'fixed', 10, 50],
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
                b4=[180005, 'fixed', 10, 50],
                c2=['md_001', 'floating', 10, 50],
                c3=['md_002', 'floating', 10, 50],
                c4=['md_003', 'floating', 10, 50],
                d2=[205201, 'fixed', 10, 50],
                d3=[205202, 'fixed', 10, 50],
                d4=[180005, 'fixed', 10, 50],
                e2=['mock', 'mock', 10, 'mock'],
                e3=['mock', 'mock', 10, 'mock'],
                e4=['untransfected', 'untransfected', 'untransfected',
                    'untransfected'])
        elif case_name == cls.CASE_ASSOCIATION_JOB_LAST:
            return dict(
                b2=[205201, 'fixed', 10, 50],
                b3=[330001, 'fixed', 10, 50],
                b4=[180005, 'fixed', 10, 50],
                c2=['md_001', 'floating', 10, 50],
                c3=['md_002', 'floating', 10, 50],
                c4=['md_003', 'floating', 10, 50],
                d2=['md_004', 'floating', 10, 50],
                d3=['md_005', 'floating', 10, 50],
                d4=['md_006', 'floating', 10, 50],
                e2=[205201, 'fixed', 10, 100],
                e3=[330001, 'fixed', 10, 100],
                e4=[180005, 'fixed', 10, 100],
                f2=['mock', 'mock', 10, 'mock'],
                f3=['mock', 'mock', 10, 'mock'],
                f4=['untransfected', 'untransfected', 'untransfected',
                    'untransfected'])
        elif case_name == cls.CASE_ASSOCIATION_SEVERAL_CONC:
            return dict(
                b3=[205201, 'fixed', 10, 50],
                b5=[330001, 'fixed', 10, 50],
                b7=[180005, 'fixed', 10, 50],
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
                f7=[180005, 'fixed', 10, 100],
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
                b10=[180005, 'fixed', 2, 50000, False, [], None, 's#1']) # ssDNA (primer)
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
                b10=[180005, 'fixed', 2, 50000, False, [], None, 's#1'], # ssDNA (primer)
                d10=[180005, 'fixed', 10, 10000, False, [], None, 's#1']) # ssDNA (primer)
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
                b10=[180005, 'fixed', 4, 50000, False, [], None, 's#1'], # ssDNA (primer)
                d10=[180005, 'fixed', 4, 10000, False, [], None, None]) # ssDNA (primer)
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
                f2=[180005, 'fixed', 3, 50000, False, [], None, None],
                f3=[180005, 'fixed', 3, 48000, False, [], None, None])
            return {iso_labels[0] : f}
        elif case_name == cls.CASE_ASSOCIATION_DIRECT:
            f = dict(
                b2=[205201, 'fixed', 2, 50000, True, [], 3, 's#1'],
                b3=[205202, 'fixed', 2, 50000, True, [], 2, 's#1'],
                b4=[180005, 'fixed', 2, 50000, True, [], 3, 's#1'],
                d2=[205201, 'fixed', 2, 50000, True, [], 3, 's#1'],
                d3=[205202, 'fixed', 2, 50000, True, [], 2, 's#1'],
                d4=[180005, 'fixed', 2, 50000, True, [], 3, 's#1'],
                e2=['mock', 'mock', 2, None, False, [], None, None],
                e3=['mock', 'mock', 2, None, False, [], None, None])
            f1 = dict(f, **dict(
                    c2=[205205, 'floating', 2, 50000, False, [], 1, 's#3'],
                    c3=[205206, 'floating', 2, 50000, False, [], 0, 's#2'],
                    c4=[205207, 'floating', 2, 50000, False, [], 1, 's#3']))
            f2 = dict(f, **dict(
                    c2=[205208, 'floating', 2, 50000, False, [], 1, 's#3'],
                    c3=[205209, 'floating', 2, 50000, False, [], 0, 's#2'],
                    c4=[205210, 'floating', 2, 50000, False, [], 1, 's#3']))
            return {iso_labels[0] : f1, iso_labels[1] : f2}
        elif case_name == cls.CASE_ASSOCIATION_96:
            f = dict(
                b2=[205201, 'fixed', 5, 50, False, [], 0, None],
                c2=[205202, 'fixed', 5, 50, False, [], 0, None],
                b4=[205203, 'fixed', 5, 50, False, [], 0, None],
                c4=[180005, 'fixed', 5, 50, False, [], 0, None],
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
                b4=[180005, 'fixed', 10, 50, False, [], 3, None],
                d2=[205201, 'fixed', 10, 50, False, [], 3, None],
                d3=[205202, 'fixed', 10, 50, False, [], 2, None],
                d4=[180005, 'fixed', 10, 50, False, [], 3, None],
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
                b4=[180005, 'fixed', 10, 50, False, [], 3, None],
                d2=[205201, 'fixed', 10, 50, False, [], 3, None],
                d3=[205202, 'fixed', 10, 50, False, [], 2, None],
                d4=[180005, 'fixed', 10, 50, False, [], 3, None],
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
                b4=[180005, 'fixed', 10, 50, True, [], None, None],
                e2=[205201, 'fixed', 15, 100, True,
                    [TransferTarget('b2', 5, 'a')], None, None],
                e3=[330001, 'fixed', 15, 100, True,
                    [TransferTarget('b3', 5, 'a')], None, None],
                e4=[180005, 'fixed', 15, 100, True,
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
                b7=[180005, 'fixed', 10, 50, True, [], None, None],
                e3=['mock', 'mock', 10, None, False, [], None, None],
                e5=['mock', 'mock', 10, None, False, [], None, None],
                e7=['mock', 'mock', 10, None, False, [], None, None],
                f3=[205201, 'fixed', 15, 100, True,
                    [TransferTarget('b3', 5, 'a')], None, None],
                f5=[330001, 'fixed', 15, 100, True,
                    [TransferTarget('b5', 5, 'a')], None, None],
                f7=[180005, 'fixed', 15, 100, True,
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
                o10=['mock', 'mock', 4, None, False, [], None, None])
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
                o10=['mock', 'mock', 4, None, False, [], None, None])
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
                      d5=[180005, 'fixed', 12, 20000, [],
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
                f1=[180005, 'fixed', 61, 50000,
                    [TransferTarget('f2', 48, 'p#1')],
                    [TransferTarget('f2', 3, 'a')], None, 's#1'],
                f2=[180005, 'fixed', 50, 48000, [],
                    [TransferTarget('f3', 3, 'a')], None, None])
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
                e7=[180005, 'fixed', 11, 25000,
                    [TransferTarget('e8', 1, 'p#1')], [], 0, 's#1'],
                e8=[180005, 'fixed', 100, 250,
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
                b4=[180005, 'fixed', 100, 500, [],
                    [TransferTarget('b4', 1, 'a')], 3, 's#1'],
                d2=[205201, 'fixed', 100, 500, [],
                    [TransferTarget('d2', 1, 'a')], 3, 's#1'],
                d3=[205202, 'fixed', 100, 500, [],
                    [TransferTarget('d3', 1, 'a')], 2, 's#1'],
                d4=[180005, 'fixed', 100, 500, [],
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
                b4=[180005, 'fixed', 100, 500, [],
                    [TransferTarget('b4', 1, 'a')], 3, 's#1'],
                d2=[205201, 'fixed', 100, 500, [],
                    [TransferTarget('d2', 1, 'a')], 3, 's#1'],
                d3=[205202, 'fixed', 100, 500, [],
                    [TransferTarget('d3', 1, 'a')], 2, 's#1'],
                d4=[180005, 'fixed', 100, 500, [],
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
                 c2=[180005, 'fixed', 100, 500, [],
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
                 e3=[180005, 'fixed', 66.7, 750, [],
                     [TransferTarget('e4', 2, 'a')], None, 's#1'])
            return {'123_job_01_jp' : jp}
        elif case_name == cls.CASE_ASSOCIATION_SEVERAL_CONC:
            jp = dict(
                 f1=[205201, 'fixed', 66.7, 750, [],
                     [TransferTarget('f3', 2, 'a')], None, 's#1'],
                 f2=[330001, 'fixed', 14.7, 750, [],
                     [TransferTarget('f5', 2, 'a')], None, 's#1'],
                 f3=[180005, 'fixed', 66.7, 750, [],
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
        if case_name == cls.CASE_ASSOCIATION_JOB_LAST:
            return RACK_SHAPE_NAMES.SHAPE_96
        elif case_name == cls.CASE_ASSOCIATION_SEVERAL_CONC:
            return RACK_SHAPE_NAMES.SHAPE_96
        elif case_name == cls.CASE_LIBRARY_SIMPLE:
            return RACK_SHAPE_NAMES.SHAPE_96
        elif case_name == cls.CASE_ASSOCIATION_NO_CYBIO:
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
        #: worklist label - type, pipetting specs name
        if case_name == cls.CASE_ORDER_ONLY:
            return {}
        elif case_name == cls.CASE_NO_JOB_DIRECT:
            return {'123_1_a_buffer' : [type_dil, ps_biomek]}
        elif case_name == cls.CASE_NO_JOB_1_PREP:
            return {'123_1_p_buffer' : [type_dil, ps_biomek],
                    '123_2_a_buffer' : [type_dil, ps_biomek],
                    '123_3_p_to_a' : [type_trans, ps_biomek]}
        elif case_name == cls.CASE_NO_JOB_COMPLEX:
            return {'123_1_p_buffer' : [type_dil, ps_biomek],
                    '123_2_a_buffer' : [type_dil, ps_biomek],
                    '123_3_p_to_p' : [type_trans, ps_biomek],
                    '123_4_p_to_p' : [type_trans, ps_biomek],
                    '123_5_p_to_p' : [type_trans, ps_biomek],
                    '123_6_p_to_a' : [type_trans, ps_biomek],
                    '123_7_a_to_a' : [type_trans, ps_biomek]}
        elif case_name == cls.CASE_ASSOCIATION_DIRECT:
            return {'123_1_a_buffer' : [type_dil, ps_biomek]}
        elif case_name == cls.CASE_ASSOCIATION_96:
            return {'123_1_p_buffer' : [type_dil, ps_cybio],
                    '123_2_a_buffer' : [type_dil, ps_biomek],
                    '123_3_p_to_p' : [type_rack, ps_cybio],
                    '123_4_p_to_a' : [type_rack, ps_cybio]}
        elif case_name == cls.CASE_ASSOCIATION_SIMPLE:
            return {'123_1_p_buffer' : [type_dil, ps_cybio],
                    '123_2_a_buffer' : [type_dil, ps_biomek],
                    '123_3_p_to_a' : [type_rack, ps_cybio]}
        elif case_name == cls.CASE_ASSOCIATION_NO_CYBIO:
            return {'123_2_p_buffer' : [type_dil, ps_biomek],
                    '123_3_a_buffer' : [type_dil, ps_biomek],
                    '123_5_p_to_a' : [type_trans, ps_biomek],
                    '123_6_a_to_a' : [type_trans, ps_biomek]}
        elif case_name == cls.CASE_ASSOCIATION_2_ALIQUOTS:
            return {'123_1_p_buffer' : [type_dil, ps_cybio],
                    '123_2_a_buffer' : [type_dil, ps_biomek],
                    '123_3_p_to_a' : [type_rack, ps_cybio]}
        elif case_name == cls.CASE_ASSOCIATION_JOB_LAST:
            return {'123_1_p_buffer' : [type_dil, ps_cybio],
                    '123_2_a_buffer' : [type_dil, ps_biomek],
                    '123_4_p_to_a' : [type_rack, ps_cybio]}
        elif case_name == cls.CASE_ASSOCIATION_SEVERAL_CONC:
            return {'123_1_p_buffer' : [type_dil, ps_cybio],
                    '123_2_a_buffer' : [type_dil, ps_biomek],
                    '123_4_p_to_a' : [type_rack, ps_cybio],
                    '123_5_a_to_a' : [type_rack, ps_cybio]}
        elif case_name == cls.CASE_LIBRARY_SIMPLE:
            return {'123_2_a_buffer' : [type_dil, ps_biomek]}
        elif case_name == cls.CASE_LIBRARY_2_ALIQUOTS:
            return {'123_2_a_buffer' : [type_dil, ps_biomek]}
        raise NotImplementedError('The value for this case is missing.')

    @classmethod
    def get_job_worklist_data(cls, case_name):
        type_dil = TRANSFER_TYPES.SAMPLE_DILUTION
        type_trans = TRANSFER_TYPES.SAMPLE_TRANSFER
        ps_biomek = get_pipetting_specs_biomek()
        #: worklist label - type, pipetting specs name
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
            return {'123_1_jp_buffer' : [type_dil, ps_biomek],
                    '123_4_jp_to_a' : [type_trans, ps_biomek]}
        elif case_name == cls.CASE_ASSOCIATION_2_ALIQUOTS:
            return dict()
        elif case_name == cls.CASE_ASSOCIATION_JOB_LAST:
            return {'123_3_jp_buffer' : [type_dil, ps_biomek],
                    '123_5_jp_to_a' : [type_trans, ps_biomek],
                    '123_6_a_to_a' : [type_trans, ps_biomek]}
        elif case_name == cls.CASE_ASSOCIATION_SEVERAL_CONC:
            return {'123_3_jp_buffer' : [type_dil, ps_biomek],
                    '123_6_jp_to_a' : [type_trans, ps_biomek],
                    '123_7_a_to_a' : [type_trans, ps_biomek]}
        elif case_name == cls.CASE_LIBRARY_SIMPLE:
            return {'123_1_jp_buffer' : [type_dil, ps_biomek],
                    '123_3_jp_to_a' : [type_trans, ps_biomek]}
        elif case_name == cls.CASE_LIBRARY_2_ALIQUOTS:
            return {'123_1_jp_buffer' : [type_dil, ps_biomek],
                    '123_3_jp_to_a' : [type_trans, ps_biomek]}
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
                return dict(d1=7.3, d2=248, d3=248, d4=248, f2=2)
            elif worklist_label == '123_2_a_buffer':
                return dict(b3=10, b4=16)
            elif worklist_label == '123_3_p_to_p':
                return  dict(d2=[2, 'd1'], f2=[48, 'f1'])
            elif worklist_label == '123_4_p_to_p':
                return  dict(d3=[2, 'd2'])
            elif worklist_label == '123_5_p_to_p':
                return dict(d4=[2, 'd3'])
            elif worklist_label == '123_6_p_to_a':
                return dict(d3=[3, 'd4'], d4=[3, 'd4'],
                            f2=[3, 'f1'], f3=[3, 'f2'])
            elif worklist_label == '123_7_a_to_a':
                return dict(b3=[10, 'b2'], b4=[4, 'b2'])
        elif case_name == cls.CASE_ASSOCIATION_DIRECT:
            if worklist_label == '123_1_a_buffer':
                return dict(e2=2, e3=2)
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
                return dict(c1=99, c2=99)
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
                return dict(b3=5, b5=5, b7=5, c3=5, c5=5, c7=5,
                            d3=14, d5=14, d7=14, f3=13, f5=13, f7=13,
                            g3=5, g5=5, g7=5, h3=14, h5=14, h7=14,
                            e3=10, e5=10, e7=10)
            elif worklist_label == '123_3_jp_buffer':
                return dict(f1=65.7, f2=13.6, f3=65.7)
            elif worklist_label == '123_4_p_to_a':
                return {2 : [1, 0, 4]}
            elif worklist_label == '123_5_a_to_a':
                return {0 : [5, 2, 4]}
            elif worklist_label == '123_6_jp_to_a':
                return dict(f3=[2, 'f1'], f5=[2, 'f2'], f7=[2, 'f3'])
            elif worklist_label == '123_7_a_to_a':
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
    def get_expected_pool_sets(cls, case_name):
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


class LabIsoTestCase(ExperimentMetadataReadingTestCase):

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
            self.library_generator = _TestLibraryGenerator()
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
        converter = LabIsoPrepLayoutConverter(log=TestingLog(),
                                              rack_layout=rack_layout)
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

    def _compare_worklist_details(self, worklist):
        wl_label = worklist.label
        wl_data = LAB_ISO_TEST_CASES.get_worklist_details(self.case, wl_label)
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
        converter = IsoRequestLayoutConverter(log=SilentLog(),
                                      rack_layout=self.iso_request.rack_layout)
        return converter.get_result()


class _TestLibraryGenerator(object):
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
