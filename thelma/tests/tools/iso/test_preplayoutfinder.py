"""
Tests for preparation layout finders.

AAB, Jan 2012
"""

from everest.entities.utils import get_root_aggregate
from pkg_resources import resource_filename # pylint: disable=E0611
from thelma.automation.tools.iso.preplayoutfinder import PrepLayoutFinderOrderOnly
from thelma.automation.tools.iso.preplayoutfinder \
    import PrepLayoutFinder384Optimisation
from thelma.automation.tools.iso.preplayoutfinder \
    import PrepLayoutFinder384Screening
from thelma.automation.tools.iso.preplayoutfinder \
    import PreparationEmptyPositionManager
from thelma.automation.tools.iso.preplayoutfinder import PrepLayoutFinder
from thelma.automation.tools.iso.preplayoutfinder import PrepLayoutFinder96
from thelma.automation.tools.iso.preplayoutfinder import PrepLayoutFinderManual
from thelma.automation.tools.metadata.generation \
    import ExperimentMetadataGenerator
from thelma.automation.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.semiconstants import get_384_rack_shape
from thelma.automation.tools.semiconstants import get_96_rack_shape
from thelma.automation.tools.semiconstants import get_experiment_metadata_type
from thelma.automation.tools.semiconstants import get_positions_for_shape
from thelma.automation.tools.semiconstants import get_rack_position_from_label
from thelma.automation.tools.utils.iso import IsoLayout
from thelma.automation.tools.utils.iso import IsoLayoutConverter
from thelma.automation.tools.utils.iso import IsoParameters
from thelma.automation.tools.utils.iso import IsoPosition
from thelma.interfaces import IMoleculeDesignPool
from thelma.interfaces import IMoleculeType
from thelma.interfaces import ISubproject
from thelma.models.experiment import ExperimentMetadata
from thelma.models.moleculedesign import MoleculeDesignPoolSet
from thelma.models.moleculetype import MOLECULE_TYPE_IDS
from thelma.models.rack import rack_shape_from_rows_columns
from thelma.models.utils import get_user
from thelma.tests.tools.tooltestingutils import TestingLog
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase


class PreparationEmptyPositionManagerTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.manager = None
        self.iso_layout = None
        # value: molecule design pool ID
        self.position_data = dict(A1=205201, B1=205201, C1=205201, D1=205201,
                                  A2=205202, B2=205202, C2=205202, D2=205202,
                                  E2=205202, F2=205202, G2=205202, H2=205202,
                                  A3=205203, B3=205203, D3=205203)

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.manager
        del self.iso_layout
        del self.position_data

    def __continue_setup(self):
        self.__create_iso_layout()
        self.__create_test_object()

    def __create_iso_layout(self):
        self.iso_layout = IsoLayout(shape=get_96_rack_shape())
        for rack_pos in get_positions_for_shape(self.iso_layout.shape):
            label = rack_pos.label
            if self.position_data.has_key(label):
                pool = self._get_pool(self.position_data[label])
                iso_pos = IsoPosition(rack_position=rack_pos,
                                molecule_design_pool=pool,
                                iso_volume=10, iso_concentration=10)
            else:
                iso_pos = IsoPosition.create_empty_position(rack_pos)
            self.iso_layout.add_position(iso_pos)

    def __create_test_object(self):
        self.manager = PreparationEmptyPositionManager(self.iso_layout)

    def test_result_still_space_in_column(self):
        self.__continue_setup()
        first_pos = self.manager.get_position_for_pool(205201)
        h1_pos = get_rack_position_from_label('H1')
        self.assert_equal(first_pos, h1_pos)
        second_pos = self.manager.get_position_for_pool(205201)
        g1_pos = get_rack_position_from_label('G1')
        self.assert_equal(second_pos, g1_pos)

    def test_full_column(self):
        self.__continue_setup()
        first_pos = self.manager.get_position_for_pool(205202)
        h4_pos = get_rack_position_from_label('H4')
        self.assert_equal(first_pos, h4_pos)
        second_pos = self.manager.get_position_for_pool(205202)
        g4_pos = get_rack_position_from_label('G4')
        self.assert_equal(second_pos, g4_pos)

    def test_hole_in_column(self):
        self.__continue_setup()
        first_pos = self.manager.get_position_for_pool(205203)
        h3_pos = get_rack_position_from_label('H3')
        self.assert_equal(first_pos, h3_pos)
        second_pos = self.manager.get_position_for_pool(205203)
        g3_pos = get_rack_position_from_label('G3')
        self.assert_equal(second_pos, g3_pos)

    def test_unknown_pool(self):
        self.__continue_setup()
        self.assert_raises(ValueError, self.manager.get_position_for_pool,
                           205204)

    def test_no_empty_pos_left(self):
        self.__continue_setup()
        no_empty_pos = 96 - len(self.position_data)
        new_positions = []
        i = 0
        while i < no_empty_pos:
            self.assert_true(self.manager.has_empty_positions())
            new_pos = self.manager.get_position_for_pool(205201)
            new_positions.append(new_pos)
            i += 1
        none_pos = self.manager.get_position_for_pool(205201)
        self.assert_is_none(none_pos)
        self.assert_false(self.manager.has_empty_positions())
        for rack_pos in get_positions_for_shape(self.iso_layout.shape):
            label = rack_pos.label
            if not self.position_data.has_key(label):
                self.assert_true(rack_pos in new_positions)

    def test_empty_positions(self):
        self.__continue_setup()
        first_pos = self.manager.get_position_for_pool(205201)
        h1_pos = get_rack_position_from_label('H1')
        self.assert_equal(first_pos, h1_pos)
        self.manager.add_empty_position(h1_pos)
        second_pos = self.manager.get_position_for_pool(205201)
        self.assert_equal(second_pos, h1_pos)


class PrepLayoutFinderTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.log = TestingLog()
        self.experiment_type_id = None
        self.expected_finder_cls = None
        self.use_factory = True
        self.rack_shape = None
        self.iso_layout = None
        self.iso_request = None
        self.molecule_type = get_root_aggregate(IMoleculeType).\
                             get_by_id(MOLECULE_TYPE_IDS.SIRNA)
        self.pool_set = None
        self.number_aliquots = None
        # data tuple: (req_volume, iso_conc, iso_volume, md pool ID,
        # iso position labels)
        self.result_data = dict()
        self.aliquot_dil_factor = 1

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.log
        del self.experiment_type_id
        del self.expected_finder_cls
        del self.rack_shape
        del self.iso_layout
        del self.iso_request
        del self.molecule_type
        del self.pool_set
        del self.number_aliquots
        del self.result_data
        del self.aliquot_dil_factor
        del self.use_factory

    def _create_tool(self):
        #pylint: disable=E1102
        if self.use_factory:
            self.tool = PrepLayoutFinder.create(iso_layout=self.iso_layout,
                                                iso_request=self.iso_request,
                                                log=self.log)
        else:
            self.tool = self.expected_finder_cls(iso_layout=self.iso_layout,
                                                iso_request=self.iso_request,
                                                log=self.log)
        #pylint: enable=E1102

    def _continue_setup(self):
        self.__create_iso_layout()
        self.__create_pool_set()
        self._create_test_iso_request()
        self._create_tool()

    def __create_iso_layout(self):
        self.iso_layout = IsoLayout(shape=self.rack_shape)
        for pos_label, trg_data in self.result_data.iteritems():
            iso_conc = trg_data[1]
            iso_volume = trg_data[2]
            pool_id = trg_data[3]
            pool = self._get_pool(pool_id)
            if len(trg_data) > 5:
                labels = trg_data[5]
                for label in labels:
                    rack_pos = get_rack_position_from_label(label)
                    iso_pos = IsoPosition(rack_position=rack_pos,
                            molecule_design_pool=pool, iso_volume=iso_volume,
                            iso_concentration=iso_conc)
                    self.iso_layout.add_position(iso_pos)
            else:
                rack_pos = get_rack_position_from_label(pos_label)
                iso_pos = IsoPosition(rack_position=rack_pos,
                            molecule_design_pool=pool, iso_volume=iso_volume,
                            iso_concentration=iso_conc)
                self.iso_layout.add_position(iso_pos)

    def __create_pool_set(self):
        floating_pools = set()
        pools = set()
        for data_tuple in self.result_data.values():
            pool_id = data_tuple[3]
            if not data_tuple[4] == IsoParameters.FLOATING_TYPE_VALUE: continue
            if pool_id in floating_pools: continue
            pool_id = len(floating_pools) + 205204
            md_pool = self._get_pool(pool_id)
            pools.add(md_pool)
            floating_pools.add(pool_id)
        self.pool_set = MoleculeDesignPoolSet(molecule_type=self.molecule_type,
                                              molecule_design_pools=pools)

    def _create_test_iso_request(self):
        self.iso_request = self._create_iso_request(
                                number_aliquots=self.number_aliquots)
        em_type = get_experiment_metadata_type(self.experiment_type_id)
        ExperimentMetadata(label='Test Em',
                           subproject=self._get_entity(ISubproject),
                           iso_request=self.iso_request,
                           number_replicates=3,
                           experiment_metadata_type=em_type,
                           molecule_design_pool_set=self.pool_set,
                           ticket_number=123)

    def _check_result(self, expected_number_pps=None):
        self.assert_true(isinstance(self.tool, self.expected_finder_cls))
        prep_layout = self.tool.get_result()
        self.assert_is_not_none(prep_layout)
        if expected_number_pps is None:
            expected_number_pps = len(self.result_data)
        self.assert_equal(len(prep_layout), expected_number_pps)
        for rack_pos, prep_pos in prep_layout.iterpositions():
            pos_label = rack_pos.label
            self.assert_true(self.result_data.has_key(pos_label))
            data_tuple = self.result_data[pos_label]
            req_vol = data_tuple[0]
            iso_conc = data_tuple[1]
            self.assert_equal(prep_pos.required_volume, req_vol)
            if iso_conc is None:
                expected_conc = None
            else:
                expected_conc = iso_conc * self.aliquot_dil_factor
            self.assert_equal(prep_pos.molecule_design_pool_id, data_tuple[3])
            self.assert_equal(prep_pos.prep_concentration, expected_conc)
            self.assert_is_none(prep_pos.stock_tube_barcode)
            self.assert_is_none(prep_pos.stock_rack_barcode)
            self._check_target_iso_positions(data_tuple, prep_pos, pos_label)

