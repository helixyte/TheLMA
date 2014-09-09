"""
Test for BioMek worklist writers.

AAB
"""
from thelma.automation.semiconstants import PIPETTING_SPECS_NAMES
from thelma.automation.semiconstants import get_96_rack_shape
from thelma.automation.semiconstants import get_item_status_managed
from thelma.automation.semiconstants import get_min_transfer_volume
from thelma.automation.semiconstants import get_pipetting_specs_biomek
from thelma.automation.semiconstants import get_pipetting_specs_manual
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.automation.tools.worklists.biomek \
    import SampleDilutionWorklistWriter
from thelma.automation.tools.worklists.biomek \
    import SampleTransferWorklistWriter
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.interfaces import IRackShape
from thelma.models.container import Tube
from thelma.models.container import TubeSpecs
from thelma.models.container import WellSpecs
from thelma.models.liquidtransfer import PlannedRackSampleTransfer
from thelma.models.liquidtransfer import PlannedSampleDilution
from thelma.models.liquidtransfer import PlannedSampleTransfer
from thelma.models.liquidtransfer import PlannedWorklist
from thelma.models.liquidtransfer import ReservoirSpecs
from thelma.models.rack import PlateSpecs
from thelma.models.rack import TubeRackSpecs
from thelma.oldtests.tools.tooltestingutils import FileCreatorTestCase



class _BiomekWorklistWriterTestCase(FileCreatorTestCase):

    def set_up(self):
        FileCreatorTestCase.set_up(self)
        self.WL_PATH = 'thelma:tests/tools/worklists/biomek/'
        self.target_rack = None
        self.worklist = None
        self.ignored_positions = []
        self.rack_shape = get_96_rack_shape()
        self.status = get_item_status_managed()
        self.source_rack_barcode = '09999991'
        self.target_rack_barcode = '09999992'
        self.plate_specs = None
        self.well_specs = None
        self.well_dead_volume = 0.000010 # 10 ul
        self.well_max_volume = 0.000500 # 100 ul
        self.pipetting_specs = get_pipetting_specs_biomek()

    def tear_down(self):
        FileCreatorTestCase.tear_down(self)
        del self.target_rack
        del self.worklist
        del self.ignored_positions
        del self.rack_shape
        del self.status
        del self.source_rack_barcode
        del self.target_rack_barcode
        del self.plate_specs
        del self.well_specs
        del self.well_dead_volume
        del self.well_max_volume
        del self.pipetting_specs

    def _get_alternative_rack(self, container_positions, volume):
        tube_spec = TubeSpecs(label='test_tube_specs',
                              max_volume=self.well_max_volume,
                              dead_volume=self.well_dead_volume,
                              tube_rack_specs=None)
        tube_rack_spec = TubeRackSpecs(shape=self.rack_shape,
                              tube_specs=[tube_spec],
                              label='test_tube_rack_spec')
        rack = tube_rack_spec.create_rack(label='invalid target rack',
                                          status=self.status)
        counter = 3
        for rack_pos in container_positions:
            barcode = '0999999%i' % (counter)
            counter += 1
            tube = Tube.create_from_rack_and_position(specs=tube_spec,
                                        status=self.status, position=rack_pos,
                                        barcode=barcode, rack=rack)
            tube.make_sample(volume)
            rack.containers.append(tube)

        return rack

    def _create_test_plate_specs(self):
        if self.well_specs is None:
            self.well_specs = WellSpecs(label='test_well_specs',
                                        max_volume=self.well_max_volume,
                                        dead_volume=self.well_dead_volume,
                                        plate_specs=None)
            self.plate_specs = PlateSpecs(label='test_plate_specs',
                                          shape=self.rack_shape,
                                          well_specs=self.well_specs)

    def _check_result(self, file_name):
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream, file_name)


