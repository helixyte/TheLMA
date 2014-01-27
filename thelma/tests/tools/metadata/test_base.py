"""
Tests the classes related in transfection.

AAB
"""
from thelma.automation.semiconstants import get_96_rack_shape
from thelma.automation.semiconstants import get_min_transfer_volume
from thelma.automation.semiconstants import get_pipetting_specs_biomek
from thelma.automation.semiconstants import get_pipetting_specs_cybio
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.semiconstants import get_reservoir_specs_standard_96
from thelma.automation.tools.metadata.base import TransfectionAssociationData
from thelma.automation.tools.metadata.base import TransfectionLayout
from thelma.automation.tools.metadata.base import TransfectionLayoutConverter
from thelma.automation.tools.metadata.base import TransfectionParameters
from thelma.automation.tools.metadata.base import TransfectionPosition
from thelma.automation.tools.metadata.base import TransfectionSectorAssociator
from thelma.automation.utils.layouts import LIBRARY_POSITION_TYPE
from thelma.automation.utils.layouts import MOCK_POSITION_TYPE
from thelma.automation.utils.layouts import UNTREATED_POSITION_TYPE
from thelma.interfaces import IMoleculeDesignPool
from thelma.interfaces import IUser
from thelma.models.moleculetype import MOLECULE_TYPE_IDS
from thelma.models.rack import RackPositionSet
from thelma.models.racklayout import RackLayout
from thelma.models.tagging import Tag
from thelma.tests.tools.utils.test_iso import IsoRequestClassesBaseTestCase
from thelma.tests.tools.utils.test_iso import _IsoRequestRackSectorToolTestCase
from thelma.tests.tools.utils.utils import ConverterTestCase
import logging


class _TransfectionClassesBaseTestCase(IsoRequestClassesBaseTestCase):

    POS_CLS = TransfectionPosition
    LAYOUT_CLS = TransfectionLayout

    _REAGENT_NAME_TAG = {
            'a1' : Tag('transfection', 'reagent_name', 'mix1'),
            'b1' : Tag('transfection', 'reagent_name', 'mix1'),
            'c1' : Tag('transfection', 'reagent_name', 'mix1'),
            'd1' : Tag('transfection', 'reagent_name', 'mix1'),
            'e1' : Tag('transfection', 'reagent_name', 'untreated'),
            'f1' : Tag('transfection', 'reagent_name', 'untransfected')}

    _REAGENT_DF_TAG = {
            'a1' : Tag('transfection', 'reagent_dilution_factor', '1400'),
            'b1' : Tag('transfection', 'reagent_dilution_factor', '2800'),
            'c1' : Tag('transfection', 'reagent_dilution_factor', '1400'),
            'd1' : Tag('transfection', 'reagent_dilution_factor', '1400'),
            'e1' : Tag('transfection', 'reagent_dilution_factor', 'untreated'),
            'f1' : Tag('transfection', 'reagent_dilution_factor',
                       'untransfected')}

    _FINAL_CONC_TAG = {
            'a1' : Tag('transfection', 'final_concentration', '1'),
            'b1' : Tag('transfection', 'final_concentration', '1'),
            'c1' : Tag('transfection', 'final_concentration', 'mock'),
            'd1' : Tag('transfection', 'final_concentration', '1'),
            'e1' : Tag('transfection', 'final_concentration', 'None'),
            'f1' : Tag('transfection', 'final_concentration', 'untransfected')}

    _OPTIMEM_DF_TAG = {
            'a1' : Tag('transfection', 'optimem_dilution_factor', '7'),
            'b1' : Tag('transfection', 'optimem_dilution_factor', '7'),
            'c1' : Tag('transfection', 'optimem_dilution_factor', '7'),
            'd1' : Tag('transfection', 'optimem_dilution_factor', '8'),
            'e1' : Tag('transfection', 'optimem_dilution_factor', 'untreated'),
            'f1' : Tag('transfection', 'optimem_dilution_factor', 'None')}

    def set_up(self):
        IsoRequestClassesBaseTestCase.set_up(self)
        # the position data is extended by reagent name, reagent df,
        # final conc and optimem dilution factor
        self.pos_data['a1'].extend(['mix1', 1400, 1, 7])
        self.pos_data['b1'].extend(['mix1', 2800, 1, 7])
        self.pos_data['c1'].extend(['mix1', 1400, 'mock', 7])
        self.pos_data['d1'].extend(['mix1', 1400, 1, 8])
        self.pos_data['e1'].extend(['untreated', 'untreated', 'None',
                                    'untreated'])
        self.pos_data['f1'].extend(['untransfected', 'untransfected',
                                    'untransfected', 'None'])
        self.pos_data['g1'].extend([None, None, None, None])

    def _get_init_data(self, pos_label):
        kw = IsoRequestClassesBaseTestCase._get_init_data(self, pos_label)
        pos_data = self.pos_data[pos_label]
        kw['reagent_name'] = pos_data[4]
        kw['reagent_dil_factor'] = pos_data[5]
        kw['final_concentration'] = pos_data[6]
        kw['optimem_dil_factor'] = pos_data[7]
        return kw

    def _get_tags(self, pos_label):
        tags = IsoRequestClassesBaseTestCase._get_tags(self, pos_label)
        self._add_optional_tag(tags, self._FINAL_CONC_TAG, pos_label)
        self._add_optional_tag(tags, self._REAGENT_NAME_TAG, pos_label)
        self._add_optional_tag(tags, self._REAGENT_DF_TAG, pos_label)
        self._add_optional_tag(tags, self._OPTIMEM_DF_TAG, pos_label)
        return tags


