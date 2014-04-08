"""
Tests ISO request ticket tools.
"""
from pkg_resources import resource_filename # pylint: disable=E0611,F0401
from thelma.automation.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.semiconstants import get_experiment_metadata_type
from thelma.automation.tools.metadata.generation \
    import ExperimentMetadataGenerator
from thelma.automation.tools.metadata.ticket \
    import IsoRequestTicketAccepter
from thelma.automation.tools.metadata.ticket \
    import IsoRequestTicketActivator
from thelma.automation.tools.metadata.ticket \
    import IsoRequestTicketCreator
from thelma.automation.tools.metadata.ticket \
    import IsoRequestTicketDescriptionBuilder
from thelma.automation.tools.metadata.ticket \
    import IsoRequestTicketDescriptionRemover
from thelma.automation.tools.metadata.ticket \
    import IsoRequestTicketDescriptionUpdater
from thelma.automation.tools.metadata.ticket \
    import IsoRequestTicketReassigner
from thelma.automation.tools.metadata.ticket import IsoRequestTicketReopener
from thelma.automation.tools.stock.base import STOCKMANAGEMENT_USER
from thelma.interfaces import IProject
from thelma.interfaces import IUser
from thelma.models.experiment import ExperimentMetadata
from thelma.models.iso import ISO_STATUS
from thelma.models.moleculedesign import MoleculeDesignPoolSet
from thelma.tests.tools.tooltestingutils \
    import ExperimentMetadataReadingTestCase
from thelma.tests.tools.tooltestingutils import FileCreatorTestCase
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase
from thelma.tests.tools.tooltestingutils import TracToolTestCase
from tractor.ticket import RESOLUTION_ATTRIBUTE_VALUES
from tractor.ticket import STATUS_ATTRIBUTE_VALUES


class _IsoRequestTicketTestCase(ExperimentMetadataReadingTestCase,
                               TracToolTestCase):

    def set_up(self):
        ExperimentMetadataReadingTestCase.set_up(self)
        TracToolTestCase.set_up_as_add_on(self)
        self.TEST_FILE_PATH = 'thelma:tests/tools/metadata/report/'
        self.VALID_FILE = 'valid_opti.xls'
        self.em_requester = self._get_entity(IUser, 'brehm')
        self.project = self._get_entity(IProject)
        self.subproject = self._create_subproject(label='test_subproject',
                                                  project=self.project)
        self.experiment_type_id = EXPERIMENT_SCENARIOS.OPTIMISATION
        self.experiment_metadata_label = 'ticket_update_test'

    def tear_down(self):
        ExperimentMetadataReadingTestCase.tear_down(self)
        TracToolTestCase.tear_down_as_add_on(self)
        del self.project
        del self.subproject
        del self.experiment_type_id
        del self.experiment_metadata_label

    def _set_experiment_metadadata(self):
        em_type = get_experiment_metadata_type(self.experiment_type_id)
        self.experiment_metadata = ExperimentMetadata(
                            label=self.experiment_metadata_label,
                            subproject=self.subproject, number_replicates=1,
                            experiment_metadata_type=em_type,
                            ticket_number=0)

    def _continue_setup(self, file_name=None):
        ExperimentMetadataReadingTestCase._continue_setup(self)
        self._create_tool()


class IsoRequestTicketCreatorTestCase(_IsoRequestTicketTestCase):

    def _create_tool(self):
        self.tool = IsoRequestTicketCreator(requester=self.em_requester,
                                experiment_metadata=self.experiment_metadata)

    def test_result(self):
        self._continue_setup()
        ticket_id = self.tool.get_ticket_id()
        self.assert_true(self.tool.transaction_completed())
        self.assert_is_not_none(ticket_id)

    def test_invalid_input_values(self):
        self._continue_setup()
        req = self.em_requester
        self.em_requester = self.em_requester.username
        self._test_and_expect_errors('requester must be a User object')
        self.em_requester = req
        self.experiment_metadata = None
        self._test_and_expect_errors('experiment metadata must be a ' \
                                     'ExperimentMetadata')


