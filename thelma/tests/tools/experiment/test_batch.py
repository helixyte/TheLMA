"""
Tests for the experiment batch tools.

AAB
"""
from thelma.automation.tools.experiment.batch \
    import ExperimentBatchWorklistWriter
from thelma.automation.tools.experiment.batch import ExperimentBatchExecutor
from thelma.automation.tools.experiment.batch import ExperimentBatchRackFiller
from thelma.automation.tools.experiment.writer import ExperimentWorklistWriters
from thelma.automation.tools.semiconstants \
    import get_experiment_type_manual_optimisation
from thelma.automation.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.semiconstants import get_experiment_type_screening
from thelma.automation.tools.semiconstants import get_item_status_future
from thelma.automation.tools.semiconstants import get_item_status_managed
from thelma.automation.tools.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.interfaces import IJobType
from thelma.models.experiment import Experiment
from thelma.models.experiment import ExperimentRack
from thelma.models.job import ExperimentJob
from thelma.models.sample import Sample
from thelma.tests.tools.experiment.test_manual \
    import RackFillerTestCase
from thelma.tests.tools.experiment.test_robotsupport \
    import ExperimentOptimisationToolTestCase
from thelma.tests.tools.experiment.test_robotsupport \
import ExperimentScreeningToolTestCase
from thelma.tests.tools.tooltestingutils import FileCreatorTestCase
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase



class ExperimentBatchTestCase(ToolsAndUtilsTestCase):
    """
    Add-on test case (not be used as solo super class).
    """

    def set_up(self):
        self.experiment_jobs = None
        self.experiment1 = None
        self.experiment2 = None
        self.iso_plate2 = None
        self.experiment_racks2 = None
        self.iso_plate2_barcode = '09999995'
        self.experiment2_rack_barcodes = ['09999996', '09999997', '09999998',
                                          '09999999']

    def tear_down(self):
        del self.experiment_jobs
        del self.experiment1
        del self.experiment2
        del self.iso_plate2
        del self.experiment_racks2
        del self.iso_plate2_barcode
        del self.experiment2_rack_barcodes

    def _continue_setup(self, experiment, iso_layout, mol_map, floating_map,
                        pool_map):
        self.experiment1 = experiment
        self.__create_iso_plate2(iso_layout, mol_map, floating_map, pool_map)
        self.__create_experiment2()
        self.__create_racks_for_experiment2()
        self.__create_experiment_job()
        self._create_tool()

    def __create_iso_plate2(self, iso_layout, mol_map, floating_map, pool_map):
        plate_specs = self.experiment1.source_rack.specs
        self.iso_plate2 = plate_specs.create_rack(label='test_iso_plate2',
                                          status=get_item_status_managed())
        self.iso_plate2.barcode = self.iso_plate2_barcode
        for well in self.iso_plate2.containers:
            rack_pos = well.location.position
            iso_pos = iso_layout.get_working_position(rack_pos)
            if iso_pos is None: continue
            sample = Sample(iso_pos.iso_volume / VOLUME_CONVERSION_FACTOR,
                            well)
            if iso_pos.is_mock:
                continue
            elif iso_pos.is_floating:
                placeholder = iso_pos.molecule_design_pool
                pool_id = floating_map[placeholder]
            else:
                pool_id = iso_pos.molecule_design_pool_id
            md_pool = pool_map[pool_id]
            conc = iso_pos.iso_concentration / \
                                (len(md_pool) * CONCENTRATION_CONVERSION_FACTOR)
            for md in md_pool:
                mol = mol_map[md.id]
                sample.make_sample_molecule(mol, conc)

    def __create_experiment2(self):
        self.experiment2 = Experiment(label='second_experiment',
                destination_rack_specs=self.experiment1.destination_rack_specs,
                source_rack=self.iso_plate2,
                experiment_design=self.experiment1.experiment_design,
                experiment_racks=self.experiment_racks2)

    def __create_racks_for_experiment2(self):
        counter = 0
        number_replicates = self.experiment1.experiment_design.\
                            experiment_metadata.number_replicates
        status = get_item_status_future()
        plate_specs = None
        for exp_rack in self.experiment1.experiment_racks:
            plate_specs = exp_rack.rack.specs
            break
        for design_rack in self.experiment1.experiment_design.design_racks:
            i = 0
            while i < number_replicates:
                barcode = self.experiment2_rack_barcodes[counter]
                plate = plate_specs.create_rack(label=barcode, status=status)
                plate.barcode = barcode
                ExperimentRack(design_rack=design_rack, rack=plate,
                               experiment=self.experiment2)
                i += 1
                counter += 1

    def __create_experiment_job(self):
        jt = self._get_entity(IJobType, 'rnai-experiment')
        experiment_job = ExperimentJob(label='batch_test_experiment_job',
                            job_type=jt,
                            experiments=[self.experiment1, self.experiment2],
                            subproject=self.experiment1.experiment_design.\
                                            experiment_metadata.subproject)
        self.experiment_jobs = [experiment_job]

    def _test_one_updated_experiment(self, expect_experiments=True):
        ej = self.experiment_jobs[0]
        ej.experiments = [self.experiment1]
        self._create_tool()
        updated_experiments1 = self.tool.get_result()
        self.assert_is_not_none(updated_experiments1)
        if expect_experiments:
            self.assert_equal(len(updated_experiments1), 1)
        ej.experiments = [self.experiment1, self.experiment2]
        self._create_tool()
        updated_experiments2 = self.tool.get_result()
        self.assert_is_not_none(updated_experiments2)
        if expect_experiments:
            self.assert_equal(len(updated_experiments2), 1)
        self._check_warning_messages('Some experiments in your selection ' \
                                     'have already been updated in the DB')

    def _test_invalid_experiment_jobs(self):
        self.experiment_jobs = dict()
        self._test_and_expect_errors('The experiment job list must be a list')
        self.experiment_jobs = [self.experiment1]
        self._test_and_expect_errors('The experiment job must be a ' \
                                     'ExperimentJob object')

    def _test_invalid_user(self):
        self.executor_user = None
        self._test_and_expect_errors('The user must be a User object')

    def _test_different_experiment_designs(self):
        em = self._create_experiment_metadata()
        ed = em.experiment_design
        ed.id = -1
        self.experiment2.experiment_design = ed
        self._test_and_expect_errors('The experiments belong to ' \
                                     'different experiment designs!')

    def _test_no_valid_experiment(self):
        status = get_item_status_managed()
        for experiment in self.experiment_jobs[0].experiments:
            for exp_rack in experiment.experiment_racks:
                exp_rack.rack.status = status
        self._test_and_expect_errors('There are no experiments awaiting ' \
                                     'update in your selection!')
        self._check_warning_messages('Some experiments in your selection ' \
                                     'have already been updated in the DB')