class TransfectionParametersTestCase(_TransfectionClassesBaseTestCase):

    def test_is_valid_mock_value(self):
        # final concentration
        m = {'mock' : True, 'MOCK' : True, None : True, 'None' : True,
             'fixed' : False, 'empty' : False, 'untreated' : False}
        self.__check_results(m, TransfectionParameters.FINAL_CONCENTRATION)
        # reagent name
        m = {'mock' : True, None : True, 'None' : True, 2 : False,
             '1' : False, 'm' : False, 'mix' : True}
        self.__check_results(m, TransfectionParameters.REAGENT_NAME)
        # reagent dilution factor
        m = {12.3 : True, '12.3' : True, None : True, 'mock' : False,
             - 2: False}
        self.__check_results(m, TransfectionParameters.REAGENT_DIL_FACTOR)
        # optimem dil factor
        self.__check_results(m, TransfectionParameters.OPTIMEM_DIL_FACTOR)

    def __check_results(self, result_map, parameter):
        for val, exp_res in result_map.iteritems():
            res = TransfectionParameters.is_valid_mock_value(val, parameter)
            self.assert_equal(res, exp_res)

    def test_calculate_iso_volume(self):
        reservoir_specs = get_reservoir_specs_standard_96()
        biomek_specs = get_pipetting_specs_biomek()
        optimem_df_sirna = 4
        iso_vol1 = TransfectionParameters.calculate_iso_volume(
                            number_target_wells=16, number_replicates=3,
                            iso_reservoir_spec=reservoir_specs,
                            optimem_dil_factor=optimem_df_sirna,
                            pipetting_specs=biomek_specs)
        self.assert_equal(iso_vol1, 33.8)
        iso_vol2 = TransfectionParameters.calculate_iso_volume(1, 1,
                                    iso_reservoir_spec=reservoir_specs,
                                    optimem_dil_factor=optimem_df_sirna,
                                    pipetting_specs=biomek_specs)
        min_vol = get_min_transfer_volume(biomek_specs)
        self.assert_equal(iso_vol2, min_vol)
        cybio_specs = get_pipetting_specs_cybio()
        iso_vol3 = TransfectionParameters.calculate_iso_volume(
                            number_target_wells=4, number_replicates=2,
                            iso_reservoir_spec=reservoir_specs,
                            optimem_dil_factor=optimem_df_sirna,
                            pipetting_specs=cybio_specs)
        self.assert_equal(iso_vol3, 6.3)
        iso_vol4 = TransfectionParameters.calculate_iso_volume(
                            number_target_wells=1, number_replicates=1,
                            iso_reservoir_spec=reservoir_specs,
                            optimem_dil_factor=optimem_df_sirna,
                            pipetting_specs=cybio_specs)
        self.assert_equal(iso_vol4, 1.9)
        optimem_df_mirna = 3
        iso_vol5 = TransfectionParameters.calculate_iso_volume(
                            number_target_wells=4, number_replicates=2,
                            iso_reservoir_spec=reservoir_specs,
                            optimem_dil_factor=optimem_df_mirna,
                            pipetting_specs=cybio_specs)
        self.assert_equal(iso_vol5, 8.4)

    def test_get_optimem_dilution_factor_from_molecule_type(self):
        meth = TransfectionParameters.\
               get_optimem_dilution_factor_from_molecule_type
        mt = MOLECULE_TYPE_IDS.SIRNA
        self.assert_equal(4, meth(mt))
        mt = MOLECULE_TYPE_IDS.MIRNA_INHI
        self.assert_equal(3, meth(mt))

    def test_get_total_dilution_factor(self):
        optimem_df_sirna = 4
        self.assert_equal(56, TransfectionParameters.\
                          get_total_dilution_factor(optimem_df_sirna))
        optimem_df_mirna = 3
        self.assert_equal(42, TransfectionParameters.\
                          get_total_dilution_factor(optimem_df_mirna))

    def test_calculate_mastermix_volume_from_target_well_number(self):
        meth = TransfectionParameters.\
                        calculate_mastermix_volume_from_target_well_number
        reservoir_specs = get_reservoir_specs_standard_96()
        biomek_specs = get_pipetting_specs_biomek()

        req_vol1 = meth(number_target_wells=10, number_replicates=3,
                        iso_reservoir_spec=reservoir_specs,
                        pipetting_specs=biomek_specs)
        self.assert_equal(req_vol1, 180)
        req_vol2 = meth(number_target_wells=10, number_replicates=1,
                        iso_reservoir_spec=reservoir_specs,
                        pipetting_specs=biomek_specs)
        self.assert_equal(req_vol2, 67)
        cybio_specs = get_pipetting_specs_cybio()
        req_vol3 = meth(number_target_wells=10, number_replicates=1,
                        iso_reservoir_spec=reservoir_specs,
                        pipetting_specs=cybio_specs)
        self.assert_equal(req_vol3, 60)

    def test_calculate_mastermix_volume_from_iso_volume(self):
        meth = TransfectionParameters.calculate_mastermix_volume_from_iso_volume
        optimem_df_sirna = 4
        self.assert_equal(80, meth(10, optimem_df_sirna))
        optimem_df_mirna = 3
        self.assert_equal(60, meth(10, optimem_df_mirna))

    def test_calculate_reagent_dilution_volume(self):
        iso_volume = 1
        optimem_df_sirna = 4
        req_vol1 = TransfectionParameters.calculate_reagent_dilution_volume(
                                                iso_volume, optimem_df_sirna)
        self.assert_equal(req_vol1, 4)
        optimem_df_mirna = 3
        req_vol2 = TransfectionParameters.calculate_reagent_dilution_volume(
                                                iso_volume, optimem_df_mirna)
        self.assert_equal(req_vol2, 3)

    def test_calculate_initial_reagent_dilution(self):
        self.assert_equal(100,
            TransfectionParameters.calculate_initial_reagent_dilution(1400))

    def test_get_layout_optimem_molecule_type(self):
        tf_layout = TransfectionLayout(shape=get_96_rack_shape())
        a1_pos = get_rack_position_from_label('A1')
        b1_pos = get_rack_position_from_label('B1')
        c1_pos = get_rack_position_from_label('C1')
        mi_rna1 = self._get_entity(IMoleculeDesignPool, '330001')
        tf_pos1 = TransfectionPosition(rack_position=a1_pos,
                               molecule_design_pool=mi_rna1)
        tf_pos1.store_optimem_dilution_factor()
        mi_rna2 = self._get_entity(IMoleculeDesignPool, '330002')
        tf_pos2 = TransfectionPosition(rack_position=b1_pos,
                               molecule_design_pool=mi_rna2)
        tf_pos2.store_optimem_dilution_factor()
        tf_pos3 = TransfectionPosition.create_mock_position(c1_pos)
        tf_layout.add_position(tf_pos1)
        tf_layout.add_position(tf_pos2)
        tf_layout.add_position(tf_pos3)
        self.assert_equal(3, TransfectionParameters.\
                          get_layout_mock_optimem_molecule_type(tf_layout))
        si_rna = self._get_entity(IMoleculeDesignPool, '205200')
        tf_pos1.molecule_design_pool = si_rna
        tf_pos1.store_optimem_dilution_factor()
        self.assert_equal(4, TransfectionParameters.\
                          get_layout_mock_optimem_molecule_type(tf_layout))