class IsoTicketDescriptionBuilderTestCase(FileCreatorTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.experiment_metadata = None
        self.experiment_type_id = EXPERIMENT_SCENARIOS.OPTIMISATION
        self.em_link = 'http://em_test_link.lnk'
        self.ir_link = 'http://iso_request_test_link.lnk'
        self.WL_PATH = 'thelma:tests/tools/metadata/csv_files/'
        self.TEST_FILE_PATH = 'thelma:tests/tools/metadata/report/'
        self.support_mastermix = True
        self.VALID_FILES = {
                    EXPERIMENT_SCENARIOS.OPTIMISATION : 'valid_opti.xls',
                    EXPERIMENT_SCENARIOS.SCREENING : 'valid_screen.xls',
                    EXPERIMENT_SCENARIOS.MANUAL : 'valid_manual.xls',
                    EXPERIMENT_SCENARIOS.ISO_LESS : 'valid_isoless.xls',
                    EXPERIMENT_SCENARIOS.ORDER_ONLY : 'valid_order.xls',
                    EXPERIMENT_SCENARIOS.LIBRARY : 'valid_library.xls'}
        self.VALID_FILES_NO_MM_SUPPORT = {
                    EXPERIMENT_SCENARIOS.OPTIMISATION : \
                                        'valid_opti_no_mastermix_support.xls',
                    EXPERIMENT_SCENARIOS.SCREENING : \
                                        'valid_screen_no_mastermix_support.xls'}
        self.requester = self._get_entity(IUser, 'it')
        self.project = self._get_entity(IProject)
        self.subproject = self._create_subproject(label='test_subproject',
                                                  project=self.project)

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.experiment_metadata
        del self.experiment_type_id
        del self.em_link
        del self.ir_link
        del self.TEST_FILE_PATH
        del self.VALID_FILES
        del self.requester
        del self.project
        del self.subproject

    def _create_tool(self):
        self.tool = IsoRequestTicketDescriptionBuilder(self.experiment_metadata,
                                                       self.em_link,
                                                       self.ir_link)

    def __continue_setup(self):
        self.__create_test_experiment_metadata()
        self._create_tool()

    def __create_test_experiment_metadata(self):
        file_map = self.VALID_FILES
        if not self.support_mastermix: file_map = self.VALID_FILES_NO_MM_SUPPORT
        ed_file = self.TEST_FILE_PATH + file_map[self.experiment_type_id]
        file_name = ed_file.split(':')
        f = resource_filename(*file_name) # pylint: disable=W0142
        stream = None
        try:
            stream = open(f, 'rb')
            source = stream.read()
        finally:
            if not stream is None:
                stream.close()
        em_type = get_experiment_metadata_type(self.experiment_type_id)
        em = ExperimentMetadata(label='DescBuilderTest',
                                subproject=self.subproject,
                                number_replicates=3,
                                experiment_metadata_type=em_type,
                                ticket_number=123)
        generator = ExperimentMetadataGenerator.create(stream=source,
                        experiment_metadata=em, requester=self.requester)
        self.experiment_metadata = generator.get_result()

    def __check_result(self, desc_file):
        self.__continue_setup()
        desc = self.tool.get_result()
        self.assert_is_not_none(desc)
        self._compare_txt_file_content(desc, desc_file)

    def test_result_opti(self):
        self.__check_result('ticket_description_opti.txt')

    def test_result_opti_no_robot_support(self):
        self.support_mastermix = False
        self.__check_result('ticket_description_opti_no_robot.txt')

    def test_result_screen(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.SCREENING
        self.__check_result('ticket_description_screen.txt')

    def test_result_screen_no_robot_support(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.SCREENING
        self.support_mastermix = False
        self.__check_result('ticket_description_screen_no_robot.txt')

    def test_result_manual(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.MANUAL
        self.__check_result('ticket_description_manual.txt')

    def test_result_iso_less(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.ISO_LESS
        self.__check_result('ticket_description_isoless.txt')

    def test_result_order_only(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.ORDER_ONLY
        self.__check_result('ticket_description_order_only.txt')

    def test_result_library(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.LIBRARY
        self.__check_result('ticket_description_library.txt')

    def test_invalid_input_values(self):
        self.__continue_setup()
        ori_em = self.experiment_metadata
        self.experiment_metadata = self.experiment_metadata.experiment_design
        self._test_and_expect_errors('experiment metadata must be a ' \
                                     'ExperimentMetadata object')
        self.experiment_metadata = ori_em
        ori_em_link = self.em_link
        self.em_link = 123
        self._test_and_expect_errors('experiment metadata link must be a ' \
                                     'basestring')
        self.em_link = ori_em_link
        self.ir_link = 123
        self._test_and_expect_errors('ISO request link must be a basestring')


class _IsoRequestTicketUpdateToolTestCase(_IsoRequestTicketTestCase):

    def set_up(self):
        _IsoRequestTicketTestCase.set_up(self)
        self.iso_request = None
        self.ticket_id = None
        self.experiment_metadata_label = 'ticket_update_test'
        self.em_link = 'http://em_test_link.lnk'

    def tear_down(self):
        _IsoRequestTicketTestCase.tear_down(self)
        del self.iso_request
        del self.ticket_id
        del self.em_link

    def _continue_setup(self): #pylint: disable=W0221
        _IsoRequestTicketTestCase._continue_setup(self,
                                                 file_name=self.VALID_FILE)
        self.iso_request = self.experiment_metadata.lab_iso_request
        self._create_ticket()
        self._create_tool()

    def _create_ticket(self):
        ticket_creator = IsoRequestTicketCreator(requester=self.em_requester,
                                experiment_metadata=self.experiment_metadata)
        self.ticket_id = ticket_creator.get_ticket_id()
        self.experiment_metadata.ticket_number = self.ticket_id

    def _test_missing_ticket(self):
        self._continue_setup()
        self.experiment_metadata.ticket_number += 1
        self._test_and_expect_errors('Fault')

    def _test_invalid_ticket_id(self):
        self._continue_setup()
        self.experiment_metadata.ticket_number = None
        self._test_and_expect_errors('ticket ID must be a int')

    def _test_invalid_id_providing_entity(self):
        self._continue_setup()
        ori_ir = self.iso_request
        self.iso_request = self.experiment_metadata.experiment_design
        ori_em = self.experiment_metadata
        self.experiment_metadata = self.experiment_metadata.experiment_design
        self._test_and_expect_errors('Unknown ID-providing entity')
        self.iso_request = ori_ir
        self.experiment_metadata = ori_em


class IsoRequestTicketDescriptionRemoverTestCase(
                                         _IsoRequestTicketUpdateToolTestCase):

    def set_up(self):
        _IsoRequestTicketUpdateToolTestCase.set_up(self)
        self.changed_em_type = True
        self.changed_num_reps = True

    def tear_down(self):
        _IsoRequestTicketUpdateToolTestCase.tear_down(self)
        del self.changed_em_type
        del self.changed_num_reps

    def _create_tool(self):
        self.tool = IsoRequestTicketDescriptionRemover(
                           experiment_metadata=self.experiment_metadata,
                           changed_num_replicates=self.changed_num_reps,
                           changed_em_type=self.changed_em_type)

    def __check_result(self):
        self.tool.run()
        self.assert_true(self.tool.transaction_completed())
        updated_ticket = self.tool.return_value
        self.assert_equal(updated_ticket.ticket_id, self.ticket_id)
        self.assert_false('Link to experiment metadata' \
                          in updated_ticket.description)

    def test_result(self):
        self._continue_setup()
        # both true
        self.__check_result()
        # em type only
        self.changed_num_reps = False
        self._create_tool()
        self.__check_result()
        # num reps only
        self.changed_num_reps = True
        self.changed_em_type = False
        self._create_tool()
        self.__check_result()
        # none of both
        self.changed_num_reps = False
        self._create_tool()
        self._test_and_expect_errors('Neither the number of replicates nor ' \
                 'the experiment metadata type have changed. The ticket ' \
                 'description does not need to be removed.')

    def test_invalid_id_providing_entity(self):
        self._test_invalid_id_providing_entity()

    def test_invalid_input_values(self):
        self._continue_setup()
        self.changed_em_type = 0.3
        self._test_and_expect_errors('The "changed experiment metadata type" ' \
                                'flag must be a bool object (obtained: float)')
        self.changed_em_type = True
        self.changed_num_reps = 0.4
        self._test_and_expect_errors('The "changed number replicates type" ' \
                                'flag must be a bool object (obtained: float).')


class IsoRequestTicketDescriptionUpdaterTestCase(
                                        _IsoRequestTicketUpdateToolTestCase):

    def set_up(self):
        _IsoRequestTicketUpdateToolTestCase.set_up(self)
        self.ir_link = 'http://iso_request_test_link.lnk'

    def tear_down(self):
        _IsoRequestTicketUpdateToolTestCase.tear_down(self)
        del self.ir_link

    def _create_tool(self):
        self.tool = IsoRequestTicketDescriptionUpdater(
                            experiment_metadata=self.experiment_metadata,
                            experiment_metadata_link=self.em_link,
                            iso_request_link=self.ir_link)

    def __check_result(self):
        self._continue_setup()
        self.tool.run()
        self.assert_true(self.tool.transaction_completed())
        update_ticket = self.tool.return_value
        self.assert_equal(update_ticket.ticket_id, self.ticket_id)
        desc = update_ticket.description
        self.assert_true(self.experiment_metadata_label in desc)
        self.assert_true(self.project.label in desc)
        self.assert_true(self.subproject.label in desc)
        self.assert_true(self.em_link in desc)
        self.assert_true(self.ir_link in desc)

    def test_result_opti(self):
        self.__check_result()
        desc = self.tool.return_value.description
        self.assert_true('Requester' in desc)
        self.assert_true(self.em_requester.username in desc)

    def test_result_isoless(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.ISO_LESS
        self.__check_result()
        desc = self.tool.return_value.description
        self.assert_false('Requester' in desc)

    def test_invalid_input_values(self):
        self._test_invalid_id_providing_entity()
        ori_em_link = self.em_link
        self.em_link = 123
        self._test_and_expect_errors('experiment metadata link must be a ' \
                                     'basestring')
        self.em_link = ori_em_link
        self.ir_link = 123
        self._test_and_expect_errors('ISO request link must be a basestring')

    def test_missing_ticket(self):
        self._test_missing_ticket()

    def test_invalid_ticket_id(self):
        self._test_invalid_ticket_id()


class IsoRequestTicketActivatorTestCase(_IsoRequestTicketUpdateToolTestCase):

    def _create_tool(self):
        self.tool = IsoRequestTicketActivator(
                                experiment_metadata=self.experiment_metadata)

    def test_result(self):
        self._continue_setup()
        self.tool.run()
        self.assert_true(self.tool.transaction_completed())
        updated_ticket = self.tool.return_value
        self.assert_equal(updated_ticket.ticket_id, self.ticket_id)
        self.assert_equal(updated_ticket.owner, STOCKMANAGEMENT_USER)

    def test_invalid_experiment_metadata(self):
        self._test_invalid_id_providing_entity()

    def test_missing_ticket(self):
        self._test_missing_ticket()

    def test_invalid_ticket_id(self):
        self._test_invalid_ticket_id()


class IsoRequestTicketAccepterTestCase(_IsoRequestTicketUpdateToolTestCase):

    def set_up(self):
        _IsoRequestTicketUpdateToolTestCase.set_up(self)
        self.accepter = 'rothe'

    def tear_down(self):
        _IsoRequestTicketUpdateToolTestCase.tear_down(self)
        del self.accepter

    def _create_tool(self):
        self.tool = IsoRequestTicketAccepter(username=self.accepter,
                            iso_request=self.iso_request)

    def test_result(self):
        self._continue_setup()
        self.tool.run()
        self.assert_true(self.tool.transaction_completed())
        updated_ticket = self.tool.return_value
        self.assert_equal(updated_ticket.ticket_id, self.ticket_id)
        self.assert_equal(updated_ticket.owner, self.accepter)
        self.assert_equal(updated_ticket.cc, STOCKMANAGEMENT_USER)

    def test_invalid_iso_request(self):
        self._test_invalid_id_providing_entity()

    def test_missing_ticket(self):
        self._test_missing_ticket()

    def test_invalid_ticket_id(self):
        self._test_invalid_ticket_id()


class IsoRequestTicketReassignerTestCase(_IsoRequestTicketUpdateToolTestCase,
                                         FileCreatorTestCase):

    def set_up(self):
        _IsoRequestTicketUpdateToolTestCase.set_up(self)
        self.VALID_FILE = 'valid_screen.xls'
        self.experiment_type_id = EXPERIMENT_SCENARIOS.SCREENING
        self.completed = False
        self.WL_PATH = 'thelma:tests/tools/metadata/csv_files/'

    def tear_down(self):
        _IsoRequestTicketUpdateToolTestCase.tear_down(self)
        del self.completed
        del self.WL_PATH

    def _create_tool(self):
        self.tool = IsoRequestTicketReassigner(iso_request=self.iso_request,
                                               completed=self.completed)

    def test_result_without_closing(self):
        self._continue_setup()
        self.tool.run()
        self.assert_true(self.tool.transaction_completed())
        updated_ticket, comment, tool_stream = self.tool.return_value # pylint:disable=W0633
        self.assert_equal(updated_ticket.ticket_id, self.ticket_id)
        self.assert_equal(updated_ticket.owner,
                          self.iso_request.requester.directory_user_id)
        self.assert_not_equal(updated_ticket.status,
                              STATUS_ATTRIBUTE_VALUES.CLOSED)
        self.assert_is_none(updated_ticket.resolution)
        self.assert_false(self.tool.COMPLETED_TEXT in comment)
        self.assert_is_none(tool_stream)

    def test_result_with_closing_no_missing_mds(self):
        self.completed = True
        self._continue_setup()
        md_set = self.experiment_metadata.molecule_design_pool_set
        self._create_lab_iso(label='test_iso', iso_request=self.iso_request,
            molecule_design_pool_set=md_set, status=ISO_STATUS.DONE)
        self.tool.run()
        self.assert_true(self.tool.transaction_completed())
        updated_ticket, comment, tool_stream = self.tool.return_value # pylint:disable=W0633
        self.assert_equal(updated_ticket.ticket_id, self.ticket_id)
        self.assert_equal(updated_ticket.owner,
                          self.iso_request.requester.directory_user_id)
        self.assert_equal(updated_ticket.status,
                          STATUS_ATTRIBUTE_VALUES.CLOSED)
        self.assert_equal(updated_ticket.resolution,
                          RESOLUTION_ATTRIBUTE_VALUES.FIXED)
        self.assert_true(self.tool.COMPLETED_TEXT in comment)
        self.assert_is_none(tool_stream)

    def test_result_with_closing_and_missing_floatings(self):
        self.completed = True
        self._continue_setup()
        pool_set = self.experiment_metadata.molecule_design_pool_set
        counter = 8
        iso_set = MoleculeDesignPoolSet(molecule_type=pool_set.molecule_type)
        all_pools = []
        for pool in pool_set: all_pools.append(pool)
        all_pools.sort(key=lambda pool: pool.id)
        for pool in all_pools:
            iso_set.molecule_design_pools.add(pool)
            counter -= 1
            if counter == 0: break
        self._create_lab_iso(label='done_iso', iso_request=self.iso_request,
            molecule_design_pool_set=iso_set, status=ISO_STATUS.DONE)
        self._create_lab_iso(label='queued_iso', iso_request=self.iso_request,
            molecule_design_pool_set=pool_set, status=ISO_STATUS.QUEUED)
        self.tool.run()
        self.assert_true(self.tool.transaction_completed())
        updated_ticket, comment, tool_stream = self.tool.return_value # pylint:disable=W0633
        self.assert_equal(updated_ticket.ticket_id, self.ticket_id)
        self.assert_equal(updated_ticket.owner,
                          self.iso_request.requester.directory_user_id)
        self.assert_equal(updated_ticket.status,
                          STATUS_ATTRIBUTE_VALUES.CLOSED)
        self.assert_equal(updated_ticket.resolution,
                          RESOLUTION_ATTRIBUTE_VALUES.FIXED)
        self.assert_true(self.tool.COMPLETED_TEXT in comment)
        self.assert_true(self.tool.MISSING_POOLS_ADDITION[:-3] in comment)
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream, 'report_missing_mds.csv')

    def test_invalid_input_values(self):
        self._test_invalid_id_providing_entity()
        self.completed = None
        self._test_and_expect_errors('completed flag must be a bool')

    def test_missing_ticket(self):
        self._test_missing_ticket()

    def test_invalid_ticket_id(self):
        self._test_invalid_ticket_id()


class IsoRequestTicketReopenerTestCase(_IsoRequestTicketUpdateToolTestCase):

    def set_up(self):
        _IsoRequestTicketUpdateToolTestCase.set_up(self)
        self.reopener = 'rothe'

    def tear_down(self):
        _IsoRequestTicketUpdateToolTestCase.tear_down(self)
        del self.reopener

    def _create_tool(self):
        self.tool = IsoRequestTicketReopener(iso_request=self.iso_request,
                                             username=self.reopener)

    def _continue_setup(self):
        _IsoRequestTicketUpdateToolTestCase._continue_setup(self)
        closer = IsoRequestTicketReassigner(iso_request=self.iso_request,
                                            completed=True)
        closer.run()
        self.assert_equal(closer.return_value[0].status,
                          STATUS_ATTRIBUTE_VALUES.CLOSED)

    def test_result(self):
        self._continue_setup()
        self.tool.run()
        self.assert_true(self.tool.transaction_completed())
        updated_ticket = self.tool.return_value
        self.assert_equal(updated_ticket.ticket_id, self.ticket_id)
        self.assert_equal(updated_ticket.status,
                          STATUS_ATTRIBUTE_VALUES.REOPENED)
        self.assert_equal(updated_ticket.owner, self.reopener)

    def test_invalid_input_values(self):
        self._test_invalid_id_providing_entity()
        self.reopener = self._get_entity(IUser, 'rothe')
        self._test_and_expect_errors()

    def test_missing_ticket(self):
        self._test_missing_ticket()

    def test_invalid_ticket_id(self):
        self._test_invalid_ticket_id()