class SampleTransferWorklistWriterTestCase(_BiomekWorklistWriterTestCase):

    def set_up(self):
        _BiomekWorklistWriterTestCase.set_up(self)
        self.WL_FILE = 'sample_transfer_worklist.csv'
        self.source_rack = None
        # target position label and transfer volume
        self.target_positions = dict(A2=20, A3=50, B2=20, B3=50)
        # source position, source volume and target positions
        self.source_positions = dict(A1=(100, ['A2', 'A3']),
                                     B1=(100, ['B2', 'B3']))
        # rack properties
        self.target_container_volume = 0.000010 # 10 ul

    def tear_down(self):
        _BiomekWorklistWriterTestCase.tear_down(self)
        del self.WL_FILE
        del self.source_rack
        del self.target_positions
        del self.source_positions
        del self.target_container_volume

    def _create_tool(self):
        self.tool = SampleTransferWorklistWriter(
                                self.worklist,
                                self.target_rack,
                                self.source_rack,
                                pipetting_specs=self.pipetting_specs,
                                ignored_positions=self.ignored_positions)

    def __continue_setup(self):
        self.__create_worklist()
        self._create_test_plate_specs()
        self.__create_target_rack()
        self.__create_source_rack()
        self._create_tool()

    def __create_worklist(self):
        self.worklist = PlannedWorklist(label='ContainerTransferWriterTest',
                            transfer_type=TRANSFER_TYPES.SAMPLE_TRANSFER,
                            pipetting_specs=self.pipetting_specs)
        for source_label, source_data in self.source_positions.iteritems():
            source_position = get_rack_position_from_label(source_label)
            if source_position in self.ignored_positions: continue
            for target_label in source_data[1]:
                target_position = get_rack_position_from_label(target_label)
                transfer_volume = self.target_positions[target_label] \
                                  / VOLUME_CONVERSION_FACTOR
                pst = PlannedSampleTransfer.get_entity(volume=transfer_volume,
                            source_position=source_position,
                            target_position=target_position)
                self.worklist.planned_liquid_transfers.append(pst)

    def __create_target_rack(self):
        self.target_rack = self.plate_specs.create_rack(label='target rack',
                                                        status=self.status)
        self.target_rack.barcode = self.target_rack_barcode
        for container in self.target_rack.containers: #pylint: disable=E1103
            pos_label = container.location.position.label
            if not self.target_positions.has_key(pos_label): continue
            container.make_sample(self.target_container_volume)

    def __create_source_rack(self):
        self.source_rack = self.plate_specs.create_rack(label='source rack',
                                                        status=self.status)
        self.source_rack.barcode = self.source_rack_barcode
        for container in self.source_rack.containers: #pylint: disable=E1103
            rack_pos = container.location.position
            if rack_pos in self.ignored_positions: continue
            pos_label = rack_pos.label
            if not self.source_positions.has_key(pos_label): continue
            source_data = self.source_positions[pos_label]
            source_volume = source_data[0] / VOLUME_CONVERSION_FACTOR
            container.make_sample(source_volume)

    def test_result(self):
        self.__continue_setup()
        self._check_result(self.WL_FILE)

    def test_result_ignored_positions(self):
        self.__continue_setup()
        # ignored positions can be None
        self.ignored_positions = None
        self._create_tool()
        self._check_result(self.WL_FILE)
        # ignored positions with samples in source rack
        self.ignored_positions = []
        self.__continue_setup()
        self.ignored_positions = [get_rack_position_from_label('A1')]
        self._create_tool()
        self._check_result('sample_transfer_worklist_ign.csv')
        # ignored positions without samples in source rack
        self.__continue_setup()
        self._check_result('sample_transfer_worklist_ign.csv')

    def test_result_pipetting_specs(self):
        self.target_positions['A2'] = 1
        self.__continue_setup()
        self._test_and_expect_errors('Some transfer volume are smaller than ' \
                             'the allowed minimum transfer volume of 2.0 ul: ' \
                             'target A2 (1.0 ul)')
        self.pipetting_specs = get_pipetting_specs_manual()
        self.__continue_setup()
        self._check_result('sample_transfer_worklist_man.csv')

    def test_invalid_input_values(self):
        self.__continue_setup()
        wl = self.worklist
        self.worklist = self.worklist.planned_liquid_transfers
        self._test_and_expect_errors('planned worklist must be a ' \
                                     'PlannedWorklist object')
        self.worklist = wl
        trg_rack = self.target_rack
        self.target_rack = self.plate_specs
        self._test_and_expect_errors('target rack must be a Rack object')
        self.target_rack = trg_rack
        ign = self.ignored_positions
        self.ignored_positions = dict()
        self._test_and_expect_errors('ignored position list must be a list')
        self.ignored_positions = ['A1']
        self._test_and_expect_errors('ignored position must be a ' \
                                     'RackPosition object')
        self.ignored_positions = ign
        src_rack = self.source_rack
        self.source_rack = self.plate_specs
        self._test_and_expect_errors('source rack must be a Rack object')
        self.source_rack = src_rack
        self.pipetting_specs = 3
        self._test_and_expect_errors('The pipetting specs must be a ' \
                                     'PipettingSpecs object')

    def test_unsupported_transfer_type(self):
        self.__continue_setup()
        prst = PlannedRackSampleTransfer.get_entity(
                                        self.target_container_volume,
                                        1, 0, 0)
        self.worklist.planned_liquid_transfers.append(prst)
        self._test_and_expect_errors('Some transfers planned in the worklist ' \
                                     'are not supported')

    def test_transfer_volume_too_small(self):
        #pylint: disable=E1103
        min_vol = self.pipetting_specs.min_transfer_volume \
                  * VOLUME_CONVERSION_FACTOR
        #pylint: enable=E1103
        invalid_volume = min_vol / 2.0
        self.target_positions['A2'] = invalid_volume
        self.target_positions['B3'] = invalid_volume
        self.__continue_setup()
        self._test_and_expect_errors('Some transfer volume are smaller than ' \
                                     'the allowed minimum transfer volume')

    def test_transfer_volume_too_large(self):
        self.source_positions['A1'] = (600, ['A2', 'A3'])
        self.target_positions['A3'] = 550
        self.__continue_setup()
        self._test_and_expect_errors('Some transfer volume are larger than ' \
                                     'the allowed maximum transfer volume')

    def test_target_container_missing(self):
        self.__continue_setup()
        target_positions = [get_rack_position_from_label('A2'),
                            get_rack_position_from_label('B2')]
        self.target_rack = self._get_alternative_rack(target_positions,
                                                self.target_container_volume)
        self._test_and_expect_errors('Could not find containers for the ' \
                                     'following target positions')

    def test_target_volume_too_large(self):
        self.well_max_volume = 0.000050 # 50 ul
        self.__continue_setup()
        self._test_and_expect_errors('Some target containers cannot take up ' \
                                     'the transfer volume')

    def test_source_container_missing(self):
        self.__continue_setup()
        source_positions = [get_rack_position_from_label('A1')]
        self.source_rack = self._get_alternative_rack(source_positions,
                                                       0.000100)
        self._test_and_expect_errors('Could not find containers for the ' \
                                     'following source positions')

    def test_source_volume_too_small(self):
        self.well_dead_volume = (self.well_dead_volume * 5)
        self.__continue_setup()
        self._test_and_expect_errors('Some source containers do not contain ' \
                'enough volume to provide liquid for all target containers')