#            if len(data_tuple) > 5:
#                position_labels = data_tuple[5]
#                if iso_vol == 0:
#                    self.assert_equal(len(prep_pos.transfer_targets), 0)
#                for tt in prep_pos.transfer_targets:
#                    self.assert_true(tt.position_label in position_labels)
#                    expected_vol = iso_vol / self.aliquot_dil_factor
#                    self.assert_equal(float(tt.transfer_volume), expected_vol)
#                if not pool_id is None:
#                    self.assert_equal(prep_pos.molecule_design_pool_id, pool_id)
#                    exp_pos_type = data_tuple[4]
#                    self.assert_equal(prep_pos.position_type, exp_pos_type)
#            else:
#                if self.experiment_type_id == EXPERIMENT_SCENARIOS.MANUAL or \
#                     self.experiment_type_id == EXPERIMENT_SCENARIOS.ORDER_ONLY:
#                    self.assert_equal(len(prep_pos.transfer_targets), 0)
#                else:
#                    self.assert_equal(len(prep_pos.transfer_targets), 1)
#                    tt = prep_pos.transfer_targets[0]
#                    self.assert_equal(tt.position_label, label)
#                    self.assert_equal(tt.transfer_volume, iso_vol)
#                self.assert_equal(prep_pos.molecule_design_pool_id, pool_id)

    def _check_target_iso_positions(self, data_tuple, prep_pos, pos_label):
        iso_vol = data_tuple[2]
        pool_id = data_tuple[3]
        if len(data_tuple) > 5:
            position_labels = data_tuple[5]
            if iso_vol == 0:
                self.assert_equal(len(prep_pos.transfer_targets), 0)
            for tt in prep_pos.transfer_targets:
                self.assert_true(tt.position_label in position_labels)
                expected_vol = iso_vol / self.aliquot_dil_factor
                self.assert_equal(float(tt.transfer_volume), expected_vol)
            if not pool_id is None:
                exp_pos_type = data_tuple[4]
                self.assert_equal(prep_pos.position_type, exp_pos_type)
        else:
            self.assert_equal(len(prep_pos.transfer_targets), 1)
            tt = prep_pos.transfer_targets[0]
            self.assert_equal(tt.position_label, pos_label)
            self.assert_equal(tt.transfer_volume, iso_vol)

    def _test_invalid_iso_layout(self):
        self._continue_setup()
        self.iso_layout = self.iso_layout.create_rack_layout()
        self._test_and_expect_errors('ISO layout must be a IsoLayout object')

    def _test_invalid_iso_request(self):
        self._continue_setup()
        self.iso_request = self.molecule_type
        kw = dict(iso_layout=self.iso_layout, iso_request=self.iso_request,
                  log=self.log)
        self.assert_is_none(PrepLayoutFinder.create(**kw))
        self.use_factory = False
        self._test_and_expect_errors('ISO request must be a IsoRequest')

    def _test_invalid_molecule_design_pool(self, pos_label):
        self._continue_setup()
        rack_pos = get_rack_position_from_label(pos_label)
        iso_pos = self.iso_layout.get_working_position(rack_pos)
        iso_pos.molecule_design_pool = 3
        self._test_and_expect_errors('Unexpected molecule design type')

    def _test_missing_pool_set(self):
        self._continue_setup()
        empty_set = MoleculeDesignPoolSet(molecule_type=self.molecule_type)
        self.iso_request.experiment_metadata.molecule_design_pool_set = \
                                                        empty_set
        self._test_and_expect_errors('There are no molecule design pools in ' \
                        'the molecule design pool set although there are ' \
                        'floating positions!')

    def _test_iso_concentration_over_stock_concentration(self):
        self.result_data = dict(A1=(20.4, 60000, 10, 205230, 'fixed'),
                                A2=(20.4, 60000, 10, 'md_001', 'floating'))
        self._continue_setup()
        self._test_and_expect_errors('Some ISO concentrations exceed the ' \
                                     'stock concentration')

    def _test_unsupported_rack_shape(self, rack_shape):
        self.use_factory = False
        self.rack_shape = rack_shape
        self._continue_setup()
        self._test_and_expect_errors('Unsupported rack shape')
        rack_shape_4 = rack_shape_from_rows_columns(1, 4)
        self.iso_layout.shape = rack_shape_4
        kw = dict(iso_layout=self.iso_layout, iso_request=self.iso_request,
                  log=self.log)
        self.assert_is_none(PrepLayoutFinder.create(**kw))


