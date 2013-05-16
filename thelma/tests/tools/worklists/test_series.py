"""
Tests for worklist series tools.

AAB
"""
from everest.testing import check_attributes
from thelma.automation.tools.semiconstants import get_384_rack_shape
from thelma.automation.tools.semiconstants import get_96_rack_shape
from thelma.automation.tools.semiconstants import get_item_status_managed
from thelma.automation.tools.semiconstants import get_rack_position_from_label
from thelma.automation.tools.worklists.base \
    import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.tools.worklists.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.worklists.biomek \
    import ContainerTransferWorklistWriter
from thelma.automation.tools.worklists.execution \
    import ContainerTransferWorklistExecutor
from thelma.automation.tools.worklists.series import ContainerDilutionJob
from thelma.automation.tools.worklists.series import ContainerTransferJob
from thelma.automation.tools.worklists.series import RackTransferJob
from thelma.automation.tools.worklists.series import RackTransferWriter
from thelma.automation.tools.worklists.series import SeriesExecutor
from thelma.automation.tools.worklists.series import SeriesWorklistWriter
from thelma.interfaces import IMoleculeDesign
from thelma.interfaces import IOrganization
from thelma.interfaces import IReservoirSpecs
from thelma.interfaces import IUser
from thelma.models.container import WellSpecs
from thelma.models.liquidtransfer import ExecutedRackTransfer
from thelma.models.liquidtransfer import ExecutedWorklist
from thelma.models.liquidtransfer import PlannedContainerDilution
from thelma.models.liquidtransfer import PlannedContainerTransfer
from thelma.models.liquidtransfer import PlannedRackTransfer
from thelma.models.liquidtransfer import PlannedWorklist
from thelma.models.rack import PlateSpecs
from thelma.models.sample import Molecule
from thelma.models.sample import Sample
from thelma.models.user import User
from thelma.tests.tools.tooltestingutils import FileComparisonUtils
from thelma.tests.tools.tooltestingutils import FileCreatorTestCase
from thelma.tests.tools.tooltestingutils import TestingLog
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase


class ContainerDilutionJobTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.planned_worklist = self._create_planned_worklist(label='test')
        self.index = 3
        self.target_rack = self._create_plate()
        self.reservoir_specs = self._create_reservoir_specs()
        self.ignored_positions = [get_rack_position_from_label('A1')]
        self.is_biomek_transfer = True
        self.source_rack_barcode = '09999994'

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.planned_worklist
        del self.index
        del self.target_rack
        del self.reservoir_specs
        del self.ignored_positions
        del self.is_biomek_transfer
        del self.source_rack_barcode

    def __get_data(self):
        return dict(planned_worklist=self.planned_worklist,
                    index=self.index,
                    target_rack=self.target_rack,
                    reservoir_specs=self.reservoir_specs,
                    source_rack_barcode=self.source_rack_barcode,
                    ignored_positions=self.ignored_positions,
                    is_biomek_transfer=self.is_biomek_transfer)

    def test_get_kw_for_worklist_writer(self):
        exp_kw = self.__get_data()
        cdj = ContainerDilutionJob(**exp_kw)
        check_attributes(cdj, exp_kw)
        log = TestingLog()
        del exp_kw['index']
        del exp_kw['is_biomek_transfer']
        exp_kw['log'] = log
        kw = cdj.get_kw_for_worklist_writer(log=log)
        self.assert_equal(kw, exp_kw)

    def test_get_kw_for_executor(self):
        exp_kw = self.__get_data()
        cdj = ContainerDilutionJob(**exp_kw)
        check_attributes(cdj, exp_kw)
        log = TestingLog()
        user = self._get_entity(IUser, 'it')
        del exp_kw['index']
        del exp_kw['source_rack_barcode']
        exp_kw['log'] = log
        exp_kw['user'] = user
        kw = cdj.get_kw_for_executor(log=log, user=user)
        self.assert_equal(kw, exp_kw)


class ContainerTransferJobTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.planned_worklist = self._create_planned_worklist(label='test')
        self.index = 3
        self.target_rack = self._create_plate()
        self.source_rack = self._create_tube_rack()
        self.ignored_positions = [get_rack_position_from_label('A1')]
        self.is_biomek_transfer = True

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.planned_worklist
        del self.index
        del self.target_rack
        del self.source_rack
        del self.ignored_positions
        del self.is_biomek_transfer

    def __get_data(self):
        return dict(planned_worklist=self.planned_worklist,
                    index=self.index,
                    target_rack=self.target_rack,
                    source_rack=self.source_rack,
                    ignored_positions=self.ignored_positions,
                    is_biomek_transfer=self.is_biomek_transfer)

    def test_get_kw_for_worklist_writer(self):
        exp_kw = self.__get_data()
        ctj = ContainerTransferJob(**exp_kw)
        check_attributes(ctj, exp_kw)
        log = TestingLog()
        del exp_kw['index']
        del exp_kw['is_biomek_transfer']
        exp_kw['log'] = log
        kw = ctj.get_kw_for_worklist_writer(log=log)
        self.assert_equal(kw, exp_kw)

    def test_get_kw_for_executor(self):
        exp_kw = self.__get_data()
        ctj = ContainerTransferJob(**exp_kw)
        check_attributes(ctj, exp_kw)
        log = TestingLog()
        user = self._get_entity(IUser, 'it')
        del exp_kw['index']
        exp_kw['log'] = log
        exp_kw['user'] = user
        kw = ctj.get_kw_for_executor(log=log, user=user)
        self.assert_equal(kw, exp_kw)


class RackTransferJobTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.index = 3
        self.target_rack = self._create_plate()
        self.source_rack = self._create_tube_rack()
        self.planned_rack_transfer = self._create_planned_rack_transfer()

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.index
        del self.target_rack
        del self.source_rack
        del self.planned_rack_transfer

    def __get_data(self):
        return dict(planned_rack_transfer=self.planned_rack_transfer,
                    index=self.index,
                    target_rack=self.target_rack,
                    source_rack=self.source_rack)

    def test_get_kw_for_worklist_writer(self):
        exp_kw = self.__get_data()
        rtj = RackTransferJob(**exp_kw)
        check_attributes(rtj, exp_kw)
        log = TestingLog()
        self.assert_raises(NotImplementedError, rtj.get_kw_for_worklist_writer,
                           log)

    def test_get_kw_for_executor(self):
        exp_kw = self.__get_data()
        rtj = RackTransferJob(**exp_kw)
        check_attributes(rtj, exp_kw)
        log = TestingLog()
        user = self._get_entity(IUser, 'it')
        del exp_kw['index']
        exp_kw['log'] = log
        exp_kw['user'] = user
        kw = rtj.get_kw_for_executor(log=log, user=user)
        self.assert_equal(kw, exp_kw)



