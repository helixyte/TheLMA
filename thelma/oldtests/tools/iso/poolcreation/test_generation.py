"""
Tests for tools involved in the creation of stock sample generation
ISO requests.

AAB
"""
from thelma.automation.tools.iso.poolcreation.base import VolumeCalculator
from thelma.automation.tools.iso.poolcreation.generation \
    import StockSampleCreationIsoGenerator
from thelma.automation.tools.iso.poolcreation.generation \
    import StockSampleCreationIsoRequestGenerator
from thelma.automation.tools.iso.poolcreation.generation \
    import StockSampleCreationWorklistGenerator
from thelma.automation.tools.iso.poolcreation.generation \
    import StockSampleCreationTicketGenerator
from thelma.automation.tools.stock.base import STOCKMANAGEMENT_USER
from thelma.automation.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.entities.utils import get_user
from thelma.oldtests.tools.iso.poolcreation.utils \
    import StockSampleCreationTestCase1
from thelma.oldtests.tools.iso.poolcreation.utils \
    import StockSampleCreationTestCase2
from thelma.oldtests.tools.iso.poolcreation.utils import SSC_TEST_DATA
from thelma.oldtests.tools.tooltestingutils import TracToolTestCase


class StockSampleCreationIsoRequestGeneratorTestCase(
                                                StockSampleCreationTestCase1):

    def set_up(self):
        StockSampleCreationTestCase1.set_up(self)
        self.exp_number_isos = 1

    def tear_down(self):
        StockSampleCreationTestCase1.tear_down(self)
        del self.exp_number_isos

    def _continue_setup(self, file_name=None):
        StockSampleCreationTestCase1._continue_setup(self, file_name=file_name)
        self._create_tool()

    def _create_tool(self):
        self.tool = StockSampleCreationIsoRequestGenerator(
                iso_request_label=self.iso_request_label,
                stream=self.stream, target_volume=self.target_volume,
                target_concentration=self.target_concentration)

    def __check_result(self, file_name=None, len_pool_set=None, exp_vol=None):
        self._continue_setup(file_name)
        iso_request = self.tool.get_result()
        self.assert_is_not_none(iso_request)
        self.assert_equal(iso_request.label, SSC_TEST_DATA.ISO_REQUEST_LABEL)
        vol = iso_request.stock_volume * VOLUME_CONVERSION_FACTOR
        if exp_vol is None:
            self.assert_equal(vol, self.target_volume)
        else:
            self.assert_equal(vol, exp_vol)
        self.assert_equal(iso_request.stock_concentration \
              * CONCENTRATION_CONVERSION_FACTOR, self.target_concentration)
        self.assert_equal(iso_request.number_designs, self.number_designs)
        self.assert_equal(iso_request.owner, STOCKMANAGEMENT_USER)
        self.assert_equal(iso_request.number_aliquots, 0)
        self._compare_worklist_series(iso_request.worklist_series)
        self.assert_equal(iso_request.expected_number_isos,
                          self.exp_number_isos)
        if len_pool_set is None:
            self._compare_iso_request_pool_set(
                                        iso_request.molecule_design_pool_set)
        else:
            self.assert_equal(len(iso_request.molecule_design_pool_set),
                              len_pool_set)

    def test_result(self):
        self.__check_result()

    def test_result_several_isos(self):
        self.exp_number_isos = 2
        self.__check_result(SSC_TEST_DATA.TEST_CASE_120, len_pool_set=120)

    def test_volume_adjustment(self):
        self.target_volume -= 1
        self.__check_result(exp_vol=30)
        self._check_warning_messages('The target volume you have requested ' \
                'needs to be increased slightly because of the constraints ' \
                'of the pipetting robot (CyBio, min. transfer volume: 1 ul, ' \
                'step size: 0.1 ul). The target volume will be increased ' \
                'from 29 ul to 30 ul.')

    def test_invalid_input_values(self):
        self._continue_setup()
        ori_label = self.iso_request_label
        self.iso_request_label = 123
        self._test_and_expect_errors('The ISO request label must be a ' \
                                     'basestring object (obtained: int).')
        self.iso_request_label = ori_label
        self.target_volume = -2
        self._test_and_expect_errors('The target volume for the pool tubes ' \
                             'must be a positive number (obtained: -2).')
        self.target_volume = SSC_TEST_DATA.TARGET_VOLUME
        self.target_concentration = 0
        self._test_and_expect_errors('The target concentration for the pool ' \
                             'tubes must be a positive number (obtained: 0).')
        self.target_concentration = SSC_TEST_DATA.TARGET_CONCENTRATION

    def test_parsing_error(self):
        self.TEST_FILE_PATH = self.TEST_FILE_PATH.split('cases')[0]
        self._continue_setup('generation/no_pools.xls')
        self._test_and_expect_errors('Unable to parse pool set!')

    def test_worklist_generation_failure(self):
        self.target_volume = 1
        self._continue_setup()
        self._test_and_expect_errors('Error when trying to generate ' \
                                     'worklist series.')