class PrepLayoutFinder96TestCase(PrepLayoutFinderTestCase):

    def set_up(self):
        PrepLayoutFinderTestCase.set_up(self)
        self.experiment_type_id = EXPERIMENT_SCENARIOS.OPTIMISATION
        self.expected_finder_cls = PrepLayoutFinder96
        # additional setup data
        self.rack_shape = get_96_rack_shape()
        self.number_aliquots = 1
        # data tuple: (req_volume, prep_conc, iso_volume, molecule design ID,
        # iso position labels)
        self.result_data = dict(
            B2=(70.5, 10000, 6.3, 205200, 'fixed', ('B2', 'B3', 'C2', 'C3')),
            B4=(66.2, 5000, 13.8, 205200, 'fixed', ('B4', 'B5', 'C4', 'C5')),
            B8=(81.0, 5000, 17.5, 205201, 'fixed', ('B8', 'B9', 'C8', 'C9')),
            E2=(41.5, 10000, 6.3, 'md_001', 'floating', ('E2', 'E3')),
            E4=(37.6, 5000, 13.8, 'md_001', 'floating', ('E4', 'E5')),
            E8=(45.6, 560, 17.5, 'md_002', 'floating', ('E8', 'E9')),
            B11=(30, None, 10, 'mock', 'mock', ('B11', 'E11')),
            H8=(16, 5000, 0, 'md_002', 'floating', []))

    def test_result(self):
        # including a additional dilution position for E8 (stock dilution)
        self._continue_setup()
        self._check_result()

    def test_additional_dilution_position_in_series(self):
        self.result_data = dict(
                        A1=(20, 1000, 10, 205202, 'fixed', ['A1']),
                        B1=(22, 50000, 10, 205202, 'fixed', ['B1']),
                        A3=(20, 1000, 10, 205203, 'fixed', ['A3']),
                        B3=(22, 50000, 10, 205203, 'fixed', ['B3']))
        self._continue_setup()
        self.result_data['H1'] = (20, 5000, 0, 205202, 'fixed', [])
        self.result_data['H3'] = (20, 5000, 0, 205203, 'fixed', [])
        self._check_result()

    def test_not_enough_empty_positions(self):
        self._continue_setup()
        ed_file = 'thelma:tests/tools/iso/prepfinder/not_enough_empty_pos.xls'
        file_name = ed_file.split(':')
        f = resource_filename(*file_name) # pylint: disable=W0142
        stream = open(f, 'rb')
        source = stream.read()
        stream.close()
        em_generator = ExperimentMetadataGenerator.create(stream=source,
                    experiment_metadata=self.iso_request.experiment_metadata,
                    requester=get_user('it'))
        em = em_generator.get_result()
        converter = IsoLayoutConverter(rack_layout=em.iso_request.iso_layout,
                                       log=self.log)
        self.iso_layout = converter.get_result()
        self.iso_request = em.iso_request
        self._test_and_expect_errors('There are no empty positions left in ' \
                                     'the preparation layout!')

    def test_buffer_volume_correction(self):
        # data tuple: (req_volume, iso_conc, iso_volume, molecule design ID,
        # iso position labels)
        self.result_data = dict(A1=(27, 45000, 1, 205202, 'fixed', ['A1']),
                                A2=(18, 40000, 1, 205202, 'fixed', ['A2']),
                                B1=(20, 45000, 1, 205204, 'fixed', ['B1']))
        self._continue_setup()
        self._check_result()

    def test_invalid_iso_layout(self):
        self._test_invalid_iso_layout()

    def test_invalid_iso_request(self):
        self._test_invalid_iso_request()

    def test_invalid_molecule_design(self):
        self._test_invalid_molecule_design_pool('B2')

    def test_missing_pool_set(self):
        self._test_missing_pool_set()

    def test_iso_concentration_over_stock_concentration(self):
        self._test_iso_concentration_over_stock_concentration()

    def test_different_stock_concentration(self):
        self.result_data = dict(A1=[20.4, 9800, 10, 205202, 'fixed', ['A1']],
                                A2=[100.0, 9800, 10, 330001, 'fixed', ['A2']])
        self._continue_setup()
        self._check_result()

    def test_unsupported_rack_shape(self):
        self._test_unsupported_rack_shape(get_384_rack_shape())


