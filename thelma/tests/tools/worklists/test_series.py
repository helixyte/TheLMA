"""
Tests for worklist series tools.

AAB
"""
from everest.repositories.rdb.testing import check_attributes
from thelma.automation.semiconstants import get_384_rack_shape
from thelma.automation.semiconstants import get_96_rack_shape
from thelma.automation.semiconstants import get_item_status_managed
from thelma.automation.semiconstants import get_pipetting_specs_biomek
from thelma.automation.semiconstants import get_pipetting_specs_cybio
from thelma.automation.semiconstants import get_pipetting_specs_manual
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.tools.worklists.biomek \
    import SampleTransferWorklistWriter
from thelma.automation.tools.worklists.execution \
    import SampleTransferWorklistExecutor
from thelma.automation.tools.worklists.series import RackSampleTransferJob
from thelma.automation.tools.worklists.series import RackSampleTransferWriter
from thelma.automation.tools.worklists.series import SampleDilutionJob
from thelma.automation.tools.worklists.series import SampleTransferJob
from thelma.automation.tools.worklists.series import SerialWriterExecutorTool
from thelma.automation.tools.worklists.series import SeriesExecutor
from thelma.automation.tools.worklists.series import _SeriesWorklistWriter
from thelma.automation.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.interfaces import IMoleculeDesign
from thelma.interfaces import IOrganization
from thelma.interfaces import IReservoirSpecs
from thelma.interfaces import IUser
from thelma.models.container import WellSpecs
from thelma.models.liquidtransfer import ExecutedRackSampleTransfer
from thelma.models.liquidtransfer import ExecutedWorklist
from thelma.models.liquidtransfer import PlannedRackSampleTransfer
from thelma.models.liquidtransfer import PlannedSampleDilution
from thelma.models.liquidtransfer import PlannedSampleTransfer
from thelma.models.liquidtransfer import PlannedWorklist
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.rack import PlateSpecs
from thelma.models.sample import Molecule
from thelma.models.sample import Sample
from thelma.models.user import User
from thelma.models.utils import get_user
from thelma.tests.tools.tooltestingutils import FileComparisonUtils
from thelma.tests.tools.tooltestingutils import FileCreatorTestCase
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase


class _TransferJobTestCase(ToolsAndUtilsTestCase):

    TRANSFER_JOB_CLS = None

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.index = 3
        self.target_rack = self._create_plate()
        self.pipetting_specs = get_pipetting_specs_biomek()
        self.executor_user = get_user('sachse')

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.pipetting_specs
        del self.index
        del self.target_rack

    def _get_init_data(self):
        pw = self._create_planned_worklist(label='test',
                                           pipetting_specs=self.pipetting_specs)
        return dict(planned_worklist=pw,
                    index=self.index,
                    target_rack=self.target_rack)

    def _test_get_writer(self):
        test_data = self.__prepare_get_tool_test()
        tj1, kw = test_data[0], test_data[1]
        writer = tj1.get_worklist_writer(None)
        self.assert_is_not_none(writer)
        check_attributes(writer, kw)
        # test unregistered pipetting technique
        self.pipetting_specs = self._create_pipetting_specs()
        test_data_no_writer = self.__prepare_get_tool_test()
        tj_no_writer = test_data_no_writer[0]
        self.assert_is_none(tj_no_writer.get_worklist_writer(None))

    def _test_get_executor(self, del_attributes=None, add_attributes=None):
        test_data = self.__prepare_get_tool_test(include_user=True)
        tj, kw = test_data[0], test_data[1]
        executor = tj.get_executor(None, self.executor_user)
        self.assert_is_not_none(executor)
        if not del_attributes is None:
            for attr_name in del_attributes: del kw[attr_name]
        if not add_attributes is None:
            for attr_name, attr_value in add_attributes.iteritems():
                kw[attr_name] = attr_value
        check_attributes(executor, kw)

    def __prepare_get_tool_test(self, include_user=False):
        kw = self._get_init_data()
        tj = self.TRANSFER_JOB_CLS(**kw) #pylint: disable=E1102
        check_attributes(tj, kw)
        del kw['index']
        if include_user:
            kw['user'] = self.executor_user
        return (tj, kw)


