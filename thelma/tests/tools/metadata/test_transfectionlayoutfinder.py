"""
tests the ISO layout finder tool

AAB Aug 03, 2011
"""

from everest.testing import check_attributes
from pkg_resources import resource_filename # pylint: disable=E0611,F0401
from thelma.automation.handlers.experimentdesign import \
        ExperimentDesignParserHandler
from thelma.automation.tools.metadata.base import TransfectionLayoutConverter
from thelma.automation.tools.metadata.base import TransfectionParameters
from thelma.automation.tools.metadata.base import TransfectionPosition
from thelma.automation.tools.metadata.transfectionlayoutfinder \
    import TransfectionLayoutFinder
from thelma.automation.tools.metadata.transfectionlayoutfinder \
    import _TransfectionLayoutOptimizer
from thelma.automation.tools.metadata.transfectionlayoutfinder \
    import _TransfectionTransferItem
from thelma.automation.semiconstants import get_384_rack_shape
from thelma.automation.semiconstants import get_96_rack_shape
from thelma.automation.semiconstants \
    import get_experiment_type_robot_optimisation
from thelma.automation.semiconstants import get_positions_for_shape
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.interfaces import IMoleculeDesignPool
from thelma.models.utils import get_user
from thelma.tests.tools.tooltestingutils import SilentLog
from thelma.tests.tools.tooltestingutils import TestingLog
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase


class TransfectionTransferItemTestCase(ToolsAndUtilsTestCase):

    def __get_transfection_position(self):
        rack_pos = get_rack_position_from_label('A1')
        pool = self._get_entity(IMoleculeDesignPool, '205200')
        tf_pos = TransfectionPosition(rack_position=rack_pos,
                            molecule_design_pool=pool,
                            reagent_name='mix',
                            reagent_dil_factor='140',
                            final_concentration='10')
        return tf_pos

    def __create_transfection_transfer_item(self, tf_pos):
        return _TransfectionTransferItem(working_pos=tf_pos)

    def test_init(self):
        tf_pos = self.__get_transfection_position()
        tid = self.__create_transfection_transfer_item(tf_pos)
        attrs = dict(working_pos=tf_pos, hash_value='205200mix14010',
                     target_row_index=0)
        check_attributes(tid, attrs)

    def test_equality(self):
        tf_pos = self.__get_transfection_position()
        tid1 = self.__create_transfection_transfer_item(tf_pos)
        tid2 = self.__create_transfection_transfer_item(tf_pos)
        ori_pos = tf_pos.rack_position
        tf_pos.rack_position = get_rack_position_from_label('G8')
        tid3 = self.__create_transfection_transfer_item(tf_pos)
        tf_pos.rack_position = ori_pos
        tf_pos.molecule_design_pool = 205201
        tid4 = self.__create_transfection_transfer_item(tf_pos)
        self.assert_equal(tid1, tid2)
        self.assert_equal(tid1, tid3)
        self.assert_not_equal(tid1, tid4)
        self.assert_not_equal(tid1, tf_pos.hash_full)

    def test_hash(self):
        tf_pos = self.__get_transfection_position()
        tid1 = self.__create_transfection_transfer_item(tf_pos)
        tf_pos.molecule_design_pool = 'mock'
        tid2 = self.__create_transfection_transfer_item(tf_pos)
        d = {tid1 : 1, tid2 : 2}
        self.assert_true(d.has_key(tid1))
        self.assert_true(d.has_key(tid2))
        self.assert_equal(d[tid1], 1)
        self.assert_equal(d[tid2], 2)


class TransfectionLayoutFinderBaseTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.FILE_PATH = 'thelma:tests/tools/metadata/iso_finder/'
        self.valid_file = 'valid_file.xls'
        self.experiment_design = None
        self.log = TestingLog()
        self.silent_log = SilentLog()
        self.user = get_user('it')
        # pos label - md pool, reagent name, reagent dil factor, final conc
        self.result_data = dict(
                A1=[205200, 'mix1', 1400, 10], B1=[205200, 'mix1', 1400, 20],
                C1=[205201, 'mix1', 1400, 10], D1=[205201, 'mix1', 1400, 20],
                E1=[205200, 'sol2', 1400, 10], F1=[205200, 'sol2', 1400, 20],
                G1=[205201, 'sol2', 1400, 10], H1=[205201, 'sol2', 1400, 20],
                A2=[205200, 'mix1', 2800, 10], B2=[205200, 'mix1', 2800, 20],
                C2=[205201, 'mix1', 2800, 10], D2=[205201, 'mix1', 2800, 20],
                E2=[205200, 'sol2', 2800, 10], F2=[205200, 'sol2', 2800, 20],
                G2=[205201, 'sol2', 2800, 10], H2=[205201, 'sol2', 2800, 20],
                A3=[205202, 'mix1', 1400, 10], B3=[205202, 'mix1', 1400, 20],
                C3=['mock', 'mix1', 1400, 'mock'],
                D3=[205202, 'sol2', 1400, 10], E3=[205202, 'sol2', 1400, 20],
                F3=['mock', 'sol2', 1400, 'mock'],
                A4=[205202, 'mix1', 2800, 10], B4=[205202, 'mix1', 2800, 20],
                C4=['mock', 'mix1', 2800, 'mock'],
                D4=[205202, 'sol2', 2800, 10], E4=[205202, 'sol2', 2800, 20],
                F4=['mock', 'sol2', 2800, 'mock'])

    def _continue_setup(self, file_name=None):
        if file_name is None: file_name = self.valid_file
        self._read_file(file_name)
        self._create_tool()

    def _read_file(self, file_name):
        full_fn = self.FILE_PATH + file_name
        fn = full_fn.split(':')
        f = resource_filename(*fn)
        try:
            stream = open(f, 'rb')
            source = stream.read()
            handler = ExperimentDesignParserHandler(stream=source,
                            requester=self.user, log=self.silent_log,
                            scenario=get_experiment_type_robot_optimisation())
            self.experiment_design = handler.get_result()
        finally:
            stream.close()

    def _check_result(self, file_name=None):
        self._continue_setup(file_name)
        tf_layout = self.tool.get_result()
        self.assert_is_not_none(tf_layout)
        self.assert_equal(len(tf_layout), len(self.result_data))
        for tf_pos in tf_layout.get_sorted_working_positions():
            pos_label = tf_pos.rack_position.label
            exp_data = self.result_data[pos_label]
            self.assert_is_not_none(tf_pos)
            self.assert_equal(tf_pos.molecule_design_pool_id, exp_data[0])
            self.assert_equal(tf_pos.reagent_name, exp_data[1])
            self.assert_equal(tf_pos.reagent_dil_factor, exp_data[2])
            self.assert_equal(tf_pos.final_concentration, exp_data[3])
            self.assert_is_none(tf_pos.iso_volume)
            self.assert_is_none(tf_pos.iso_concentration)


class TransfectionLayoutFinderTestCase(TransfectionLayoutFinderBaseTestCase):

    def _create_tool(self):
        self.tool = TransfectionLayoutFinder(log=self.log,
                                    experiment_design=self.experiment_design)

    def _test_and_expect_errors(self, msg=None):
        TransfectionLayoutFinderBaseTestCase._test_and_expect_errors(self,
                                                                     msg=msg)
        self.assert_is_none(self.tool.get_experiment_transfection_layouts())

    def _check_result(self, file_name=None):
        TransfectionLayoutFinderBaseTestCase._check_result(self,
                                                           file_name=file_name)
        els = self.tool.get_experiment_transfection_layouts()
        self.assert_equal(len(els), 2)

    def test_result(self):
        self._check_result()

    def test_additional_iso_concentration(self):
        self._check_result('additional_iso_conc.xls')
        self._check_warning_messages('has ISO concentration specifications')

    def test_additional_iso_volume(self):
        self._check_result('additional_iso_vol.xls')
        self._check_warning_messages('has ISO volume specifications')

    def test_additional_volume_and_concentration(self):
        self._check_result('additional_iso_conc_and_vol.xls')
        self._check_warning_messages('has ISO volume and ISO concentration ' \
                                     'specifications')

    def test_invalid_experiment_design(self):
        self._continue_setup()
        self.experiment_design = None
        self._test_and_expect_errors('The experiment design must be a ' \
                                     'ExperimentDesign object')

    def test_converter_error(self):
        self._continue_setup('converter_failure.xls')
        self._test_and_expect_errors('Error when trying to convert design ' \
                                     'rack layout for design rack "1"')

    def test_no_controls(self):
        self._continue_setup('no_controls.xls')
        self._test_and_expect_errors('There are no controls in the layout ' \
                                     'for design rack')

    def test_optimiser_failure(self):
        self._continue_setup('not_enough_src_postitions.xls')
        self._test_and_expect_errors('Error when trying to optimise ISO layout')