class TransfectionPositionTestCase(_TransfectionClassesBaseTestCase):

    def test_init(self):
        self._test_position_init()

    def test_empty_init_failures(self):
        kw = self._get_init_data('g1')
        ep = self._get_position('g1', attrs=kw)
        self.assert_is_not_none(ep)
        kw['reagent_name'] = 'None'
        self._expect_error(ValueError, self.POS_CLS,
            'The reagent name must be None for empty positions ' \
            '(obtained: None)!', **kw)
        kw['reagent_name'] = None
        kw['reagent_dil_factor'] = 'None'
        self._expect_error(ValueError, self.POS_CLS,
            'The reagent dilution factor must be None for empty positions ' \
            '(obtained: None)!', **kw)
        kw['reagent_dil_factor'] = None
        kw['final_concentration'] = 'None'
        self._expect_error(ValueError, self.POS_CLS,
            'The final concentration must be None for empty positions ' \
            '(obtained: None)!', **kw)
        kw['final_concentration'] = None
        kw['optimem_dil_factor'] = 2
        self._expect_error(ValueError, self.POS_CLS,
            'The optimem dilution factor must be None for empty positions ' \
            '(obtained: 2)!', **kw)

    def test_untransfected_init_failures(self):
        kw = self._get_init_data('f1')
        ep = self._get_position('f1', attrs=kw)
        self.assert_is_not_none(ep)
        kw['reagent_name'] = 'mix1'
        self._expect_error(ValueError, self.POS_CLS,
               'The value "mix1" is invalid for the reagent name of ' \
               'untransfected positions. Allowed values are: (None, ' \
               '\'UNTREATED\', \'NONE\', \'UNTRANSFECTED\')', **kw)
        kw['reagent_name'] = None
        kw['reagent_dil_factor'] = 1400
        self._expect_error(ValueError, self.POS_CLS,
                'The value "1400.0" is invalid for the reagent dilution ' \
                'factor of untransfected positions. Allowed values are: ' \
                '(None, \'UNTREATED\', \'NONE\', \'UNTRANSFECTED\')', **kw)
        kw['reagent_dil_factor'] = None
        kw['final_concentration'] = 5
        self._expect_error(ValueError, self.POS_CLS,
                'The value "5.0" is invalid for the final concentration ' \
                'of untransfected positions. Allowed values are: ' \
                '(None, \'UNTREATED\', \'NONE\', \'UNTRANSFECTED\')', **kw)
        kw['final_concentration'] = None
        kw['optimem_dil_factor'] = 2
        self._expect_error(ValueError, self.POS_CLS,
                'The value "2" is invalid for the optimem dilution ' \
                'factor of untransfected positions. Allowed values are: ' \
                '(None, \'UNTREATED\', \'NONE\', \'UNTRANSFECTED\')', **kw)

    def test_untreated_init_failures(self):
        kw = self._get_init_data('e1')
        ep = self._get_position('e1', attrs=kw)
        self.assert_is_not_none(ep)
        kw['reagent_name'] = 'mix1'
        self._expect_error(ValueError, self.POS_CLS,
               'The value "mix1" is invalid for the reagent name of ' \
               'untreated positions. Allowed values are: (None, ' \
               '\'UNTREATED\', \'NONE\', \'UNTRANSFECTED\')', **kw)
        kw['reagent_name'] = None
        kw['reagent_dil_factor'] = 1400
        self._expect_error(ValueError, self.POS_CLS,
                'The value "1400.0" is invalid for the reagent dilution ' \
                'factor of untreated positions. Allowed values are: ' \
                '(None, \'UNTREATED\', \'NONE\', \'UNTRANSFECTED\')', **kw)
        kw['reagent_dil_factor'] = None
        kw['final_concentration'] = 5
        self._expect_error(ValueError, self.POS_CLS,
                'The value "5.0" is invalid for the final concentration ' \
                'of untreated positions. Allowed values are: ' \
                '(None, \'UNTREATED\', \'NONE\', \'UNTRANSFECTED\')', **kw)
        kw['final_concentration'] = None
        kw['optimem_dil_factor'] = 2
        self._expect_error(ValueError, self.POS_CLS,
                'The value "2" is invalid for the optimem dilution ' \
                'factor of untreated positions. Allowed values are: ' \
                '(None, \'UNTREATED\', \'NONE\', \'UNTRANSFECTED\')', **kw)

    def test_library_init_failure(self):
        kw = self._get_init_data('d1')
        ep = self._get_position('d1', attrs=kw)
        self.assert_is_not_none(ep)
        kw['reagent_name'] = 3
        self._expect_error(ValueError, self.POS_CLS,
               'The reagent name must be at least 2 characters long if ' \
               'there is one (obtained: "3")!', **kw)
        kw['reagent_name'] = None
        kw['reagent_dil_factor'] = LIBRARY_POSITION_TYPE
        self._expect_error(ValueError, self.POS_CLS,
                'The reagent dilution factor must be a positive number ' \
                '(obtained: library).', **kw)
        kw['reagent_dil_factor'] = None
        kw['final_concentration'] = LIBRARY_POSITION_TYPE
        self._expect_error(ValueError, self.POS_CLS,
                'The final concentration must be a positive number ' \
                '(obtained: library).', **kw)
        kw['final_concentration'] = None
        kw['optimem_dil_factor'] = LIBRARY_POSITION_TYPE
        self._expect_error(ValueError, self.POS_CLS,
                'The optimem dilution factor must be a positive number ' \
                '(obtained: library).', **kw)

    def test_mock_init_failure(self):
        kw = self._get_init_data('c1')
        ep = self._get_position('c1', attrs=kw)
        self.assert_is_not_none(ep)
        kw['reagent_name'] = 3
        self._expect_error(ValueError, self.POS_CLS,
               'The reagent name must be at least 2 characters long if ' \
               'there is one (obtained: "3")!', **kw)
        kw['reagent_name'] = None
        kw['reagent_dil_factor'] = -2
        self._expect_error(ValueError, self.POS_CLS,
                'The reagent dilution factor must be a positive number ' \
                '(obtained: -2).', **kw)
        kw['reagent_dil_factor'] = None
        kw['final_concentration'] = 'default'
        self._expect_error(ValueError, self.POS_CLS,
                'The value "default" is invalid for the final concentration ' \
                'of mock positions. Allowed values are: (None, \'MOCK\', ' \
                '\'NONE\')', **kw)
        kw['final_concentration'] = None
        kw['optimem_dil_factor'] = 'default'
        self._expect_error(ValueError, self.POS_CLS,
                'The optimem dilution factor must be a positive number ' \
                '(obtained: default)', **kw)

    def test_floating_init_failure(self):
        kw = self._get_init_data('b1')
        ep = self._get_position('b1', attrs=kw)
        self.assert_is_not_none(ep)
        kw['reagent_name'] = 3
        self._expect_error(ValueError, self.POS_CLS,
               'The reagent name must be at least 2 characters long if ' \
               'there is one (obtained: "3")!', **kw)
        kw['reagent_name'] = None
        kw['reagent_dil_factor'] = -2
        self._expect_error(ValueError, self.POS_CLS,
                'The reagent dilution factor must be a positive number ' \
                '(obtained: -2).', **kw)
        kw['reagent_dil_factor'] = None
        kw['final_concentration'] = -2
        self._expect_error(ValueError, self.POS_CLS,
               'The final concentration must be a positive number ' \
               '(obtained: -2).', **kw)
        kw['final_concentration'] = None
        kw['optimem_dil_factor'] = 'default'
        self._expect_error(ValueError, self.POS_CLS,
                'The optimem dilution factor must be a positive number ' \
                '(obtained: default).', **kw)

    def test_fixed_init_failure(self):
        kw = self._get_init_data('a1')
        ep = self._get_position('a1', attrs=kw)
        self.assert_is_not_none(ep)
        kw['reagent_name'] = 'm'
        self._expect_error(ValueError, self.POS_CLS,
               'The reagent name must be at least 2 characters long if ' \
               'there is one (obtained: "m")!', **kw)
        kw['reagent_name'] = None
        kw['reagent_dil_factor'] = -2
        self._expect_error(ValueError, self.POS_CLS,
                'The reagent dilution factor must be a positive number ' \
                '(obtained: -2).', **kw)
        kw['reagent_dil_factor'] = None
        kw['final_concentration'] = -2
        self._expect_error(ValueError, self.POS_CLS,
                'The final concentration must be a positive number ' \
                '(obtained: -2).', **kw)
        kw['final_concentration'] = None
        kw['optimem_dil_factor'] = 'default'
        self._expect_error(ValueError, self.POS_CLS,
                'The optimem dilution factor must be a positive number ' \
                '(obtained: default).', **kw)

    def test_equality(self):
        self._test_position_equality(
                dict(iso_concentration=70, iso_volume=100,
                     reagent_name='other', reagent_dil_factor='17',
                     final_concentration=7),
                irrelevant_values=dict())
        attrs = self._get_init_data('a1')
        tp1 = self._get_position('a1', attrs)
        tp2 = self._get_position('a1', attrs)
        attrs['optimem_dil_factor'] = 100
        tp3 = self._get_position('a1', attrs)
        self.assert_equal(tp1, tp2)
        self.assert_equal(tp1, tp3)

    def test_hash_full(self):
        hash_map = dict(a1='205200mix114001',
                        b1='md_1mix128001',
                        c1='mockmix11400None',
                        d1='librarymix114001',
                        e1='E1', f1='F1', g1='G1')
        for pos_label in self.pos_data.keys():
            exp_hash = hash_map[pos_label]
            tp = self._get_position(pos_label)
            self.assert_equal(tp.hash_full, exp_hash)

    def test_hash_partial(self):
        hash_map = dict(a1='205200mix11400',
                        b1='md_1mix12800',
                        c1='mockmix11400',
                        d1='librarymix11400',
                        e1='E1', f1='F1', g1='G1')
        for pos_label in self.pos_data.keys():
            exp_hash = hash_map[pos_label]
            tp = self._get_position(pos_label)
            self.assert_equal(tp.hash_partial, exp_hash)

    def test_optimem_dilution_factor(self):
        tp1 = self._get_position('a1')
        self.assert_equal(tp1.optimem_dil_factor, 7)
        self._expect_error(AttributeError, setattr, 'can\'t set attribute',
                *(tp1, 'optimem_dil_factor', 2))
        tp1.store_optimem_dilution_factor()
        self.assert_equal(tp1.optimem_dil_factor, 4)
        attrs = self._get_init_data('b1')
        del attrs['optimem_dil_factor']
        tp2 = self._get_position('b1', attrs)
        self.assert_is_none(tp2.optimem_dil_factor)
        self._expect_error(AttributeError, setattr, 'can\'t set attribute',
                *(tp2, 'optimem_dil_factor', 2))
        self._expect_error(ValueError, tp2.set_optimem_dilution_factor,
                'The OptiMem dilution factor must be a positive number ' \
                '(obtained: a)', **dict(optimem_df='a'))
        tp2.set_optimem_dilution_factor(9)
        self._expect_error(AttributeError, tp2.set_optimem_dilution_factor,
                'The OptiMem dilution factor has already been set!',
                **dict(optimem_df=2))
        self.assert_equal(tp2.optimem_dil_factor, 9)

    def test_get_total_dilution_factor(self):
        tp1 = self._get_position('a1') # odf 7
        self.assert_equal(tp1.get_total_dilution_factor(), 98)
        tp2 = self._get_position('d1') # odf 8
        self.assert_equal(tp2.get_total_dilution_factor(), 112)

    def test_calculate_reagent_dilution_volume(self):
        tp1 = self._get_position('a1') # odf 7, iso vol 5
        self.assert_equal(tp1.calculate_reagent_dilution_volume(), 35)
        tp1.iso_volume = None
        self.assert_is_none(tp1.calculate_reagent_dilution_volume())
        tp2 = self._get_position('e1') # untreated
        self.assert_is_none(tp2.calculate_reagent_dilution_volume())

    def test_library_position_factory(self):
        kw = dict(rack_position=get_rack_position_from_label('d1'),
                  position_type=LIBRARY_POSITION_TYPE,
                  molecule_design_pool=LIBRARY_POSITION_TYPE)
        tp = self._get_position('d1', attrs=kw)
        rack_pos = kw['rack_position']
        fac_tp = self.POS_CLS.create_library_position(rack_pos)
        self.assert_is_not_none(fac_tp)
        self.assert_equal(fac_tp, tp)

    def test_mock_position_factory(self):
        kw = dict(rack_position=get_rack_position_from_label('c1'),
                  position_type=MOCK_POSITION_TYPE,
                  molecule_design_pool=MOCK_POSITION_TYPE)
        tp = self._get_position('c1', attrs=kw)
        rack_pos = kw['rack_position']
        fac_tp = self.POS_CLS.create_mock_position(rack_pos)
        self.assert_is_not_none(fac_tp)
        self.assert_equal(fac_tp, tp)

    def test_untreated_position_factory(self):
        kw = dict(rack_position=get_rack_position_from_label('e1'),
                  position_type=UNTREATED_POSITION_TYPE,
                  molecule_design_pool=UNTREATED_POSITION_TYPE,
                  final_concentration=UNTREATED_POSITION_TYPE,
                  reagent_name=UNTREATED_POSITION_TYPE,
                  reagent_dil_factor=UNTREATED_POSITION_TYPE)
        tp = self._get_position('e1', attrs=kw)
        rack_pos = kw['rack_position']
        fac_tp = self.POS_CLS.create_untreated_position(rack_pos,
                                                        UNTREATED_POSITION_TYPE)
        self.assert_is_not_none(fac_tp)
        self.assert_equal(fac_tp, tp)

    def test_copy(self):
        tp1 = self._get_position('a1')
        tp2 = tp1.copy()
        self.assert_equal(tp1, tp2)
        tp2.reagent_name = 'other'
        self.assert_not_equal(tp1, tp2)

    def test_position_get_tag_set(self):
        self._test_position_get_tag_set()