class SeriesToolTestCase(FileCreatorTestCase):
    """
    Assumes a 3-step intra-rack transfer:
    1. dilution (20 to 80 ul in 2 positions of sector 0)
    2. rack transfer (50 ul  (= 1/2) from sector 0 to 2)
    3. container transfer from sector 2 positions to neighbouring empty
        positions (30 ul)
    """

    def set_up(self):
        FileCreatorTestCase.set_up(self)
        self.WL_PATH = 'thelma:tests/tools/worklists/test_files/'
        self.log = TestingLog()
        self.transfer_jobs = None
        # transfer data
        self.dilution_data = dict(A1=80, A3=80)
        self.transfer_data = dict(B1=('B2', 30), B3=('B4', 30))
        self.number_sectors = 4
        self.source_sector = 0
        self.target_sector = 2
        self.rack_transfer_volume = 0.000050 # 50 ul
        self.is_biomek_transfer = True
        self.source_rack_barcode = 'source_reservoir'
        self.ignored_position_dil = []
        self.ignored_positions_ct = None
        # other setup values
        self.shape = get_96_rack_shape()
        self.status = get_item_status_managed()
        self.molecule_design = self._get_entity(IMoleculeDesign)
        self.reservoir_specs = self._get_entity(IReservoirSpecs)
        self.supplier = self._get_entity(IOrganization)
        self.user = User(username='series_test_user',
                         directory_user_id=None, user_preferenceses=None)
        self.test_plate = None
        self.plate_barcode = '09999991'
        self.dilution_worklist = None
        self.transfer_worklist = None
        self.rack_transfer = None
        self.dilution_job = None
        self.ct_job = None
        self.rack_job = None
        self.well_max_volume = 0.000200 # 200 ul
        self.well_dead_volume = 0.000010 # 10 ul
        self.diluent_info = 'buffer'
        self.starting_volume = 0.000020 # 20 ul
        self.well_specs = None
        self.plate_specs = None
        self.starting_molecule_conc = 100 / CONCENTRATION_CONVERSION_FACTOR

    def tear_down(self):
        FileCreatorTestCase.tear_down(self)
        del self.log
        del self.transfer_jobs
        del self.dilution_data
        del self.transfer_data
        del self.number_sectors
        del self.source_sector
        del self.target_sector
        del self.rack_transfer_volume
        del self.is_biomek_transfer
        del self.source_rack_barcode
        del self.ignored_position_dil
        del self.ignored_positions_ct
        del self.shape
        del self.status
        del self.molecule_design
        del self.reservoir_specs
        del self.supplier
        del self.test_plate
        del self.plate_barcode
        del self.dilution_worklist
        del self.transfer_worklist
        del self.rack_transfer
        del self.dilution_job
        del self.ct_job
        del self.rack_job
        del self.well_max_volume
        del self.well_dead_volume
        del self.diluent_info
        del self.starting_volume
        del self.well_specs
        del self.plate_specs
        del self.starting_molecule_conc

    def _continue_setup(self):
        self.__create_container_dilution_worklist()
        self.__create_rack_transfer()
        self.__create_container_transfer_worklist()
        self.__create_test_plate()
        self.__create_transfer_jobs()
        self._create_tool()

    def __create_container_dilution_worklist(self):
        self.dilution_worklist = PlannedWorklist(label='Series Dilution')
        for pos_label, transfer_volume in self.dilution_data.iteritems():
            volume = transfer_volume / VOLUME_CONVERSION_FACTOR
            target_pos = get_rack_position_from_label(pos_label)
            pcd = PlannedContainerDilution(volume=volume,
                    target_position=target_pos, diluent_info=self.diluent_info)
            self.dilution_worklist.planned_transfers.append(pcd)

    def __create_rack_transfer(self):
        self.rack_transfer = PlannedRackTransfer(
                        volume=self.rack_transfer_volume,
                        source_sector_index=self.source_sector,
                        target_sector_index=self.target_sector,
                        sector_number=self.number_sectors)

    def __create_container_transfer_worklist(self):
        self.transfer_worklist = PlannedWorklist(label='Series Transfer')
        for pos_label, target_data in self.transfer_data.iteritems():
            source_pos = get_rack_position_from_label(pos_label)
            target_pos = get_rack_position_from_label(target_data[0])
            volume = target_data[1] / VOLUME_CONVERSION_FACTOR
            pct = PlannedContainerTransfer(volume=volume,
                        source_position=source_pos,
                        target_position=target_pos)
            self.transfer_worklist.planned_transfers.append(pct)

    def __create_test_plate(self):
        if self.well_specs is None:
            self.well_specs = WellSpecs(label='series test well specs',
                                        max_volume=self.well_max_volume,
                                        dead_volume=self.well_dead_volume,
                                        plate_specs=None)
        if self.plate_specs is None:
            self.plate_specs = PlateSpecs(label='series test plate specs',
                                          shape=self.shape,
                                          well_specs=self.well_specs)
        self.test_plate = self.plate_specs.create_rack(label='test rack',
                                                       status=self.status)
        self.test_plate.barcode = self.plate_barcode
        for container in self.test_plate.containers:
            rack_pos = container.location.position
            if rack_pos in self.ignored_position_dil: continue
            pos_label = rack_pos.label
            if not self.dilution_data.has_key(pos_label): continue
            sample = Sample(self.starting_volume, container)
            mol = Molecule(molecule_design=self.molecule_design,
                           supplier=self.supplier)
            sample.make_sample_molecule(mol, self.starting_molecule_conc)

    def __create_transfer_jobs(self):
        self.dilution_job = ContainerDilutionJob(index=0,
                planned_worklist=self.dilution_worklist,
                target_rack=self.test_plate,
                reservoir_specs=self.reservoir_specs,
                source_rack_barcode=self.source_rack_barcode,
                ignored_positions=self.ignored_position_dil,
                is_biomek_transfer=self.is_biomek_transfer)
        self.ct_job = ContainerTransferJob(index=2,
                planned_worklist=self.transfer_worklist,
                target_rack=self.test_plate,
                source_rack=self.test_plate,
                ignored_positions=self.ignored_positions_ct,
                is_biomek_transfer=self.is_biomek_transfer)
        self.rack_job = RackTransferJob(index=1,
                planned_rack_transfer=self.rack_transfer,
                target_rack=self.test_plate,
                source_rack=self.test_plate)
        self.transfer_jobs = [self.dilution_job, self.ct_job, self.rack_job]

    def _test_invalid_transfer_jobs(self):
        self._continue_setup()
        self.transfer_jobs = dict()
        self._test_and_expect_errors('The transfer job list must be a ' \
                                     'list object')
        self.transfer_jobs = [self.dilution_worklist]
        self._test_and_expect_errors('The transfer job must be a ' \
                                     'TransferJob object')

    def _test_duplicate_job_index(self):
        self._continue_setup()
        self.rack_job.index = 0
        self._test_and_expect_errors('Duplicate job index')

    def _test_failed_execution(self):
        self.well_dead_volume = 0.000060 # 60 ul
        self._continue_setup()
        self._test_and_expect_errors('Error when trying to execute transfer ' \
                                     'job')


