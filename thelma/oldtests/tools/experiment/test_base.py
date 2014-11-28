"""
Tests for base tools dealing with experiment job handling.

AAB
"""
from thelma.tools.semiconstants import RACK_SPECS_NAMES
from thelma.tools.semiconstants import get_rack_position_from_label
from thelma.tools.experiment.base import ReagentPreparationWriter
from thelma.tools.experiment.base import SourceRackVerifier
from thelma.tools.iso.lab.base import FinalLabIsoLayout
from thelma.tools.iso.lab.base import FinalLabIsoPosition
from thelma.tools.metadata.base import TransfectionLayout
from thelma.tools.metadata.base import TransfectionPosition
from thelma.tools.utils.layouts import FIXED_POSITION_TYPE
from thelma.tools.utils.layouts import MOCK_POSITION_TYPE
from thelma.entities.rack import RACK_TYPES
from thelma.entities.racklayout import RackLayout
from thelma.oldtests.tools.experiment.utils import EXPERIMENT_TEST_DATA
from thelma.oldtests.tools.tooltestingutils import FileCreatorTestCase
from thelma.oldtests.tools.tooltestingutils import FileReadingTestCase
from thelma.oldtests.tools.utils.utils import VerifierTestCase


class SourceRackVerifierTestCase(VerifierTestCase):

    LAYOUT_CLS = TransfectionLayout
    POSITION_CLS = TransfectionPosition

    def set_up(self):
        VerifierTestCase.set_up(self)
        self.plate_type = RACK_TYPES.PLATE
        self.rack_specs = RACK_SPECS_NAMES.from_name(
                                                RACK_SPECS_NAMES.STANDARD_96)
        self.iso_request = None
        # pos label - pos type, pool ID, floating_placeholder
        self.position_data = dict(a1=['fixed', 205200, None],
                                  b1=['floating', 205201, 'md_001'],
                                  b2=['floating', 205201, 'md_001'],
                                  c1=['floating', 205202, 'md_002'],
                                  d1=['mock', 'mock', 'mock'])
        self.alt_iso_data = dict(a1=['fixed', 205200, None],
                                  b1=['floating', 205203, 'md_001'],
                                  b2=['floating', 205203, 'md_001'],
                                  c1=['floating', 205204, 'md_002'],
                                  d1=['mock', 'mock', 'mock'])
        self.iso_layouts = dict()

    def tear_down(self):
        VerifierTestCase.tear_down(self)
        del self.iso_request
        del self.alt_iso_data
        del self.iso_layouts

    def _create_tool(self):
        self.tool = SourceRackVerifier(self.rack, self.iso_request)

    def _get_position_kw(self, pos_label, pos_data):
        kw = dict(rack_position=get_rack_position_from_label(pos_label),
                  iso_volume=5, iso_concentration=10,
                  reagent_name='mix1', reagent_dil_factor=140,
                  final_concentration=1)
        pos_type = pos_data[0]
        if pos_type == FIXED_POSITION_TYPE:
            pool = self._get_pool(pos_data[1])
        elif pos_type == MOCK_POSITION_TYPE:
            pool = pos_data[2]
            kw['final_concentration'] = None
            kw['iso_concentration'] = None
        else:
            pool = pos_data[2]
        kw['molecule_design_pool'] = pool
        return kw

    def _fill_rack(self, session):
        for well in self.rack.containers:
            pos_label = well.location.position.label.lower()
            if self.position_data.has_key(pos_label):
                pool_id = self.position_data[pos_label][1]
                if not pool_id == MOCK_POSITION_TYPE:
                    self._add_sample(well, pool_id)

    def _create_other_objects(self):
        self.iso_request = self._create_lab_iso_request(
                            rack_layout=self.layout.create_rack_layout())
        layout1 = self.__create_iso_layout(self.position_data)
        pool_set1 = self.__create_molecule_design_pool_set(layout1)
        iso1 = self._create_lab_iso(iso_request=self.iso_request, label='iso1',
                             molecule_design_pool_set=pool_set1,
                             rack_layout=layout1.create_rack_layout())
        self.iso_layouts[iso1] = layout1
        layout2 = self.__create_iso_layout(self.alt_iso_data)
        pool_set2 = self.__create_molecule_design_pool_set(layout2)
        iso2 = self._create_lab_iso(iso_request=self.iso_request, label='iso2',
                             molecule_design_pool_set=pool_set2,
                             rack_layout=layout2.create_rack_layout())
        self.iso_layouts[iso2] = layout2

    def __create_molecule_design_pool_set(self, layout):
        pools = []
        for fp in layout.working_positions():
            if fp.is_mock: continue
            pools.append(fp.molecule_design_pool)
        return self._create_molecule_design_pool_set(
                                    molecule_type=pools[0].molecule_type,
                                    molecule_design_pools=set(pools))

    def __create_iso_layout(self, position_data):
        layout = FinalLabIsoLayout(shape=self.shape)
        for pos_label, pos_data in position_data.iteritems():
            rack_pos = get_rack_position_from_label(pos_label)
            pool_id = pos_data[1]
            if pool_id == MOCK_POSITION_TYPE:
                pool = MOCK_POSITION_TYPE
                conc = None
            else:
                pool = self._get_pool(pool_id)
                conc = 10
            fp = FinalLabIsoPosition(rack_position=rack_pos,
                                     molecule_design_pool=pool,
                                     position_type=pos_data[0],
                                     concentration=conc, volume=1)
            layout.add_position(fp)
        return layout

    def test_result_no_floatings(self):
        self.position_data['b1'] = ['fixed', 205201, None]
        del self.position_data['b2']
        del self.position_data['c1']
        self._continue_setup()
        self._test_and_expect_compliance()

    def test_result_floatings(self):
        self._continue_setup()
        self._test_and_expect_compliance()

    def test_invalid_input_values(self):
        self._continue_setup()
        ori_rack = self.rack
        self.rack = self._create_tube_rack()
        self._test_and_expect_errors('The rack must be a Plate object ' \
                                     '(obtained: TubeRack).')
        self.rack = ori_rack
        self.iso_request = self.iso_layouts.keys()[0]
        self._test_and_expect_errors('The ISO request must be a ' \
                                     'LabIsoRequest object (obtained: LabIso).')

    def test_and_expect_missing_sample(self):
        self.add_pos_data = dict(g8=['fixed', 1056000, 'md_003'])
        self._continue_setup()
        self._test_and_expect_missing_sample()

    def test_and_expect_mismatching_samples(self):
        self._continue_setup()
        for well in self.rack.containers:
            if well.sample is None: continue
            pool = self._get_pool(330001)
            for md in pool:
                mol = self._create_molecule(molecule_design=md)
                well.sample.make_sample_molecule(molecule=mol,
                                                 concentration=0.00001)
            break
        self._test_and_expect_mismatching_samples()

    def test_and_expect_additional_samples(self):
        self._continue_setup()
        for well in self.rack.containers:
            if well.sample is None:
                sample = well.make_sample(volume=0.00001)
                pool = self._get_pool(330001)
                for md in pool:
                    mol = self._create_molecule(molecule_design=md)
                    sample.make_sample_molecule(molecule=mol,
                                                concentration=0.00001)
        self._test_and_expect_additional_samples()

    def test_and_expect_rack_shape_mismatch(self):
        self.rack_specs = RACK_SPECS_NAMES.from_name(
                                            RACK_SPECS_NAMES.STANDARD_384)
        self._continue_setup()
        self._test_and_expect_rack_shape_mismatch()

    def test_mixed_floatings(self):
        self._continue_setup()
        for iso, layout in self.iso_layouts.iteritems():
            for fp in layout.working_positions():
                if fp.is_mock: continue
                if fp.molecule_design_pool.id == 205202:
                    fp.molecule_design_pool = self._get_pool(205204)
                    break
            iso.rack_layout = layout.create_rack_layout()
        self._test_and_expect_mismatching_samples()

    def test_transfection_layout_conversion_error(self):
        self._continue_setup()
        self.iso_request.rack_layout = RackLayout()
        self._test_and_expect_errors('Error when trying to convert ' \
                                     'transfection layout.')

    def test_iso_layout_conversion_error(self):
        self._continue_setup()
        iso_label = None
        for iso in self.iso_layouts.keys():
            iso_label = iso.label
            iso.rack_layout = RackLayout()
            break
        self._test_and_expect_errors('Error when trying to convert layout ' \
                                     'for ISO "%s"' % (iso_label))

    def test_no_isos(self):
        self._continue_setup()
        self.iso_request.isos = []
        self._test_and_expect_errors('There are no ISOs for this ISO request!')


class ReagentPreparationWriterTestCase(FileReadingTestCase,
                                       FileCreatorTestCase):

    def set_up(self):
        FileReadingTestCase.set_up(self)
        self.TEST_FILE_PATH = EXPERIMENT_TEST_DATA.TEST_FILE_PATH
        self.WL_PATH = EXPERIMENT_TEST_DATA.WORKLIST_FILE_PATH
        self.VALID_FILE = 'reagent_worklist.csv'

    def tear_down(self):
        FileReadingTestCase.tear_down(self)
        del self.WL_PATH

    def _create_tool(self):
        self.tool = ReagentPreparationWriter(self.stream)

    def _continue_setup(self, file_name=None):
        FileReadingTestCase._continue_setup(self, file_name=file_name)
        self._create_tool()

    def test_result(self):
        self._continue_setup()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream, 'reagent_preparation.csv')

    def test_invalid_input_values(self):
        self._test_and_expect_errors('The reagent dilution worklist stream ' \
                                'must be a str object (obtained: NoneType).')