class SampleDilutionJobTestCase(_TransferJobTestCase):

    TRANSFER_JOB_CLS = SampleDilutionJob

    def set_up(self):
        _TransferJobTestCase.set_up(self)
        self.reservoir_specs = self._create_reservoir_specs()
        self.ignored_positions = [get_rack_position_from_label('A1')]
        self.source_rack_barcode = '09999994'

    def tear_down(self):
        _TransferJobTestCase.tear_down(self)
        del self.reservoir_specs
        del self.ignored_positions
        del self.source_rack_barcode

    def _get_init_data(self):
        kw = _TransferJobTestCase._get_init_data(self)
        kw['reservoir_specs'] = self.reservoir_specs
        kw['source_rack_barcode'] = self.source_rack_barcode
        kw['ignored_positions'] = self.ignored_positions
        return kw

    def test_get_writer(self):
        self._test_get_writer()

    def test_get_executor(self):
        self._test_get_executor(['source_rack_barcode'])


class SampleTransferJobTestCase(_TransferJobTestCase):

    TRANSFER_JOB_CLS = SampleTransferJob

    def set_up(self):
        _TransferJobTestCase.set_up(self)
        self.source_rack = self._create_tube_rack()
        self.ignored_positions = [get_rack_position_from_label('A1')]

    def tear_down(self):
        _TransferJobTestCase.tear_down(self)
        del self.source_rack
        del self.ignored_positions

    def _get_init_data(self):
        kw = _TransferJobTestCase._get_init_data(self)
        kw['source_rack'] = self.source_rack
        kw['ignored_positions'] = self.ignored_positions
        return kw

    def test_get_writer(self):
        self._test_get_writer()

    def test_get_executor(self):
        self._test_get_executor()


class RackSampleTransferJobTestCase(_TransferJobTestCase):

    TRANSFER_JOB_CLS = RackSampleTransferJob

    def set_up(self):
        _TransferJobTestCase.set_up(self)
        self.source_rack = self._create_tube_rack()
        self.prst = self._create_planned_rack_sample_transfer()

    def tear_down(self):
        _TransferJobTestCase.tear_down(self)
        del self.source_rack
        del self.prst

    def _get_init_data(self):
        return dict(planned_rack_sample_transfer=self.prst,
                    index=self.index,
                    target_rack=self.target_rack,
                    source_rack=self.source_rack)

    def test_get_writer(self):
        # there are no writers for rack transfer jobs
        kw = self._get_init_data()
        tj = self.TRANSFER_JOB_CLS(**kw)
        check_attributes(tj, kw)
        self.assert_is_none(tj.get_worklist_writer(None))

    def test_get_executor(self):
        add_attributes = dict(pipetting_specs=get_pipetting_specs_cybio())
        self._test_get_executor(add_attributes=add_attributes)


class _SeriesWorklistWriterDummy(_SeriesWorklistWriter):
    """
    Only serves for testing.
    """
    pass


class _SeriesExecutorDummy(SeriesExecutor):
    """
    Only serves for testing.
    """
    pass


class _SerialWriterExecutorDummy(SerialWriterExecutorTool):
    """
    Only serves for testing. Does not add real functionality.
    """

    FILE_NAME_RST = 'series_rack_transfer.txt'
    WORKLIST_LABEL_RST = 'rack_sample_transfer_wl'
    NAME = 'Serial Writer Executor Dummy'

    def __init__(self, transfer_jobs, mode, user=None, **kw):
        SerialWriterExecutorTool.__init__(self, mode, user=user, **kw)
        self.__transfer_jobs = transfer_jobs
        self.__rack_sample_transfer_worklist = None

    def _create_transfer_jobs(self):
        self._transfer_jobs = self.__transfer_jobs
        for i, job in self._transfer_jobs.iteritems():
            if isinstance(job, RackSampleTransferJob):
                if self.__rack_sample_transfer_worklist is None:
                    self.__rack_sample_transfer_worklist = PlannedWorklist(
                            label=self.WORKLIST_LABEL_RST,
                            transfer_type=TRANSFER_TYPES.RACK_SAMPLE_TRANSFER,
                            pipetting_specs=get_pipetting_specs_cybio())
            self._rack_transfer_worklists[i] = \
                                        self.__rack_sample_transfer_worklist

    def _get_file_map(self, merged_stream_map, rack_transfer_stream):
        file_map = {self.FILE_NAME_RST : rack_transfer_stream}
        for wl, stream in merged_stream_map.iteritems():
            file_map['%s.csv' % (wl)] = stream
        return file_map