class TransfectionLayoutTestCase(_TransfectionClassesBaseTestCase):

    def test_init(self):
        self._test_layout_init()

    def test_copy(self):
        tl1 = self._create_test_layout()
        tl2 = tl1.copy()
        self.assert_equal(tl1, tl2)
        a1_pos = get_rack_position_from_label('a1')
        tl2.del_position(a1_pos)
        self.assert_not_equal(tl1, tl2)

    def test_has_iso_concentrations(self):
        tl = self._create_test_layout()
        self.assert_true(tl.has_iso_concentrations())
        for tf_pos in tl.working_positions():
            if tf_pos.is_mock or tf_pos.is_empty: continue
            tf_pos.iso_concentration = None
        self.assert_false(tl.has_iso_concentrations())

    def test_has_iso_volumes(self):
        tl = self._create_test_layout()
        self.assert_true(tl.has_iso_volumes())
        for tf_pos in tl.working_positions():
            if tf_pos.is_empty: continue
            tf_pos.iso_volume = None
        self.assert_false(tl.has_iso_volumes())

    def test_has_final_concentrations(self):
        tl = self._create_test_layout()
        self.assert_true(tl.has_final_concentrations())
        for tf_pos in tl.working_positions():
            if tf_pos.is_mock or tf_pos.is_empty: continue
            tf_pos.final_concentration = None
        self.assert_false(tl.has_final_concentrations())

    def test_create_merged_rack_layout(self):
        tl = self._create_test_layout()
        tag1 = Tag('some', 'other', 'things')
        positions1 = [get_rack_position_from_label('a1'),
                     get_rack_position_from_label('b1')]
        rps1 = RackPositionSet.from_positions(positions1)
        trps1 = self._create_tagged_rack_position_set(tags=[tag1],
                                                      rack_position_set=rps1)
        positions2 = positions1[:1]
        rps2 = RackPositionSet.from_positions(positions2)
        tag2 = Tag('more', 'additional', 'data')
        trps2 = self._create_tagged_rack_position_set(tags=[tag2],
                                                      rack_position_set=rps2)
        rl1 = tl.create_rack_layout()
        add_trps = {rps1.hash_value : trps1, rps2.hash_value : trps2}
        rl2 = tl.create_merged_rack_layout(add_trps, self._get_entity(IUser))
        self.assert_is_not_none(rl2)
        # the rps for set 2 is also part of rack layout 1
        self.assert_equal(len(rl1.tagged_rack_position_sets) + 1,
                          len(rl2.tagged_rack_position_sets))
        self.assert_equal(rl1.get_positions(), rl2.get_positions())
        tags1 = rl1.get_tags()
        tags2 = rl2.get_tags()
        for tag in tags1:
            self.assert_true(tag in tags2)
        self.assert_false(tag1 in tags1)
        self.assert_false(tag2 in tags1)
        self.assert_true(tag1 in tags2)
        self.assert_true(tag2 in tags2)

    def test_complete_rack_layout_with_screening_tags(self):
        tl = self._create_test_layout()
        rl1 = tl.create_rack_layout()
        tag1 = Tag('some', 'other', 'things')
        positions1 = [get_rack_position_from_label('a1'),
                     get_rack_position_from_label('b1')]
        rps1 = RackPositionSet.from_positions(positions1)
        trps1 = self._create_tagged_rack_position_set(tags=[tag1],
                                                      rack_position_set=rps1)
        positions2 = positions1[:1]
        rps2 = RackPositionSet.from_positions(positions2)
        tag2 = Tag('more', 'additional', 'data')
        trps2 = self._create_tagged_rack_position_set(tags=[tag2],
                                                      rack_position_set=rps2)
        rl2 = RackLayout(shape=rl1.shape,
                         tagged_rack_position_sets=[trps1, trps2])
        test_rl = tl.complete_rack_layout_with_screening_tags(rl2, rl1,
                                                  self._get_entity(IUser))
        self.assert_equal(rl1.get_positions(), test_rl.get_positions())
        tags2 = rl2.get_tags()
        test_tags = test_rl.get_tags()
        for tag in tags2:
            self.assert_true(tag in test_tags)
        tags1 = rl1.get_tags()
        for tag in tags1:
            if tag.predicate in (TransfectionParameters.ISO_VOLUME,
                                 TransfectionParameters.ISO_CONCENTRATION):
                self.assert_false(tag in test_tags)
            else:
                self.assert_true(tag in test_tags)

    def test_compare_ignoring_untreated_types(self):
        tl1 = self._create_test_layout()
        tl2 = tl1.copy()
        self.assert_equal(tl1, tl2)
        self.assert_true(self.LAYOUT_CLS.compare_ignoring_untreated_types(tl1,
                                                                          tl2))
        unt_pos = get_rack_position_from_label('e1')
        tl2.del_position(unt_pos)
        self.assert_not_equal(tl1, tl2)
        self.assert_true(self.LAYOUT_CLS.compare_ignoring_untreated_types(tl1,
                                                                          tl2))
        fixed_pos = get_rack_position_from_label('a1')
        tl2.del_position(fixed_pos)
        self.assert_not_equal(tl1, tl2)
        self.assert_false(self.LAYOUT_CLS.compare_ignoring_untreated_types(tl1,
                                                                           tl2))


