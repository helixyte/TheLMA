"""
Tests the liquid transfer plan tools for the ISO processing.

AAB, Jan 2012
"""
from thelma.automation.tools.iso.prep_utils import PrepIsoAssociationData
from thelma.automation.tools.iso.prep_utils import PrepIsoLayout
from thelma.automation.tools.iso.prep_utils import PrepIsoPosition
from thelma.automation.tools.iso.processingworklist \
    import IsoAliquotBufferWorklistGenerator
from thelma.automation.tools.iso.processingworklist \
    import IsoBufferWorklistGenerator
from thelma.automation.tools.iso.processingworklist \
    import IsoBufferWorklistGeneratorOptimisation
from thelma.automation.tools.iso.processingworklist \
    import IsoBufferWorklistGeneratorScreening
from thelma.automation.tools.iso.processingworklist \
    import IsoDilutionWorklistsGeneratorOptimisation
from thelma.automation.tools.iso.processingworklist \
    import IsoDilutionWorklistsGeneratorScreening
from thelma.automation.tools.iso.processingworklist \
    import IsoTransferWorklistGeneratorOptimisation
from thelma.automation.tools.iso.processingworklist \
    import IsoTransferWorklistGeneratorScreening
from thelma.automation.tools.iso.processingworklist \
    import IsoDilutionWorklistsGenerator
from thelma.automation.tools.iso.processingworklist \
    import IsoTransferWorklistGenerator
from thelma.automation.tools.iso.processingworklist \
    import IsoWorklistSeriesGenerator
from thelma.automation.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.semiconstants import get_384_rack_shape
from thelma.automation.tools.semiconstants import get_96_rack_shape
from thelma.automation.tools.semiconstants import get_experiment_metadata_type
from thelma.automation.tools.semiconstants import get_rack_position_from_label
from thelma.automation.tools.utils.base import FIXED_POSITION_TYPE
from thelma.automation.tools.utils.base import FLOATING_POSITION_TYPE
from thelma.automation.tools.utils.base import MOCK_POSITION_TYPE
from thelma.automation.tools.utils.base import TransferTarget
from thelma.automation.tools.utils.iso import IsoLayout
from thelma.automation.tools.utils.iso import IsoPosition
from thelma.automation.tools.worklists.base import VOLUME_CONVERSION_FACTOR
from thelma.interfaces import ISubproject
from thelma.models.experiment import ExperimentMetadata
from thelma.models.iso import IsoRequest
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.moleculedesign import MoleculeDesignPoolSet
from thelma.models.racklayout import RackLayout
from thelma.models.utils import get_user
from thelma.tests.tools.tooltestingutils import TestingLog
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase


class IsoWorklistGeneratorTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.log = TestingLog()
        self.shape = None
        self.user = get_user('it')
        self.prep_layout = None
        self.experiment_type_id = EXPERIMENT_SCENARIOS.OPTIMISATION
        self.iso_request = None
        self.iso_request_name = 'iso_request_55'
        self.pool_set = None
        self.iso_volume = 10
        self.iso_layout = None
        self.stock_concentration = 50000
        self.aliquot_buffer_volume = 0
        # key: rack position, value: (pool ID, prep conc, parent well, req_vol,
        #: transfer target positions, iso conc (if different from prep conc))
        # estimated iso volume: 10 ul
        self.position_data = None
        self.transfer_volumes = None
        #: key: rack_pos, value: dilution volume
        self.annealing_result_data = None

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.log
        del self.shape
        del self.prep_layout
        del self.experiment_type_id
        del self.iso_request
        del self.iso_request_name
        del self.pool_set
        del self.iso_volume
        del self.iso_layout
        del self.stock_concentration
        del self.aliquot_buffer_volume
        del self.position_data
        del self.transfer_volumes
        del self.annealing_result_data

    def _continue_setup(self):
        self._create_layouts()
        self._associate_sectors()
        self._create_test_pool_set()
        self._create_test_iso_request()
        self._create_tool()

    def _create_layouts(self):
        self.prep_layout = PrepIsoLayout(shape=self.shape)
        self.iso_layout = IsoLayout(shape=self.shape)
        for pos_label, data_tuple in self.position_data.iteritems():
            rack_pos = get_rack_position_from_label(pos_label)
            pool_id = data_tuple[0]
            prep_conc = data_tuple[1]
            parent_well = data_tuple[2]
            if not parent_well is None:
                parent_well = get_rack_position_from_label(parent_well)
            req_volume = data_tuple[3]
            transfer_targets = []
            for target_label in data_tuple[4]:
                transfer_volume = self.iso_volume - self.aliquot_buffer_volume
                if not self.transfer_volumes is None:
                    transfer_volume = self.transfer_volumes[target_label]
                tt = TransferTarget(rack_position=target_label,
                        transfer_volume=transfer_volume)
                transfer_targets.append(tt)
            pool = self._get_pool(pool_id)
            if isinstance(pool_id, int):
                pos_type = FIXED_POSITION_TYPE
            elif pool_id == MOCK_POSITION_TYPE:
                pos_type = MOCK_POSITION_TYPE
            else:
                pos_type = FLOATING_POSITION_TYPE
            prep_pos = PrepIsoPosition(rack_position=rack_pos,
                                       molecule_design_pool=pool,
                                       position_type=pos_type,
                                       prep_concentration=prep_conc,
                                       required_volume=req_volume,
                                       transfer_targets=transfer_targets,
                                       parent_well=parent_well)
            self.prep_layout.add_position(prep_pos)
            if len(data_tuple) > 5:
                iso_conc = data_tuple[5]
            else:
                iso_conc = prep_conc
            iso_pos = IsoPosition(rack_position=rack_pos,
                                  molecule_design_pool=pool,
                                  iso_concentration=iso_conc,
                                  iso_volume=self.iso_volume)
            self.iso_layout.add_position(iso_pos)
        self.prep_layout.set_floating_stock_concentration(
                                                    self.stock_concentration)

    def _create_test_pool_set(self):
        pass

    def _associate_sectors(self):
        pass

    def _create_test_iso_request(self):
        self.iso_request = IsoRequest(requester=self.user,
                        iso_layout=self.iso_layout.create_rack_layout(),
                        plate_set_label=self.iso_request_name)
        em_type = get_experiment_metadata_type(self.experiment_type_id)
        ExperimentMetadata(label='iso_worklist_generation_test',
                           subproject=self._get_entity(ISubproject),
                           iso_request=self.iso_request,
                           number_replicates=2,
                           experiment_metadata_type=em_type,
                           molecule_design_pool_set=self.pool_set)

    def _test_annealing_worklist(self, buffer_worklist=None):
        if buffer_worklist is None:
            self._continue_setup()
            buffer_worklist = self.tool.get_result()
        self.assert_is_not_none(buffer_worklist)
        label = '%s%s' % (self.iso_request_name,
                          IsoBufferWorklistGenerator.WORKLIST_SUFFIX)
        self.assert_equal(buffer_worklist.label, label)
        self.assert_equal(len(buffer_worklist.executed_worklists), 0)
        self.assert_equal(len(buffer_worklist.planned_transfers),
                          len(self.annealing_result_data))
        for pcd in buffer_worklist.planned_transfers:
            self.assert_equal(pcd.type, TRANSFER_TYPES.CONTAINER_DILUTION)
            expected_vol = self.annealing_result_data[pcd.target_position.label]
            pcd_volume = pcd.volume * VOLUME_CONVERSION_FACTOR
            self.assert_equal(expected_vol, pcd_volume)
            self.assert_equal(pcd.diluent_info,
                              IsoBufferWorklistGenerator.DILUENT_INFO)

    def _test_invalid_iso_request_name(self):
        self.iso_request_name = 5
        self._continue_setup()
        self._test_and_expect_errors('ISO request name must be a ' \
                                     'basestring object')

    def _test_invalid_iso_request(self):
        self._continue_setup()
        self.iso_request = 5
        self._test_and_expect_errors('The ISO request must be a IsoRequest ' \
                                     'object')

    def _test_invalid_prep_layout(self):
        self._continue_setup()
        self.prep_layout = self.prep_layout.create_rack_layout()
        self._test_and_expect_errors('preparation plate layout must be a ' \
                                     'PrepIsoLayout object')