class _SeriesToolTestCase(FileCreatorTestCase):
    """
    Assumes a 3-step intra-rack transfer:
    1. dilution (20 to 80 ul in 2 positions of sector 0)
    2. rack transfer (50 ul  (= 1/2) from sector 0 to 2)
    3. sample transfer from sector 2 positions to neighbouring empty
        positions (30 ul)
    """

    _DILUTION_WORKLIST = 'series_dilution'
    _TRANSFER_WORKLIST = 'series_transfer'

    _DILUTION_INDEX = 1
    _RACK_TRANSFER_INDEX = 2
    _TRANSFER_INDEX = 3

    def set_up(self):
        FileCreatorTestCase.set_up(self)
        self.WL_PATH = 'thelma:tests/tools/worklists/series/'
        self.transfer_jobs = None
        # transfer data
        self.dilution_data = dict(A1=80, A3=80)
        self.transfer_data = dict(B1=('B2', 30), B3=('B4', 30))
        self.number_sectors = 4
        self.source_sector = 0
        self.target_sector = 2
        self.rack_transfer_volume = 0.000050 # 50 ul
        self.source_rack_barcode = 'source_reservoir'
        self.ignored_position_dil = []
        self.ignored_positions_ct = None
        self.pipetting_specs_cd_ct = get_pipetting_specs_biomek()
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
        self.transfer_job = None
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
        del self.transfer_jobs
        del self.dilution_data
        del self.transfer_data
        del self.number_sectors
        del self.source_sector
        del self.target_sector
        del self.rack_transfer_volume
        del self.source_rack_barcode
        del self.ignored_position_dil
        del self.ignored_positions_ct
        del self.pipetting_specs_cd_ct
        del self.shape
        del self.status
        del self.molecule_design
        del self.reservoir_specs
        del self.test_plate
        del self.plate_barcode
        del self.dilution_worklist
        del self.transfer_worklist
        del self.rack_transfer
        del self.dilution_job
        del self.transfer_job
        del self.rack_job
        del self.well_max_volume
        del self.well_dead_volume
        del self.diluent_info
        del self.starting_volume
        del self.well_specs
        del self.plate_specs
        del self.starting_molecule_conc

    def _continue_setup(self):
        self.__create_sample_dilution_worklist()
        self.__create_rack_sample_transfer()
        self.__create_sample_transfer_worklist()
        self.__create_test_plate()
        self.__create_transfer_jobs()
        self._create_tool()

    def __create_sample_dilution_worklist(self):
        self.dilution_worklist = \
                PlannedWorklist(self._DILUTION_WORKLIST,
                                TRANSFER_TYPES.SAMPLE_DILUTION,
                                self.pipetting_specs_cd_ct)
        for pos_label, transfer_volume in self.dilution_data.iteritems():
            volume = transfer_volume / VOLUME_CONVERSION_FACTOR
            target_pos = get_rack_position_from_label(pos_label)
            psd = PlannedSampleDilution.get_entity(volume=volume,
                    target_position=target_pos, diluent_info=self.diluent_info)
            self.dilution_worklist.planned_liquid_transfers.append(psd)

    def __create_rack_sample_transfer(self):
        self.rack_transfer = PlannedRackSampleTransfer.get_entity(
                                                self.rack_transfer_volume,
                                                self.number_sectors,
                                                self.source_sector,
                                                self.target_sector)

    def __create_sample_transfer_worklist(self):
        self.transfer_worklist = PlannedWorklist(label=self._TRANSFER_WORKLIST,
                                 pipetting_specs=self.pipetting_specs_cd_ct,
                                 transfer_type=TRANSFER_TYPES.SAMPLE_TRANSFER)
        for pos_label, target_data in self.transfer_data.iteritems():
            source_pos = get_rack_position_from_label(pos_label)
            target_pos = get_rack_position_from_label(target_data[0])
            volume = target_data[1] / VOLUME_CONVERSION_FACTOR
            pst = PlannedSampleTransfer.get_entity(volume=volume,
                        source_position=source_pos,
                        target_position=target_pos)
            self.transfer_worklist.planned_liquid_transfers.append(pst)

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
        self.dilution_job = SampleDilutionJob(index=1,
                planned_worklist=self.dilution_worklist,
                target_rack=self.test_plate,
                reservoir_specs=self.reservoir_specs,
                source_rack_barcode=self.source_rack_barcode,
                ignored_positions=self.ignored_position_dil)
        self.transfer_job = SampleTransferJob(index=3,
                planned_worklist=self.transfer_worklist,
                target_rack=self.test_plate,
                source_rack=self.test_plate,
                ignored_positions=self.ignored_positions_ct)
        self.rack_job = RackSampleTransferJob(index=2,
                planned_rack_sample_transfer=self.rack_transfer,
                target_rack=self.test_plate,
                source_rack=self.test_plate)
        self.transfer_jobs = {self._DILUTION_INDEX : self.dilution_job,
                              self._RACK_TRANSFER_INDEX : self.rack_job,
                              self._TRANSFER_INDEX : self.transfer_job}

    def _test_invalid_transfer_jobs(self):
        ori_jobs = self.transfer_jobs
        self.transfer_jobs = dict()
        self._test_and_expect_errors('The transfer job map is empty!')
        self.transfer_jobs = ori_jobs

    def _test_invalid_user(self):
        ori_user = self.executor_user
        self.executor_user = self.executor_user.username
        self._test_and_expect_errors('The user must be a User object')
        self.executor_user = ori_user

    def _test_failed_execution(self):
        self.well_dead_volume = 0.000060 # 60 ul
        self._continue_setup()
        self._test_and_expect_errors('Error when trying to execute transfer ' \
                                     'job')

    def _check_sample_molecule(self, sample):
        self.assert_equal(len(sample.sample_molecules), 1)
        sm = sample.sample_molecules[0]
        self.assert_equal(sm.molecule.molecule_design,
                          self.molecule_design)
        expected_conc = 20
        sm_conc = sm.concentration * CONCENTRATION_CONVERSION_FACTOR
        self.assert_equal(sm_conc, expected_conc)


