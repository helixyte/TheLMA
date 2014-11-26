"""
Tests for metadata report tools.
"""

from thelma.automation.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.semiconstants import get_experiment_metadata_type
from thelma.automation.tools.metadata.ticket import IsoRequestTicketCreator
from thelma.automation.tools.metadata.uploadreport \
    import ExperimentMetadataAssignmentWriter
from thelma.automation.tools.metadata.uploadreport \
    import ExperimentMetadataInfoWriter
from thelma.automation.tools.metadata.uploadreport \
    import ExperimentMetadataInfoWriterLibrary
from thelma.automation.tools.metadata.uploadreport \
    import ExperimentMetadataInfoWriterWarningOnly
from thelma.automation.tools.metadata.uploadreport \
    import ExperimentMetadataIsoPlateWriter
from thelma.automation.tools.metadata.uploadreport \
    import ExperimentMetadataReportUploader
from thelma.automation.tools.worklists.base import RESERVOIR_SPECS_NAMES
from thelma.automation.tools.worklists.base import get_reservoir_spec
from thelma.interfaces import ISubproject
from thelma.entities.experiment import ExperimentMetadata
from thelma.entities.utils import get_user
from thelma.oldtests.tools.tooltestingutils \
    import ExperimentMetadataReadingTestCase
from thelma.oldtests.tools.tooltestingutils import FileCreatorTestCase
from thelma.oldtests.tools.tooltestingutils import TracToolTestCase


class _ExperimentMetadataReportTestCase(FileCreatorTestCase,
                                        ExperimentMetadataReadingTestCase):

    def set_up(self):
        ExperimentMetadataReadingTestCase.set_up(self)
        self.TEST_FILE_PATH = 'thelma:tests/tools/metadata/report/'
        self.WL_PATH = 'thelma:tests/tools/metadata/csv_files/'
        self.VALID_FILES = {
                    EXPERIMENT_SCENARIOS.OPTIMISATION : 'valid_opti.xls',
                    EXPERIMENT_SCENARIOS.SCREENING : 'valid_screen.xls',
                    EXPERIMENT_SCENARIOS.LIBRARY : 'valid_library.xls',
                    EXPERIMENT_SCENARIOS.MANUAL : 'valid_manual.xls',
                    EXPERIMENT_SCENARIOS.ISO_LESS : 'valid_isoless.xls',
                    EXPERIMENT_SCENARIOS.ORDER_ONLY : 'valid_order.xls'}
        self.experiment_type_id = EXPERIMENT_SCENARIOS.OPTIMISATION
        self.generator = None
        self.experiment_metadata = None
        self.ticket_number = 123
        self.experiment_metadata_label = 'EM Report Test'
        self.em_requester = get_user('it')
        self.iso_request = None
        self.source_layout = None

    def tear_down(self):
        ExperimentMetadataReadingTestCase.tear_down(self)
        del self.WL_PATH
        del self.experiment_type_id
        del self.generator
        del self.VALID_FILES
        del self.ticket_number
        del self.experiment_metadata_label
        del self.iso_request
        del self.source_layout

    def _continue_setup(self, file_name=None):
        if file_name is None:
            file_name = self.VALID_FILES[self.experiment_type_id]
        self.generator = ExperimentMetadataReadingTestCase._continue_setup(
                                                            self, file_name)
        if not self.experiment_metadata is None:
            self.iso_request = self.experiment_metadata.lab_iso_request
            self.source_layout = self.generator.get_source_layout()
        self._create_tool()

    def _set_experiment_metadadata(self):
        if self.experiment_metadata is None:
            em_type = get_experiment_metadata_type(self.experiment_type_id)
            self.experiment_metadata = ExperimentMetadata(
                                label=self.experiment_metadata_label,
                                subproject=self._get_entity(ISubproject),
                                number_replicates=3,
                                ticket_number=self.ticket_number,
                                experiment_metadata_type=em_type)

    def _test_failed_generator(self, msg):
        self.raise_error = False
        self.experiment_type_id = EXPERIMENT_SCENARIOS.LIBRARY
        file_name = self.VALID_FILES[EXPERIMENT_SCENARIOS.OPTIMISATION]
        self._continue_setup(file_name)
        self._test_and_expect_errors(msg)

    def _test_invalid_generator(self, msg=None):
        self._continue_setup()
        self.generator = None
        if msg is None:
            msg = 'The experiment metadata generator must be a ' \
                  'ExperimentMetadataGenerator object'
        self._test_and_expect_errors(msg)