class ExperimentBatchRackFillerTestCase(RackFillerTestCase,
                                        ExperimentBatchTestCase):

    def set_up(self):
        RackFillerTestCase.set_up(self)
        ExperimentBatchTestCase.set_up(self)
        self.number_experiments = 2

    def tear_down(self):
        ExperimentBatchTestCase.tear_down(self)
        RackFillerTestCase.tear_down(self)

    def _create_tool(self):
        self.tool = ExperimentBatchRackFiller(user=self.executor_user,
                                        experiment_jobs=self.experiment_jobs)

    def _check_design_racks(self):
        if self.experiment_type.id == EXPERIMENT_SCENARIOS.SCREENING:
            for drack in self.experiment_metadata.experiment_design.\
                            design_racks:
                self.assert_is_none(drack.worklist_series)
        else:
            RackFillerTestCase._check_design_racks(self)

    def __continue_setup(self):
        RackFillerTestCase._continue_setup(self)
        ExperimentBatchTestCase._continue_setup(self,
                        experiment=self.experiment, iso_layout=self.iso_layout,
                        mol_map=self.mol_map, pool_map=self.pool_map,
                        floating_map=self.floating_map)

    def __check_result(self):
        self.__continue_setup()
        updated_experiments = self.tool.get_result()
        self.assert_is_not_none(updated_experiments)
        for experiment in updated_experiments:
            self._check_result(experiment)

    def test_result_optimisation(self):
        self.__check_result()

    def test_result_screening(self):
        self.experiment_type = get_experiment_type_screening()
        self.__check_result()

    def test_result_manual(self):
        self.experiment_type = get_experiment_type_manual_optimisation()
        self.__check_result()

    def test_result_one_updated_experiment(self):
        self.__continue_setup()
        self._test_one_updated_experiment()
        self._check_result(self.experiment1)
        self._check_result(self.experiment2)

    def test_invalid_experiment_jobs(self):
        self.__continue_setup()
        self._test_invalid_experiment_jobs()

    def test_invalid_user(self):
        self.__continue_setup()
        self._test_invalid_user()

    def test_different_experiment_designs(self):
        self.__continue_setup()
        self._test_different_experiment_designs()

    def test_no_valid_experiment(self):
        self.__continue_setup()
        self._test_no_valid_experiment()

    def test_filler_failure(self):
        self.__continue_setup()
        for container in self.iso_rack.containers:
            container.make_sample(10 / VOLUME_CONVERSION_FACTOR)
        self._test_and_expect_errors('Error when trying to update experiment')


class ExperimentBatchExecutorTestCase(ExperimentBatchTestCase,
                                ExperimentScreeningToolTestCase,
                                ExperimentOptimisationToolTestCase):

    def set_up(self):
        ExperimentOptimisationToolTestCase.set_up(self)
        # the screening tool has the same setup method
        ExperimentBatchTestCase.set_up(self)
        self.number_experiments = 2

    def tear_down(self):
        ExperimentBatchTestCase.tear_down(self)
        # the optimisation tool has the same tear down method
        ExperimentOptimisationToolTestCase.tear_down(self)

    def _create_tool(self):
        self.tool = ExperimentBatchExecutor(user=self.executor_user,
                                    experiment_jobs=self.experiment_jobs)

    def __continue_setup(self):
        if self.experiment_type.id == EXPERIMENT_SCENARIOS.SCREENING:
            ExperimentScreeningToolTestCase._continue_setup(self)
        else:
            ExperimentOptimisationToolTestCase._continue_setup(self)
        ExperimentBatchTestCase._continue_setup(self,
                        experiment=self.experiment, iso_layout=self.iso_layout,
                        mol_map=self.mol_map, pool_map=self.pool_map,
                        floating_map=self.floating_map)

    def __check_result(self):
        self.__continue_setup()
        updated_experiments = self.tool.get_result()
        self.assert_is_not_none(updated_experiments)
        if self.experiment_type.id == EXPERIMENT_SCENARIOS.OPTIMISATION:
            meth = ExperimentOptimisationToolTestCase._check_execution_results
        else:
            meth = ExperimentScreeningToolTestCase._check_execution_results
        meth(self, self.experiment1)
        self.iso_plate_barcode = self.iso_plate2_barcode
        self.experiment_rack_barcodes = self.experiment2_rack_barcodes
        meth(self, self.experiment2)

    def test_result_optimisation(self):
        self.__check_result()

    def test_result_screening(self):
        self.experiment_type = get_experiment_type_screening()
        self.__check_result()

    def test_unsupported_experiment_type(self):
        self.experiment_type = get_experiment_type_manual_optimisation()
        self.__continue_setup()
        self._test_and_expect_errors('This experiment type (manual ' \
                    'optimisation) does not support robot database updates')

    def test_result_one_updated_experiment_optimisation(self):
        self.__continue_setup()
        self._test_one_updated_experiment()
        ExperimentOptimisationToolTestCase._check_execution_results(
                                                    self, self.experiment1)
        ExperimentOptimisationToolTestCase._check_execution_results(
                                                    self, self.experiment2)

    def test_result_one_updated_experiment_screening(self):
        self.experiment_type = get_experiment_type_screening()
        self.__continue_setup()
        self._test_one_updated_experiment()
        ExperimentScreeningToolTestCase._check_execution_results(
                                                    self, self.experiment1)
        self.iso_plate_barcode = self.iso_plate2_barcode
        self.experiment_rack_barcodes = self.experiment2_rack_barcodes
        ExperimentScreeningToolTestCase._check_execution_results(
                                                    self, self.experiment2)

    def test_invalid_experiment_jobs(self):
        self.__continue_setup()
        self._test_invalid_experiment_jobs()

    def test_invalid_user(self):
        self.__continue_setup()
        self._test_invalid_user()

    def test_different_experiment_designs(self):
        self.__continue_setup()
        self._test_different_experiment_designs()

    def test_no_valid_experiment(self):
        self.__continue_setup()
        self._test_no_valid_experiment()

    def test_executor_failure(self):
        self.max_vol = (self.max_vol / 10)
        self.__continue_setup()
        self._test_and_expect_errors('Error when trying to update experiment')