class TransfectionLayoutConverterTestCase(ConverterTestCase,
                                          _TransfectionClassesBaseTestCase):

    PARAMETER_SET = TransfectionParameters
    POS_CLS = TransfectionPosition
    LAYOUT_CLS = TransfectionLayout
    CONVERTER_CLS = TransfectionLayoutConverter

    __ISO_VOL_INDEX = 2
    __ISO_CONC_INDEX = 3
    __FINAL_CONC_INDEX = 4
    __REAGENT_NAME_INDEX = 5
    __REAGENT_DF_INDEX = 6
    __OPTIMEM_INDEX = 7

    def set_up(self):
        ConverterTestCase.set_up(self)
        self.pos_set_data = {1 : ['a1', 'a2'], 2 : ['b1'], 3 : ['c1'],
                             4 : ['d1'], 5 : ['e1'], 6 : ['f1'],
                             7 : ['g1'], 8 : ['a1', 'b1', 'c1']}
        # Do not alter tag attributes but overwrite the index!
        self.tag_data = {
            1 : [self.TYPE_TAGS['fixed'], self.POOL_TAGS['fixed']],
            2 : [self.TYPE_TAGS['floating'], self.POOL_TAGS['floating']],
            3 : [self.TYPE_TAGS['mock'], self.POOL_TAGS['mock']],
            4 : [self.TYPE_TAGS['library'], self.POOL_TAGS['library']],
            5 : [self.TYPE_TAGS['untreated'], self.POOL_TAGS['untreated']],
            6 : [self.TYPE_TAGS['untransfected'],
                 self.POOL_TAGS['untransfected']],
            7 : [self.TYPE_TAGS['empty']],
            8 : [Tag('some', 'other', 'data')]}
        self.tag_key_map = {1 : 'a1', 2 : 'b1', 3 : 'c1', 4 : 'd1', 5 : 'e1',
                            6 : 'f1'}
        for k, pos_label in self.tag_key_map.iteritems():
            self._insert_tag_data_tag(k, pos_label, self._ISO_VOLUME_TAGS,
                                      self.__ISO_VOL_INDEX)
            self._insert_tag_data_tag(k, pos_label,
                        self._ISO_CONCENTRATION_TAGS, self.__ISO_CONC_INDEX)
            self._insert_tag_data_tag(k, pos_label, self._FINAL_CONC_TAG,
                                      self.__FINAL_CONC_INDEX)
            self._insert_tag_data_tag(k, pos_label, self._REAGENT_NAME_TAG,
                                      self.__REAGENT_NAME_INDEX)
            self._insert_tag_data_tag(k, pos_label, self._REAGENT_DF_TAG,
                                      self.__REAGENT_DF_INDEX)
            self._insert_tag_data_tag(k, pos_label, self._OPTIMEM_DF_TAG,
                                      self.__OPTIMEM_INDEX)
        self.is_iso_request_layout = True
        self.is_mastermix_template = False

    def tear_down(self):
        ConverterTestCase.tear_down(self)
        del self.is_iso_request_layout
        del self.is_mastermix_template

    def _create_tool(self):
        self.tool = TransfectionLayoutConverter(rack_layout=self.rack_layout,
                log=self.log, is_iso_request_layout=self.is_iso_request_layout,
                is_mastermix_template=self.is_mastermix_template)

    def test_result(self):
        self._test_result()

    def _continue_setup_without_iso_tags(self):
        del_indices = [self.__ISO_VOL_INDEX, self.__ISO_CONC_INDEX]
        del_indices.sort(reverse=True)
        for k in self.tag_key_map.keys():
            tags = self.tag_data[k]
            for i in del_indices: del tags[i]
        self._continue_setup()

    def _continue_setup_without_mastermix_tags(self):
        del_indices = [self.__OPTIMEM_INDEX, self.__REAGENT_DF_INDEX,
                       self.__REAGENT_NAME_INDEX]
        del_indices.sort(reverse=True)
        for k in self.tag_key_map.keys():
            tags = self.tag_data[k]
            for i in del_indices: del tags[i]
        self._continue_setup()

    def _get_all_positions(self):
        positions = []
        for i in range(4):
            positions.extend(self.pos_set_data[i + 1])
        return positions

    def _get_all_tags(self):
        tags = []
        for i in range(4):
            tags.extend(self.tag_data[i + 1])
        tags = set(tags)
        return list(tags)

    def _test_tag_for_position(self, layout):
        rack_pos = get_rack_position_from_label('a2')
        exp_tags = self.tag_data[1]
        tag_set = layout.get_tags_for_position(rack_pos)
        self._compare_tag_sets(exp_tags, tag_set)
        rack_pos_empty = get_rack_position_from_label('f1')
        tag_set_empty = layout.get_tags_for_position(rack_pos_empty)
        self.assert_equal(len(tag_set_empty), 0)

    def _test_position_for_tag(self, layout):
        try:
            tag = self.tag_data[4][7]
            exp_positions = self.pos_set_data[4]
        except IndexError:
            tag = self.tag_data[1][0]
            exp_positions = self.pos_set_data[1]
        pos_set = layout.get_positions_for_tag(tag)
        self._compare_pos_sets(exp_positions, pos_set)
        pos_set_empty = layout.get_positions_for_tag(self.TYPE_TAGS[
                                                                'untreated'])
        self.assert_equal(len(pos_set_empty), 0)

    def test_invalid_input_values(self):
        self._test_invalid_input_values()
        self.is_iso_request_layout = None
        self._test_and_expect_errors(' The "is ISO request layout" flag must ' \
                                     'be a bool')
        self.is_iso_request_layout = True
        self.is_mastermix_template = None
        self._test_and_expect_errors('The "is mastermix template" flag must ' \
                                     'be a bool')
        self.is_mastermix_template = True
        self._test_and_expect_errors('The layout cannot be a mastermix ' \
                         'layout and an ISO request layout at the same time!')

    def test_is_iso_request_layout(self):
        self._continue_setup_without_iso_tags()
        self._test_and_expect_errors('There is no iso_volume specification ' \
                'for this rack layout. Valid factor names are: iso ' \
                'volume (case-insensitive)')
        self._check_error_messages('There is no iso_concentration ' \
                'specification for this rack layout. Valid factor names are: ' \
                'iso concentration (case-insensitive)')
        self.is_iso_request_layout = False
        self._create_tool()
        self._test_result(continue_setup=False)

    def test_is_mastermix_layout(self):
        self._continue_setup_without_mastermix_tags()
        self.is_iso_request_layout = False
        self.is_mastermix_template = True
        self._test_and_expect_errors('There is no reagent_dilution_factor ' \
                                     'specification for this rack layout')
        self._check_error_messages('There is no reagent_name specification ' \
                                   'for this rack layout.')
        self.is_mastermix_template = False
        self._create_tool()
        self._test_result(continue_setup=False)

    def test_invalid_reagent_name(self):
        self.tag_data[1][self.__REAGENT_NAME_INDEX] = \
            Tag(TransfectionParameters.DOMAIN,
                TransfectionParameters.REAGENT_NAME, 'x')
        self._continue_setup()
        self._test_and_expect_errors('The following rack positions have ' \
             'invalid reagent names: A1, A2. A valid reagent name must ' \
             'be a string of at least 2 characters length')

    def test_invalid_reagent_df(self):
        self.tag_data[1][self.__REAGENT_DF_INDEX] = Tag(
                        TransfectionParameters.DOMAIN,
                        TransfectionParameters.REAGENT_DIL_FACTOR, '-1')
        self._continue_setup()
        self._test_and_expect_errors('The following rack positions have ' \
             'invalid reagent dilution factors: A1, A2. The reagent dilution ' \
             'factor must be a positive number.')

    def test_invalid_final_concentration(self):
        self.tag_data[1][self.__FINAL_CONC_INDEX] = Tag(
                        TransfectionParameters.DOMAIN,
                        TransfectionParameters.FINAL_CONCENTRATION, '-1')
        self._continue_setup()
        self._test_and_expect_errors('The following rack positions have ' \
            'invalid final concentrations: A1 (-1), A2 (-1). The final ' \
            'concentration must be a positive number.')

    def test_invalid_optimem_factor(self):
        self.tag_data[1][self.__OPTIMEM_INDEX] = Tag(
                        TransfectionParameters.DOMAIN,
                        TransfectionParameters.OPTIMEM_DIL_FACTOR, '-1')
        self._continue_setup()
        self._test_and_expect_errors('The following rack positions have ' \
            'invalid OptiMem dilution factors: A1 (-1), A2 (-1). The OptiMem ' \
            'dilution factor must be a positive number')

    def test_missing_reagent_name(self):
        self.is_mastermix_template = True
        self.is_iso_request_layout = False
        del self.tag_data[1][self.__REAGENT_NAME_INDEX]
        self._continue_setup()
        self._test_and_expect_errors('The following rack positions do not ' \
                                     'have a reagent name: A1, A2')

    def test_missing_reagent_dilution_factor(self):
        self.is_mastermix_template = True
        self.is_iso_request_layout = False
        del self.tag_data[1][self.__REAGENT_DF_INDEX]
        self._continue_setup()
        self._test_and_expect_errors('The following rack positions do not ' \
                                     'have a reagent dilution factor: A1, A2.')

    def test_missing_final_concentration(self):
        self.is_iso_request_layout = False
        del self.tag_data[1][self.__FINAL_CONC_INDEX]
        self._continue_setup()
        self._test_and_expect_errors('The following rack positions do not ' \
                                     'have a final concentration: A1, A2.')

    def test_inconsistent_optimem_factors(self):
        del self.tag_data[1][self.__OPTIMEM_INDEX]
        self._continue_setup()
        self._test_and_expect_errors('Some positions do not have an ' \
            'OptiMem dilution factor although there are OptiMem dilution ' \
            'factors in this layout!')


