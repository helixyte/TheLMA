"""
Test for BioMek worklist writers.

AAB
"""
from thelma.automation.tools.semiconstants import get_96_rack_shape
from thelma.automation.tools.semiconstants import get_item_status_managed
from thelma.automation.tools.semiconstants import get_rack_position_from_label
from thelma.automation.tools.worklists.base import MIN_BIOMEK_TRANSFER_VOLUME
from thelma.automation.tools.worklists.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.worklists.biomek \
    import ContainerDilutionWorklistWriter
from thelma.automation.tools.worklists.biomek \
    import ContainerTransferWorklistWriter
from thelma.interfaces import IRackShape
from thelma.models.container import Tube
from thelma.models.container import TubeSpecs
from thelma.models.container import WellSpecs
from thelma.models.liquidtransfer import PlannedContainerDilution
from thelma.models.liquidtransfer import PlannedContainerTransfer
from thelma.models.liquidtransfer import PlannedRackTransfer
from thelma.models.liquidtransfer import PlannedWorklist
from thelma.models.liquidtransfer import ReservoirSpecs
from thelma.models.rack import PlateSpecs
from thelma.models.rack import TubeRackSpecs
from thelma.tests.tools.tooltestingutils import FileCreatorTestCase
from thelma.tests.tools.tooltestingutils import TestingLog



class BiomekWorklistWriterTestCase(FileCreatorTestCase):

    def set_up(self):
        FileCreatorTestCase.set_up(self)
        self.WL_PATH = 'thelma:tests/tools/worklists/test_files/'
        self.log = TestingLog()
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

    def tear_down(self):
        FileCreatorTestCase.tear_down(self)
        del self.log
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