class IsoWorklistGeneratorOptiTestCase(IsoWorklistGeneratorTestCase):

    def set_up(self):
        IsoWorklistGeneratorTestCase.set_up(self)
        self.shape = get_96_rack_shape()
        self.experiment_type_id = EXPERIMENT_SCENARIOS.OPTIMISATION
        # key: rack position, value: (md ID, prep conc, parent well, req_vol,
        #: transfer target positions, iso conc (if different from prep conc))
        # estimated iso volume: 10 ul
        self.position_data = dict(A1=('md_1', 10000, None, 20,
                                      ['A1', 'A2', 'A3', 'A4']),
                                  B1=('md_2', 10000, None, 30, ['B1', 'B3']),
                                  B2=('md_2', 5000, 'B1', 20, ['B2', 'B4']),
                                  C1=('md_3', 10000, None, 36, ['C1']),
                                  C2=('md_3', 5000, 'C1', 32, ['C2']),
                                  C3=('md_3', 2000, 'C2', 30, ['C3']),
                                  C4=('md_3', 1000, 'C3', 20, ['C4']),
                                  D1=('mock', None, None, 20, ['D6']))
        #: key: rack_pos, value: dilution volume
        self.annealing_result_data = dict(A1=16, B1=24, B2=10,
                                          C1=28.8, C2=16, C3=18, C4=10,
                                          D1=20)
        #: key: rack_pos, value: datatuple (target_pos label, transfer volume)
        self.series_result_data = {1: dict(B1=('B2', 10), C1=('C2', 16)),
                                   2: dict(C2=('C3', 12)),
                                   3: dict(C3=('C4', 10))}

    def tear_down(self):
        IsoWorklistGeneratorTestCase.tear_down(self)
        del self.series_result_data

    def _test_dilution_series_worklists(self, st_worklists=None):
        modifier = 0
        if st_worklists is None:
            self._continue_setup()
            st_worklists = self.tool.get_result()
            modifier = 1
        self.assert_is_not_none(st_worklists)
        self.assert_equal(len(st_worklists), 3)
        for wl_index, st_worklist in st_worklists.iteritems():
            label = '%s%s%s' % (self.iso_request_name,
                       IsoDilutionWorklistsGenerator.BASE_PLAN_NAME,
                       (wl_index + modifier))
            self.assert_equal(st_worklist.label, label)
            result_data = self.series_result_data[wl_index + modifier]
            self.assert_equal(len(st_worklist.executed_worklists), 0)
            self.assert_equal(len(st_worklist.planned_transfers),
                              len(result_data))
            for pct in st_worklist.planned_transfers:
                self.assert_equal(pct.type, TRANSFER_TYPES.CONTAINER_TRANSFER)
                pos_data = result_data[pct.source_position.label]
                target_pos = get_rack_position_from_label(pos_data[0])
                self.assert_equal(target_pos, pct.target_position)
                expected_vol = pos_data[1]
                pct_volume = pct.volume * VOLUME_CONVERSION_FACTOR
                self.assert_equal(expected_vol, pct_volume)

    def _test_transfer_worklist(self, transfer_worklist=None):
        if transfer_worklist is None:
            self._continue_setup()
            transfer_worklist = self.tool.get_result()
        self.assert_is_not_none(transfer_worklist)
        label = '%s%s' % (self.iso_request_name,
                          IsoTransferWorklistGenerator.WORKLIST_SUFFIX)
        self.assert_equal(transfer_worklist.label, label)
        self.assert_equal(len(transfer_worklist.executed_worklists), 0)
        all_trg_pos = []
        for trg_data in self.position_data.values():
            for target_pos in trg_data[4]: all_trg_pos.append(target_pos)
        self.assert_equal(len(transfer_worklist.planned_transfers),
                          len(all_trg_pos))
        for pct in transfer_worklist.planned_transfers:
            self.assert_equal(pct.type, TRANSFER_TYPES.CONTAINER_TRANSFER)
            source_pos = pct.source_position
            prep_pos = self.prep_layout.get_working_position(source_pos)
            target_map = dict()
            for tt in prep_pos.transfer_targets:
                exp_volume = tt.transfer_volume
                target_pos = get_rack_position_from_label(tt.position_label)
                target_map[target_pos] = exp_volume
            self.assert_true(pct.target_position.label in all_trg_pos)
            exp_volume = target_map[pct.target_position]
            pct_volume = pct.volume * VOLUME_CONVERSION_FACTOR
            self.assert_equal(exp_volume, pct_volume)


class IsoBufferWorklistGeneratorOptiTestCase(
                                IsoWorklistGeneratorOptiTestCase):

    def _create_tool(self):
        self.tool = IsoBufferWorklistGeneratorOptimisation(
                                    iso_request=self.iso_request,
                                    preparation_layout=self.prep_layout,
                                    log=self.log)

    def test_result(self):
        self._test_annealing_worklist()

    def test_invalid_iso_request(self):
        self._test_invalid_iso_request()

    def test_invalid_prep_layout(self):
        self._test_invalid_prep_layout()

    def test_min_buffer_volume(self):
        self.iso_volume = 1
        # value: (md ID, iso conc, parent well, req_vol, transfer target
        # positions), estimated iso volume: 1 ul
        self.position_data = dict(A1=('md_1', 40000, None, 11, ['A1']),
                                  A2=('md_1', 30000, 'A1', 11, ['A2']),
                                  B1=('md_2', 40000, None, 11, ['B1']))
        self._continue_setup()
        self._test_and_expect_errors('buffer volume for some wells is too ' \
                                     'small')