class SeriesWorklistWriterTestCase(_SeriesToolTestCase):

    def _create_tool(self):
        self.tool = _SeriesWorklistWriterDummy(self.transfer_jobs)

    def _get_file_name_for_index(self, job_index):
        if job_index == self._DILUTION_INDEX:
            return '%s.csv' % (self.dilution_worklist.label)
        elif job_index == self._RACK_TRANSFER_INDEX:
            return _SerialWriterExecutorDummy.FILE_NAME_RST
        else:
            return '%s.csv' % (self.transfer_worklist.label)

    def __check_result(self):
        stream_map = self.tool.get_result()
        self.assert_is_not_none(stream_map)
        self.assert_equal(len(stream_map), 3)
        for job_index, tool_stream in stream_map.iteritems():
            fn = self._get_file_name_for_index(job_index)
            if fn.endswith('.txt'):
                self._compare_txt_file_stream(tool_stream, fn)
            else:
                self._compare_csv_file_stream(tool_stream, fn)

    def test_result(self):
        self._continue_setup()
        transfer_writer = SampleTransferWorklistWriter(
                                self.transfer_worklist,
                                self.test_plate,
                                self.test_plate,
                                ignored_positions=self.ignored_positions_ct)
        self.assert_is_none(transfer_writer.get_result())
        self.__check_result()

    def test_result_ignored_positions(self):
        self.ignored_position_dil = [get_rack_position_from_label('A1')]
        self.ignored_positions_ct = [get_rack_position_from_label('B1')]
        self._continue_setup()
        self.dilution_worklist.label = 'series_dilution_ign'
        self.transfer_worklist.label = 'series_transfer_ign'
        self.__check_result()

    def test_invalid_input_values(self):
        self._continue_setup()
        self._test_invalid_transfer_jobs()
        self.transfer_jobs = []
        self._test_and_expect_errors('The transfer job map must be a dict ' \
                                     'object (obtained: list)')

    def test_failed_execution(self):
        self._test_failed_execution()

    def test_failed_worklist_generation(self):
        self.well_max_volume = 0.000090 # 90 ul
        self._continue_setup()
        self._test_and_expect_errors('Error when trying to generate file for ' \
                                     'worklist "series_dilution"')