class ExperimentBatchWorklistWriterTestCase(ExperimentBatchTestCase,
                                ExperimentScreeningToolTestCase,
                                ExperimentOptimisationToolTestCase,
                                FileCreatorTestCase):

    def set_up(self):
        ExperimentOptimisationToolTestCase.set_up(self)
        # the screening tool has the same setup method
        ExperimentBatchTestCase.set_up(self)
        self.number_experiments = 2
        self.WL_PATH = 'thelma:tests/tools/experiment/csv_files/'

    def tear_down(self):
        del self.WL_PATH
        ExperimentBatchTestCase.tear_down(self)
        # the optimisation tool has the same tear down method
        ExperimentOptimisationToolTestCase.tear_down(self)

    def _create_tool(self):
        self.tool = ExperimentBatchWorklistWriter(
                                        experiment_jobs=self.experiment_jobs)

    def __continue_setup(self):
        if self.experiment_type.id == EXPERIMENT_SCENARIOS.SCREENING:
            ExperimentScreeningToolTestCase._continue_setup(self)
        else:
            ExperimentOptimisationToolTestCase._continue_setup(self)
        ExperimentBatchTestCase._continue_setup(self,
                        experiment=self.experiment, iso_layout=self.iso_layout,
                        mol_map=self.mol_map, pool_map=self.pool_map,
                        floating_map=self.floating_map)

    def test_result_optimisation(self):
        self.__continue_setup()
        zip_stream = self.tool.get_result()
        archive = self._get_zip_archive(zip_stream)
        self.assert_equal(len(archive.namelist()), 8)
        for fn in archive.namelist():
            tool_content = archive.read(fn)
            if ExperimentWorklistWriters.OPTI_FILE_SUFFIX in fn:
                exp_fn = 'optimem_opti.csv'
                if self.experiment2.label in fn:
                    exp_fn = 'optimem_opti2.csv'
                self._compare_csv_file_content(tool_content, exp_fn)
            elif ExperimentWorklistWriters.REAGENT_FILE_SUFFIX in fn:
                exp_fn = 'reagent_opti.csv'
                if self.experiment2.label in fn:
                    exp_fn = 'reagent_opti2.csv'
                self._compare_csv_file_content(tool_content, exp_fn)
            elif ExperimentWorklistWriters.PREPARATION_FILE_SUFFIX in fn:
                self._compare_csv_file_content(tool_content,
                                                    'reagent_prep_opti.csv')
            else:
                exp_fn = 'transfer_opti.csv'
                if self.experiment2.label in fn:
                    exp_fn = 'transfer_opti2.csv'
                self._compare_csv_file_content(tool_content, exp_fn)

    def test_result_screen(self):
        self.experiment_type = get_experiment_type_screening()
        self.__continue_setup()
        zip_stream = self.tool.get_result()
        archive = self._get_zip_archive(zip_stream)
        self.assert_equal(len(archive.namelist()), 8)
        for fn in archive.namelist():
            tool_content = archive.read(fn)
            if ExperimentWorklistWriters.OPTI_FILE_SUFFIX in fn:
                exp_fn = 'optimem_screen.csv'
                if self.experiment2.label in fn:
                    exp_fn = 'optimem_screen2.csv'
                self._compare_csv_file_content(tool_content, exp_fn)
            elif ExperimentWorklistWriters.REAGENT_FILE_SUFFIX in fn:
                exp_fn = 'reagent_screen.csv'
                if self.experiment2.label in fn:
                    exp_fn = 'reagent_screen2.csv'
                self._compare_csv_file_content(tool_content, exp_fn)
            elif ExperimentWorklistWriters.PREPARATION_FILE_SUFFIX in fn:
                self._compare_csv_file_content(tool_content,
                                                    'reagent_prep_screen.csv')
            else:
                exp_fn = 'cybio_transfer.txt'
                if self.experiment2.label in fn:
                    exp_fn = 'cybio_transfer2.txt'
                self._compare_csv_file_content(tool_content, exp_fn)

    def test_unsupported_experiment_type(self):
        self.experiment_type = get_experiment_type_manual_optimisation()
        self.__continue_setup()
        self._test_and_expect_errors('This experiment type (manual ' \
                        'optimisation) does not support robot worklists')

    def test_result_one_updated_experiment_optimisation(self):
        self.__continue_setup()
        self._test_one_updated_experiment(expect_experiments=False)
        zip_stream = self.tool.return_value
        zip_archive = self._get_zip_archive(zip_stream)
        self.assert_equal(len(zip_archive.namelist()), 4)
        for fn in zip_archive.namelist():
            tool_content = zip_archive.read(fn)
            if ExperimentWorklistWriters.OPTI_FILE_SUFFIX in fn:
                self._compare_csv_file_content(tool_content,
                                                    'optimem_opti2.csv')
            elif ExperimentWorklistWriters.REAGENT_FILE_SUFFIX in fn:
                self._compare_csv_file_content(tool_content,
                                                    'reagent_opti2.csv')
            elif ExperimentWorklistWriters.PREPARATION_FILE_SUFFIX \
                            in fn:
                self._compare_csv_file_content(tool_content,
                                                    'reagent_prep_opti.csv')
            else:
                self._compare_csv_file_content(tool_content,
                                                    'transfer_opti2.csv')

    def test_result_one_updated_experiment_screening(self):
        self.experiment_type = get_experiment_type_screening()
        self.__continue_setup()
        self._test_one_updated_experiment(expect_experiments=False)
        zip_stream = self.tool.return_value
        zip_archive = self._get_zip_archive(zip_stream)
        self.assert_equal(len(zip_archive.namelist()), 4)
        for fn in zip_archive.namelist():
            tool_content = zip_archive.read(fn)
            if ExperimentWorklistWriters.OPTI_FILE_SUFFIX in fn:
                self._compare_csv_file_content(tool_content,
                                                    'optimem_screen2.csv')
            elif ExperimentWorklistWriters.REAGENT_FILE_SUFFIX in fn:
                self._compare_csv_file_content(tool_content,
                                                    'reagent_screen2.csv')
            elif ExperimentWorklistWriters.PREPARATION_FILE_SUFFIX \
                            in fn:
                self._compare_csv_file_content(tool_content,
                                                    'reagent_prep_screen.csv')
            else:
                self._compare_txt_file_content(tool_content,
                                                    'cybio_transfer2.txt')

    def test_invalid_experiment_jobs(self):
        self.__continue_setup()
        self._test_invalid_experiment_jobs()

    def test_different_experiment_designs(self):
        self.__continue_setup()
        self._test_different_experiment_designs()

    def test_no_valid_experiment(self):
        self.__continue_setup()
        self._test_no_valid_experiment()

    def test_executor_failure(self):
        self.max_vol = (self.max_vol / 10)
        self.__continue_setup()
        self._test_and_expect_errors()