class IsoDilutionWorklistGeneratorOptiTestCase(
                                IsoWorklistGeneratorOptiTestCase):

    def _create_tool(self):
        self.tool = IsoDilutionWorklistsGeneratorOptimisation(
                                    iso_request_name=self.iso_request_name,
                                    preparation_layout=self.prep_layout,
                                    log=self.log)

    def test_result(self):
        self._test_dilution_series_worklists()

    def test_only_one_concentration(self):
        new_pos_data = dict()
        new_pos_data['A1'] = self.position_data['A1']
        new_pos_data['B1'] = self.position_data['B1']
        new_pos_data['C1'] = self.position_data['C1']
        self.position_data = new_pos_data
        self._continue_setup()
        dil_worklists = self.tool.get_result()
        self.assert_is_not_none(dil_worklists)
        self.assert_equal(len(dil_worklists), 0)

    def test_invalid_iso_request_name(self):
        self._test_invalid_iso_request_name()

    def test_invalid_prep_layout(self):
        self._test_invalid_prep_layout()


class IsoTransferWorklistGeneratorTestCase(
                                IsoWorklistGeneratorOptiTestCase):

    def set_up(self):
        IsoWorklistGeneratorOptiTestCase.set_up(self)
        self.transfer_volumes = dict(A1=10, A2=10, A3=20, A4=40,
                                     B1=10, B2=10, B3=20, B4=20,
                                     C1=10, C2=10, C3=20, C4=20,
                                     D6=10)

    def _create_tool(self):
        self.tool = IsoTransferWorklistGeneratorOptimisation(
                            iso_request_name=self.iso_request_name,
                            preparation_layout=self.prep_layout,
                            log=self.log)

    def test_result(self):
        self._test_transfer_worklist()

    def test_invalid_iso_request_name(self):
        self._test_invalid_iso_request_name()

    def test_invalid_prep_layout(self):
        self._test_invalid_prep_layout()