class SeriesExecutorTestCase(_SeriesToolTestCase):

    def _create_tool(self):
        self.tool = _SeriesExecutorDummy(self.transfer_jobs,
                                         self.executor_user)

    def set_up(self):
        _SeriesToolTestCase.set_up(self)
        self.executor_user = self._get_entity(IUser, 'sachse')

    def __check_execution_map(self, execution_map, number_containers=2):
        self.assert_equal(len(execution_map), 3)
        for job_index, executed_item in execution_map.iteritems():
            if job_index == self._RACK_TRANSFER_INDEX:
                self.assert_true(isinstance(executed_item,
                                            ExecutedRackSampleTransfer))
                self.assert_equal(executed_item.transfer_type,
                                  TRANSFER_TYPES.RACK_SAMPLE_TRANSFER)
                self.assert_is_not_none(executed_item.timestamp)
                self.assert_equal(executed_item.user, self.executor_user)
                attr_names = ['number_sectors', 'target_sector_index',
                              'source_sector_index']
                prst = executed_item.planned_liquid_transfer
                for attr_name in attr_names:
                    self.assert_equal(getattr(self.rack_transfer, attr_name),
                                      getattr(prst, attr_name))
            else:
                self.assert_true(isinstance(executed_item, ExecutedWorklist))
                for elt in executed_item.executed_liquid_transfers:
                    self.assert_equal(elt.user, self.executor_user)
                    self.assert_is_not_none(elt.timestamp)
                if job_index == self._DILUTION_INDEX:
                    self.assert_equal(
                            len(self.dilution_worklist.executed_worklists), 1)
                    self.assert_equal(executed_item.planned_worklist.label,
                                      self._DILUTION_WORKLIST)
                    self.assert_equal(number_containers,
                              len(executed_item.executed_liquid_transfers))
                else:
                    self.assert_equal(
                            len(self.transfer_worklist.executed_worklists), 1)
                    self.assert_equal(executed_item.planned_worklist.label,
                                      self._TRANSFER_WORKLIST)
                    self.assert_equal(number_containers,
                              len(executed_item.executed_liquid_transfers))

    def test_result(self):
        self._continue_setup()
        transfer_executor = SampleTransferWorklistExecutor(
                                self.user,
                                self.transfer_worklist,
                                self.test_plate,
                                self.test_plate,
                                self.pipetting_specs_cd_ct,
                                ignored_positions=self.ignored_positions_ct)
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
                self._check_sample_molecule(sample)
            elif target_data.has_key(pos_label):
                expected_volume = target_data[pos_label]
                sample_volume = sample.volume * VOLUME_CONVERSION_FACTOR
                self.assert_equal(sample_volume, expected_volume)
                self._check_sample_molecule(sample)
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
                self._check_sample_molecule(sample)
            elif target_data.has_key(pos_label):
                expected_volume = target_data[pos_label]
                sample_volume = sample.volume * VOLUME_CONVERSION_FACTOR
                self.assert_equal(sample_volume, expected_volume)
                self._check_sample_molecule(sample)
            else:
                self.assert_is_none(sample)

    def test_result_pipetting_specs(self):
        self.transfer_data['B1'] = ('B2', 1)
        self._continue_setup()
        self._test_and_expect_errors('Some transfer volumes are smaller than ' \
                                     'the allowed minimum transfer volume')
        self.pipetting_specs_cd_ct = get_pipetting_specs_manual()
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
                self._check_sample_molecule(sample)
            elif target_data.has_key(pos_label):
                expected_volume = target_data[pos_label]
                sample_volume = sample.volume * VOLUME_CONVERSION_FACTOR
                self.assert_equal(sample_volume, expected_volume)
                self._check_sample_molecule(sample)
            else:
                self.assert_is_none(sample)

    def test_invalid_input_values(self):
        self._continue_setup()
        self._test_invalid_transfer_jobs()
        self._test_invalid_user()

    def test_failed_execution(self):
        self._test_failed_execution()