class ContainerTransferWorklistWriterTestCase(BiomekWorklistWriterTestCase):

    def set_up(self):
        BiomekWorklistWriterTestCase.set_up(self)
        self.WL_FILE = 'container_transfer_worklist.csv'
        self.source_rack = None
        # target position label and transfer volume
        self.target_positions = dict(A2=20, A3=50, B2=20, B3=50)
        # source position, source volume and target positions
        self.source_positions = dict(A1=(100, ['A2', 'A3']),
                                     B1=(100, ['B2', 'B3']))
        # rack properties
        self.target_container_volume = 0.000010 # 10 ul

    def tear_down(self):
        BiomekWorklistWriterTestCase.tear_down(self)
        del self.WL_FILE
        del self.source_rack
        del self.target_positions
        del self.source_positions
        del self.target_container_volume

    def _create_tool(self):
        self.tool = ContainerTransferWorklistWriter(log=self.log,
                            planned_worklist=self.worklist,
                            target_rack=self.target_rack,
                            source_rack=self.source_rack,
                            ignored_positions=self.ignored_positions)

    def __continue_setup(self):
        self.__create_worklist()
        self._create_test_plate_specs()
        self.__create_target_rack()
        self.__create_source_rack()
        self._create_tool()

    def __create_worklist(self):
        self.worklist = PlannedWorklist(label='ContainerTransferWriterTest')
        for source_label, source_data in self.source_positions.iteritems():
            source_position = get_rack_position_from_label(source_label)
            if source_position in self.ignored_positions: continue
            for target_label in source_data[1]:
                target_position = get_rack_position_from_label(target_label)
                transfer_volume = self.target_positions[target_label] \
                                  / VOLUME_CONVERSION_FACTOR
                pct = PlannedContainerTransfer(volume=transfer_volume,
                            source_position=source_position,
                            target_position=target_position)
                self.worklist.planned_transfers.append(pct)

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
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream, self.WL_FILE)

    def test_result_ignored_positions(self):
        self.__continue_setup()
        # ignored positions can be None
        self.ignored_positions = None
        self._create_tool()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream, self.WL_FILE)
        # ignored positions with samples in source rack
        self.ignored_positions = []
        self.__continue_setup()
        self.ignored_positions = [get_rack_position_from_label('A1')]
        self._create_tool()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream,
                    'container_transfer_worklist_ign.csv')
        # ignored positions without samples in source rack
        self.__continue_setup()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream,
                    'container_transfer_worklist_ign.csv')

    def test_invalid_worklist(self):
        self.__continue_setup()
        self.worklist = self.worklist.planned_transfers
        self._test_and_expect_errors('planned worklist must be a ' \
                                     'PlannedWorklist object')

    def test_invalid_target_rack(self):
        self.__continue_setup()
        self.target_rack = self.plate_specs
        self._test_and_expect_errors('target rack must be a Rack object')

    def test_invalid_ignored_positions(self):
        self.__continue_setup()
        self.ignored_positions = dict()
        self._test_and_expect_errors('ignored position list must be a list')
        self.ignored_positions = ['A1']
        self._test_and_expect_errors('ignored rack position must be a ' \
                                     'RackPosition object')

    def test_invalid_source_rack(self):
        self.__continue_setup()
        self.source_rack = self.plate_specs
        self._test_and_expect_errors('source rack must be a Rack object')

    def test_unsupported_transfer_type(self):
        self.__continue_setup()
        prt = PlannedRackTransfer(volume=self.target_container_volume,
                  source_sector_index=0, target_sector_index=0, sector_number=1)
        self.worklist.planned_transfers.append(prt)
        self._test_and_expect_errors('Some transfers planned in the worklist ' \
                                     'are not supported')

    def test_transfer_volume_too_small(self):
        invalid_volume = MIN_BIOMEK_TRANSFER_VOLUME / 2.0
        self.target_positions['A2'] = invalid_volume
        self.target_positions['B3'] = invalid_volume
        self.__continue_setup()
        self._test_and_expect_errors('Some transfer volume are smaller than ' \
                                     'the allowed minimum transfer volume')

    def test_transfer_volume_too_large(self):
        self.source_positions['A1'] = (300, ['A2', 'A3'])
        self.target_positions['A3'] = 250
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
        self._test_and_expect_errors('Some target container cannot take up ' \
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


class ContainerDilutionWorklistWriterTestCase(BiomekWorklistWriterTestCase):

    def set_up(self):
        BiomekWorklistWriterTestCase.set_up(self)
        self.WL_FILE = 'container_dilution_worklist.csv'
        self.reservoir_specs = None
        # target position, diluent info, transfer volume in ul
        self.target_positions = dict(A1=('mix1', 10),
                                     B2=('mix1', 30),
                                     C3=('mix2', 10),
                                     D4=('mix2', 30),
                                     E5=('mix1', 90))
        # rack and reservoir specs
        self.rack_shape_reservoir = self._get_entity(IRackShape, '1x4')
        self.target_container_volume = 0.000010 # 10 ul
        self.reservoir_max_volume = 0.000500 # 500 ul
        self.reservoir_min_dead_volume = 0.000020 # 20 ul
        self.reservoir_max_dead_volume = 0.000100 # 100 ul

    def tear_down(self):
        BiomekWorklistWriterTestCase.tear_down(self)
        del self.WL_FILE
        del self.reservoir_specs
        del self.target_positions
        del self.rack_shape_reservoir
        del self.target_container_volume
        del self.reservoir_max_volume
        del self.reservoir_min_dead_volume
        del self.reservoir_max_dead_volume

    def _create_tool(self):
        self.tool = ContainerDilutionWorklistWriter(log=self.log,
                                planned_worklist=self.worklist,
                                target_rack=self.target_rack,
                                source_rack_barcode=self.source_rack_barcode,
                                reservoir_specs=self.reservoir_specs,
                                ignored_positions=self.ignored_positions)

    def __continue_setup(self):
        self.__create_worklist()
        self.__create_reservoir_specs()
        self._create_test_plate_specs()
        self.__create_target_rack()
        self._create_tool()

    def __create_worklist(self):
        self.worklist = PlannedWorklist(label='ContainerDilutionWriterTest')
        for pos_label, transfer_data in self.target_positions.iteritems():
            rack_pos = get_rack_position_from_label(pos_label)
            volume = transfer_data[1] / VOLUME_CONVERSION_FACTOR
            pcd = PlannedContainerDilution(volume=volume,
                                           target_position=rack_pos,
                                           diluent_info=transfer_data[0])
            self.worklist.planned_transfers.append(pcd)

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
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream, self.WL_FILE)

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
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream,
                    'container_dilution_worklist_ign.csv')
        # ignored positions without samples in target rack
        self.__continue_setup()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream,
                    'container_dilution_worklist_ign.csv')

    def test_result_split_volumes(self):
        self.well_max_volume = 0.000500 # 500 ul
        self.target_positions['F6'] = ('mix1', 401)
        self.__continue_setup()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream,
                                        'container_dilution_worklist_split.csv')
        warnings = ' '.join(self.tool.get_messages())
        self.assert_true('Some dilution volumes exceed the allowed maximum ' \
                         'transfer volume' in warnings)

    def test_result_several_source_wells(self):
        self.reservoir_max_volume = 0.000100 # 100 ul
        self.reservoir_max_dead_volume = 0.000020 # 20 ul
        self.reservoir_min_dead_volume = 0.000010 # 10 ul
        self.__continue_setup()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream,
                                        'container_dilution_worklist_cap.csv')
        self._check_warning_messages('The source for the following diluents ' \
                'has been split and distributed over several containers ' \
                'because one single container could not have taken up the ' \
                'required volume (max volume of a source container')

    def test_invalid_worklist(self):
        self.__continue_setup()
        self.worklist = self.worklist.planned_transfers
        self._test_and_expect_errors('planned worklist must be a ' \
                                     'PlannedWorklist object')

    def test_invalid_target_rack(self):
        self.__continue_setup()
        self.target_rack = self.plate_specs
        self._test_and_expect_errors('target rack must be a Rack object')

    def test_invalid_source_rack_barcode(self):
        self.__continue_setup()
        self.source_rack_barcode = 3
        self._test_and_expect_errors('source rack barcode must be a basestring')

    def test_invalid_reservoir_specs(self):
        self.__continue_setup()
        self.reservoir_specs = None
        self._test_and_expect_errors('The reservoir specs must be a ' \
                                     'ReservoirSpecs object')

    def test_invalid_ignored_positions(self):
        self.__continue_setup()
        self.ignored_positions = dict()
        self._test_and_expect_errors('ignored position list must be a list')
        self.ignored_positions = ['A1']
        self._test_and_expect_errors('ignored rack position must be a ' \
                                     'RackPosition object')

    def test_unsupported_transfer_type(self):
        self.__continue_setup()
        prt = PlannedRackTransfer(volume=self.target_container_volume,
                source_sector_index=0, target_sector_index=0, sector_number=1)
        self.worklist.planned_transfers.append(prt)
        self._test_and_expect_errors('Some transfers planned in the worklist ' \
                                     'are not supported')

    def test_transfer_volume_too_small(self):
        invalid_volume = MIN_BIOMEK_TRANSFER_VOLUME / 2.0
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
        self._test_and_expect_errors('Some target container cannot take up ' \
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