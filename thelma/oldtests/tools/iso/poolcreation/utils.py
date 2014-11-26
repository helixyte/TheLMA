"""
Base classes for stock sample generation ISO testing.
"""
from everest.entities.utils import get_root_aggregate
from thelma.automation.semiconstants import RACK_SPECS_NAMES
from thelma.automation.semiconstants import get_96_rack_shape
from thelma.automation.semiconstants import get_item_status_future
from thelma.automation.semiconstants import get_item_status_managed
from thelma.automation.semiconstants import get_pipetting_specs_biomek_stock
from thelma.automation.semiconstants import get_pipetting_specs_cybio
from thelma.automation.semiconstants import get_positions_for_shape
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.tools.iso.base import StockRackLayout
from thelma.automation.tools.iso.base import StockRackLayoutConverter
from thelma.automation.tools.iso.poolcreation.base \
    import PoolCreationStockRackLayoutConverter
from thelma.automation.tools.iso.poolcreation.base \
    import PoolCreationStockRackPosition
from thelma.automation.tools.iso.poolcreation.base \
    import SingleDesignStockRackLayoutConverter
from thelma.automation.tools.iso.poolcreation.base \
    import StockSampleCreationLayout
from thelma.automation.tools.iso.poolcreation.base \
    import StockSampleCreationLayoutConverter
from thelma.automation.tools.iso.poolcreation.base \
    import StockSampleCreationPosition
from thelma.automation.tools.iso.poolcreation.base import DILUENT_INFO
from thelma.automation.tools.iso.poolcreation.base import LABELS
from thelma.automation.tools.iso.poolcreation.generation \
    import StockSampleCreationIsoRequestGenerator
from thelma.automation.tools.iso.poolcreation.jobcreator \
    import StockSampleCreationIsoPopulator
from thelma.automation.tracbase import BaseTracTool
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.utils.base import are_equal_values
from thelma.interfaces import ITubeRack
from thelma.entities.liquidtransfer import PlannedSampleDilution
from thelma.entities.liquidtransfer import PlannedSampleTransfer
from thelma.entities.liquidtransfer import PlannedWorklist
from thelma.entities.liquidtransfer import TRANSFER_TYPES
from thelma.entities.moleculedesign import MoleculeDesign
from thelma.entities.moleculedesign import MoleculeDesignPool
from thelma.entities.moleculetype import MOLECULE_TYPE_IDS
from thelma.oldtests.tools.tooltestingutils import FileReadingTestCase
from thelma.oldtests.tools.tooltestingutils import TracToolTestCase