class _TransfectionRackSectorToolTestCase(_IsoRequestRackSectorToolTestCase):

    LAYOUT_CLS = TransfectionLayout

    def _get_case_data(self, case_num):
        self.current_case_num = case_num
        # these cases would fail with a normal ISO value associator because
        # all flaoting placeholders here are different. However, the
        # transfection associator treats all floating positions as one pool
        if case_num == 1:
            # different pools and concentration, 1 empty
            return dict(
                C3=[0, 1, 10], C4=[1, 2, 20],
                    D3=[2, 'mock', None], D4=[3, 'mock', None],
                C5=[0, 3, 10], C6=[1, 4, 20],
                    D5=[2, 'md_001', 30], D6=[3, None, None],
                E3=[0, 'md_002', 10], E4=[1, 'md_004', 20],
                    F3=[2, 'md_003', 30], F4=[3, 'untreated', None],
                E5=[0, 7, 10], E6=[1, 9, 20],
                    F5=[2, 10, 30], F6=[3, None, None])
        elif case_num == 2:
            # different pools, equal concentrations, 1 empty
            return dict(
                C3=[0, 1, 10], C4=[1, 2, 10],
                    D3=[2, 'mock', None], D4=[3, 'mock', None],
                C5=[0, 3, 10], C6=[1, 4, 10],
                    D5=[2, 'md_001', 10], D6=[3, None, None],
                E3=[0, 'md_003', 10], E4=[1, 'md_004', 10],
                    F3=[2, 'md_002', 10], F4=[3, 'untreated', None],
                E5=[0, 7, 10], E6=[1, 9, 10],
                    F5=[2, 10, 10], F6=[3, None, None])
        elif case_num == 3:
            # 2 x 2 association, different concentrations
            return dict(
                C3=[0, 1, 10], C4=[1, 'mock', None],
                    D3=[2, 1, 20], D4=[3, 'mock', None],
                C5=[0, 3, 10], C6=[1, 4, 10],
                    D5=[2, 3, 20], D6=[3, 4, 20],
                E3=[0, 'md_001', 10], E4=[1, 'md_001', 10],
                    F3=[2, 'md_001', 20], F4=[3, 'md_002', 20],
                E5=[0, 5, 10], E6=[1, 5, 10],
                    F5=[2, 5, 20], F6=[3, 5, 20],
                E7=[0, 'md_003', 10], E8=[1, 'md_004', 10],
                    F7=[2, 'md_003', 20], F8=[3, 'md_004', 20])
        elif case_num == 4:
            # 2 x 2 association, all equal concentrations
            return dict(
                C3=[0, 1, 10], C4=[1, 'mock', None],
                    D3=[2, 1, 10], D4=[3, 'mock', None],
                C5=[0, 3, 10], C6=[1, 4, 10],
                    D5=[2, 3, 10], D6=[3, 4, 10],
                E3=[0, 'md_001', 10], E4=[1, 'md_001', 10],
                    F3=[2, 'md_001', 10], F4=[3, 'md_002', 10],
                E5=[0, 5, 10], E6=[1, 5, 10],
                    F5=[2, 5, 10], F6=[3, 5, 10],
                E7=[0, 'md_003', 10], E8=[1, 'md_004', 10],
                    F7=[2, 'md_003', 10], F8=[3, 'md_004', 10])

    def _fill_layout(self):
        for pos_label, pos_data in self.position_data.iteritems():
            rack_pos = get_rack_position_from_label(pos_label)
            pool_id = pos_data[1]
            if pool_id is None or pool_id == UNTREATED_POSITION_TYPE:
                ir_pos = TransfectionPosition.create_empty_position(rack_pos)
                self.layout.add_position(ir_pos)
                continue
            conc = pos_data[2]
            iso_conc = None
            if not conc is None: iso_conc = conc * 3
            pool = self._get_pool(pool_id)
            ir_pos = TransfectionPosition(rack_position=rack_pos,
                                          molecule_design_pool=pool,
                                          final_concentration=conc,
                                          iso_volume=((pos_data[0] + 1) * 2),
                                          iso_concentration=iso_conc)
            self.layout.add_position(ir_pos)

    def _create_sector_associator(self):
        self.tool = TransfectionSectorAssociator(layout=self.layout,
                        log=self.log, regard_controls=self.regard_controls,
                        number_sectors=self.number_sectors)

    def _create_association_data(self):
        return TransfectionAssociationData(layout=self.layout,
                           regard_controls=self.regard_controls, log=self.log)

    def _get_expected_associated_sectors(self):
        if not self.regard_controls and self.current_case_num == 1:
            return [[0, 1, 2]]
        elif not self.regard_controls and self.current_case_num == 4:
            return [[0], [1], [2], [3]]
        else:
            return _IsoRequestRackSectorToolTestCase.\
                                 _get_expected_associated_sectors(self)

    def _get_expected_parent_sectors(self):
        if not self.regard_controls and self.current_case_num == 1:
            return {0: 1, 1 : 2, 2 : None}
        if not self.regard_controls and self.current_case_num == 4:
            return {0: None, 1 : None, 2 : None, 3 : None}
        return _IsoRequestRackSectorToolTestCase._get_expected_parent_sectors(
                                                                        self)

    def _get_expected_sector_volumes(self):
        if not self.regard_controls and self.current_case_num == 1:
            return {0 : 2, 1 : 4, 2 : 6}
        return _IsoRequestRackSectorToolTestCase._get_expected_sector_volumes(
                                                                        self)


