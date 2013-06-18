"""
Tests the ISO generator tool
AAB Aug 10, 2011
"""

from everest.testing import check_attributes
from thelma.automation.tools.iso.optimizer import IsoCandidate
from thelma.automation.tools.iso.optimizer import IsoOptimizer
from thelma.automation.tools.iso.prep_utils import PrepIsoLayout
from thelma.automation.tools.iso.prep_utils import PrepIsoPosition
from thelma.automation.tools.semiconstants import get_384_rack_shape
from thelma.automation.tools.semiconstants import get_rack_position_from_label
from thelma.automation.tools.utils.base import TransferTarget
from thelma.automation.tools.utils.base \
    import CONCENTRATION_CONVERSION_FACTOR
from thelma.interfaces import IOrganization
from thelma.tests.tools.tooltestingutils import TestingLog
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase



class IsoOptimizerTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.log = TestingLog()
        self.md_pool_ids = set([205200, 205201, 205230])
        self.preparation_layout = None
        self.excluded_racks = None
        # key: rack position, value: (md pool ID, iso conc, parent well,
        # req_vol, pos type, transfer target positions)
        # estimated iso volume: 10 ul, take out volume: 1 ul (min)
        self.position_data = dict(
                    # first quadrant
                    A1=(205200, 1000, None, 50, 'fixed', ['A1']),
                    A2=(205200, 500, 'A1', 20, 'fixed', ['A2']),
                    B1=(205201, 1000, None, 50, 'fixed', ['B1']),
                    B2=(205201, 500, 'B1', 20, 'fixed', ['B2']),
                    # second quadrant
                    A3=(205230, 1000, None, 50, 'fixed', ['A3']),
                    A4=(205230, 500, 'A3', 20, 'fixed', ['A4']),
                    B3=('md_4', 1000, None, 50, 'floating', ['B3']),
                    B4=('md_4', 500, 'B3', 20, 'floating', ['B4']),
                    # third quadrant
                    A5=('md_5', 1000, None, 50, 'floating', ['A5']),
                    A6=('md_5', 500, 'A5', 20, 'floating', ['A6']),
                    # fourth quadrant
                    D1=('mock', 1000, None, 50, 'mock', ['D1']),
                    D2=('mock', 500, 'D1', 20, 'mock', ['D2']))
        self.expected_concentrations = [50000]

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.log
        del self.md_pool_ids
        del self.preparation_layout
        del self.excluded_racks
        del self.position_data
        del self.expected_concentrations

    def _create_tool(self):
        self.tool = IsoOptimizer(molecule_design_pools=self.md_pool_ids,
                    preparation_layout=self.preparation_layout,
                    log=self.log, excluded_racks=self.excluded_racks)

    def __continue_setup(self):
        self.__create_prep_layout()
        self._create_tool()

    def __create_prep_layout(self):
        self.preparation_layout = PrepIsoLayout(shape=get_384_rack_shape())
        stock_conc = None
        for pos_label, pos_data in self.position_data.iteritems():
            rack_pos = get_rack_position_from_label(pos_label)
            tt = TransferTarget(rack_position=rack_pos, transfer_volume=10)
            parent_well = pos_data[2]
            if not parent_well is None:
                parent_well = get_rack_position_from_label(parent_well)
            pool = self._get_pool(pos_data[0])
            prep_pos = PrepIsoPosition(rack_position=rack_pos,
                    molecule_design_pool=pool,
                    position_type=pos_data[4],
                    required_volume=pos_data[3],
                    transfer_targets=[tt],
                    prep_concentration=pos_data[1],
                    parent_well=parent_well)
            self.preparation_layout.add_position(prep_pos)
            if stock_conc is None and prep_pos.is_fixed:
                stock_conc = prep_pos.stock_concentration
        self.preparation_layout.set_floating_stock_concentration(stock_conc)

    def __check_result(self, candidates):
        self.assert_true(len(candidates) >= len(self.md_pool_ids))
        pool_map = dict()
        for candidate in candidates:
            pool_id = candidate.pool_id
            if not pool_map.has_key(pool_id): pool_map[pool_id] = []
            pool_map[pool_id].append(candidate)
            conc = candidate.concentration
            self.assert_true(conc in self.expected_concentrations)
        for pool_id in self.md_pool_ids:
            self.assert_true(pool_map.has_key(pool_id))
        self.assert_equal(len(pool_map), len(self.md_pool_ids))

    def test_result(self):
        self.__continue_setup()
        candidates = self.tool.get_result()
        self.assert_is_not_none(candidates)
        self.__check_result(candidates)

    def test_result_different_stock_concentrations(self):
        self.md_pool_ids = set([330001, 205201, 205202])
        self.position_data['A1'] = (330001, 100, None, 50, 'fixed', ['A1'])
        self.position_data['A2'] = (330001, 50, 'A1', 20, 'fixed', ['A2'])
        self.__continue_setup()
        candidates = self.tool.get_result()
        self.assert_is_not_none(candidates)
        self.expected_concentrations = [10000, 50000]
        self.__check_result(candidates)

    def test_result_excluded_racks(self):
        self.__continue_setup()
        # get excluded rack
        candidates = self.tool.get_result()
        self.__check_result(candidates)
        candidate_counts = set()
        rack_barcode = None
        for candidate in candidates:
            if not candidate.pool_id in candidate_counts:
                candidate_counts.add(candidate.pool_id)
            else:
                rack_barcode = candidate.rack_barcode
                break
        self.assert_is_not_none(rack_barcode)
        # rerun with excluded rack
        self.excluded_racks = [rack_barcode]
        self._create_tool()
        candidates = self.tool.get_result()
        for candidate in candidates:
            self.assert_not_equal(candidate.rack_barcode, rack_barcode)
        self.__check_result(candidates)

    def test_invalid_molecule_design_pools(self):
        self.__continue_setup()
        self.md_pool_ids = dict()
        self._test_and_expect_errors('The molecule design pool list must be a ' \
                                     'set object')
        self.md_pool_ids = set(['13', '12'])
        self._test_and_expect_errors('The molecule design pool ID must be a ' \
                                     'int')
        self.md_pool_ids = set()
        self._test_and_expect_errors('The molecule design pool list is empty!')


    def test_invalid_preparation_layout(self):
        self.__continue_setup()
        self.preparation_layout = self.preparation_layout.create_rack_layout()
        self._test_and_expect_errors('The preparation plate layout must be ' \
                                     'a PrepIsoLayout object')

    def test_invalid_excluded_racks(self):
        self.__continue_setup()
        self.excluded_racks = dict()
        self._test_and_expect_errors('The excluded racks list must be a ' \
                                     'list object')
        self.excluded_racks = [123, 456]
        self._test_and_expect_errors('The excluded rack barcode must be a ' \
                                     'basestring object')

    def test_no_molecule_pool_ids(self):
        self.md_pool_ids = set([1])
        self.__continue_setup()
        self._test_and_expect_errors('Could not find stock sample IDs for ' \
                            'the given molecule design pools and suppliers!')

    def test_supplier(self):
        supplier = self._create_organization(name='invalid', id= -1)
        self.__continue_setup()
        for prep_pos in self.preparation_layout.working_positions():
            if prep_pos.is_mock or prep_pos.is_floating: continue
            prep_pos.set_supplier(supplier)
        self._create_tool()
        self._test_and_expect_errors('Could not find stock sample IDs for ' \
                            'the given molecule design pools and suppliers!')
        supplier = self._get_entity(IOrganization, 'ambion')
        self.assert_is_not_none(supplier)
        for prep_pos in self.preparation_layout.working_positions():
            if prep_pos.is_mock or prep_pos.is_floating: continue
            prep_pos.set_supplier(supplier)
        self._create_tool()
        candidates = self.tool.get_result()
        self.assert_is_not_none(candidates)
        self.__check_result(candidates)

    def test_volume(self):
        self.__continue_setup()
        for prep_pos in self.preparation_layout.working_positions():
            if prep_pos.is_floating:
                prep_pos.prep_concentration = 50000
                prep_pos.required_volume = 300
        candidates = self.tool.get_result()
        self.assert_is_not_none(candidates)
        self.__check_result(candidates)
        self.md_pool_ids = set([205204])
        self._test_and_expect_errors('The optimisation query did not ' \
                                     'return any result.')