class SSC_TEST_DATA(object):

    TEST_FILE_PATH = 'thelma:tests/tools/iso/poolcreation/cases/'
    WORKLIST_FILE_PATH = 'thelma:tests/tools/iso/poolcreation/worklists/'
    TEST_CASE_11 = '11_pools.xls'
    TEST_CASE_120 = '120_pools.xls'

    NUMBER_POOLS_11 = 11

    ISO_REQUEST_LABEL = 'ssgen_test'
    BUFFER_WORKLIST_LABEL = 'ssgen_test_buffer'
    TARGET_VOLUME = 30 # ul
    TARGET_CONCENTRATION = 10000 # nM
    BUFFER_VOLUME = 24 # ul
    SINGLE_DESIGN_TRANSFER_VOLUME = 2 # ul

    # pool ID - molecule design IDs
    POOL_IDS = {1063102 : [10247990, 10331567, 10339513],
                1058382 : [10247991, 10331568, 10339514],
                1064324 : [10247992, 10331569, 10339515],
                1065599 : [10247993, 10331570, 10339516],
                1059807 : [10247986, 10331563, 10339509],
                1060579 : [10247987, 10331564, 10339510],
                1065602 : [10247988, 10331565, 10339511],
                1063754 : [10247989, 10331566, 10339512],
                1059776 : [10247998, 10331574, 10339520],
                1060625 : [10247999, 10331575, 10339521],
                1065628 : [10248000, 10331576, 10339522]}
    # md ID - (final) pool ID
    SINGLE_DESIGN_LOOKUP = {
                10247990 : 1063102, 10331567 : 1063102, 10339513 : 1063102,
                10247991 : 1058382, 10331568 : 1058382, 10339514 : 1058382,
                10247992 : 1064324, 10331569 : 1064324, 10339515 : 1064324,
                10247993 : 1065599, 10331570 : 1065599, 10339516 : 1065599,
                10247986 : 1059807, 10331563 : 1059807, 10339509 : 1059807,
                10247987 : 1060579, 10331564 : 1060579, 10339510 : 1060579,
                10247988 : 1065602, 10331565 : 1065602, 10339511 : 1065602,
                10247989 : 1063754, 10331566 : 1063754, 10339512 : 1063754,
                10247998 : 1059776, 10331574 : 1059776, 10339520 : 1059776,
                10247999 : 1060625, 10331575 : 1060625, 10339521 : 1060625,
                10248000 : 1065628, 10331576 : 1065628, 10339522 : 1065628}

    # md id - single design pool ID
    SINGLE_DESIGN_POOL_IDS = {
            10247986 : 298377, 10247987 : 298378, 10247988 : 298379,
            10247989 : 298380, 10247990 : 298381, 10247991 : 298382,
            10247992 : 298383, 10247993 : 298384, 10247998 : 298389,
            10247999 : 298390, 10248000 : 298391, 10331563 : 303629,
            10331564 : 303630, 10331565 : 303631, 10331566 : 303632,
            10331567 : 303633, 10331568 : 303634, 10331569 : 303635,
            10331570 : 303636, 10331574 : 303641, 10331575 : 303642,
            10331576 : 303643, 10339509 : 311654, 10339510 : 311655,
            10339511 : 311656, 10339512 : 311657, 10339513 : 311658,
            10339514 : 311659, 10339515 : 311660, 10339516 : 311661,
            10339520 : 311666, 10339521 : 311667, 10339522 : 311668}

    ISO_LABELS = {1 : 'ssgen_test_01', 2 : 'ssgen_test_02'}

    #: pos_label - pool ID
    ISO_LAYOUT_DATA = dict(a1=1063102, b1=1058382, c1=1064324, d1=1065599,
                 e1=1059807, f1=1060579, g1=1065602, h1=1063754,
                 a2=1059776, b2=1060625, c2=1065628)
    #: pool ID - pos label
    POOL_POSITION_LOOKUP = {
                1063102 : 'a1', 1058382 : 'b1', 1064324 : 'c1',
                1065599 : 'd1', 1059807 : 'e1', 1060579 : 'f1',
                1065602 : 'g1', 1063754 : 'h1', 1059776 : 'a2',
                1060625 : 'b2', 1065628 : 'c2'}

    FILE_NAME_LAYOUT = 'ssgen_test_01_layout.csv'
    @classmethod
    def get_stock_tubes_barcodes(cls, pool):
        barcodes = []
        for md in pool:
            barcodes.append(cls.get_tube_barcode_for_md(md))
        return barcodes

    @classmethod
    def get_tube_barcode_for_md(cls, md):
        md_id = md
        if isinstance(md, MoleculeDesign):
            md_id = md.id
        return '1%09i' % (md_id)

    @classmethod
    def get_tube_barcode_for_pool(cls, pool):
        pool_id = pool
        if isinstance(pool, MoleculeDesignPool):
            pool_id = pool.id
        return '1%09i' % (pool_id)


    POOL_STOCK_RACK_BARCODE = '09999999'
    POOL_STOCK_RACK_LABEL = 'ssgen_test_01_psr'
    # barcode, stock rack label
    TUBE_DESTINATION_RACKS = {
                      '09999981' : 'ssgen_test_01_sds#1',
                      '09999982' : 'ssgen_test_01_sds#2',
                      '09999983' : 'ssgen_test_01_sds#3'}

    FILE_NAME_INSTRUCTIONS = 'ssgen_test_01_instructions.txt'
    FILE_NAME_XL20_SUMMARY = 'ssgen_test_01_xl20_summary.csv'
    FILE_NAME_XL20_WORKLIST = 'ssgen_test_01_xl20_worklist.csv'
    STOCK_TRANSFER_WORKLIST_LABEL = 'stock_transfer_ssgen_test_01'

    STOCK_POSITIONS_3_RACKS = [
            'a1', 'b1', 'c1', 'd1', 'e1', 'f1', 'g1', 'h1',
            'a2', 'b2', 'c2']
    # pos label - molecule design IDs
    STOCK_POSITIONS_SINGLE_RACK = {
            'a1' : 10331567, 'b1' : 10339513, 'c1' : 10247990,
            'd1' : 10331574, 'e1' : 10339520, 'f1' : 10247998,
            'g1' : 10331568, 'h1' : 10339514, 'a2' : 10247991,
            'b2' : 10331575, 'c2' : 10339521, 'd2' : 10247999,
            'e2' : 10331569, 'f2' : 10339515, 'g2' : 10247992,
            'h2' : 10331576, 'a3' : 10339522, 'b3' : 10248000,
            'c3' : 10331570, 'd3' : 10339516, 'e3' : 10247993,
            'f3' : 10331563, 'g3' : 10339509, 'h3' : 10247986,
            'a4' : 10331564, 'b4' : 10339510, 'c4' : 10247987,
            'd4' : 10331565, 'e4' : 10339511, 'f4' : 10247988,
            'g4' : 10331566, 'h4' : 10339512, 'a5' : 10247989}
    SINGLE_STOCK_RACK_LABEL = 'ssgen_test_01_sds'
    FILE_NAME_STOCK_TRANSFER_BIOMEK = 'ssgen_test_01_biomek_worklist.csv'

    @classmethod
    def get_target_pos_for_single_rack_source_pos(cls, source_pos_label):
        md_id = cls.STOCK_POSITIONS_SINGLE_RACK[source_pos_label.lower()]
        pool_id = cls.SINGLE_DESIGN_LOOKUP[md_id]
        trg_pos_label = cls.POOL_POSITION_LOOKUP[pool_id]
        return get_rack_position_from_label(trg_pos_label)

    @classmethod
    def get_all_pool_stock_rack_tube_barcodes(cls):
        barcodes = []
        for pool_id in cls.POOL_IDS.keys():
            barcode = cls.get_tube_barcode_for_pool(pool_id)
            barcodes.append(barcode)
        return barcodes

    @classmethod
    def get_all_source_tube_barcodes(cls, rack_barcode, use_single_src_rack):
        barcodes = []
        if use_single_src_rack:
            for md_id in cls.STOCK_POSITIONS_SINGLE_RACK.values():
                single_pool_id = cls.SINGLE_DESIGN_POOL_IDS[md_id]
                barcodes.append(cls.get_tube_barcode_for_md(single_pool_id))
        else:
            rack_label = cls.TUBE_DESTINATION_RACKS[rack_barcode]
            value_parts = LABELS.parse_stock_rack_label(rack_label)
            rack_marker = value_parts[LABELS.MARKER_RACK_MARKER]
            marker_parts = LABELS.parse_rack_marker(rack_marker)
            rack_num = marker_parts[LABELS.MARKER_RACK_NUM]
            rack_index = rack_num - 1
            for md_ids in cls.POOL_IDS.values():
                md_id = md_ids[rack_index]
                single_pool_id = cls.SINGLE_DESIGN_POOL_IDS[md_id]
                barcodes.append(cls.get_tube_barcode_for_md(single_pool_id))
        return barcodes

    FILE_NAME_LOG = 'log_file.csv'