class SeriesWorklistWriterTestCase(SeriesToolTestCase):

    def _create_tool(self):
        self.tool = SeriesWorklistWriter(transfer_jobs=self.transfer_jobs,
                                         log=self.log)

    def test_result(self):
        self._continue_setup()
        transfer_writer = ContainerTransferWorklistWriter(
                    planned_worklist=self.transfer_worklist,
                    target_rack=self.test_plate,
                    source_rack=self.test_plate,
                    log=self.log,
                    ignored_positions=self.ignored_positions_ct)
        self.assert_is_none(transfer_writer.get_result())
        stream_map = self.tool.get_result()
        self.assert_is_not_none(stream_map)
        self.assert_equal(len(stream_map), 3)
        for job_index, tool_stream in stream_map.iteritems():
            if job_index == 0:
                self._compare_csv_file_stream(tool_stream,
                                'series_container_dilution.csv')
            elif job_index == 1:
                self._compare_txt_file_stream(tool_stream,
                                'series_rack_transfer.txt')
            else:
                self._compare_csv_file_stream(tool_stream,
                                'series_container_transfer.csv')

    def test_result_ignored_positions(self):
        self.ignored_position_dil = [get_rack_position_from_label('A1')]
        self.ignored_positions_ct = [get_rack_position_from_label('B1')]
        self._continue_setup()
        stream_map = self.tool.get_result()
        self.assert_is_not_none(stream_map)
        self.assert_equal(len(stream_map), 3)
        for job_index, tool_stream in stream_map.iteritems():
            if job_index == 0:
                self._compare_csv_file_stream(tool_stream,
                                'series_container_dilution_ign.csv')
            elif job_index == 1:
                self._compare_txt_file_stream(tool_stream,
                                'series_rack_transfer.txt')
            else:
                self._compare_csv_file_stream(tool_stream,
                                'series_container_transfer_ign.csv')

    def test_overwrite_transfer_range(self):
        self.transfer_data = dict(B1=('B2', 1), B3=('B4', 1))
        self._continue_setup()
        self.ct_job.min_transfer_volume = 1
        self.assert_is_not_none(self.tool.get_result())

    def test_invalid_transfer_range(self):
        # belongs to "test_overwrite_transfer_range" but cannot be run in
        # the same test for ORM reasons
        self.transfer_data = dict(B1=('B2', 1), B3=('B4', 1))
        self._continue_setup()
        self._test_and_expect_errors('Some transfer volume are smaller than ' \
                                     'the allowed minimum transfer volume')

    def test_invalid_transfer_jobs(self):
        self._test_invalid_transfer_jobs()

    def test_duplicate_job_index(self):
        self._test_duplicate_job_index()

    def test_failed_execution(self):
        self._test_failed_execution()

    def test_failed_worklist_generation(self):
        self.well_max_volume = 0.000090 # 90 ul
        self._continue_setup()
        self._test_and_expect_errors('Error when trying to generate file ' \
                                     'for worklist')