class IsoWorklistSeriesGeneratorOptiTestCase(
                                IsoWorklistGeneratorOptiTestCase):

    def _create_tool(self):
        self.tool = IsoWorklistSeriesGenerator(iso_request=self.iso_request,
                                    preparation_layout=self.prep_layout,
                                    log=self.log)

    def test_result(self):
        self._continue_setup()
        series = self.tool.get_result()
        self.assert_is_not_none(series)
        self.assert_equal(len(series), 5)
        buffer_worklist = None
        dil_worklists = dict()
        transfer_worklist = None
        for worklist in series:
            if worklist.index == 0:
                buffer_worklist = worklist
            elif worklist.index == 4:
                transfer_worklist = worklist
            else:
                dil_worklists[worklist.index] = worklist
        self._test_annealing_worklist(buffer_worklist)
        self._test_dilution_series_worklists(dil_worklists)
        self._test_transfer_worklist(transfer_worklist)

    def test_result_384(self):
        self.shape = get_384_rack_shape()
        self._continue_setup()
        series = self.tool.get_result()
        self.assert_is_not_none(series)
        self.assert_equal(len(series), 5)
        buffer_worklist = None
        dil_worklists = dict()
        transfer_worklist = None
        for worklist in series:
            if worklist.index == 0:
                buffer_worklist = worklist
            elif worklist.index == 4:
                transfer_worklist = worklist
            else:
                dil_worklists[worklist.index] = worklist
        self._test_annealing_worklist(buffer_worklist)
        self._test_dilution_series_worklists(dil_worklists)
        self._test_transfer_worklist(transfer_worklist)

    def test_only_one_concentration(self):
        new_pos_data = dict()
        new_pos_data['A1'] = self.position_data['A1']
        new_pos_data['B1'] = self.position_data['B1']
        new_pos_data['C1'] = self.position_data['C1']
        self.position_data = new_pos_data
        new_an_results = dict()
        new_an_results['A1'] = self.annealing_result_data['A1']
        new_an_results['B1'] = self.annealing_result_data['B1']
        new_an_results['C1'] = self.annealing_result_data['C1']
        self.annealing_result_data = new_an_results
        self._continue_setup()
        series = self.tool.get_result()
        self.assert_equal(len(series), 2)
        buffer_worklist = None
        transfer_worklist = None
        for worklist in series:
            if worklist.index == 0:
                buffer_worklist = worklist
            else:
                transfer_worklist = worklist
        self._test_annealing_worklist(buffer_worklist)
        self._test_transfer_worklist(transfer_worklist)

    def test_invalid_iso_request(self):
        self._test_invalid_iso_request()

    def test_invalid_prep_layout(self):
        self._test_invalid_prep_layout()

    def test_wrong_experiment_type(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.SCREENING
        self.shape = get_384_rack_shape()
        self._continue_setup()
        self._test_and_expect_errors('Error when trying to associate rack ' \
                                     'sectors by molecule design')


class IsoWorklistGeneratorScreenTestCase(IsoWorklistGeneratorTestCase):
    """
    Dilutions series from sectors 0-2-1 (0 largest), 3 is independent.
    Alternatively: two indepent dilutions 0-1, 2-3
    """

    def set_up(self):
        IsoWorklistGeneratorTestCase.set_up(self)
        self.shape = get_384_rack_shape()
        self.experiment_type_id = EXPERIMENT_SCENARIOS.SCREENING
        self.association_data = None
        # key: rack position, value: (md ID, prep conc, parent well, req_vol,
        #: transfer target positions, iso conc (if different from prep conc))
        # estimated iso volume: 10 ul
        self.position_data = dict(
                    # first quadrant
                    A1=('md_1', 25000, None, 32, ['A1']),
                    A2=('md_1', 5000, 'B1', 20, ['A2']),
                    B1=('md_1', 10000, 'A1', 30, ['B1']),
                    B2=(205200, 10000, None, 20, ['B2']),
                    # second quadrant
                    A3=('md_2', 25000, None, 32, ['A3']),
                    A4=('md_2', 5000, 'B3', 20, ['A4']),
                    B3=('md_2', 10000, 'A3', 30, ['B3']),
                    B4=(205200, 10000, None, 20, ['B4']),
                    # third quadrant
                    A5=('md_3', 25000, None, 32, ['A5']),
                    A6=('md_3', 5000, 'B5', 20, ['A6']),
                    B5=('md_3', 10000, 'A5', 30, ['B5']),
                    # fourth quadrant
                    D2=(205201, 10000, None, 20, ['D2']))
        self.alternative_data = dict(
                    # first quadrant
                    A1=('md_1', 10000, None, 30, ['A1']),
                    A2=('md_1', 5000, 'A1', 20, ['A2']),
                    B1=('md_2', 10000, None, 30, ['B1']),
                    B2=('md_2', 5000, 'B1', 20, ['B2']),
                    # second quadrant
                    A3=('md_3', 10000, None, 30, ['A3']),
                    A4=('md_3', 5000, 'A3', 20, ['A4']),
                    B3=('md_4', 10000, None, 30, ['B3']),
                    B4=('md_4', 5000, 'B3', 20, ['B4']),
                    # third quadrant
                    A5=('md_5', 10000, None, 30, ['A5']),
                    A6=('md_5', 5000, 'A5', 20, ['A6']),
                    # fourth quadrant
                    D1=('md_6', 10000, None, 30, ['D1']),
                    D2=('md_6', 5000, 'D1', 20, ['D2']))
        self.one_sector_data = dict(
                    # first quadrant
                    A1=('md_1', 10000, None, 30, ['A1']),
                    B1=('md_2', 10000, None, 30, ['B1']),
                    # second quadrant
                    A3=('md_3', 10000, None, 30, ['A3']),
                    B3=('md_4', 10000, None, 30, ['B3']),
                    # third quadrant
                    A5=('md_5', 10000, None, 30, ['A5']),
                    # fourth quadrant
                    D1=('md_6', 10000, None, 30, ['D1']))
        self.aliquot_buffer_data = dict(
                    # first quadrant
                    A1=('md_1', 500, None, 100, ['A1'], 100),
                    A2=('md_1', 250, 'A1', 14, ['A2'], 50),
                    B1=('md_2', 500, None, 100, ['B1'], 100),
                    B2=('md_2', 250, 'B1', 14, ['B2'], 50),
                    # second quadrant
                    A3=('md_3', 500, None, 100, ['A3'], 100),
                    A4=('md_3', 250, 'A3', 14, ['A4'], 50),
                    B3=('md_4', 500, None, 100, ['B3'], 100),
                    B4=('md_4', 250, 'B3', 14, ['B4'], 50),
                    # third quadrant
                    A5=('md_5', 500, None, 100, ['A5'], 100),
                    A6=('md_5', 250, 'A5', 14, ['A6'], 50),
                    # fourth quadrant
                    D1=('md_6', 500, None, 100, ['D1'], 100),
                    D2=('md_6', 250, 'D1', 14, ['D2'], 50))

        #: key: rack_pos, value: dilution volume
        self.annealing_result_data = dict(
                    A1=16, A2=10, B1=18, B2=16,
                    A3=16, A4=10, B3=18, B4=16,
                    A5=16, A6=10, B5=18, D2=16)
        self.alt_annealing_result_data = dict(
                    A1=24, A2=10, B1=24, B2=10,
                    A3=24, A4=10, B3=24, B4=10,
                    A5=24, A6=10, D1=24, D2=10)
        self.iso_volume = 10
        self.aliquot_annealing_result_data = dict(
                    A1=99, A2=7, B1=99, B2=7,
                    A3=99, A4=7, B3=99, B4=7,
                    A5=99, A6=7, D1=99, D2=7)

        #: key: source sector value: target sector, volume)
        self.series_result_data = {1: {0 : (2, 12)},
                                   2: {2 : (1, 10)}}
        self.alt_series_result_data = {1 : {0 : (1, 10), 2 : (3, 10)}}
        self.albuffer_series_result_data = {1 : {0 : (1, 7), 2 : (3, 7)}}

    def _associate_sectors(self):
        self.association_data = PrepIsoAssociationData(
                                    preparation_layout=self.prep_layout,
                                    log=self.log)

    def _create_test_pool_set(self):
        md_pool = self._get_pool(205230)
        self.pool_set = MoleculeDesignPoolSet(
                                molecule_type=md_pool.molecule_type,
                                molecule_design_pools=set([md_pool]))

    def _test_invalid_association_data(self):
        self._continue_setup()
        self.association_data = dict()
        self._test_and_expect_errors('The association data must be a ' \
                                     'PrepIsoAssociationData object')

    def _test_dilution_series_worklists(self, dil_worklists=None):
        modifier = 0
        if dil_worklists is None:
            self._continue_setup()
            dil_worklists = self.tool.get_result()
            modifier = 1
        self.assert_is_not_none(dil_worklists)
        self.assert_equal(len(dil_worklists), len(self.series_result_data))
        for wl_index, dil_worklist in dil_worklists.iteritems():
            label = '%s%s%s' % (self.iso_request_name,
                       IsoDilutionWorklistsGenerator.BASE_PLAN_NAME,
                       (wl_index + modifier))
            self.assert_equal(dil_worklist.label, label)
            result_data = self.series_result_data[wl_index + modifier]
            self.assert_equal(len(dil_worklist.executed_worklists), 0)
            self.assert_equal(len(dil_worklist.planned_transfers),
                              len(result_data))
            for prt in dil_worklist.planned_transfers:
                self.assert_equal(prt.type, TRANSFER_TYPES.RACK_TRANSFER)
                transfer_data = result_data[prt.source_sector_index]
                target_sector = transfer_data[0]
                self.assert_equal(prt.target_sector_index, target_sector)
                expected_vol = transfer_data[1]
                prt_volume = prt.volume * VOLUME_CONVERSION_FACTOR
                self.assert_equal(expected_vol, prt_volume)

    def _test_aliquot_buffer_worklist(self, aliquot_buffer_worklist=None):
        if aliquot_buffer_worklist is None:
            self._continue_setup()
            aliquot_buffer_worklist = self.tool.get_result()
        self.assert_is_not_none(aliquot_buffer_worklist)
        label = '%s%s' % (self.iso_request_name,
                          IsoAliquotBufferWorklistGenerator.WORKLIST_SUFFIX)
        self.assert_equal(aliquot_buffer_worklist.label, label)
        self.assert_equal(len(aliquot_buffer_worklist.executed_worklists), 0)
        self.assert_equal(len(aliquot_buffer_worklist.planned_transfers),
                          len(self.annealing_result_data))
        for pcd in aliquot_buffer_worklist.planned_transfers:
            self.assert_equal(pcd.type, TRANSFER_TYPES.CONTAINER_DILUTION)
            pcd_volume = pcd.volume * VOLUME_CONVERSION_FACTOR
            self.assert_equal(self.aliquot_buffer_volume, pcd_volume)
            self.assert_equal(pcd.diluent_info,
                              IsoAliquotBufferWorklistGenerator.DILUENT_INFO)

    def _test_transfer_worklist(self, transfer_worklist=None):
        if transfer_worklist is None:
            self._continue_setup()
            transfer_worklist = self.tool.get_result()
        self.assert_is_not_none(transfer_worklist)
        label = '%s%s' % (self.iso_request_name,
                          IsoTransferWorklistGenerator.WORKLIST_SUFFIX)
        self.assert_equal(transfer_worklist.label, label)
        self.assert_equal(len(transfer_worklist.executed_worklists), 0)
        self.assert_equal(len(transfer_worklist.planned_transfers), 1)
        prt = transfer_worklist.planned_transfers[0]
        self.assert_equal(prt.source_sector_index, 0)
        self.assert_equal(prt.target_sector_index, 0)
        self.assert_equal(prt.sector_number, 1)
        if self.aliquot_buffer_volume == 0:
            expected_volume = self.iso_volume
        else:
            expected_volume = self.iso_volume - self.aliquot_buffer_volume
        prt_volume = prt.volume * VOLUME_CONVERSION_FACTOR
        self.assert_equal(expected_volume, prt_volume)

    def tear_down(self):
        IsoWorklistGeneratorTestCase.tear_down(self)
        del self.alternative_data
        del self.one_sector_data
        del self.aliquot_buffer_data
        del self.alt_annealing_result_data
        del self.aliquot_annealing_result_data
        del self.alt_series_result_data
        del self.albuffer_series_result_data


class IsoBufferWorklistGeneratorScreenTestCase(
                                IsoWorklistGeneratorScreenTestCase):

    def _create_tool(self):
        self.tool = IsoBufferWorklistGeneratorScreening(
                    iso_request=self.iso_request,
                    preparation_layout=self.prep_layout,
                    association_data=self.association_data, log=self.log)

    def test_result(self):
        self._test_annealing_worklist()

    def test_result_alternative_setup(self):
        self.position_data = self.alternative_data
        self.annealing_result_data = self.alt_annealing_result_data
        self._test_annealing_worklist()

    def test_invalid_iso_request(self):
        self._test_invalid_iso_request()

    def test_invalid_prep_layout(self):
        self._test_invalid_prep_layout()

    def test_invalid_association_data(self):
        self._test_invalid_association_data()


class IsoDilutionWorklistGeneratorScreenTestCase(
                                        IsoWorklistGeneratorScreenTestCase):

    def _create_tool(self):
        self.tool = IsoDilutionWorklistsGeneratorScreening(log=self.log,
                    iso_request_name=self.iso_request_name,
                    preparation_layout=self.prep_layout,
                    association_data=self.association_data)

    def test_result(self):
        self._test_dilution_series_worklists()

    def test_result_alternative_setup(self):
        self.position_data = self.alternative_data
        self.series_result_data = self.alt_series_result_data
        self._test_dilution_series_worklists()

    def test_result_one_concentration(self):
        self.position_data = self.one_sector_data
        self._continue_setup()
        dil_worklists = self.tool.get_result()
        self.assert_is_not_none(dil_worklists)
        self.assert_equal(len(dil_worklists), 0)

    def test_invalid_iso_request_name(self):
        self._test_invalid_iso_request_name()

    def test_invalid_prep_layout(self):
        self._test_invalid_prep_layout()

    def test_invalid_association_data(self):
        self._test_invalid_association_data()


class IsoTransferWorklistGeneratorScreenTestCase(
                                        IsoWorklistGeneratorScreenTestCase):

    def _create_tool(self):
        self.tool = IsoTransferWorklistGeneratorScreening(log=self.log,
                    iso_request_name=self.iso_request_name,
                    preparation_layout=self.prep_layout,
                    association_data=self.association_data)

    def test_result(self):
        self._test_transfer_worklist()

    def test_result_alternative_setup(self):
        self.position_data = self.alternative_data
        self._test_transfer_worklist()

    def test_invalid_iso_request_name(self):
        self._test_invalid_iso_request_name()

    def test_invalid_prep_layout(self):
        self._test_invalid_prep_layout()

    def test_invalid_association_data(self):
        self._test_invalid_association_data()

    def test_more_than_one_iso_volume(self):
        self._continue_setup()
        prep_pos = self.prep_layout.working_positions()[0]
        for tt in prep_pos.transfer_targets:
            tt.transfer_volume = 20
        self._test_and_expect_errors('There is more than one ISO volume for ' \
                                     'this screening preparation layout')


class IsoAliquotBufferWorklistGeneratorTestCase(
                                        IsoWorklistGeneratorScreenTestCase):

    def set_up(self):
        IsoWorklistGeneratorScreenTestCase.set_up(self)
        self.aliquot_buffer_volume = 8

    def _create_tool(self):
        self.tool = IsoAliquotBufferWorklistGenerator(log=self.log,
                        iso_request_name=self.iso_request_name,
                        preparation_layout=self.prep_layout,
                        buffer_volume=self.aliquot_buffer_volume)

    def test_result(self):
        self.position_data = self.aliquot_buffer_data
        self._test_aliquot_buffer_worklist()

    def test_invalid_iso_request_name(self):
        self._test_invalid_iso_request_name()

    def test_invalid_prep_layout(self):
        self._test_invalid_prep_layout()

    def test_invalid_buffer_volume(self):
        self.position_data = self.aliquot_buffer_data
        self._continue_setup()
        self.aliquot_buffer_volume = -3
        self._test_and_expect_errors('The buffer volume must be a positive ' \
                                     'number')
        self.aliquot_buffer_volume = '4,9'
        self._test_and_expect_errors('The buffer volume must be a positive ' \
                                     'number')


class IsoWorklistSeriesGeneratorScreenTestCase(
                                    IsoWorklistGeneratorScreenTestCase):

    def _create_tool(self):
        self.tool = IsoWorklistSeriesGenerator(log=self.log,
                        iso_request=self.iso_request,
                        preparation_layout=self.prep_layout)

    def __check_result(self, number_worklists, has_aliquot_buffer_wl=False):
        self._continue_setup()
        series = self.tool.get_result()
        self.assert_is_not_none(series)
        self.assert_equal(len(series), number_worklists)
        dil_worklists = dict()
        for worklist in series:
            if worklist.index == 0:
                self._test_annealing_worklist(worklist)
            elif worklist.index == (number_worklists - 1):
                self._test_transfer_worklist(worklist)
            elif has_aliquot_buffer_wl and \
                                worklist.index == (number_worklists - 2):
                self._test_aliquot_buffer_worklist(worklist)
            else:
                dil_worklists[worklist.index] = worklist

        if number_worklists > 2:
            self._test_dilution_series_worklists(dil_worklists)

    def test_result(self):
        self.__check_result(4)

    def test_result_alternative_setup(self):
        self.position_data = self.alternative_data
        self.annealing_result_data = self.alt_annealing_result_data
        self.series_result_data = self.alt_series_result_data
        self.__check_result(3)

    def test_one_concentration(self):
        self.position_data = self.one_sector_data
        self.annealing_result_data = dict(
                    A1=24, B1=24, A3=24, B3=24, A5=24, D1=24)
        self.__check_result(2)

    def test_with_aliquot_dilution(self):
        self.aliquot_buffer_volume = 8
        self.position_data = self.aliquot_buffer_data
        self.annealing_result_data = self.aliquot_annealing_result_data
        self.series_result_data = self.albuffer_series_result_data
        self.__check_result(number_worklists=4, has_aliquot_buffer_wl=True)

    def test_invalid_iso_request(self):
        self._test_invalid_iso_request()

    def test_invalid_prep_layout(self):
        self._test_invalid_prep_layout()

    def test_invalid_iso_layout(self):
        self._continue_setup()
        self.iso_request.iso_layout = RackLayout(shape=self.shape)
        self._test_and_expect_errors('Error when trying to convert ISO layout!')

    def test_inconsistent_aliquot_buffer_volumes(self):
        self._continue_setup()
        for prep_pos in self.prep_layout.working_positions():
            if prep_pos.is_mock: continue
            tt = prep_pos.transfer_targets[0]
            tt.transfer_volume = (self.iso_volume / 2)
            break
        self._test_and_expect_errors('There is more than buffer volume for ' \
                                     'this aliquot plate')


class IsoWorklistGeneratorManualTestCase(IsoWorklistGeneratorTestCase):

    def set_up(self):
        IsoWorklistGeneratorTestCase.set_up(self)
        self.shape = get_96_rack_shape()
        self.experiment_type_id = EXPERIMENT_SCENARIOS.MANUAL
        # key: rack position, value: (md ID, prep conc, parent well, req_vol,
        #: transfer target positions, iso conc (if different from prep conc))
        # estimated iso volume: 10 ul
        self.position_data = dict(A1=(205200, 50000, None, 1, []),
                                  A2=(205201, 40000, None, 5, []),
                                  A3=(205202, 30000, None, 2.5, []))
        #: key: rack_pos, value: dilution volume
        self.result_data = dict(A2=1, A3=1)

    def _create_tool(self):
        self.tool = IsoWorklistSeriesGenerator(iso_request=self.iso_request,
                                        preparation_layout=self.prep_layout,
                                        log=self.log)

    def __check_result(self, expected_worklist_number):
        self._continue_setup()
        ws = self.tool.get_result()
        self.assert_is_not_none(ws)
        self.assert_equal(len(ws), expected_worklist_number)
        if expected_worklist_number > 0:
            wl = ws.planned_worklists[0]
            self.assert_equal(len(wl.planned_transfers), len(self.result_data))
            for pcd in wl.planned_transfers:
                self.assert_equal(pcd.type, TRANSFER_TYPES.CONTAINER_DILUTION)
                pos_label = pcd.target_position.label
                expected_volume = self.result_data[pos_label]
                transfer_volume = pcd.volume * VOLUME_CONVERSION_FACTOR
                self.assert_equal(expected_volume, transfer_volume)
                self.assert_equal(pcd.diluent_info,
                                  IsoBufferWorklistGenerator.DILUENT_INFO)

    def test_result_some_dilutions(self):
        self.__check_result(expected_worklist_number=1)

    def test_result_no_dilutions(self):
        self.position_data = dict(A1=(205200, 50000, None, 1, []),
                                  A2=(205201, 50000, None, 5, []),
                                  A3=(205202, 50000, None, 2.5, []))
        self.result_data = dict()
        self.__check_result(expected_worklist_number=0)

    def test_invalid_iso_request(self):
        self._test_invalid_iso_request()

    def test_invalid_prep_layout(self):
        self._test_invalid_prep_layout()