class PrepLayoutFinder384OptimisationTestCase(PrepLayoutFinderTestCase):

    def set_up(self):
        PrepLayoutFinderTestCase.set_up(self)
        self.experiment_type_id = EXPERIMENT_SCENARIOS.OPTIMISATION
        self.expected_finder_cls = PrepLayoutFinder384Optimisation
        self.rack_shape = get_384_rack_shape()
        self.number_aliquots = 2
        # data tuple: (req_volume, iso_conc, iso_volume, molecule design ID)
        self.result_data = dict(
                A1=(137.5, 10000, 10, 205200, 'fixed', ['A1', 'A3', 'A5', 'A7']),
                A2=(91, 5000, 10, 205200, 'fixed', ['A2', 'A4', 'A6', 'A8']),
                B1=(197.5, 10000, 15, 205201, 'fixed', ['B1', 'B3', 'B5', 'B7']),
                B2=(131, 5000, 15, 205201, 'fixed', ['B2', 'B4', 'B6', 'B8']),
                C1=(75, 10000, 10, 205202, 'fixed', ['C1', 'C3']),
                C2=(50, 5000, 10, 205202, 'fixed', ['C2', 'C4']),
                D1=(40, 10000, 15, 'md_001', 'floating', ['D1']),
                E1=(30, None, 10, 'mock', 'mock'))

    def test_result(self):
        self._continue_setup()
        self._check_result()

    def test_additional_dilution_position(self):
        self.number_aliquots = 2
        # results are still different from the 96-well case, because
        # there are different minimum volumes.
        self.result_data = dict(
        # data tuple: (req_volume, iso_conc, iso_volume, molecule design ID)
                        A1=(30, 1000, 10, 205200, 'fixed', ['A1']),
                        B1=(32, 50000, 10, 205200, 'fixed', ['B1']),
                        A3=(30, 1000, 10, 205201, 'fixed', ['A3']),
                        B3=(32, 50000, 10, 205201, 'fixed', ['B3']))
        self._continue_setup()
        self.result_data['P1'] = (20, 5000, 0, 205200, 'fixed', [])
        self.result_data['P3'] = (20, 5000, 0, 205201, 'fixed', [])
        self._check_result()

    def test_different_stock_concentration(self):
        self.result_data = dict(A1=(20, 9950, 5, 330001, 'fixed'))
        self._continue_setup()
        self._check_result()

    def test_invalid_iso_layout(self):
        self._test_invalid_iso_layout()

    def test_invalid_iso_request(self):
        self._test_invalid_iso_request()

    def test_invalid_pool(self):
        self._test_invalid_molecule_design_pool('A1')

    def test_iso_concentration_over_stock_concentration(self):
        self._test_iso_concentration_over_stock_concentration()

    def test_unsupported_rack_shape(self):
        self._test_unsupported_rack_shape(get_96_rack_shape())


