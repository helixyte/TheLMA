"""
Tests functions and classes of the stock base module

AAB
"""
from everest.entities.utils import get_root_aggregate
from everest.repositories.rdb.testing import RdbContextManager
from thelma.automation.tools.stock.base import RackLocationQuery
from thelma.automation.tools.stock.base import get_default_stock_concentration
from thelma.automation.tools.stock.base import get_stock_tube_specs_db_term
from thelma.interfaces import IMoleculeType
from thelma.entities.moleculetype import MOLECULE_TYPE_IDS
from thelma.oldtests.tools.tooltestingutils import ToolsAndUtilsTestCase
from thelma.automation.tools.stock.base import get_stock_rack_shape
from thelma.automation.semiconstants import get_96_rack_shape
from thelma.automation.tools.stock.base import get_stock_rack_size

class StockBaseFunctionsTestCase(ToolsAndUtilsTestCase):

    def test_get_stock_concentration(self):
        mt_agg = get_root_aggregate(IMoleculeType)
        mimi = mt_agg.get_by_id(MOLECULE_TYPE_IDS.MIRNA_MIMI)
        self.assert_equal(get_default_stock_concentration(
                          MOLECULE_TYPE_IDS.MIRNA_MIMI), 10000)
        self.assert_equal(get_default_stock_concentration(mimi), 10000)
        miinh = mt_agg.get_by_id(MOLECULE_TYPE_IDS.MIRNA_INHI)
        self.assert_equal(get_default_stock_concentration(
                          MOLECULE_TYPE_IDS.MIRNA_INHI), 10000)
        self.assert_equal(get_default_stock_concentration(miinh), 10000)
        sirna = mt_agg.get_by_id(MOLECULE_TYPE_IDS.SIRNA)
        self.assert_equal(get_default_stock_concentration(
                          MOLECULE_TYPE_IDS.SIRNA), 50000)
        self.assert_equal(get_default_stock_concentration(sirna), 50000)
        self.assert_equal(get_default_stock_concentration(
                          MOLECULE_TYPE_IDS.SIRNA, 3), 10000)
        self.assert_equal(get_default_stock_concentration(sirna, 3), 10000)
        esi = mt_agg.get_by_id(MOLECULE_TYPE_IDS.ESI_RNA)
        self.assert_equal(get_default_stock_concentration(
                          MOLECULE_TYPE_IDS.ESI_RNA), 3800)
        self.assert_equal(get_default_stock_concentration(esi), 3800)
        self.assert_equal(get_default_stock_concentration(
                          MOLECULE_TYPE_IDS.ESI_RNA, 3), 3800)
        self.assert_equal(get_default_stock_concentration(esi, 3), 3800)
        ldr = mt_agg.get_by_id(MOLECULE_TYPE_IDS.LONG_DSRNA)
        self.assert_equal(get_default_stock_concentration(
                          MOLECULE_TYPE_IDS.LONG_DSRNA), 50000)
        self.assert_equal(get_default_stock_concentration(ldr), 50000)
        self.assert_equal(get_default_stock_concentration(
                          MOLECULE_TYPE_IDS.LONG_DSRNA, 3), 50000)
        self.assert_equal(get_default_stock_concentration(ldr, 3), 50000)
        compound = mt_agg.get_by_id(MOLECULE_TYPE_IDS.COMPOUND)
        self.assert_equal(get_default_stock_concentration(compound), 5000000)
        self.assert_equal(get_default_stock_concentration(
                          MOLECULE_TYPE_IDS.COMPOUND), 5000000)
        self.assert_raises(TypeError, get_default_stock_concentration, 1)
        self.assert_raises(ValueError, get_default_stock_concentration, 'unknown type')

    def test_get_stock_tube_specs_db_term(self):
        term = get_stock_tube_specs_db_term()
        exp_term = '(\'MATRIX0500\', \'MATRIX1400\')'
        self.assert_equal(term, exp_term)

    def test_get_stock_rack_shape(self):
        self.assert_equal(get_stock_rack_shape(), get_96_rack_shape())

    def test_get_stock_rack_size(self):
        self.assert_equal(get_stock_rack_size(), 96)


class RackLocationQueryTestCase(ToolsAndUtilsTestCase):

    def test_run(self):
        with RdbContextManager() as session:
            rack_barcodes = ['02481623', '02486186']
            query = RackLocationQuery(rack_barcodes=rack_barcodes)
            self.assert_is_not_none(query)
            self.assert_is_none(query.get_query_results())
            query.run(session=session)
            results = query.get_query_results()
            self.assert_equal(len(results), 2)
            for rack_barcode, location_name in results.iteritems():
                self.assert_true(rack_barcode in rack_barcodes)
                self.assert_is_not_none(location_name)