class SerialWriterExecutorTestCase(_SeriesToolTestCase):

    TEST_CLS = _SerialWriterExecutorDummy

    def set_up(self):
        _SeriesToolTestCase.set_up(self)
        self.mode = None

    def tear_down(self):
        _SeriesToolTestCase.tear_down(self)
        del self.mode

    def _create_tool(self):
        self.tool = _SerialWriterExecutorDummy(transfer_jobs=self.transfer_jobs,
                                               mode=self.mode,
                                               user=self.executor_user)

    def test_writer(self):
        self._continue_setup()
        self.tool = self.TEST_CLS.create_writer(
                                        transfer_jobs=self.transfer_jobs)
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        archive = self._get_zip_archive(zip_stream)
        self.assert_equal(len(archive.namelist()), 3)
        for fn in archive.namelist():
            tool_content = archive.read(fn)
            if fn.endswith('.txt'):
                self._compare_txt_file_content(tool_content, fn)
            else:
                self._compare_csv_file_content(tool_content, fn)

    def test_executor(self):
        self._continue_setup()
        self.executor_user = self._get_entity(IUser)
        self.tool = self.TEST_CLS.create_executor(user=self.executor_user,
                                    transfer_jobs=self.transfer_jobs)
        execution_list = self.tool.get_result()
        self.__check_execution_list(execution_list)

    def __check_execution_list(self, execution_list, number_containers=2):
        self.assert_equal(len(execution_list), 3)
        for executed_worklist in execution_list:
            self.assert_true(isinstance(executed_worklist, ExecutedWorklist))
            for elt in executed_worklist.executed_liquid_transfers:
                self.assert_equal(elt.user, self.executor_user)
                self.assert_is_not_none(elt.timestamp)
            label = executed_worklist.planned_worklist.label
            if label == self.TEST_CLS.WORKLIST_LABEL_RST:
                self.assert_equal(1,
                              len(executed_worklist.executed_liquid_transfers))
                erst = executed_worklist.executed_liquid_transfers[0]
                attr_names = ['number_sectors', 'target_sector_index',
                              'source_sector_index']
                prst = erst.planned_liquid_transfer
                for attr_name in attr_names:
                    self.assert_equal(getattr(self.rack_transfer, attr_name),
                                      getattr(prst, attr_name))
            elif label == self._DILUTION_WORKLIST:
                self.assert_equal(
                            len(self.dilution_worklist.executed_worklists), 1)
                self.assert_equal(number_containers,
                              len(executed_worklist.executed_liquid_transfers))
            else:
                self.assert_equal(executed_worklist.planned_worklist.label,
                                  self._TRANSFER_WORKLIST)
                self.assert_equal(number_containers,
                              len(executed_worklist.executed_liquid_transfers))

    def test_invalid_input_values(self):
        self._continue_setup()
        self.executor_user = self._get_entity(IUser, 'sachse')
        self._test_and_expect_errors('The mode must be a str object')
        self.mode = 'invalid'
        self._test_and_expect_errors('Unexpected mode: invalid. Allowed ' \
                                     'modes: execute, print.')
        self.mode = self.TEST_CLS.MODE_EXECUTE
        self._test_invalid_transfer_jobs()
        self._test_invalid_user()
        self.mode = self.TEST_CLS.MODE_PRINT_WORKLISTS
        self.executor_user = None
        self._create_tool()
        res = self.tool.get_result()
        self.assert_is_not_none(res)
        self.assert_false(self.tool.has_errors())

    def test_failed_execution(self):
        self.mode = self.TEST_CLS.MODE_EXECUTE
        self.executor_user = self._get_entity(IUser, 'sachse')
        self._test_failed_execution()
        self._check_error_messages('Error when running serial worklist ' \
                                   'executor!')

    def test_failed_worklist_generation(self):
        self.mode = self.TEST_CLS.MODE_PRINT_WORKLISTS
        self.well_max_volume = 0.000090 # 90 ul
        self._continue_setup()
        self._test_and_expect_errors('Error when trying to generate file ' \
                                     'for worklist')
        self._check_error_messages('Error when running serial worklist printer')