class SeriesExecutorTestCase(SeriesToolTestCase):

    def _create_tool(self):
        self.tool = SeriesExecutor(transfer_jobs=self.transfer_jobs,
                                   user=self.user, log=self.log)

    def __check_execution_map(self, execution_map, number_containers=2):
        self.assert_equal(len(execution_map), 3)
        for job_index, executed_item in execution_map.iteritems():
            if job_index == 0:
                # dilution worklist
                self.assert_true(isinstance(executed_item, ExecutedWorklist))
                self.assert_equal(executed_item.planned_worklist.label,
                                  self.dilution_worklist.label)
                self.assert_equal(len(executed_item.executed_transfers),
                                  number_containers)
                self.assert_equal(
                            len(self.dilution_worklist.executed_worklists), 1)
                for et in executed_item.executed_transfers:
                    self.assert_equal(et.user, self.user)
                    self.assert_is_not_none(et.timestamp)
            elif job_index == 1:
                # rack transfer job
                self.assert_true(isinstance(executed_item,
                                            ExecutedRackTransfer))
                attr_names = ['sector_number', 'target_sector_index',
                              'source_sector_index']
                for attr_name in attr_names:
                    self.assert_equal(getattr(self.rack_transfer, attr_name),
                        getattr(executed_item.planned_transfer, attr_name))
                self.assert_equal(executed_item.user, self.user)
                self.assert_is_not_none(executed_item.timestamp)
            else:
                # container transfer job
                self.assert_true(isinstance(executed_item, ExecutedWorklist))
                self.assert_equal(executed_item.planned_worklist.label,
                                  self.transfer_worklist.label)
                self.assert_equal(len(executed_item.executed_transfers),
                                  number_containers)
                self.assert_equal(
                            len(self.transfer_worklist.executed_worklists), 1)
                for et in executed_item.executed_transfers:
                    self.assert_equal(et.user, self.user)
                    self.assert_is_not_none(et.timestamp)

    def __check_sample_molecule(self, sample):
        self.assert_equal(len(sample.sample_molecules), 1)
        sm = sample.sample_molecules[0]
        self.assert_equal(sm.molecule.molecule_design,
                          self.molecule_design)
        expected_conc = 20
        sm_conc = sm.concentration * CONCENTRATION_CONVERSION_FACTOR
        self.assert_equal(sm_conc, expected_conc)

    def test_result(self):
        self._continue_setup()
        transfer_executor = ContainerTransferWorklistExecutor(user=self.user,
                            planned_worklist=self.transfer_worklist,
                            target_rack=self.test_plate,
                            source_rack=self.test_plate,
                            log=self.log,
                            ignored_positions=self.ignored_positions_ct,
                            is_biomek_transfer=self.is_biomek_transfer)
        self.assert_is_none(transfer_executor.get_result())
        execution_map = self.tool.get_result()
        self.assert_is_not_none(execution_map)
        self.__check_execution_map(execution_map, number_containers=2)
        target_data = dict(B1=20, B2=30, B3=20, B4=30)
        for container in self.test_plate.containers:
            pos_label = container.location.position.label
            sample = container.sample
            if self.dilution_data.has_key(pos_label):
                sample_volume = sample.volume * VOLUME_CONVERSION_FACTOR
                self.assert_equal(sample_volume, 50)
                self.__check_sample_molecule(sample)
            elif target_data.has_key(pos_label):
                expected_volume = target_data[pos_label]
                sample_volume = sample.volume * VOLUME_CONVERSION_FACTOR
                self.assert_equal(sample_volume, expected_volume)
                self.__check_sample_molecule(sample)
            else:
                self.assert_is_none(sample)

    def test_result_ignored_positions(self):
        self.ignored_position_dil = [get_rack_position_from_label('A1')]
        self.ignored_positions_ct = [get_rack_position_from_label('B1')]
        self._continue_setup()
        execution_map = self.tool.get_result()
        self.assert_is_not_none(execution_map)
        self.__check_execution_map(execution_map, number_containers=1)
        target_data = dict(B3=20, B4=30)
        for container in self.test_plate.containers:
            pos_label = container.location.position.label
            sample = container.sample
            if pos_label == 'A3':
                sample_volume = sample.volume * VOLUME_CONVERSION_FACTOR
                self.assert_equal(sample_volume, 50)
                self.__check_sample_molecule(sample)
            elif target_data.has_key(pos_label):
                expected_volume = target_data[pos_label]
                sample_volume = sample.volume * VOLUME_CONVERSION_FACTOR
                self.assert_equal(sample_volume, expected_volume)
                self.__check_sample_molecule(sample)
            else:
                self.assert_is_none(sample)

    def test_result_is_biomek_transfer(self):
        self.transfer_data['B1'] = ('B2', 1)
        self._continue_setup()
        self._test_and_expect_errors('Some transfer volumes are smaller than ' \
                                     'the allowed minimum transfer volume')
        self.is_biomek_transfer = False
        self._continue_setup()
        execution_map = self.tool.get_result()
        self.assert_is_not_none(execution_map)
        self.__check_execution_map(execution_map)
        target_data = dict(B1=49, B2=1, B3=20, B4=30)
        for container in self.test_plate.containers:
            pos_label = container.location.position.label
            sample = container.sample
            if self.dilution_data.has_key(pos_label):
                sample_volume = sample.volume * VOLUME_CONVERSION_FACTOR
                self.assert_equal(sample_volume, 50)
                self.__check_sample_molecule(sample)
            elif target_data.has_key(pos_label):
                expected_volume = target_data[pos_label]
                sample_volume = sample.volume * VOLUME_CONVERSION_FACTOR
                self.assert_equal(sample_volume, expected_volume)
                self.__check_sample_molecule(sample)
            else:
                self.assert_is_none(sample)

    def test_overwrite_transfer_range(self):
        self.transfer_data = dict(B1=('B2', 1), B3=('B4', 1))
        self._continue_setup()
        self.ct_job.min_transfer_volume = 1
        self.assert_is_not_none(self.tool.get_result())

    def test_invalid_transfer_jobs(self):
        self._test_invalid_transfer_jobs()

    def test_invalid_user(self):
        self._continue_setup()
        self.user = self.user.username
        self._test_and_expect_errors('The user must be a User object')

    def test_duplicate_job_index(self):
        self._test_duplicate_job_index()

    def test_failed_execution(self):
        self._test_failed_execution()