class PrepLayoutFinder384ScreeningTestCase(PrepLayoutFinderTestCase):

    def set_up(self):
        PrepLayoutFinderTestCase.set_up(self)
        self.experiment_type_id = EXPERIMENT_SCENARIOS.SCREENING
        self.expected_finder_cls = PrepLayoutFinder384Screening
        self.rack_shape = get_384_rack_shape()
        self.number_aliquots = 2
        # data tuple: (req_volume, iso_conc, iso_volume, md pool ID)
        self.result_data = dict(
                    # first quadrant
                    A1=(45, 10000, 10, 'md_001', 'floating', ['A1']),
                    A2=(30, 5000, 10, 'md_001', 'floating', ['A2']),
                    B1=(45, 10000, 10, 205200, 'fixed', ['B1']),
                    B2=(30, 5000, 10, 205200, 'fixed', ['B2']),
                    # second quadrant
                    A3=(45, 10000, 10, 'md_002', 'floating', ['A3']),
                    A4=(30, 5000, 10, 'md_002', 'floating', ['A4']),
                    B3=(45, 10000, 10, 205200, 'fixed', ['B3']),
                    B4=(30, 5000, 10, 205200, 'fixed', ['B4']),
                    # third quadrant
                    C1=(45, 10000, 10, 'md_003', 'floating', ['C1']),
                    C2=(30, 5000, 10, 'md_003', 'floating', ['C2']),
                    # fourth quadrant
                    C3=(30, None, 10, 'mock', 'mock', ['C3']),
                    C4=(30, None, 10, 'mock', 'mock', ['C4']))

    def test_result(self):
        self._continue_setup()
        exp_number = len(self.result_data) - 2 # 2 mocks
        self._check_result(exp_number)

    def test_result_one_concentration(self):
        # data tuple: (req_volume, iso_conc, iso_volume, md pool ID)
        self.result_data = dict(
                    # first quadrant
                    A1=(30, 10000, 10, 'md_001', 'floating', ['A1']),
                    B1=(30, 10000, 10, 205200, 'fixed', ['B1']),
                    # second quadrant
                    A3=(30, 10000, 10, 'md_002', 'floating', ['A3']),
                    B3=(30, 10000, 10, 205200, 'fixed', ['B3']),
                    # third quadrant
                    C1=(30, 10000, 10, 'md_003', 'floating', ['C1']),
                    # fourth quadrant
                    C3=(30, None, 10, 'mock', 'mock', ['C3']),
                    C4=(30, None, 10, 'mock', 'mock', ['C4']))
        self._continue_setup()
        exp_number = len(self.result_data) - 2 # 2 mocks
        self._check_result(exp_number)

    def test_different_stock_concentration(self):
        self.result_data = dict(A1=(30, 25000, 10, 'md_001', 'floating'))
        self._continue_setup()
        self._check_result()
        mihi = self._get_entity(IMoleculeDesignPool, '330001')
        pool_set = MoleculeDesignPoolSet(molecule_type=mihi.molecule_type,
                                         molecule_design_pools=set([mihi]))
        self.iso_request.experiment_metadata.molecule_design_pool_set = \
                                                            pool_set
        self._test_and_expect_errors('Some ISO concentrations exceed the ' \
                    'stock concentration for this experiment (10000 nM)')

    def test_aliquot_dilution_factor(self):
        # data tuple: (req_volume, iso_conc, iso_volume, md pool ID)
        self.result_data = dict(
                    # first quadrant
                    A1=(100, 100, 10, 'md_001', 'floating', ['A1']),
                    A2=(14, 50, 10, 'md_001', 'floating', ['A2']),
                    B1=(100, 100, 10, 205200, 'fixed', ['B1']),
                    B2=(14, 50, 10, 205200, 'fixed', ['B2']),
                    # second quadrant
                    A3=(100, 100, 10, 'md_002', 'floating', ['A3']),
                    A4=(14, 50, 10, 'md_002', 'floating', ['A4']),
                    B3=(100, 100, 10, 205200, 'fixed', ['B3']),
                    B4=(14, 50, 10, 205200, 'fixed', ['B4']),
                    # third quadrant
                    C1=(100, 100, 10, 'md_003', 'floating', ['C1']),
                    C2=(14, 50, 10, 'md_003', 'floating', ['C2']),
                    # fourth quadrant
                    C3=(14, None, 10, 'mock', 'mock', ['C3']),
                    C4=(14, None, 10, 'mock', 'mock', ['C4']))
        self._continue_setup()
        self.aliquot_dil_factor = 5
        exp_number_pps = len(self.result_data) - 2 # 2 mock
        self._check_result(exp_number_pps)

    def test_different_iso_volumes(self):
        self.result_data['B3'] = (45, 10000, 15, 205200, 'fixed', ['B3'])
        self._continue_setup()
        self._test_and_expect_errors('There is more than one ISO volume ' \
                                     'in this layout')

    def test_inconsistent_sectors(self):
        self.result_data['E1'] = (45, 10000, 10, 'md_008', 'floating', ['E1'])
        self._continue_setup()
        self._test_and_expect_errors('Error when trying to associate rack ' \
                                     'sectors by molecule design')

    def test_invalid_iso_layout(self):
        self._test_invalid_iso_layout()

    def test_invalid_iso_request(self):
        self._test_invalid_iso_request()

    def test_invalid_molecule_design_pool(self):
        self._test_invalid_molecule_design_pool('B1')

    def test_missing_pool_set(self):
        self._test_missing_pool_set()

    def test_iso_concentration_over_stock_concentration(self):
        self._test_iso_concentration_over_stock_concentration()

    def test_unsupported_rack_shape(self):
        self._test_unsupported_rack_shape(get_96_rack_shape())

    def test_iso_concentration_too_low(self):
        # data tuple: (req_volume, iso_conc, iso_volume, molecule design ID)
        self.result_data = dict(
                    # first quadrant
                    A1=(100, 0.1, 10, 'md_001', 'floating', ['A1']),
                    A2=(14, 0.05, 10, 'md_001', 'floating', ['A2']))
        self._continue_setup()
        self._test_and_expect_errors('The ISO concentration is to low to be ' \
                        'reached in 2 steps! The allowed maximum dilution ' \
                        'factor per step')