class StockSampleCreationWorklistGeneratorTestCase(
                                            StockSampleCreationTestCase1):

    def set_up(self):
        StockSampleCreationTestCase1.set_up(self)
        self.volume_calculator = None

    def tear_down(self):
        StockSampleCreationTestCase1.tear_down(self)
        del self.volume_calculator

    def _continue_setup(self, file_name=None):
        self.volume_calculator = VolumeCalculator(self.target_volume,
                                                  self.target_concentration,
                                                  3,
                                                  50000)
        self._create_tool()

    def _create_tool(self):
        self.tool = \
            StockSampleCreationWorklistGenerator(self.volume_calculator,
                                                 self.iso_request_label)

    def test_result(self):
        self._continue_setup()
        worklist_series = self.tool.get_result()
        self.assert_is_not_none(worklist_series)
        self._compare_worklist_series(worklist_series)

    def test_invalid_input_values(self):
        self._continue_setup()
        ori_calc = self.volume_calculator
        self.volume_calculator = None
        self._test_and_expect_errors('The volume calculator must be a ' \
                            'VolumeCalculator object (obtained: NoneType).')
        self.volume_calculator = ori_calc
        self.iso_request_label = 123
        self._test_and_expect_errors('The ISO request label must be a ' \
                             'basestring object (obtained: int).')

    def test_incompatible_volumes(self):
        self.target_volume = 1
        self._continue_setup()
        self._test_and_expect_errors('Error when trying to determine buffer ' \
            'volume: The target volume you have requested (1 ul) is too low ' \
            'for the required dilution (1:15) since the CyBio cannot pipet ' \
            'less than 1.0 ul per transfer. The volume that has to be taken ' \
            'from the stock for each single molecule design would be lower ' \
            'that that. Increase the target volume to 15.0 ul or increase ' \
            'the target concentration.')


class StockSampleCreationTicketGeneratorTestCase(TracToolTestCase):

    def set_up(self):
        TracToolTestCase.set_up(self)
        self.requester = get_user('tondera')
        self.iso_label = 'ssgen_test_4'
        self.layout_number = 4

    def tear_down(self):
        TracToolTestCase.tear_down(self)
        del self.requester
        del self.iso_label
        del self.layout_number

    def _create_tool(self):
        self.tool = StockSampleCreationTicketGenerator(self.requester,
                                                        self.iso_label,
                                                        self.layout_number)

    def test_result(self):
        self._create_tool()
        ticket_id = self.tool.get_ticket_id()
        self.assert_true(self.tool.transaction_completed())
        self.assert_is_not_none(ticket_id)

    def test_invalid_input(self):
        req = self.requester
        self.requester = self.requester.username
        self._test_and_expect_errors('The requester must be a User object ' \
                                     '(obtained: unicode).')
        self.requester = req
        self.layout_number = '14'
        self._test_and_expect_errors('The layout number must be a int')
        self.layout_number = 14
        self.iso_label = 14
        self._test_and_expect_errors('The ISO label must be a basestring')