class TransfectionLayoutOptimizerTestCase(TransfectionLayoutFinderBaseTestCase):

    def set_up(self):
        TransfectionLayoutFinderBaseTestCase.set_up(self)
        self.design_rack_layouts = dict()
        self.placeholders = dict()

    def tear_down(self):
        TransfectionLayoutFinderBaseTestCase.tear_down(self)
        del self.design_rack_layouts
        del self.placeholders

    def _create_tool(self):
        self.tool = _TransfectionLayoutOptimizer(log=self.log,
                                design_rack_layouts=self.design_rack_layouts)

    def _continue_setup(self, file_name=None):
        if file_name is None: file_name = self.valid_file
        self._read_file(file_name)
        self.__convert_layouts()
        self.__sort_floatings()
        self._create_tool()

    def __convert_layouts(self):
        for design_rack in self.experiment_design.experiment_design_racks:
            converter = TransfectionLayoutConverter(log=self.silent_log,
                                        rack_layout=design_rack.rack_layout,
                                        is_iso_request_layout=False,
                                        is_mastermix_template=True)
            self.design_rack_layouts[design_rack.label] = converter.get_result()

    def __sort_floatings(self):
        for tf_layout in self.design_rack_layouts.values():
            for tf_pos in tf_layout.get_sorted_working_positions():
                if not tf_pos.is_floating: continue
                old_placeholder = tf_pos.molecule_design_pool
                if self.placeholders.has_key(old_placeholder):
                    new_placeholder = self.placeholders[old_placeholder]
                else:
                    new_placeholder = '%s%03i' % (
                                    TransfectionParameters.FLOATING_INDICATOR,
                                    len(self.placeholders) + 1)
                    self.placeholders[old_placeholder] = new_placeholder
                tf_pos.molecule_design_pool = new_placeholder

    def test_result_384_to_96(self):
        # different design racks, 1 subcolumn per column
        self.result_data = dict(
                A1=[205200, 'mix1', 1400, 10], B1=[205200, 'mix1', 1400, 20],
                C1=[205201, 'mix1', 1400, 10], D1=[205201, 'mix1', 1400, 20],
                E1=[205200, 'sol2', 1400, 10], F1=[205200, 'sol2', 1400, 20],
                G1=[205201, 'sol2', 1400, 10], H1=[205201, 'sol2', 1400, 20],
                A2=[205200, 'mix1', 2800, 10], B2=[205200, 'mix1', 2800, 20],
                C2=[205201, 'mix1', 2800, 10], D2=[205201, 'mix1', 2800, 20],
                E2=[205200, 'sol2', 2800, 10], F2=[205200, 'sol2', 2800, 20],
                G2=[205201, 'sol2', 2800, 10], H2=[205201, 'sol2', 2800, 20],
                A3=[205202, 'mix1', 1400, 10], B3=[205202, 'mix1', 1400, 20],
                C3=['mock', 'mix1', 1400, 'mock'],
                D3=[205202, 'sol2', 1400, 10], E3=[205202, 'sol2', 1400, 20],
                F3=['mock', 'sol2', 1400, 'mock'],
                A4=[205202, 'mix1', 2800, 10], B4=[205202, 'mix1', 2800, 20],
                C4=['mock', 'mix1', 2800, 'mock'],
                D4=[205202, 'sol2', 2800, 10], E4=[205202, 'sol2', 2800, 20],
                F4=['mock', 'sol2', 2800, 'mock'])
        self._check_result()

    def test_result_384_to_96_2_subcolumns(self):
        # different design racks, 2 subcolumns per column
        self.result_data = dict(
                A1=[205200, 'mix1', 1400, 10], B1=[205200, 'mix1', 1400, 20],
                C1=[205200, 'sol2', 1400, 10], D1=[205200, 'sol2', 1400, 20],
                E1=[205201, 'mix1', 1400, 10], F1=[205201, 'mix1', 1400, 20],
                G1=[205201, 'sol2', 1400, 10], H1=[205201, 'sol2', 1400, 20],
                A2=[205200, 'mix1', 2800, 10], B2=[205200, 'mix1', 2800, 20],
                C2=[205200, 'sol2', 2800, 10], D2=[205200, 'sol2', 2800, 20],
                E2=[205201, 'mix1', 2800, 10], F2=[205201, 'mix1', 2800, 20],
                G2=[205201, 'sol2', 2800, 10], H2=[205201, 'sol2', 2800, 20],
                A3=[205202, 'mix1', 1400, 10], B3=[205202, 'mix1', 1400, 20],
                C3=[205202, 'sol2', 1400, 10], D3=[205202, 'sol2', 1400, 20],
                E3=[205202, 'mix1', 2800, 10], F3=[205202, 'mix1', 2800, 20],
                G3=[205202, 'sol2', 2800, 10], H3=[205202, 'sol2', 2800, 20],
                A4=['mock', 'mix1', 1400, None],
                B4=['mock', 'sol2', 1400, None],
                C4=['mock', 'mix1', 2800, None],
                D4=['mock', 'sol2', 2800, None])
        self._check_result('valid_file_2_subcolumns.xls')

    def test_result_384_to_96_merge_columns(self):
        # equal design racks, 2 subcolumns per column, partly used tids
        self.result_data = dict(
                A1=[205200, 'mix', 1400, 10], B1=[205201, 'mix', 1400, 10],
                C1=[205202, 'mix', 1400, 10], D1=[205202, 'mix', 2800, 10],
                E1=[205203, 'mix', 1400, 10], F1=[205203, 'mix', 2800, 10],
                G1=['mock', 'mix', 1400, 'mock'],
                H1=['mock', 'mix', 2800, 'mock'],
                A2=[205200, 'mix', 1400, 20], B2=[205201, 'mix', 1400, 20],
                C2=[205202, 'mix', 1400, 20], D2=[205202, 'mix', 2800, 20],
                E2=[205203, 'mix', 1400, 20], F2=[205203, 'mix', 2800, 20],
                G2=[205200, 'mix', 2800, 10], H2=[205201, 'mix', 2800, 10],
                A3=[205200, 'mix', 2800, 20], B3=[205201, 'mix', 2800, 20])
        self._check_result('valid_file_merge_columns.xls')

    def test_result_merge_large_columns(self):
        # equal design racks, 2 subcolumns per column, partly used tids
        self.result_data = dict(
                A1=[205200, 'mix', 1400, 10], B1=[205201, 'mix', 1400, 10],
                C1=[205202, 'mix', 1400, 10], D1=[205202, 'mix', 2800, 10],
                E1=[205202, 'mix', 1400, 20], F1=[205202, 'mix', 2800, 20],
                G1=[205203, 'mix', 1400, 10], H1=[205203, 'mix', 2800, 10],
                A2=[205200, 'mix', 2800, 10], B2=[205201, 'mix', 2800, 10],
                C2=['mock', 'mix', 1400, None], D2=['mock', 'mix', 2800, None],
                E2=[205200, 'mix', 1400, 20], F2=[205201, 'mix', 1400, 20],
                G2=[205203, 'mix', 1400, 20], H2=[205203, 'mix', 2800, 20],
                A3=[205200, 'mix', 2800, 20], B3=[205201, 'mix', 2800, 20])
        self._check_result('valid_file_merge_columns_too_large.xls')

    def test_result_96_one_to_one(self):
        # 1 to 1 for 96 wells
        self.result_data = dict(
                A1=[205200, 'mix', 140, 10], A2=[205200, 'mix', 140, 20],
                A4=[205202, 'mix', 140, 10], A5=[205202, 'mix', 140, 20],
                B1=[205200, 'mix', 280, 10], B2=[205200, 'mix', 280, 20],
                B4=[205202, 'mix', 280, 10], B5=[205202, 'mix', 280, 20],
                E1=[205201, 'mix', 140, 10], E2=[205201, 'mix', 140, 20],
                E4=['mock', 'mix', 140, None],
                F1=[205201, 'mix', 280, 10], F2=[205201, 'mix', 280, 20],
                F4=['mock', 'mix', 280, None])
        self._check_result('valid_file_96_one_to_one.xls')

    def test_result_384_one_to_one(self):
        # 1 to 1 for 384
        self.result_data = dict(
                B2=[205200, 'mix', 140, 10], C2=[205201, 'mix', 140, 10],
                B4=['mock', 'mix', 140, None])
        non_floating_positions = ['B2', 'B3', 'B4', 'C2', 'C3', 'C4',
                                  'B12', 'B13', 'B14', 'C12', 'C13', 'C14']
        c = 0
        for rack_pos in get_positions_for_shape(get_384_rack_shape()):
            if rack_pos.column_index in (0, 23): continue
            if rack_pos.row_index in (0, 15): continue
            if rack_pos.label in non_floating_positions: continue
            c += 1
            md_id = '%s%03i' % (TransfectionParameters.FLOATING_INDICATOR, c)
            self.result_data[rack_pos.label] = [md_id, 'mix', 140, 10]
        self._check_result('valid_file_384_one_to_one.xls')

    def test_result_384(self):
        # 2 different design racks, different subcolumns (src and trg)
        pos_data = dict(
            A1=205200, A2=205201, A3='mock', A4='md_001', A5='md_002',
            B1=205200, B2=205201, B3='mock', B4='md_001', B5='md_002',
            C1='md_006', C2='md_007', C3='md_008', C4='md_011', C5='md_012',
            D1='md_006', D2='md_007', D3='md_008', D4='md_011', D5='md_012',
            E1='md_016', E2='md_017', E3='md_018', E4='md_021', E5='md_022',
            F1='md_016', F2='md_017', F3='md_018', F4='md_021', F5='md_022',
            G1='md_026', G2='md_027', G3='md_028', G4='md_031', G5='md_032',
            H1='md_026', H2='md_027', H3='md_028', H4='md_031', H5='md_032',
            I1='md_036', I2='md_037', I3='md_038', I4='md_041', I5='md_042',
            J1='md_036', J2='md_037', J3='md_038', J4='md_041', J5='md_042',
            K1='md_046', K2='md_047', K3='md_048',
            L1='md_046', L2='md_047', L3='md_048',
            A6='md_003', A7='md_004', A8='md_009', A9='md_005', A10='md_010',
            B6='md_003', B7='md_004', B8='md_009', B9='md_005', B10='md_010',
            C6='md_013', C7='md_014', C8='md_019', C9='md_015', C10='md_020',
            D6='md_013', D7='md_014', D8='md_019', D9='md_015', D10='md_020',
            E6='md_023', E7='md_024', E8='md_029', E9='md_025', E10='md_030',
            F6='md_023', F7='md_024', F8='md_029', F9='md_025', F10='md_030',
            G6='md_033', G7='md_034', G8='md_039', G9='md_035', G10='md_040',
            H6='md_033', H7='md_034', H8='md_039', H9='md_035', H10='md_040',
            I6='md_043', I7='md_044', I8='md_049', I9='md_045', I10='md_050',
            J6='md_043', J7='md_044', J8='md_049', J9='md_045', J10='md_050')
        for pos_label, md_id in pos_data.iteritems():
            rack_pos = get_rack_position_from_label(pos_label)
            if rack_pos.row_index % 2 == 0:
                reagent_dil_factor = 140
            else:
                reagent_dil_factor = 280
            fc = 10
            if md_id == 'mock': fc = None
            self.result_data[pos_label] = [md_id, 'mix', reagent_dil_factor, fc]
        self._check_result('valid_file_384.xls')

    def test_devide_subcolumns(self):
        # 2 different design racks, each having 7 stretches of 6 tids
        # (2 subcolumns per stretch)
        self.result_data = dict(
                G1=[205206, 'mix', 140, 10], H1=[205206, 'mix', 140, 30],
                G2=[205206, 'mix', 140, 20], H2=[205206, 'mix', 140, 40],
                G3=[205206, 'mix', 280, 10], H3=[205206, 'mix', 280, 30],
                G4=[205206, 'mix', 280, 20], H4=[205206, 'mix', 280, 40],
                G5=[205206, 'mix', 140, 50], H5=[205206, 'mix', 140, 60],
                G6=[205206, 'mix', 280, 50], H6=[205206, 'mix', 280, 60])
        shape = get_96_rack_shape()
        mds = {0 : 205200, 1 : 205200, 2 : 205201, 3 : 205201, 4 : 205202,
               5 : 205202, 6 : 205203, 7 : 205203, 8 : 205204, 9 : 205204,
               10: 205205, 11 : 205205}
        fcs = {0 : 10, 1 : 30, 2 : 50, 3 : 20, 4 : 40, 5 : 60}
        for rack_pos in get_positions_for_shape(shape):
            row_index = rack_pos.row_index
            if row_index > 5: continue
            col_index = rack_pos.column_index
            if col_index % 2 == 0:
                rdf = 140
            else:
                rdf = 280
            self.result_data[rack_pos.label] = [mds[col_index], 'mix', rdf,
                                                fcs[row_index]]
        self._check_result('valid_file_devide_subcolumns.xls')

    def test_invalid_design_rack_layouts(self):
        self._continue_setup()
        self.design_rack_layouts = dict()
        self._test_and_expect_errors('There is no design rack in the layout ' \
                                     'map!')
        self.design_rack_layouts = {'1' : 1}
        self._test_and_expect_errors('The design rack layout must be a ' \
                                     'TransfectionLayout object')
        self.design_rack_layouts = []
        self._test_and_expect_errors('The design rack layout map must be a ' \
                                     'dict')

    def test_not_enough_src_postitions(self):
        self._continue_setup('not_enough_src_postitions.xls')
        self._test_and_expect_errors('The number of source positions ' \
                                     '(392) exceeds 384!')