class PrepLayoutFinderManualTestCase(PrepLayoutFinderTestCase):

    def set_up(self):
        PrepLayoutFinderTestCase.set_up(self)
        self.experiment_type_id = EXPERIMENT_SCENARIOS.MANUAL
        self.expected_finder_cls = PrepLayoutFinderManual
        self.rack_shape = get_96_rack_shape()
        self.number_aliquots = 1
        # data tuple: (req_volume, prep_conc, iso_volume, molecule design ID,
        # iso position labels)
        self.result_data = dict(
                    A1=(1, 50000, 1, 205201, 'fixed'),
                    A2=(5, 40000, 5, 205202, 'fixed'),
                    A3=(2.5, 30000, 2.5, 205203, 'fixed'))

    def _check_target_iso_positions(self, data_tuple, prep_pos, pos_label):
        self.assert_equal(len(prep_pos.transfer_targets), 0)

    def test_result_96(self):
        self._continue_setup()
        self._check_result()

    def test_result_384(self):
        self.rack_shape = get_384_rack_shape()
        self._continue_setup()
        self._check_result()

    def test_invalid_iso_layout(self):
        self._test_invalid_iso_layout()


class PrepLayoutFinderOrderOnlyTestCase(PrepLayoutFinderTestCase):

    def set_up(self):
        PrepLayoutFinderTestCase.set_up(self)
        self.experiment_type_id = EXPERIMENT_SCENARIOS.ORDER_ONLY
        self.expected_finder_cls = PrepLayoutFinderOrderOnly
        self.rack_shape = get_96_rack_shape()
        self.number_aliquots = 1
        # data tuple: (req_volume, prep_conc, iso_volume, molecule design ID,
        # iso position labels)
        self.result_data = dict(
                B2=[1, 50000, 1, 205201, 'fixed'],
                B4=[1, 10000, 1, 330001, 'fixed'],
                B6=[1, 5000000, 1, 333803, 'fixed'],
                B8=[1, 10000, 1, 1056000, 'fixed'],
                B10=[1, 50000, 1, 180202, 'fixed'])

    def _check_target_iso_positions(self, data_tuple, prep_pos, pos_label):
        self.assert_equal(len(prep_pos.transfer_targets), 0)

    def test_result_96(self):
        self._continue_setup()
        self._check_result()

    def test_result_384(self):
        self.rack_shape = get_384_rack_shape()
        self._continue_setup()
        self._check_result()

    def test_invalid_iso_layout(self):
        self._test_invalid_iso_layout()

    def test_invalid_concentration(self):
        self.result_data['B8'][1] = 5000
        self._continue_setup()
        self._test_and_expect_errors('For order only scenarios, molecule ' \
                 'design pools can only be ordered in stock concentration. ' \
                 'Some ordered concentrations in this layout are different: ' \
                 '1056000 (B8, expected: 5000, found: 10000)')