class SampleDilutionWorklistWriterTestCase(_BiomekWorklistWriterTestCase):

    def set_up(self):
        _BiomekWorklistWriterTestCase.set_up(self)
        self.WL_FILE = 'sample_dilution_worklist.csv'
        self.reservoir_specs = None
        # target position, diluent info, transfer volume in ul
        self.target_positions = dict(A1=['mix1', 10],
                                     B2=['mix1', 30],
                                     C3=['mix2', 10],
                                     D4=['mix2', 30],
                                     E5=['mix1', 90])
        # rack and reservoir specs
        self.rack_shape_reservoir = self._get_entity(IRackShape, '1x4')
        self.target_container_volume = 0.000010 # 10 ul
        self.reservoir_max_volume = 0.000500 # 500 ul
        self.reservoir_min_dead_volume = 0.000020 # 20 ul
        self.reservoir_max_dead_volume = 0.000100 # 100 ul

    def tear_down(self):
        _BiomekWorklistWriterTestCase.tear_down(self)
        del self.WL_FILE
        del self.reservoir_specs
        del self.target_positions
        del self.rack_shape_reservoir
        del self.target_container_volume
        del self.reservoir_max_volume
        del self.reservoir_min_dead_volume
        del self.reservoir_max_dead_volume

    def _create_tool(self):
        self.tool = SampleDilutionWorklistWriter(
                                    self.worklist,
                                    self.target_rack,
                                    self.source_rack_barcode,
                                    self.reservoir_specs,
                                    pipetting_specs=self.pipetting_specs,
                                    ignored_positions=self.ignored_positions)

    def __continue_setup(self):
        self.__create_worklist()
        self.__create_reservoir_specs()
        self._create_test_plate_specs()
        self.__create_target_rack()
        self._create_tool()

    def __create_worklist(self):
        self.worklist = PlannedWorklist(label='SampleDilutionWriterTest',
                            pipetting_specs=self.pipetting_specs,
                            transfer_type=TRANSFER_TYPES.SAMPLE_DILUTION)
        for pos_label, transfer_data in self.target_positions.iteritems():
            rack_pos = get_rack_position_from_label(pos_label)
            volume = transfer_data[1] / VOLUME_CONVERSION_FACTOR
            psd = PlannedSampleDilution.get_entity(volume=volume,
                            diluent_info=transfer_data[0],
                            target_position=rack_pos)
            self.worklist.planned_liquid_transfers.append(psd)

    def __create_reservoir_specs(self):
        self.reservoir_specs = ReservoirSpecs(
                        name='Container Dilution Test Reservoir Specs',
                        description='test specs - not to be stored',
                        rack_shape=self.rack_shape_reservoir,
                        max_volume=self.reservoir_max_volume,
                        min_dead_volume=self.reservoir_min_dead_volume,
                        max_dead_volume=self.reservoir_max_dead_volume)

    def __create_target_rack(self):
        self.target_rack = self.plate_specs.create_rack(label='target rack',
                                                        status=self.status)
        self.target_rack.barcode = self.target_rack_barcode
        for container in self.target_rack.containers: #pylint: disable=E1103
            pos_label = container.location.position.label
            if not self.target_positions.has_key(pos_label):
                continue
            container.make_sample(self.target_container_volume)

    def test_result(self):
        self.__continue_setup()
        self._check_result(self.WL_FILE)

    def test_result_ignored_positions(self):
        self.__continue_setup()
        # ignored positions can be None
        self.ignored_positions = None
        self._create_tool()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream, self.WL_FILE)
        # ignored positions with samples in target rack
        self.ignored_positions = []
        self.__continue_setup()
        self.ignored_positions = [get_rack_position_from_label('A1'),
                                  get_rack_position_from_label('B2')]
        self._create_tool()
        self._check_result('sample_dilution_worklist_ign.csv')
        # ignored positions without samples in target rack
        self.__continue_setup()
        self._check_result('sample_dilution_worklist_ign.csv')

    def test_result_split_volumes(self):
        self.well_max_volume = 0.001000 # 1000 ul
        self.target_positions['F6'] = ('mix1', 501)
        self.__continue_setup()
        self._check_result('sample_dilution_worklist_split.csv')
        self._check_warning_messages('Some dilution volumes exceed the ' \
                                     'allowed maximum transfer volume')

    def test_result_several_source_wells(self):
        self.reservoir_max_volume = 0.000100 # 100 ul
        self.reservoir_max_dead_volume = 0.000020 # 20 ul
        self.reservoir_min_dead_volume = 0.000010 # 10 ul
        self.__continue_setup()
        self._check_result('sample_dilution_worklist_cap.csv')
        self._check_warning_messages('The source for the following diluents ' \
                'has been split and distributed over several containers ' \
                'because one single container could not have taken up the ' \
                'required volume (max volume of a source container')

    def test_result_pipetting_specs(self):
        self.target_positions['A1'][1] = 1
        self.__continue_setup()
        self._test_and_expect_errors('Some transfer volume are smaller than ' \
                             'the allowed minimum transfer volume of 2.0 ul: ' \
                             'target A1 (1.0 ul)')
        self.pipetting_specs = get_pipetting_specs_manual()
        self.__continue_setup()
        self._check_result('sample_dilution_worklist_man.csv')

    def test_invalid_input_values(self):
        self.__continue_setup()
        wl = self.worklist
        self.worklist = self.worklist.planned_liquid_transfers
        self._test_and_expect_errors('planned worklist must be a ' \
                                     'PlannedWorklist object')
        self.worklist = wl
        trg_rack = self.target_rack
        self.target_rack = self.plate_specs
        self._test_and_expect_errors('target rack must be a Rack object')
        self.target_rack = trg_rack
        srb = self.source_rack_barcode
        self.source_rack_barcode = 3
        self._test_and_expect_errors('source rack barcode must be a basestring')
        self.source_rack_barcode = srb
        rs = self.reservoir_specs
        self.reservoir_specs = None
        self._test_and_expect_errors('The reservoir specs must be a ' \
                                     'ReservoirSpecs object')
        self.reservoir_specs = rs
        ign = self.ignored_positions
        self.ignored_positions = dict()
        self._test_and_expect_errors('ignored position list must be a list')
        self.ignored_positions = ['A1']
        self._test_and_expect_errors('ignored position must be a ' \
                                     'RackPosition object')
        self.ignored_positions = ign
        self.pipetting_specs = 3
        self._test_and_expect_errors('The pipetting specs must be a ' \
                                     'PipettingSpecs object (obtained: int)')

    def test_unsupported_transfer_type(self):
        self.__continue_setup()
        prst = PlannedRackSampleTransfer.get_entity(
                                        self.target_container_volume,
                                        1, 0, 0)
        self.worklist.planned_liquid_transfers.append(prst)
        self._test_and_expect_errors('Some transfers planned in the worklist ' \
                                     'are not supported')

    def test_transfer_volume_too_small(self):
        min_transfer_vol = get_min_transfer_volume(PIPETTING_SPECS_NAMES.BIOMEK)
        invalid_volume = min_transfer_vol / 2.0
        self.target_positions['A1'] = ('mix1', invalid_volume)
        self.target_positions['B3'] = ('mix2', invalid_volume)
        self.__continue_setup()
        self._test_and_expect_errors('Some transfer volume are smaller than ' \
                                     'the allowed minimum transfer volume')

    def test_target_container_missing(self):
        self.__continue_setup()
        target_positions = [get_rack_position_from_label('A1'),
                            get_rack_position_from_label('B2')]
        self.target_rack = self._get_alternative_rack(target_positions,
                                                self.target_container_volume)
        self._test_and_expect_errors('Could not find containers for the ' \
                                     'following target positions')

    def test_target_volume_too_large(self):
        self.well_max_volume = 0.000050 # 50 ul
        self.__continue_setup()
        self._test_and_expect_errors('Some target containers cannot take up ' \
                                     'the transfer volume')

    def test_not_enough_source_containers(self):
        self.target_positions = dict(A1=('mix1', 10),
                                     B2=('mix2', 30),
                                     C3=('mix3', 10),
                                     D4=('mix4', 30),
                                     E5=('mix5', 90))
        self.__continue_setup()
        self._test_and_expect_errors('There is not enough space for all ' \
                            'source containers in the source rack or reservoir')