class TransfectionRackSectorAssociatorTestCase(
                                        _TransfectionRackSectorToolTestCase):

    def _create_tool(self):
        self._create_sector_associator()

    def test_result(self):
        self._test_sector_associator()

    def test_regard_controls(self):
        self._adjust_pos_data_for_regard_control_test()
        self._continue_setup()
        self._test_and_expect_errors('Error when trying to determine rack ' \
                                     'sector concentrations.')
        self.regard_controls = False
        self._create_tool()
        exp_res = self._get_expected_associated_sectors()
        self._check_sector_associator_run(exp_res)
        # check other cases - all floatings are treated the same way but
        # the result should remain the same
        for case_num in (1, 2, 4):
            self.position_data = self._get_case_data(case_num)
            self._continue_setup()
            exp_res = self._get_expected_associated_sectors()
            self._check_sector_associator_run(exp_res)

    def test_invalid_input_values(self):
        self._continue_setup()
        self._test_invalid_layout()
        self._test_invalid_regard_controls()
        self._test_invalid_number_sectors()

    def test_value_determiner_failure(self):
        self._adjust_pos_data_for_regard_control_test()
        self._continue_setup()
        self._test_and_expect_errors('Error when trying to determine rack ' \
                                     'sector concentrations.')

    def test_inconsistent_quadrants(self):
        exp_msg = 'The molecule design pools in the different quadrants are ' \
            'not consistent. Found associated pools: 0.1.2 ([\'E5\', \'E6\', ' \
            '\'F5\']) - 0.1.2.3 ([\'E3\', \'E4\', \'F3\', \'F4\'], [\'E7\', ' \
            '\'E8\', \'F7\', \'F8\']) - 0.2 ([\'C3\', \'D3\'], [\'C5\', ' \
            '\'D5\']) - 1.3 ([\'C6\', \'D6\']).'
        self._test_associator_inconsistent_quadrants(exp_msg)

    def test_different_set_lengths(self):
        exp_msg = 'The sets of molecule design pools in a quadrant have ' \
            'different lengths: 0.1.2.3 ([\'E5\', \'E6\', \'F5\', \'F6\'], '\
            '[\'E7\', \'E8\', \'F7\', \'F8\']) - 0.2 ([\'C3\', \'D3\'], ' \
            '[\'C5\', \'D5\']) - 0.2.3 ([\'E3\', \'F3\', \'F4\']) - 1 ' \
            '([\'C6\'], [\'E4\']) - 3 ([\'D6\']).'
        self._test_associator_different_set_lengths(exp_msg)

    def test_different_concentration_combinations(self):
        self._test_different_concentration_combinations()