class RackSampleTransferWriterTestCase(FileCreatorTestCase):
    """
    Three transfers:

    1. small to large plate (target sector 1)
    2. sector 1 to 2 intra-plate
    3. one to one (replicate)
    """

    def set_up(self):
        FileCreatorTestCase.set_up(self)
        self.rack_transfer_jobs = dict()
        self.WL_PATH = 'thelma:tests/tools/worklists/series/'
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
        self.tool = RackSampleTransferWriter(self.rack_transfer_jobs)

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
        rt1 = PlannedRackSampleTransfer.get_entity(self.volume1, 4, 0, 1)
        rtj1 = RackSampleTransferJob(0, rt1, self.int_plate, self.small_plate)
        self.rack_transfer_jobs[0] = rtj1
        rt2 = PlannedRackSampleTransfer.get_entity(self.volume2, 4, 1, 2)
        rtj2 = RackSampleTransferJob(1, rt2, self.int_plate, self.int_plate)
        self.rack_transfer_jobs[1] = rtj2
        rt3 = PlannedRackSampleTransfer.get_entity(self.volume3, 1, 0, 0)
        rtj3 = RackSampleTransferJob(2, rt3, self.rep_plate, self.int_plate)
        self.rack_transfer_jobs[2] = rtj3

    def test_result(self):
        self._continue_setup()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        tool_lines = FileComparisonUtils.convert_stream(tool_stream)
        exp_stream = self._get_expected_file_stream(self.TEST_FILE)
        exp_lines = FileComparisonUtils.convert_stream(exp_stream)
        self.assert_equal(len(tool_lines), len(exp_lines))
        for i in range(len(tool_lines)):
            t_lin = tool_lines[i]
            e_lin = exp_lines[i]
            self.assert_equal(t_lin, e_lin)

    def test_invalid_rack_transfer_jobs(self):
        self._continue_setup()
        a1_pos = get_rack_position_from_label('A1')
        pst = PlannedSampleTransfer.get_entity(volume=self.volume1,
                        source_position=a1_pos, target_position=a1_pos)
        worklist = PlannedWorklist(label='invalid worklist',
                                   planned_liquid_transfers=[pst],
                                   pipetting_specs=get_pipetting_specs_biomek(),
                                   transfer_type=TRANSFER_TYPES.SAMPLE_TRANSFER)
        pstj = SampleTransferJob(index=3, planned_worklist=worklist,
                                target_rack=self.rep_plate,
                                source_rack=self.small_plate)
        self.rack_transfer_jobs[0] = pstj
        self._test_and_expect_errors('The rack transfer job must be a ' \
                                     'RackSampleTransferJob object')

    def test_failed_execution(self):
        self.volume2 = 50 / VOLUME_CONVERSION_FACTOR
        self._continue_setup()
        self._test_and_expect_errors('Error when trying to execute ' \
                                     'transfer job')