class IsoCandidateTest(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.pool_id = 5
        self.rack_barcode = '12345678'
        self.rack_position = get_rack_position_from_label('A1')
        self.container_barcode = '87654321'
        self.concentration = 50 / CONCENTRATION_CONVERSION_FACTOR
        self.init_data = dict(pool_id=self.pool_id,
                              rack_barcode=self.rack_barcode,
                              rack_position=self.rack_position,
                              container_barcode=self.container_barcode,
                              concentration=self.concentration)

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.pool_id
        del self.rack_barcode
        del self.rack_position
        del self.container_barcode
        del self.concentration
        del self.init_data

    def test_iso_candidate_init(self):
        iso_candidate = IsoCandidate(**self.init_data)
        self.assert_is_not_none(iso_candidate)
        self.init_data['concentration'] = self.concentration * \
                                          CONCENTRATION_CONVERSION_FACTOR
        check_attributes(iso_candidate, self.init_data)

    def test_immutablity(self):
        iso_candidate = IsoCandidate(**self.init_data)
        for attr_name, value in self.init_data.iteritems():
            values = (iso_candidate, attr_name, value)
            self.assert_raises(AttributeError, setattr, *values)

    def test_iso_candidate_factory(self):
        record = [self.pool_id, self.rack_barcode, 0, 0, self.container_barcode,
                  78, self.concentration]
        iso_candidate = IsoCandidate.create_from_query_result(record)
        self.init_data['concentration'] = self.concentration \
                                          * CONCENTRATION_CONVERSION_FACTOR
        check_attributes(iso_candidate, self.init_data)