class StockSampleCreationTestCase1(FileReadingTestCase):
    """
    Assumes that the ISO request has not been generated yet.
    """

    def set_up(self):
        FileReadingTestCase.set_up(self)
        self.TEST_FILE_PATH = SSC_TEST_DATA.TEST_FILE_PATH
        self.VALID_FILE = SSC_TEST_DATA.TEST_CASE_11
        self.iso_request_label = SSC_TEST_DATA.ISO_REQUEST_LABEL
        self.target_volume = SSC_TEST_DATA.TARGET_VOLUME
        self.target_concentration = SSC_TEST_DATA.TARGET_CONCENTRATION
        self.iso_request = None
        self.number_designs = 3

    def tear_down(self):
        FileReadingTestCase.tear_down(self)
        del self.iso_request_label
        del self.target_volume
        del self.target_concentration
        del self.iso_request
        del self.number_designs

    def _get_iso_request_pools(self):
        pools = []
        for pool_id in SSC_TEST_DATA.ISO_LAYOUT_DATA.values():
            pool = self._get_pool(pool_id)
            pools.append(pool)
        return pools

    def _get_iso_request_pool_set(self):
        pools = self._get_iso_request_pools()
        return self._create_molecule_design_pool_set(
                            molecule_type=pools[0].molecule_type,
                            molecule_design_pools=pools)

    def _compare_iso_request_pool_set(self, pool_set):
        self.assert_equal(pool_set.molecule_type.id,
                          MOLECULE_TYPE_IDS.SIRNA)
        exp_ids = sorted(SSC_TEST_DATA.ISO_LAYOUT_DATA.values())
        found_pool_ids = []
        for pool in pool_set:
            found_pool_ids.append(pool.id)
        self.assert_equal(len(found_pool_ids), len(exp_ids))
        self.assert_equal(sorted(found_pool_ids), sorted(exp_ids))

    def _generate_iso_request_worklist_series(self):
        psds = []
        vol = SSC_TEST_DATA.BUFFER_VOLUME / VOLUME_CONVERSION_FACTOR
        for rack_pos in get_positions_for_shape(get_96_rack_shape()):
            psd = PlannedSampleDilution.get_entity(volume=vol,
                      target_position=rack_pos, diluent_info=DILUENT_INFO)
            psds.append(psd)
        worklist = self._create_planned_worklist(
                            label='ssgen_test_buffer',
                            pipetting_specs=get_pipetting_specs_cybio(),
                            planned_liquid_transfers=psds,
                            transfer_type=TRANSFER_TYPES.SAMPLE_DILUTION)
        ws = self._create_worklist_series()
        ws.add_worklist(index=0, worklist=worklist)
        return ws

    def _compare_worklist_series(self, worklist_series):
        self.assert_is_not_none(worklist_series)
        self.assert_equal(len(worklist_series), 1)
        worklist = None
        for wl in worklist_series:
            worklist = wl
        if not worklist.index == 0:
            msg = 'The buffer worklist has an unexpected index (%i instead ' \
                  'of 0).' % (worklist.index)
            raise AssertionError(msg)
        self.assert_equal(worklist.pipetting_specs, get_pipetting_specs_cybio())
        self.assert_equal(worklist.transfer_type,
                          TRANSFER_TYPES.SAMPLE_DILUTION)
        self.assert_equal(worklist.label, SSC_TEST_DATA.BUFFER_WORKLIST_LABEL)
        psds = worklist.planned_liquid_transfers
        self.assert_equal(len(psds), 96)
        rack_positions = []
        exp_vol = SSC_TEST_DATA.BUFFER_VOLUME
        for psd in psds:
            rack_pos = psd.target_position
            rack_positions.append(rack_pos)
            if not psd.diluent_info == DILUENT_INFO:
                msg = 'Unexpected diluent info for buffer dilution in ' \
                      'position %s: %s.' % (rack_pos.label, psd.diluent_info)
                raise AssertionError(msg)
            vol = psd.volume * VOLUME_CONVERSION_FACTOR
            if not are_equal_values(vol, exp_vol):
                msg = 'Unexpected volume for buffer dilution in ' \
                      'position %s: %s.' % (rack_pos.label, vol)
                raise AssertionError(msg)
        exp_positions = get_positions_for_shape(get_96_rack_shape())
        self.assert_equal(sorted(rack_positions), sorted(exp_positions))