class TransfectionAssociationDataTestCase(_TransfectionRackSectorToolTestCase):

    def __get_expected_iso_concentrations(self):
        if self.current_case_num == 1:
            # different pools and concentration, 1 empty
            return {0 : 30, 1 : 60, 2 : 90}
        elif self.current_case_num == 2:
            # different pools, equal concentrations, 1 empty
            return {0 : 30, 1 : 30, 2 : 30}
        elif self.current_case_num == 3:
            # 2 x 2 association, different concentrations
            return {0 : 30, 1 : 30, 2 : 60, 3 : 60}
        else: # 2 x 2 association, all equal concentrations
            return {0 : 30, 1 : 30, 2 : 30, 3 : 30}

    def test_result_384(self):
        self._test_association_data_384()

    def _check_association_data_384(self):
        ad = _TransfectionRackSectorToolTestCase._check_association_data_384(
                                                                        self)
        if not ad is None:
            exp_volumes = self._get_expected_sector_volumes()
            if not ad.sector_volumes == exp_volumes:
                msg = 'The sector volumes for case %i differ.\nExpected: %s' \
                      '\nFound:%s' % (self.current_case_num, exp_volumes,
                                      ad.sector_volumes)
                raise AssertionError(msg)
            exp_iso_concentrations = self.__get_expected_iso_concentrations()
            if not ad.iso_concentrations == exp_iso_concentrations:
                msg = 'The ISO concentrations for case %i differ.\n' \
                      'Expected: %s\nFound:%s' % (self.current_case_num,
                              exp_iso_concentrations, ad.iso_concentrations)
                raise AssertionError(msg)

    def test_result_96(self):
        self._test_assocation_data_96()
        pp = None
        for pool_pos in self.layout.working_positions():
            if pool_pos.is_empty: continue
            pp = pool_pos
            break
        ori_vol = pp.iso_volume
        pp.iso_volume = (2 * ori_vol)
        self._expect_error(ValueError, self._create_association_data,
                           'Error when trying to determine sector volumes.')
        pp.iso_volume = ori_vol
        pp.iso_concentration = (2 * pp.iso_concentration)
        self._expect_error(ValueError, self._create_association_data,
               'There is more than one value for sector 1! Attribute: ' \
               'iso_concentration. Values: 30, 60.')

    def _check_association_data_96(self):
        ad = _TransfectionRackSectorToolTestCase._check_association_data_96(
                                                                        self)
        if not ad is None:
            self.assert_equal({0 : 10}, ad.sector_volumes)
            self.assert_equal({0 : 30}, ad.iso_concentrations)

    def test_regard_controls(self):
        self._adjust_pos_data_for_regard_control_test()
        self._continue_setup()
        self._expect_error(ValueError, self._create_association_data,
                    'Error when trying to find rack sector association.')
        self.assert_equal(len(self.log.get_messages(logging.ERROR)), 0)
        self.regard_controls = False
        self._check_association_data_384()
        # check other cases - all floatings are treated the same way but
        # the result should remain the same
        for case_num in (1, 2, 4):
            self.position_data = self._get_case_data(case_num)
            self._continue_setup()
            self._check_association_data_384()

    def test_failure(self):
        self._adjust_pos_data_for_regard_control_test()
        self._continue_setup()
        self._expect_error(ValueError, self._create_association_data,
                           'Error when trying to find rack sector association.')
        self.assert_equal(len(self.log.get_messages(logging.ERROR)), 0)

    def test_find(self):
        self._continue_setup()
        ad, regard_controls = TransfectionAssociationData.find(log=self.log,
                                       layout=self.layout)
        self.assert_is_not_none(ad)
        self.assert_true(regard_controls)
        self._adjust_pos_data_for_regard_control_test()
        self._continue_setup()
        ad, regard_controls = TransfectionAssociationData.find(log=self.log,
                                       layout=self.layout)
        self.assert_is_not_none(ad)
        self.assert_false(regard_controls)
        pp = None
        for pool_pos in self.layout.working_positions():
            if not pool_pos.is_floating: continue
            pp = pool_pos
            break
        ori_vol = pp.iso_volume
        pp.iso_volume = (2 * ori_vol)
        self.assert_equal((None, None), TransfectionAssociationData.find(
                          log=self.log, layout=self.layout))
        pp.iso_volume = ori_vol
        pp.iso_concentration = pp.iso_concentration * 2
        self.assert_equal((None, None), TransfectionAssociationData.find(
                                    log=self.log, layout=self.layout))