class ExperimentMetadataAssignmentWriterTestCase(
                                            _ExperimentMetadataReportTestCase):

    def _create_tool(self):
        self.tool = ExperimentMetadataAssignmentWriter(self.generator)

    def test_result_opti(self):
        self._continue_setup()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream, 'assignments_opti.csv')

    def test_result_manual(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.MANUAL
        self._continue_setup()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream, 'assignments_manual.csv')

    def test_failed_generator(self):
        self._test_failed_generator('Error when trying to fetch report data.')

    def test_invalid_generator(self):
        self._test_invalid_generator()


class ExperimentMetadataIsoPlateWriterTestCase(_ExperimentMetadataReportTestCase):


    def _create_tool(self):
        self.tool = ExperimentMetadataIsoPlateWriter(self.generator)

    def __check_result(self, reference_file_name):
        self._continue_setup()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream, reference_file_name)

    def test_result_opti(self):
        self.__check_result('iso_data_opti.csv')

    def test_result_screen(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.SCREENING
        self.__check_result('iso_data_screen.csv')

    def test_result_manual(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.MANUAL
        self.__check_result('iso_data_manual.csv')

    def test_result_order(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.ORDER_ONLY
        self.__check_result('iso_data_order.csv')

    def test_failed_generator(self):
        self._test_failed_generator('The generator has errors.')

    def test_invalid_generator(self):
        self._test_invalid_generator()


class ExperimentMetadataInfoWriterTestCase(_ExperimentMetadataReportTestCase):

    def set_up(self):
        _ExperimentMetadataReportTestCase.set_up(self)
        self.supports_mastermix = True
        self.reservoir_specs = get_reservoir_spec(
                                            RESERVOIR_SPECS_NAMES.STANDARD_96)
        self.number_replicates = 3

    def tear_down(self):
        _ExperimentMetadataReportTestCase.tear_down(self)
        del self.supports_mastermix
        del self.reservoir_specs
        del self.number_replicates

    def _create_tool(self):
        self.tool = ExperimentMetadataInfoWriter(self.generator,
                                                 self.number_replicates,
                                                 self.supports_mastermix,
                                                 self.reservoir_specs)

    def test_result_supports_mastermix(self):
        self._continue_setup()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_txt_file_stream(tool_stream,
                                      'report_info_supports_mastermix.txt')

    def test_result_no_mastermix_support(self):
        self.supports_mastermix = False
        self._continue_setup()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_txt_file_stream(tool_stream,
                                      'report_info_no_mastermix_support.txt')

    def test_info_writer_failed_generator(self):
        self._test_failed_generator('generator did not complete its run')

    def test_invalid_number_replicates(self):
        self._continue_setup()
        self.number_replicates = '3'
        self._test_and_expect_errors('number of replicates must be a int')

    def test_supports_mastermix_flag(self):
        self.supports_mastermix = None
        self._continue_setup()
        self._test_and_expect_errors('"supports mastermix" flag must be a bool')

    def test_invalid_reservoir_specs(self):
        self.reservoir_specs = self.reservoir_specs.name
        self._continue_setup()
        self._test_and_expect_errors('The ISO plate reservoir specs must be ' \
                                     'a ReservoirSpecs object')


class ExperimentMetadataInfoWriterWarningOnlyTestCase(
                                            _ExperimentMetadataReportTestCase):

    def set_up(self):
        _ExperimentMetadataReportTestCase.set_up(self)
        self.experiment_type_id = EXPERIMENT_SCENARIOS.ISO_LESS

    def _create_tool(self):
        self.tool = ExperimentMetadataInfoWriterWarningOnly(
                                            self.generator,
                                            self.experiment_metadata_label)

    def __check_result(self):
        self._continue_setup()
        # without warnings
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_txt_file_stream(tool_stream,
                                      'report_info_warnings_only.txt')
        # with warnings
        warn = 'a warning'
        self.generator.add_warning(warn)
        self._create_tool()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        tool_content = tool_stream.read()
        self.assert_false(self.tool.NO_WARNINGS_LINE in tool_content)
        self.assert_true(warn in tool_content)

    def test_result_iso_less(self):
        self.__check_result()

    def test_result_order_only(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.ORDER_ONLY
        self.__check_result()

    def test_invalid_input_values(self):
        self._continue_setup()
        ori_em_label = self.experiment_metadata_label
        self.experiment_metadata_label = 3
        self._test_and_expect_errors('The experiment metadata label must be ' \
                                     'a basestring')
        self.experiment_metadata_label = ori_em_label


class ExperimentMetadataInfoWriterLibraryTestCase(
                                            _ExperimentMetadataReportTestCase):

    def set_up(self):
        _ExperimentMetadataReportTestCase.set_up(self)
        self.experiment_type_id = EXPERIMENT_SCENARIOS.LIBRARY

    def _create_tool(self):
        self.tool = ExperimentMetadataInfoWriterLibrary(self.generator)

    def test_result(self):
        self._continue_setup()
        # no warnings
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        content = tool_stream.read()
        self.assert_true(self.tool.NO_WARNINGS_LINE in content)
        # with warnings
        warn = 'a warning'
        self.generator.add_warning(warn)
        self._create_tool()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        tool_content = tool_stream.read()
        self.assert_false(self.tool.NO_WARNINGS_LINE in tool_content)
        self.assert_true(warn in tool_content)

    def test_invalid_input_values(self):
        self._test_failed_generator('The generator has errors')
        self.generator.reset()
        self._test_and_expect_errors('The generator has not run!')
        self.experiment_metadata = None
        self._test_invalid_generator('The experiment metadata generator must ' \
                            'be a ExperimentMetadataGeneratorLibrary object')

    def test_invalid_generator_values(self):
        self._continue_setup()
        self.generator.supports_mastermix = None
        self._test_and_expect_errors('Error when trying to fetch ' \
                                '"support mastermix" flag from the generator')


class ExperimentMetadataReportUploaderTestCase(TracToolTestCase,
                                _ExperimentMetadataReportTestCase):

    def set_up(self):
        _ExperimentMetadataReportTestCase.set_up(self)
        TracToolTestCase.set_up_as_add_on(self)
        self.em_link = 'http://em_test_link.lnk'
        self.ir_link = 'http://iso_request_test_link.lnk'

    def tear_down(self):
        _ExperimentMetadataReportTestCase.tear_down(self)
        TracToolTestCase.tear_down_as_add_on(self)
        del self.em_link
        del self.ir_link

    def _continue_setup(self, file_name=None):
        _ExperimentMetadataReportTestCase._continue_setup(self, file_name)
        self._create_ticket()
        self._create_tool()

    def _create_tool(self):
        self.tool = ExperimentMetadataReportUploader(generator=self.generator,
                            experiment_metadata_link=self.em_link,
                            iso_request_link=self.ir_link)

    def _create_ticket(self):
        ticket_creator = IsoRequestTicketCreator(requester=self.em_requester,
                    experiment_metadata=self.experiment_metadata)
        self.ticket_number = ticket_creator.get_ticket_id()
        if not self.experiment_metadata is None:
            self.experiment_metadata.ticket_number = self.ticket_number

    def __check_result(self, number_files):
        self._continue_setup()
        self.tool.run()
        self.assert_true(self.tool.transaction_completed())
        self.assert_equal(len(self.tool.return_value), number_files)

    def test_result_opti(self):
        self.__check_result(number_files=4)

    def test_result_screen(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.SCREENING
        self.__check_result(number_files=3)

    def test_result_library(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.LIBRARY
        self.__check_result(number_files=2)

    def test_result_manual(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.MANUAL
        self.__check_result(number_files=3)

    def test_result_isoless(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.ISO_LESS
        self.__check_result(number_files=2)

    def test_result_order_only(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.ORDER_ONLY
        self.__check_result(number_files=3)

    def test_failed_generator(self):
        self._test_failed_generator('generator did not complete its run')

    def test_invalid_generator(self):
        self._test_invalid_generator()

    def test_invalid_em_link(self):
        self.em_link = [self.em_link]
        self._continue_setup()
        self._test_and_expect_errors('experiment metadata link must be a ' \
                                     'basestring')

    def test_invalid_iso_request_link(self):
        self.ir_link = [self.ir_link]
        self._continue_setup()
        self._test_and_expect_errors('ISO request link must be a basestring')

    def test_failed_stream_generation(self):
        self._continue_setup()
        self.generator.supports_mastermix = 'True'
        self._test_and_expect_errors('Error when trying to write info ' \
                                     'file stream!')

    def test_trac_error(self):
        self._continue_setup()
        self.experiment_metadata.ticket_number += 1
        self._test_and_expect_errors('Fault')