class StockSampleCreationTestCase2(StockSampleCreationTestCase1,
                                   TracToolTestCase):
    """
    Assumes that there is an ISO request.
    Generates ISOs but does not populate them.
    Population can be launched, however.
    """
    def set_up(self):
        StockSampleCreationTestCase1.set_up(self)
        self.create_test_tickets = False
        self.number_isos = 1
        self.isos = dict()
        self.iso_layouts = dict()
        self.compare_iso_layout_positions = True

    def tear_down(self):
        if self.create_test_tickets:
            TracToolTestCase.tear_down_as_add_on(self)
        StockSampleCreationTestCase1.tear_down(self)
        del self.create_test_tickets
        del self.number_isos
        del self.isos
        del self.iso_layouts
        del self.compare_iso_layout_positions

    def _continue_setup(self, file_name=None):
        if self.create_test_tickets:
            TracToolTestCase.set_up_as_add_on(self)
        if self.number_isos > 1:
            self.VALID_FILE = SSC_TEST_DATA.TEST_CASE_120
        StockSampleCreationTestCase1._continue_setup(self, file_name=file_name)
        self.__create_iso_request()
        self.__generate_isos()

    def _test_and_expect_errors(self, msg=None):
        if isinstance(self.tool, BaseTracTool):
            TracToolTestCase._test_and_expect_errors(self, msg)
        else:
            StockSampleCreationTestCase1._test_and_expect_errors(self, msg=msg)

    def __create_iso_request(self):
        generator = StockSampleCreationIsoRequestGenerator(
                                                self.iso_request_label,
                                                self.stream,
                                                self.target_volume,
                                                self.target_concentration,
                                                parent=self.tool)
        self.iso_request = generator.get_result()
        if self.iso_request is None:
            raise ValueError('ISO request generation has failed!')

    def __generate_isos(self):
        for i in range(self.number_isos):
            if self.create_test_tickets:
                ticket_id = self._get_ticket()
            else:
                ticket_id = i + 1
            layout_num = (i + 1)
            iso = self._create_stock_sample_creation_iso(
                       iso_request=self.iso_request,
                       label=SSC_TEST_DATA.ISO_LABELS[layout_num],
                       layout_number=layout_num,
                       ticket_number=ticket_id,
                       number_stock_racks=self.number_designs)
            self.isos[iso.layout_number] = iso
        self.assert_equal(len(self.iso_request.isos), self.number_isos)

    def _check_pool_set(self, pool_set, layout_num):
        if self.number_isos == 1:
            self._compare_iso_request_pool_set(pool_set)
        else:
            self.assert_equal(pool_set.molecule_type.id,
                              MOLECULE_TYPE_IDS.SIRNA)
            if layout_num == 1:
                exp_length = 96
            else:
                exp_length = 120 - 96
            self.assert_equal(len(pool_set), exp_length)

    def _check_iso_layout(self, rack_layout, layout_num):
        converter = StockSampleCreationLayoutConverter(rack_layout)
        layout = converter.get_result()
        if layout is None:
            msg = 'Error when trying to convert the ISO layout for layout ' \
                  'number %i!' % (layout_num)
            raise AssertionError(msg)
        layout_name = 'ISO layout for layout number %i' % (layout_num)
        tested_labels = []
        all_barcodes = set()
        all_pools = set()
        if self.number_isos == 1:
            layout_data = SSC_TEST_DATA.ISO_LAYOUT_DATA
            if not self.compare_iso_layout_positions:
                pools = []
                for pool_id in SSC_TEST_DATA.POOL_IDS.keys():
                    pools.append(self._get_pool(pool_id))
        else:
            pools = self.isos[layout_num].molecule_design_pool_set
        for rack_pos, ssc_pos in layout.iterpositions():
            pos_label = rack_pos.label.lower()
            tested_labels.append(pos_label)
            if self.number_isos == 1 and self.compare_iso_layout_positions:
                pool_id = layout_data[pos_label]
                self._compare_layout_value(pool_id, 'molecule_design_pool',
                                           ssc_pos, layout_name)
                pool = self._get_pool(pool_id)
            else:
                pool = ssc_pos.molecule_design_pool
                self.assert_false(pool in all_pools)
                all_pools.add(pool)
                self.assert_true(pool in pools)
            mds = sorted([md for md in pool])
            self.assert_equal(len(mds), self.number_designs)
            self._compare_layout_value(mds, 'molecule_designs', ssc_pos,
                                       layout_name)
            barcodes = ssc_pos.stock_tube_barcodes
            self.assert_equal(len(barcodes), self.number_designs)
            for barcode in barcodes:
                self.assert_false(barcode in all_barcodes)
                all_barcodes.add(barcode)
        if self.number_isos == 1:
            self.assert_equal(sorted(tested_labels), sorted(layout_data.keys()))
        elif layout_num == 1:
            self.assert_equal(len(tested_labels), 96)
        else:
            self.assert_equal(len(tested_labels), (120 - 96))

    def _generate_pool_sets(self):
        layout_pools = dict()
        if self.number_isos == 1:
            pool_ids = SSC_TEST_DATA.POOL_IDS.keys()
            pools = []
            for pool_id in pool_ids:
                pools.append(self._get_pool(pool_id))
            layout_pools[1] = pools
        else:
            layout_num = 1
            pools = []
            for pool in sorted(self.iso_request.molecule_design_pool_set):
                pools.append(pool)
                if len(pools) == 96:
                    layout_pools[layout_num] = pools
                    pools = []
                    layout_num += 1
            layout_pools[layout_num] = pools
        for layout_num, pools in layout_pools.iteritems():
            mt = pools[0].molecule_type
            pool_set = self._create_molecule_design_pool_set(molecule_type=mt,
                                             molecule_design_pools=set(pools))
            self.isos[layout_num].molecule_design_pool_set = pool_set

    def _generate_iso_layouts(self):
        if self.number_isos == 1:
            layout = StockSampleCreationLayout()
            #: pos_label - pool ID
            layout_data = SSC_TEST_DATA.ISO_LAYOUT_DATA
            for pos_label, pool_id in layout_data.iteritems():
                pool = self._get_pool(pool_id)
                rack_pos = get_rack_position_from_label(pos_label)
                self.__create_stock_sample_creation_position(pool, rack_pos,
                                                             layout)
            self.iso_layouts[1] = layout
        else:
            for iso in self.isos.values():
                pool_set = iso.molecule_design_pool_set
                layout = StockSampleCreationLayout()
                positions = get_positions_for_shape(layout.shape)
                pools = sorted([p for p in pool_set.molecule_design_pools])
                for i in range(len(pools)):
                    pool = pools[i]
                    rack_pos = positions[i]
                self.__create_stock_sample_creation_position(pool, rack_pos,
                                                             layout)
                self.iso_layouts[iso.layout_number] = layout
        for layout_num, layout in self.iso_layouts.iteritems():
            iso = self.isos[layout_num]
            iso.rack_layout = layout.create_rack_layout()

    def __create_stock_sample_creation_position(self, pool, rack_pos, layout):
        barcodes = SSC_TEST_DATA.get_stock_tubes_barcodes(pool)
        ssc_pos = StockSampleCreationPosition(rack_position=rack_pos,
                         molecule_design_pool=pool,
                         stock_tube_barcodes=barcodes)
        layout.add_position(ssc_pos)
        return layout