class StockSampleCreationIsoCreatorTestCase(StockSampleCreationTestCase2):

    def set_up(self):
        StockSampleCreationTestCase2.set_up(self)
        self.VALID_FILE = SSC_TEST_DATA.TEST_CASE_120
        self.create_test_tickets = True
        self.number_isos = 0
        self.ticket_numbers = None
        self.reporter = None

    def tear_down(self):
        StockSampleCreationTestCase2.tear_down(self)
        del self.ticket_numbers
        del self.reporter

    def _create_tool(self):
        self.tool = StockSampleCreationIsoGenerator(iso_request=self.iso_request,
              ticket_numbers=self.ticket_numbers, reporter=self.reporter)

    def _continue_setup(self, file_name=None):
        StockSampleCreationTestCase2._continue_setup(self, file_name=file_name)
        self._create_tool()

    def __check_result(self, exp_ticket_numbers=None):
        iso_request = self.tool.get_result()
        self.assert_is_not_none(iso_request)
        self.assert_equal(len(iso_request.isos), 2)
        layout_numbers = []
        ticket_numbers = set()
        labels = []
        for ssci in iso_request.isos:
            self.assert_equal(ssci.number_stock_racks, self.number_designs)
            labels.append(ssci.label)
            layout_numbers.append(ssci.layout_number)
            ti = ssci.ticket_number
            self.assert_is_not_none(ti)
            if self.ticket_numbers is None:
                self.assert_false(ti in ticket_numbers)
            else:
                self.assert_equal(ti, exp_ticket_numbers[ssci.layout_number])
            ticket_numbers.add(ti)
            self.assert_equal(len(ssci.rack_layout.tagged_rack_position_sets),
                              0)
            self.assert_is_none(ssci.molecule_design_pool_set)
        self.assert_equal(sorted(layout_numbers), [1, 2])
        self.assert_equal(sorted(labels), ['ssgen_test_01', 'ssgen_test_02'])
        if self.ticket_numbers is not None:
            self.assert_equal(sorted(list(ticket_numbers)),
                              sorted(list(set(exp_ticket_numbers.values()))))

    def test_result_new_tickets(self):
        self.reporter = get_user('it')
        self._continue_setup()
        self.__check_result()

    def test_result_1_ticket(self):
        self.ticket_numbers = [4]
        self._continue_setup()
        self.__check_result(exp_ticket_numbers={1 : 4, 2 : 4})

    def test_result_one_ticket_per_iso(self):
        self.ticket_numbers = [7, 8]
        self._continue_setup()
        self.__check_result(exp_ticket_numbers={1 : 7, 2 : 8})

    def test_existing_iso(self):
        self.ticket_numbers = [4]
        self._continue_setup()
        self._create_stock_sample_creation_iso(iso_request=self.iso_request,
                       label='ssgen_test_01', layout_number=1,
                       ticket_number=99, number_stock_racks=self.number_designs)
        self.__check_result(exp_ticket_numbers={1 : 99, 2 : 4})

    def test_invalid_input_values(self):
        self.reporter = get_user('it')
        self._continue_setup()
        ori_ir = self.iso_request
        self.iso_request = None
        self._test_and_expect_errors('The ISO request must be a ' \
                'StockSampleCreationIsoRequest object (obtained: NoneType)')
        self.iso_request = ori_ir
        self.ticket_numbers = dict()
        self._test_and_expect_errors('The ticket number list must be a list ' \
                                     'object (obtained: dict).')
        self.ticket_numbers = ['a']
        self._test_and_expect_errors('The ticket number must be a int ' \
                                     'object (obtained: str).')
        self.ticket_numbers = None
        self.reporter = None
        self._test_and_expect_errors('If you do not specify ticket numbers, ' \
                 'you have to provide a reporter for the ISO tickets! The ' \
                 'reporter must be User object!')
        self.reporter = 3
        self._test_and_expect_errors('If you do not specify ticket numbers, ' \
                 'you have to provide a reporter for the ISO tickets! The ' \
                 'reporter must be User object!')

    def test_no_isos_left(self):
        self.reporter = get_user('it')
        self.number_isos = 2
        self.create_test_tickets = False
        self._continue_setup()
        self._test_and_expect_errors('The ISOs have already been created.')

    def test_invalid_number_of_tickets(self):
        self.ticket_numbers = [1, 2, 3]
        self._continue_setup()
        self._test_and_expect_errors('You must specify either 1 ticket ' \
            'number (in which case all ISOs will get the same ticket number) ' \
            'or one for each ISO to generate (2). You specified 3 numbers ')