class RackTransferWriterTestCase(FileCreatorTestCase):
    """
    Three transfers:

    1. small to large plate (target sector 1)
    2. sector 1 to 2 intra-plate
    3. one to one (replicate)
    """

    def set_up(self):
        FileCreatorTestCase.set_up(self)
        self.rack_transfer_jobs = []
        self.log = TestingLog()
        self.WL_PATH = 'thelma:tests/tools/worklists/test_files/'
        self.TEST_FILE = 'rack_transfer_test.txt'
        # position data (md_id)
        self.position_data = dict(A1=11, A2=12)
        self.volume1 = 50 / VOLUME_CONVERSION_FACTOR
        self.volume2 = 20 / VOLUME_CONVERSION_FACTOR
        self.volume3 = 10 / VOLUME_CONVERSION_FACTOR
        self.small_plate = None
        self.int_plate = None
        self.rep_plate = None
        self.small_plate_barcode = '09999911'
        self.int_plate_barcode = '09999922'
        self.rep_plate_barcode = '09999933'
        # other setup values
        self.status = get_item_status_managed()
        self.well_specs = None
        self.plate_specs_small = None
        self.plate_specs_large = None
        self.source_volume = 100 / VOLUME_CONVERSION_FACTOR

    def tear_down(self):
        FileCreatorTestCase.tear_down(self)
        del self.rack_transfer_jobs
        del self.log
        del self.TEST_FILE
        del self.position_data
        del self.volume1
        del self.volume2
        del self.volume3
        del self.small_plate
        del self.int_plate
        del self.rep_plate
        del self.small_plate_barcode
        del self.int_plate_barcode
        del self.rep_plate_barcode
        del self.status
        del self.well_specs
        del self.plate_specs_small
        del self.plate_specs_large
        del self.source_volume

    def _create_tool(self):
        self.tool = RackTransferWriter(log=self.log,
                            rack_transfer_jobs=self.rack_transfer_jobs)

    def _continue_setup(self):
        self.__create_plate_specs()
        self.__create_small_plate()
        self.__create_other_plates()
        self.__create_transfer_jobs()
        self._create_tool()

    def __create_plate_specs(self):
        self.well_specs = WellSpecs(label='rack transfer test well specs',
                        max_volume=200 / VOLUME_CONVERSION_FACTOR,
                        dead_volume=10 / VOLUME_CONVERSION_FACTOR,
                        plate_specs=None)
        self.plate_specs_small = PlateSpecs(label='small plate specs',
                                shape=get_96_rack_shape(),
                                well_specs=self.well_specs)
        self.plate_specs_large = PlateSpecs(label='large plate specs',
                                shape=get_384_rack_shape(),
                                well_specs=self.well_specs)

    def __create_small_plate(self):
        self.small_plate = self.plate_specs_small.create_rack(
                                label='small plate', status=self.status)
        self.small_plate.barcode = self.small_plate_barcode
        conc = 10000 / CONCENTRATION_CONVERSION_FACTOR
        for container in self.small_plate.containers:
            pos_label = container.location.position.label
            if not self.position_data.has_key(pos_label): continue
            sample = Sample(self.source_volume, container)
            md_id = self.position_data[pos_label]
            md = self._get_entity(IMoleculeDesign, str(md_id))
            mol = Molecule(molecule_design=md, supplier=None)
            sample.make_sample_molecule(mol, conc)

    def __create_other_plates(self):
        self.int_plate = self.plate_specs_large.create_rack(
                                label='intermediate plate', status=self.status)
        self.int_plate.barcode = self.int_plate_barcode
        self.rep_plate = self.plate_specs_large.create_rack(
                                label='replicate plate', status=self.status)
        self.rep_plate.barcode = self.rep_plate_barcode

    def __create_transfer_jobs(self):
        rt1 = PlannedRackTransfer(volume=self.volume1, sector_number=4,
                                  source_sector_index=0, target_sector_index=1)
        rtj1 = RackTransferJob(index=0, planned_rack_transfer=rt1,
                               target_rack=self.int_plate,
                               source_rack=self.small_plate)
        self.rack_transfer_jobs.append(rtj1)
        rt2 = PlannedRackTransfer(volume=self.volume2, sector_number=4,
                                  source_sector_index=1, target_sector_index=2)
        rtj2 = RackTransferJob(index=1, planned_rack_transfer=rt2,
                        target_rack=self.int_plate, source_rack=self.int_plate)
        self.rack_transfer_jobs.append(rtj2)
        rt3 = PlannedRackTransfer(volume=self.volume3, sector_number=1,
                                  source_sector_index=0, target_sector_index=0)
        rtj3 = RackTransferJob(index=2, planned_rack_transfer=rt3,
                    target_rack=self.rep_plate, source_rack=self.int_plate)
        self.rack_transfer_jobs.append(rtj3)

    def test_result(self):
        self._continue_setup()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        tool_lines = FileComparisonUtils.convert_stream(tool_stream)
        exp_stream = self._get_expected_worklist_stream(self.TEST_FILE)
        exp_lines = FileComparisonUtils.convert_stream(exp_stream)
        self.assert_equal(len(tool_lines), len(exp_lines))
        for i in range(len(tool_lines)):
            t_lin = tool_lines[i]
            e_lin = exp_lines[i]
            self.assert_equal(t_lin, e_lin)

    def test_invalid_rack_transfer_jobs(self):
        self._continue_setup()
        a1_pos = get_rack_position_from_label('A1')
        pct = PlannedContainerTransfer(volume=self.volume1,
                        source_position=a1_pos, target_position=a1_pos)
        worklist = PlannedWorklist(label='invalid worklist',
                                   planned_transfers=[pct])
        pctj = ContainerTransferJob(index=3, planned_worklist=worklist,
                                    target_rack=self.rep_plate,
                                    source_rack=self.small_plate,
                                    is_biomek_transfer=True)
        self.rack_transfer_jobs.append(pctj)
        self._test_and_expect_errors('The rack transfer job must be a ' \
                                     'RackTransferJob object')

    def test_duplicate_job_index(self):
        self._continue_setup()
        for job in self.rack_transfer_jobs:
            job.index = 0
        self._test_and_expect_errors('Duplicate job index')

    def test_failed_execution(self):
        self.volume2 = 50 / VOLUME_CONVERSION_FACTOR
        self._continue_setup()
        self._test_and_expect_errors('Error when trying to execute ' \
                                     'transfer job')