class StockSampleCreationTestCase3(StockSampleCreationTestCase2):
    """
    Assumes that there is an ISO request and populated ISOs.
    Stock racks can be created, too (both empty and populated).
    """

    def set_up(self):
        StockSampleCreationTestCase2.set_up(self)
        self.pick_tubes_for_isos = False
        self.tube_destination_racks = sorted(
                                    SSC_TEST_DATA.TUBE_DESTINATION_RACKS.keys())
        self.rack_generator = None
        self.tube_generator = None

    def tear_down(self):
        StockSampleCreationTestCase2.tear_down(self)
        del self.pick_tubes_for_isos
        del self.tube_destination_racks
        del self.rack_generator
        del self.tube_generator

    def _continue_setup(self, file_name=None):
        StockSampleCreationTestCase2._continue_setup(self, file_name=file_name)
        if self.pick_tubes_for_isos:
            self.__populate_iso()
        else:
            self._generate_pool_sets()
            self._generate_iso_layouts()

    def __populate_iso(self):
        populator = StockSampleCreationIsoPopulator(self.iso_request, 1)
        isos = populator.get_result()
        if isos is None:
            raise ValueError('Error during ISO generation!')
        warnings = ' '.join(populator.get_messages())
        self.assert_false('Unable to find valid tubes for the following ' \
                          'pools' in warnings)
        converter = StockSampleCreationLayoutConverter(isos[0].rack_layout)
        layout = converter.get_result()
        if layout is None:
            raise ValueError('Error during ISO layout conversion!')
        # sort positions
        pool_positions = dict()
        for iso_pos in layout.working_positions():
            pool_positions[iso_pos.molecule_design_pool.id] = iso_pos
        new_layout = StockSampleCreationLayout(layout.shape)
        layout_data = SSC_TEST_DATA.ISO_LAYOUT_DATA
        for pos_label, pool_id in layout_data.iteritems():
            iso_pos = pool_positions[pool_id]
            rack_pos = get_rack_position_from_label(pos_label)
            new_pos = StockSampleCreationPosition(rack_position=rack_pos,
                          molecule_design_pool=iso_pos.molecule_design_pool,
                          stock_tube_barcodes=iso_pos.stock_tube_barcodes)
            new_layout.add_position(new_pos)
        self.iso_layouts[1] = new_layout
        self.isos[1].rack_layout = new_layout.create_rack_layout()

    def _generate_stock_racks(self):
        if self.rack_generator is None:
            self.rack_generator = _RackGenerator()
        for barcode in self.tube_destination_racks:
            self.rack_generator.create_rack(barcode)

    def _generate_pool_stock_rack(self):
        if self.rack_generator is None:
            self.rack_generator = _RackGenerator()
        rack = self.rack_generator.create_rack(
                                        SSC_TEST_DATA.POOL_STOCK_RACK_BARCODE)
        tube_specs = rack.specs.tube_specs[0]
        self.tube_generator = _TubeGenerator(tube_specs=tube_specs)
        for rack_pos, ssc_pos in self.iso_layouts[1].iterpositions():
            self.tube_generator.create_tube(rack, rack_pos,
                                            ssc_pos.molecule_design_pool)

    def _get_stock_rack_layout(self, stock_rack, is_pool_stock_rack=False,
                               is_single_stock_rack=False):
        if is_pool_stock_rack:
            converter_cls = PoolCreationStockRackLayoutConverter
        elif is_single_stock_rack:
            converter_cls = SingleDesignStockRackLayoutConverter
        else:
            converter_cls = StockRackLayoutConverter
        converter = converter_cls(stock_rack.rack_layout)
        layout = converter.get_result()
        if layout is None:
            raise AssertionError('Unable to convert layout of stock rack ' \
                                 '"%s".' % (stock_rack.label))
        return layout

    def _compare_stock_rack_worklist_series(self, worklist_series,
                                            single_rack=False):
        self.assert_equal(len(worklist_series), 1)
        worklist = None
        for wl in worklist_series:
            self.assert_equal(wl.index, 0)
            worklist = wl
        self.assert_equal(worklist.label,
                          SSC_TEST_DATA.STOCK_TRANSFER_WORKLIST_LABEL)
        self.assert_equal(worklist.transfer_type,
                          TRANSFER_TYPES.SAMPLE_TRANSFER)
        if single_rack:
            exp_ps = get_pipetting_specs_biomek_stock()
        else:
            exp_ps = get_pipetting_specs_cybio()
        self.assert_equal(worklist.pipetting_specs, exp_ps)
        trg_pos_labels = set()
        src_pos_labels = []
        for pst in worklist:
            vol = pst.volume * VOLUME_CONVERSION_FACTOR
            self.assert_equal(vol, SSC_TEST_DATA.SINGLE_DESIGN_TRANSFER_VOLUME)
            if len(self.tube_destination_racks) == 3:
                self.assert_equal(pst.target_position, pst.source_position)
            trg_pos_labels.add(pst.target_position.label.lower())
            src_pos_labels.append(pst.source_position.label.lower())
        self.assert_equal(sorted(list(trg_pos_labels)),
                          sorted(SSC_TEST_DATA.STOCK_POSITIONS_3_RACKS))
        if single_rack:
            exp_positions = SSC_TEST_DATA.STOCK_POSITIONS_SINGLE_RACK.keys()
            self.assert_equal(sorted(src_pos_labels), sorted(exp_positions))

    def _generate_pool_stock_rack_layout(self):
        layout = StockRackLayout()
        layout_data = SSC_TEST_DATA.ISO_LAYOUT_DATA
        for pos_label, pool_id in layout_data.iteritems():
            pool = self._get_pool(pool_id)
            rack_pos = get_rack_position_from_label(pos_label)
            tube_barcode = SSC_TEST_DATA.get_tube_barcode_for_pool(pool)
            sr_pos = PoolCreationStockRackPosition(rack_position=rack_pos,
                        molecule_design_pool=pool,
                        tube_barcode=tube_barcode)
            layout.add_position(sr_pos)
        return layout

    def _generate_stock_rack_worklist_series(self, use_single_source_rack):
        layout_data = SSC_TEST_DATA.ISO_LAYOUT_DATA
        psts = []
        vol = SSC_TEST_DATA.SINGLE_DESIGN_TRANSFER_VOLUME \
              / VOLUME_CONVERSION_FACTOR
        if use_single_source_rack:
            ps = get_pipetting_specs_biomek_stock()
            for pos_label in SSC_TEST_DATA.STOCK_POSITIONS_SINGLE_RACK.keys():
                src_pos = get_rack_position_from_label(pos_label)
                trg_pos = SSC_TEST_DATA.\
                        get_target_pos_for_single_rack_source_pos(src_pos.label)
                pst = PlannedSampleTransfer.get_entity(volume=vol,
                        source_position=src_pos, target_position=trg_pos)
                psts.append(pst)
        else:
            ps = get_pipetting_specs_cybio()
            for pos_label in layout_data.keys():
                rack_pos = get_rack_position_from_label(pos_label)
                pst = PlannedSampleTransfer.get_entity(volume=vol,
                            source_position=rack_pos,
                            target_position=rack_pos)
                psts.append(pst)
        worklist = PlannedWorklist(pipetting_specs=ps,
                           label=SSC_TEST_DATA.STOCK_TRANSFER_WORKLIST_LABEL,
                           transfer_type=TRANSFER_TYPES.SAMPLE_TRANSFER,
                           planned_liquid_transfers=psts)
        ws = self._create_worklist_series()
        ws.add_worklist(0, worklist)
        return ws


class _RackGenerator(object):

    def __init__(self):
        self.__specs = RACK_SPECS_NAMES.from_name(RACK_SPECS_NAMES.STOCK_RACK)
        self.__status = get_item_status_managed()
        self.__agg = get_root_aggregate(ITubeRack)
        self.barcode_map = dict()

    def create_rack(self, barcode):
        rack = self.__specs.create_rack(status=self.__status, label='',
                                        barcode=barcode)
        self.barcode_map[barcode] = rack
        self.__agg.add(rack)
        return rack


class _TubeGenerator(object):

    def __init__(self, tube_specs):
        self.__status = get_item_status_future()
        self.__tube_specs = tube_specs

    def create_tube(self, rack, rack_pos, pool):
        barcode = SSC_TEST_DATA.get_tube_barcode_for_pool(pool)
        tube = self.__tube_specs.create_tube(self.__status, barcode)
        rack.add_tube(tube, rack_pos)
        rack.containers.append(tube)
        return tube


