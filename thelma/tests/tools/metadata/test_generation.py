"""
Tests the tool involved in experiment metadata generation.
AAB Aug 08, 2011
"""

from pkg_resources import resource_filename # pylint: disable=E0611,F0401
from thelma.automation.tools.metadata.generation import ExperimentMetadataGeneratorOrder
from thelma.automation.handlers.experimentdesign \
    import ExperimentDesignParserHandler
from thelma.automation.tools.metadata.generation \
    import ExperimentMetadataGenerator
from thelma.automation.tools.metadata.generation \
    import ExperimentMetadataGeneratorIsoless
from thelma.automation.tools.metadata.generation \
    import ExperimentMetadataGeneratorLibrary
from thelma.automation.tools.metadata.generation \
    import ExperimentMetadataGeneratorManual
from thelma.automation.tools.metadata.generation \
    import ExperimentMetadataGeneratorOpti
from thelma.automation.tools.metadata.generation \
import ExperimentMetadataGeneratorScreen
from thelma.automation.tools.metadata.transfection_utils \
    import TransfectionParameters
from thelma.automation.tools.metadata.transfection_utils \
    import TransfectionPosition
from thelma.automation.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.semiconstants import get_96_rack_shape
from thelma.automation.tools.semiconstants import get_experiment_metadata_type
from thelma.automation.tools.semiconstants import get_rack_position_from_label
from thelma.automation.tools.utils.base import MOCK_POSITION_TYPE
from thelma.interfaces import IJobType
from thelma.interfaces import IPlate
from thelma.interfaces import ISubproject
from thelma.interfaces import IUser
from thelma.models.experiment import Experiment
from thelma.models.experiment import ExperimentMetadata
from thelma.models.iso import Iso
from thelma.models.job import ExperimentJob
from thelma.models.rack import RackPositionSet
from thelma.models.racklayout import RackLayout
from thelma.models.tagging import Tag
from thelma.models.tagging import TaggedRackPositionSet
from thelma.models.utils import get_user
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase


class ExperimentMetadataGeneratorTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.FILE_PATH = 'thelma:tests/tools/metadata/generator/'
        self.VALID_FILES = {
                        EXPERIMENT_SCENARIOS.OPTIMISATION : 'valid_opti.xls',
                        EXPERIMENT_SCENARIOS.SCREENING : 'valid_screen.xls',
                        EXPERIMENT_SCENARIOS.LIBRARY : 'valid_library.xls',
                        EXPERIMENT_SCENARIOS.MANUAL : 'valid_manual.xls',
                        EXPERIMENT_SCENARIOS.ISO_LESS : 'valid_isoless.xls',
                        EXPERIMENT_SCENARIOS.ORDER_ONLY : 'valid_order.xls'}
        self.update_file = None
        self.source = None
        self.experiment_metadata = None
        self.user = get_user('it')
        self.requester = self._get_entity(IUser, 'sachse')
        self.experiment_type_id = None
        self.generator_cls = None
        # other setup values
        self.label = 'em_generator_test'
        self.number_replicates = 3
        self.ticket_number = 123
        self.ed_domain = ExperimentDesignParserHandler.TAG_DOMAIN
        # result values
        self.number_experiment_design_wls = None
        self.number_rack_wls = None
        self.check_iso_layout_conc = True
        self.iso_request_comment = None
        self.number_aliquots = 1
        self.number_plates = 1
        self.len_pool_set = 0
        # pos label, values: md, iso vol, iso conc, reagent name, reagent df
        self.iso_layout_values = None

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.FILE_PATH
        del self.VALID_FILES
        del self.update_file
        del self.source
        del self.requester
        del self.experiment_metadata
        del self.experiment_type_id
        del self.generator_cls
        del self.label
        del self.ticket_number
        del self.ed_domain
        del self.number_experiment_design_wls
        del self.number_rack_wls
        del self.check_iso_layout_conc
        del self.iso_request_comment
        del self.number_plates
        del self.number_aliquots
        del self.len_pool_set
        del self.iso_layout_values

    def _create_tool(self):
        self.tool = ExperimentMetadataGenerator.create(stream=self.source,
                            experiment_metadata=self.experiment_metadata,
                            requester=self.requester)

    def _create_tool_without_factory(self):
        #pylint: disable=E1102
        self.tool = self.generator_cls(stream=self.source,
                            experiment_metadata=self.experiment_metadata,
                            requester=self.requester)
        #pylint: enable=E1102

    def _continue_setup(self, file_name=None):
        if file_name is None:
            file_name = self.VALID_FILES[self.experiment_type_id]
        self.__read_stream(file_name)
        self.__create_metadata()
        self._create_tool()

    def _continue_setup_update(self, second_file, create_iso,
                               create_experiment, create_tool=True):
        # for update tests
        if create_experiment:
            plate = self._get_entity(IPlate)
            plate_specs = plate.specs
        self._continue_setup()
        self.experiment_metadata = self.tool.get_result()
        if not self.experiment_type_id == EXPERIMENT_SCENARIOS.ISO_LESS:
            self._check_result()
        if create_iso: self.__create_iso()
        if create_experiment: self.__create_experiment(plate, plate_specs)
        self.__read_stream(second_file)
        if create_tool: self._create_tool()

    def __read_stream(self, file_name):
        em_file = self.FILE_PATH + file_name
        fn = em_file.split(':')
        f = resource_filename(*fn) #pylint: disable=W0142
        stream = None
        try:
            stream = open(f, 'rb')
            self.source = stream.read()
        finally:
            if not stream is None: stream.close()

    def __create_metadata(self):
        em_type = get_experiment_metadata_type(self.experiment_type_id)
        iso_request = self._create_iso_request()
        self.experiment_metadata = ExperimentMetadata(label=self.label,
                    subproject=self._get_entity(ISubproject),
                    number_replicates=self.number_replicates,
                    experiment_metadata_type=em_type,
                    ticket_number=self.ticket_number,
                    iso_request=iso_request)

    def __create_iso(self):
        Iso(label='test_ISO', iso_request=self.experiment_metadata.iso_request)

    def __create_experiment(self, plate, plate_specs):
        exp = Experiment(label='update_test_experiment', source_rack=plate,
                   destination_rack_specs=plate_specs,
                   experiment_design=self.experiment_metadata.experiment_design)
        experiment_jt = self._get_entity(IJobType, 'rnai-experiment')
        ExperimentJob(label='test_job', job_type=experiment_jt,
                      experiments=[exp],
                      subproject=self.experiment_metadata.subproject)

    def _check_result(self, is_update_check=False):
        self.assert_false(self.tool.has_errors())
        if self.tool.return_value is None:
            em = self.tool.get_result()
        else:
            em = self.experiment_metadata
        self.assert_is_not_none(em)
        self.__check_em_attributes(em)
        if self.tool.HAS_EXPERIMENT_DESIGN: self.__check_worklists_series(em)
        self._check_source_layout()
        no_association_types = [EXPERIMENT_SCENARIOS.SCREENING,
                                EXPERIMENT_SCENARIOS.LIBRARY,
                                EXPERIMENT_SCENARIOS.ORDER_ONLY]
        if self.experiment_type_id in no_association_types:
            self.assert_is_none(self.tool.get_final_concentrations())
            self.assert_is_none(self.tool.get_association_layouts())
        else:
            self.__check_final_concentrations(em)
            self.__check_association_layouts(em)
        if not is_update_check: self._check_experiment_design_tag(em)

    def __check_em_attributes(self, em):
        self.assert_equal(em.number_replicates, self.number_replicates)
        self.assert_equal(em.label, self.label)
        if self.tool.HAS_EXPERIMENT_DESIGN:
            self.assert_is_not_none(em.experiment_design)
        else:
            self.assert_is_none(em.experiment_design)
        self.assert_equal(em.ticket_number, self.ticket_number)
        iso_request = em.iso_request
        if self.tool.HAS_ISO_REQUEST:
            self.assert_is_not_none(iso_request)
            self.assert_equal(iso_request.requester, self.requester)
            self.assert_equal(iso_request.number_aliquots, self.number_aliquots)
            self.assert_equal(iso_request.number_plates, self.number_plates)
            self.assert_equal(iso_request.comment, self.iso_request_comment)
            self.assert_is_none(iso_request.worklist_series)
        else:
            self.assert_is_none(iso_request)
        if self.len_pool_set == 0:
            self.assert_is_none(em.molecule_design_pool_set)
        else:
            self.assert_equal(len(em.molecule_design_pool_set),
                              self.len_pool_set)

    def __check_worklists_series(self, em):
        ed_series = em.experiment_design.worklist_series
        if self.number_experiment_design_wls == 0:
            self.assert_is_none(ed_series)
        else:
            self.assert_equal(len(ed_series), self.number_experiment_design_wls)
        for design_rack in em.experiment_design.design_racks:
            rack_series = design_rack.worklist_series
            if self.number_rack_wls == 0:
                self.assert_is_none(rack_series)
            else:
                self.assert_equal(len(rack_series), self.number_rack_wls)

    def _check_source_layout(self):
        tf_layout = self.tool.get_source_layout()
        self.assert_is_not_none(tf_layout)
        self.assert_equal(len(tf_layout), len(self.iso_layout_values))
        for rack_pos, tf_pos in tf_layout.iterpositions():
            result_data = self.iso_layout_values[rack_pos.label]
            self.assert_equal(tf_pos.molecule_design_pool_id, result_data[0])
            self.assert_equal(tf_pos.iso_volume, result_data[1])
            if self.check_iso_layout_conc:
                self.assert_equal(tf_pos.iso_concentration, result_data[2])
            self.assert_equal(tf_pos.reagent_name, result_data[3])
            self.assert_equal(tf_pos.reagent_dil_factor, result_data[4])

    def __check_final_concentrations(self, em):
        fcs = self.tool.get_final_concentrations()
        self.assert_is_not_none(fcs)
        design_racks = em.experiment_design.design_racks
        self.assert_equal(len(fcs), len(design_racks))
        md_predicate = TransfectionParameters.MOLECULE_DESIGN_POOL\
                       .replace('_', ' ')
        fc_predicate = TransfectionParameters.FINAL_CONCENTRATION.\
                       replace('_', ' ')
        fc_domain = ExperimentDesignParserHandler.TAG_DOMAIN
        if self.experiment_type_id == EXPERIMENT_SCENARIOS.SCREENING:
            fc_domain = TransfectionParameters.DOMAIN
            fc_predicate = TransfectionParameters.FINAL_CONCENTRATION
        for design_rack in design_racks:
            fc_map = fcs[design_rack.label]
            for rack_pos, final_conc in fc_map.iteritems():
                tags = design_rack.layout.get_tags_for_position(rack_pos)
                if not self.experiment_type_id \
                                            == EXPERIMENT_SCENARIOS.SCREENING:
                    all_predicates = set()
                    for tag in tags: all_predicates.add(tag.predicate)
                    self.assert_true(md_predicate in all_predicates)
                if final_conc is None: continue
                fc_tag = Tag(fc_domain, fc_predicate, final_conc)
                self.assert_true(fc_tag in tags)

    def __check_association_layouts(self, em):
        al = self.tool.get_association_layouts()
        self.assert_is_not_none(al)
        design_racks = em.experiment_design.design_racks
        self.assert_equal(len(al), len(design_racks))
        md_predicate = TransfectionParameters.\
                       MOLECULE_DESIGN_POOL.replace('_', ' ')
        for design_rack in design_racks:
            tf_layout = al[design_rack.label]
            md_positions = []
            for rack_pos in design_rack.layout.get_positions():
                tags = design_rack.layout.get_tags_for_position(rack_pos)
                for tag in tags:
                    if tag.predicate == md_predicate:
                        if self.experiment_type_id == \
                                EXPERIMENT_SCENARIOS.MANUAL and \
                                tag.value == \
                                TransfectionParameters.MOCK_TYPE_VALUE:
                            continue
                        if self.experiment_type_id \
                                != EXPERIMENT_SCENARIOS.SCREENING and \
                                tag.value == TransfectionParameters.\
                                UNTREATED_TYPE_VALUE: continue

                        md_positions.append(rack_pos)
                        break
            tf_positions = []
            for tf_pos in tf_layout.working_positions():
                for trg_pos in tf_pos.cell_plate_positions:
                    tf_positions.append(trg_pos)
            self._compare_pos_sets(tf_positions, md_positions)

    def _check_experiment_design_tag(self, em):
        raise NotImplementedError('Abstract method')

    def _test_and_expect_errors(self, msg=None):
        ToolsAndUtilsTestCase._test_and_expect_errors(self, msg=msg)
        self.assert_is_none(self.tool.get_source_layout())
        self.assert_is_none(self.tool.get_association_layouts())
        self.assert_is_none(self.tool.get_final_concentrations())

    def _test_unsupported_type(self):
        self._continue_setup()
        kw = dict(stream=self.source, requester=self.user,
                  experiment_metadata=self.experiment_metadata)
        self.experiment_metadata.experiment_metadata_type = \
                  get_experiment_metadata_type(EXPERIMENT_SCENARIOS.QPCR)
        # pylint: disable=W0142
        self.assert_raises(KeyError, ExperimentMetadataGenerator.create, **kw)
        # pylint: enable=W0142
        self._create_tool_without_factory()
        em = self.tool.get_result()
        self.assert_is_none(em)
        self._check_error_messages('Unsupported experiment type "qPCR"')
        self.assert_is_none(self.tool.get_source_layout())

    def _test_invalid_experiment_metadata(self):
        self._continue_setup()
        self.experiment_metadata = None
        self._create_tool_without_factory()
        em = self.tool.get_result()
        self.assert_is_none(em)
        self._check_error_messages('The experiment metadata must be a ' \
                                   'ExperimentMetadata object')
        self.assert_is_none(self.tool.get_source_layout())
        kw = dict(stream=self.source, requester=self.user,
                  experiment_metadata=self.experiment_metadata)
        # pylint: disable=W0142
        self.assert_raises(ValueError, ExperimentMetadataGenerator.create, **kw)
        # pylint: enable=W0142

    def _test_invalid_requester(self):
        self.requester = None
        self._continue_setup()
        self._test_and_expect_errors('The requester must be a User object')

    def _test_missing_ticket_number(self):
        self._continue_setup()
        self.experiment_metadata.ticket_number = None
        self._test_and_expect_errors('Unable to find ticket number!')

    def _test_invalid_experiment_design(self, file_name):
        self._continue_setup(file_name)
        self._test_and_expect_errors('Error when trying to generate ' \
                                     'experiment design.')

    def _test_missing_iso_request_sheet(self, file_name):
        self._continue_setup(file_name)
        em_type = get_experiment_metadata_type(self.experiment_type_id)
        msg = 'For experiment metadata of the type "%s", you need to ' \
              'provide an ISO sheet!' % (em_type.display_name)
        self._test_and_expect_errors(msg)

    def _test_invalid_iso_request(self, file_name):
        self._continue_setup(file_name)
        self._test_and_expect_errors('Error when trying to generate ISO ' \
                                     'request.')

    def _test_invalid_pool_set(self, file_name):
        self._continue_setup(file_name)
        self._test_and_expect_errors('Error when trying to determine ' \
                        'molecule design pool set for floating positions.')

    def _test_missing_pool_set(self, file_name):
        self._continue_setup(file_name)
        self._test_and_expect_errors('Error when trying to determine ' \
                'molecule design pool set for floating positions: There are ' \
                'no molecule design pool IDs on the molecule design sheet!')

    def _test_with_pool_set(self, file_name):
        em_type = get_experiment_metadata_type(self.experiment_type_id)
        self._continue_setup(file_name)
        self._test_and_expect_errors('There are molecule design pools for ' \
                'floating positions specified. Floating positions are not ' \
                'allowed for %s experiments!' % (em_type.display_name))

    def _test_no_floatings_but_md_set(self, file_name):
        self._continue_setup(file_name)
        self._test_and_expect_errors('There are molecule design pools for ' \
                    'floating positions specified although there are no ' \
                    'floating positions!')

    def _test_worklist_generation_failure(self, file_name):
        self._continue_setup(file_name)
        self._test_and_expect_errors('Error when trying to generate ' \
                                     'experiment worklists.')

    def _test_update_converter_error(self):
        self._continue_setup_update(self.update_file, create_iso=True,
                                    create_experiment=False, create_tool=False)
        self.experiment_metadata.iso_request.iso_layout = \
                                        RackLayout(shape=get_96_rack_shape())
        self._test_and_expect_errors('Error when trying to convert ' \
                                     'ISO layout of the existing ISO request.')

    def _test_update_changed_number_aliquots(self):
        self._continue_setup_update(self.update_file, create_iso=True,
                                    create_experiment=False, create_tool=False)
        self.experiment_metadata.iso_request.number_aliquots = 3
        self._test_and_expect_errors('The current file upload would change ' \
                    'some properties of the ISO request which must not be ' \
                    'altered anymore')
        self._check_error_messages('number of aliquots')

    def _test_update_changed_plate_set_label(self):
        self._continue_setup_update(self.update_file, create_iso=True,
                                    create_experiment=False, create_tool=False)
        self.experiment_metadata.iso_request.plate_set_label = 'changed'
        self._test_and_expect_errors('The current file upload would change ' \
                    'some properties of the ISO request which must not be ' \
                    'altered anymore')
        self._check_error_messages('plate set label')

    def _test_update_changed_iso_layout(self):
        self._continue_setup_update(self.update_file, create_iso=True,
                                    create_experiment=False, create_tool=False)
        source_layout = self.tool.get_source_layout()
        for tf_pos in source_layout.working_positions():
            tf_pos.reagent_name = 'completeely different'
            break
        self.experiment_metadata.iso_request.iso_layout = \
                                            source_layout.create_rack_layout()
        self._test_and_expect_errors('The current file upload would change ' \
                    'some properties of the ISO request which must not be ' \
                    'altered anymore')
        self._check_error_messages('ISO layout')

    def _test_update_different_number_design_racks(self):
        valid_file = self.VALID_FILES[self.experiment_type_id]
        self._continue_setup_update(valid_file, create_iso=True,
                                    create_experiment=True, create_tool=False)
        del self.experiment_metadata.experiment_design.design_racks[0]
        self._test_and_expect_errors('The current file upload would change ' \
                    'some properties of the experiment design. The ' \
                    'experiment design must not be altered anymore')
        self._check_error_messages('different number of design racks')

    def _test_update_different_design_rack_labels(self):
        valid_file = self.VALID_FILES[self.experiment_type_id]
        self._continue_setup_update(valid_file, create_iso=True,
                                    create_experiment=True, create_tool=False)
        self.experiment_metadata.experiment_design.design_racks[0].label = '10'
        self._test_and_expect_errors('The current file upload would change ' \
                    'some properties of the experiment design. The ' \
                    'experiment design must not be altered anymore')
        self._check_error_messages('different design rack labels')

    def _test_update_different_number_trp_sets(self):
        valid_file = self.VALID_FILES[self.experiment_type_id]
        self._continue_setup_update(valid_file, create_iso=True,
                                    create_experiment=True, create_tool=False)
        for dr in self.experiment_metadata.experiment_design.design_racks:
            tag = Tag('some', 'unimportant', 'tag')
            rack_pos = get_rack_position_from_label('A1')
            rps = RackPositionSet.from_positions(positions=[rack_pos])
            trps = TaggedRackPositionSet(tags=set([tag]), rack_position_set=rps,
                                         user=self.user)
            dr.layout.tagged_rack_position_sets.append(trps)
            break
        self._test_and_expect_errors('The current file upload would change ' \
                    'some properties of the experiment design. The ' \
                    'experiment design must not be altered anymore')
        self._check_error_messages('different number of tag sets')

    def _test_update_different_rack_position_sets(self):
        valid_file = self.VALID_FILES[self.experiment_type_id]
        self._continue_setup_update(valid_file, create_iso=True,
                                    create_experiment=True, create_tool=False)
        for dr in self.experiment_metadata.experiment_design.design_racks:
            for trps in dr.layout.tagged_rack_position_sets:
                rack_pos = get_rack_position_from_label('A1')
                pos_set = set([rack_pos])
                for pos in trps.rack_position_set: pos_set.add(pos)
                rps = RackPositionSet.from_positions(pos_set)
                trps.rack_position_set = rps
                break
            break
        self._test_and_expect_errors('The current file upload would change ' \
                    'some properties of the experiment design. The ' \
                    'experiment design must not be altered anymore')
        self._check_error_messages('different rack position sets')

    def _test_update_different_tags(self):
        valid_file = self.VALID_FILES[self.experiment_type_id]
        self._continue_setup_update(valid_file, create_iso=True,
                                    create_experiment=True, create_tool=False)
        for dr in self.experiment_metadata.experiment_design.design_racks:
            for trps in dr.layout.tagged_rack_position_sets:
                tag = Tag('some', 'unimportant', 'tag')
                trps.tags.add(tag)
                break
            break
        self._test_and_expect_errors('The current file upload would change ' \
                    'some properties of the experiment design. The ' \
                    'experiment design must not be altered anymore')
        self._check_error_messages('different tags')


class ExperimentMetadataGeneratorOptiTestCase(
                                        ExperimentMetadataGeneratorTestCase):

    def set_up(self):
        ExperimentMetadataGeneratorTestCase.set_up(self)
        self.experiment_type_id = EXPERIMENT_SCENARIOS.OPTIMISATION
        self.generator_cls = ExperimentMetadataGeneratorOpti
        self.iso_request_comment = 'autogenerated layout'
        self.number_experiment_design_wls = 2
        self.number_rack_wls = 2
        self.update_file = 'update_opti_with_isos.xls'
        # pos label, values: md, iso vol, iso conc, reagent name, reagent df
        self.iso_layout_values = dict(
                            A1=[205200, 3.2, 560, 'mix1', 1400],
                            B1=[205201, 3.2, 560, 'mix1', 1400],
                            C1=['mock', 5.4, None, 'mix1', 1400],
                            D1=[205200, 3.2, 1120, 'mix1', 1400],
                            E1=[205201, 3.2, 1120, 'mix1', 1400],
                            F1=[205200, 3.2, 560, 'mix1', 2800],
                            G1=['mock', 5.4, None, 'mix1', 2800],
                            H1=[205200, 3.2, 1120, 'mix1', 2800],
                            A2=[205200, 3.2, 560, 'sol2', 700],
                            B2=[205201, 3.2, 560, 'sol2', 700],
                            C2=['mock', 5.4, None, 'sol2', 700],
                            D2=[205200, 3.2, 1120, 'sol2', 700],
                            E2=[205201, 3.2, 1120, 'sol2', 700],
                            F2=[205200, 3.2, 560, 'sol2', 1400],
                            G2=['mock', 5.4, None, 'sol2', 1400],
                            H2=[205200, 3.2, 1120, 'sol2', 1400])

    def _check_experiment_design_tag(self, em):
        cell_tag = Tag(self.ed_domain, 'cell line', 'default')
        for design_rack in em.experiment_design.design_racks:
            pos_set = design_rack.layout.get_positions_for_tag(cell_tag)
            if design_rack.label == '1':
                expected_length = 36
            else:
                expected_length = 24
            self.assert_equal(len(pos_set), expected_length)

    def test_result(self):
        self._continue_setup()
        self._check_result()
        self._check_warning_messages('You did not specify an ISO layout. ' \
                'The system will try to generate the ISO layout by itself.')

    def test_result_with_layout(self):
        for pos_data in self.iso_layout_values.values():
            if pos_data[2] == None: pos_data[2] = 'None'
        self.iso_request_comment = 'opti with layout'
        self._continue_setup('valid_opti_layout.xls')
        self._check_result()
        # test additional ISO layout tag
        irl = self.tool.return_value.iso_request.iso_layout
        add_tag = Tag('transfection', 'sample type', 'pos')
        self._has_tag(irl, add_tag)

    def test_result_different_molecule_types(self):
        for pos_data in self.iso_layout_values.values():
            if pos_data[2] == None: pos_data[2] = 'None'
        self._continue_setup('valid_opti_different_mts.xls')
        self.iso_request_comment = 'opti with different molecule types'
        self.iso_layout_values['B1'] = (330001, 4.2, 420, 'mix1', 1400)
        self.iso_layout_values['E1'] = (330001, 4.2, 840, 'mix1', 1400)
        self.iso_layout_values['B2'] = (330001, 4.2, 420, 'sol2', 700)
        self.iso_layout_values['E2'] = (330001, 4.2, 840, 'sol2', 700)
        self._check_result()

    def test_result_layout_without_fc(self):
        self.check_iso_layout_conc = False
        self.iso_request_comment = 'opti with layout'
        self._continue_setup('valid_opti_layout_without_fc.xls')
        self._check_result()

    def test_result_layout_with_values(self):
        # incl. deepwell warning
        self.iso_layout_values['C1'] = ('mock', 60, None, 'mix1', 1400)
        self.iso_layout_values['G1'] = ('mock', 60, None, 'mix1', 2800)
        self.iso_layout_values['C2'] = ('mock', 60, None, 'sol2', 700)
        self.iso_layout_values['G2'] = ('mock', 60, None, 'sol2', 1400)
        self.iso_request_comment = 'opti with layout'
        self._continue_setup('valid_opti_layout_with_values.xls')
        self._check_result()
        self._check_warning_messages('Use deep well plates for the ISO ' \
                    'plate. The volumes for the mastermix preparation will ' \
                    'exceed 250 ul.')

    def test_result_layout_no_mastermix_support(self):
        self.number_experiment_design_wls = 0
        self.iso_request_comment = 'opti with layout'
        self.iso_layout_values['B1'] = (205201, 3, 560, 'mix1', 1400)
        self.iso_layout_values['E1'] = (205201, 3, 1120, 'mix1', 1400)
        self.iso_layout_values['B2'] = (205201, 3, 560, 'sol2', 700)
        self.iso_layout_values['E2'] = (205201, 3, 1120, 'sol2', 700)
        self._continue_setup('valid_opti_no_mastermix_support.xls')
        self._check_result()
        self._check_warning_messages('The following volumes are not ' \
                            'sufficient to provide mastermix for all target ' \
                            'wells in the cell plate')

    def test_result_layout_with_floatings(self):
        # incl. critical conc warning, no robot support
        self.number_experiment_design_wls = 0
        self.len_pool_set = 3
        self.iso_request_comment = 'opti with layout and floatings'
        self.iso_layout_values = dict(
                B2=(205200, 7, 45000, 'mix1', 140),
                B3=(205201, 7, 45000, 'mix1', 140),
                D2=('md_001', 7, 45000, 'mix1', 140),
                D3=('md_002', 7, 45000, 'mix1', 140),
                D4=('md_003', 7, 45000, 'mix1', 140),
                D5=('md_004', 7, 45000, 'mix1', 140),
                F2=('mock', 7, 'None', 'mix1', 140))
        self._continue_setup('valid_opti_layout_floatings.xls')
        self._check_result()
        self._check_warning_messages('Using that large concentrations will ' \
                'increase the waste volume generated during ISO processing.')

    def test_result_update_blocked_ISO_request(self):
        self._continue_setup_update(self.update_file, create_iso=True,
                                    create_experiment=False)
        self._check_result(is_update_check=True)
        self._check_warning_messages('The ISO generation for this experiment ' \
                                     'metadata has already started!')

    def test_result_update_blocked_experiment_design(self):
        second_file = self.VALID_FILES[self.experiment_type_id]
        self._continue_setup_update(second_file, create_iso=True,
                                    create_experiment=True)
        self.iso_request_comment = 'changed comment'
        self.experiment_metadata.iso_request.comment = self.iso_request_comment
        self._check_result(is_update_check=True)
        self._check_warning_messages('There are already experiment jobs for ' \
                                     'this metadata!')

    def test_with_compound(self):
        self.iso_request_comment = 'opti with compound'
        for pos_data in self.iso_layout_values.values():
            if pos_data[2] == None: pos_data[2] = 'None'
        self.iso_layout_values['B1'] = (277700, 3.2, 560, 'mix1', 1400)
        self.iso_layout_values['E1'] = (277700, 3.2, 1120, 'mix1', 1400)
        self.iso_layout_values['B2'] = (277700, 3.2, 560, 'sol2', 700)
        self.iso_layout_values['E2'] = (277700, 3.2, 1120, 'sol2', 700)
        self._continue_setup('opti_with_compound.xls')
        self._check_result()
        self._check_warning_messages('Attention! There are compounds among ' \
                                     'your control molecule design pools.')

    def test_unsupported_type(self):
        self._test_unsupported_type()

    def test_invalid_experiment_metadata(self):
        self._test_invalid_experiment_metadata()

    def test_invalid_requester(self):
        self._test_invalid_requester()

    def test_missing_ticket_number(self):
        self._test_missing_ticket_number()

    def test_invalid_experiment_design(self):
        self._test_invalid_experiment_design(
                                        'opti_invalid_experiment_design.xls')

    def test_invalid_iso_request_sheet(self):
        self._continue_setup('opti_invalid_iso_request.xls')
        self._test_and_expect_errors('There are errors in the ISO sheet.')

    def test_iso_layout_finder_failure(self):
        self._continue_setup('opti_finder_failure.xls')
        self._test_and_expect_errors('Could not obtain an ISO source layout ' \
                                     'from experiment design.')

    def test_invalid_pool_set(self):
        self._test_invalid_pool_set('opti_invalid_molecule_design_set.xls')

    def test_missing_pool_set(self):
        self._test_missing_pool_set('opti_missing_molecule_design_set.xls')

    def test_no_floatings_but_md_set(self):
        self._test_no_floatings_but_md_set('opti_no_floatings_but_md_set.xls')

    def test_association_error(self):
        self._continue_setup('opti_association_error.xls')
        self._test_and_expect_errors('Error when trying to associate ISO ' \
                                     'source layout and design racks.')

    def test_ambigous_source_well(self):
        self._continue_setup('opti_ambigous_source_well.xls')
        self._test_and_expect_errors('Each position in the ISO layout must ' \
                    'have a unique combination of the following factor levels')

    def test_above_stock_concentration(self):
        self._continue_setup('opti_above_stock_concentration.xls')
        self._test_and_expect_errors('You have tried to order ISO ' \
                    'concentrations that are larger than the maximum ' \
                    'concentration')

    def test_robot_support_determiner_failure(self):
        self._continue_setup('opti_support_determiner_failure.xls')
        self._test_and_expect_errors('Error when trying to determine ' \
                                     'mastermix support.')

    def test_worklist_generation_failure(self):
        self._test_worklist_generation_failure(
                                        'opti_worklist_generation_failure.xls')

    def test_update_converter_error(self):
        self._test_update_converter_error()

    def test_update_changed_plate_set_label(self):
        self._test_update_changed_plate_set_label()

    def test_update_changed_iso_layout(self):
        self._test_update_changed_iso_layout()

    def test_update_different_number_design_racks(self):
        self._test_update_different_number_design_racks()

    def test_update_different_design_rack_labels(self):
        self._test_update_different_design_rack_labels()

    def test_update_different_number_trp_sets(self):
        self._test_update_different_number_trp_sets()

    def test_update_different_rack_position_sets(self):
        self._test_update_different_rack_position_sets()

    def test_update_different_tags(self):
        self._test_update_different_tags()


class ExperimentMetadataGeneratorScreenTestCase(
                                    ExperimentMetadataGeneratorTestCase):

    def set_up(self):
        ExperimentMetadataGeneratorTestCase.set_up(self)
        self.experiment_type_id = EXPERIMENT_SCENARIOS.SCREENING
        self.update_file = 'update_screen_with_isos.xls'
        self.generator_cls = ExperimentMetadataGeneratorScreen
        self.number_rack_wls = 0
        self.number_aliquots = 2
        self.number_plates = 4
        self.len_pool_set = 13
        self.number_experiment_design_wls = 4
        self.iso_request_comment = 'screening layout mastermix compatible'
        # pos label, values: mdpool, iso vol, iso conc, reagent name, reagent df
        self.iso_layout_values = dict(
            B3=[205200, 5, 560, 'mix1', 140],
            B4=[205200, 5, 1120, 'mix1', 140],
            B5=['md_001', 5, 560, 'mix1', 140],
            B6=['md_001', 5, 1120, 'mix1', 140],
            C3=[205201, 5, 560, 'mix1', 140],
            C4=[205201, 5, 1120, 'mix1', 140],
            C5=['md_002', 5, 560, 'mix1', 140],
            C6=['md_002', 5, 1120, 'mix1', 140],
            D3=[205200, 5, 560, 'mix1', 140],
            D4=[205200, 5, 1120, 'mix1', 140],
            D5=['md_003', 5, 560, 'mix1', 140],
            D6=['md_003', 5, 1120, 'mix1', 140],
            E3=[205201, 5, 560, 'mix1', 140],
            E4=[205201, 5, 1120, 'mix1', 140],
            E5=['md_004', 5, 560, 'mix1', 140],
            E6=['md_004', 5, 1120, 'mix1', 140],
            F3=['mock', 5, 'None', 'mix1', 140],
            F4=['mock', 5, 'None', 'mix1', 140],
            F5=['untreated', None, None, 'None', 'None'],
            F6=['untreated', None, None, 'None', 'None'])

    def _check_experiment_design_tag(self, em):
        cell_tag1 = Tag(self.ed_domain, 'cell line', 'Line 1')
        cell_tag2 = Tag(self.ed_domain, 'cell line', 'Line 2')
        for design_rack in em.experiment_design.design_racks:
            pos_set1 = design_rack.layout.get_positions_for_tag(cell_tag1)
            pos_set2 = design_rack.layout.get_positions_for_tag(cell_tag2)
            if design_rack.label == '1':
                self.assert_equal(len(pos_set1), 20)
                self.assert_equal(len(pos_set2), 0)
            else:
                self.assert_equal(len(pos_set1), 0)
                self.assert_equal(len(pos_set2), 20)

    def test_result(self):
        self._continue_setup()
        self._check_result()

    def test_result_no_mastermix_support(self):
        for pos_data in self.iso_layout_values.values():
            if pos_data[0] == MOCK_POSITION_TYPE: pos_data[2] = None
        self.number_experiment_design_wls = 2
        self.iso_request_comment = 'screening layout no mastermix support'
        for result_data in self.iso_layout_values.values():
            if not result_data[1] is None:
                result_data[1] = 1
        self._continue_setup('valid_screen_no_mastermix_support.xls')
        self._check_result()
        self._check_warning_messages('Robot support is disabled now')

    def test_result_iso_volume_adjustment(self):
        for pos_data in self.iso_layout_values.values():
            if not pos_data[2] is None and \
                    not pos_data[0] == MOCK_POSITION_TYPE:
                pos_data[2] = pos_data[2] / 10
        self._continue_setup('valid_screen_volume_adj.xls')
        self._check_result()
        self._check_warning_messages('The ISO volume has to be increased to ' \
                    '5.0 ul, because the requested ISO concentration is ' \
                    'so low that that it requires a larger dilution volume.')

    def test_result_96_well_plate(self):
        self.iso_request_comment = 'screening layout 96-well plate'
        self._continue_setup('valid_screen_96.xls')
        self._check_result()

    def test_result_update_blocked_ISO_request(self):
        self._continue_setup_update(self.update_file, create_iso=True,
                                    create_experiment=False)
        self._check_result(is_update_check=True)
        self._check_warning_messages('The ISO generation for this experiment ' \
                                     'metadata has already started!')

    def test_result_update_blocked_experiment_design(self):
        self._continue_setup_update('update_screen_with_experiments.xls',
                                    create_iso=True, create_experiment=True)
        self.iso_request_comment = 'changed comment'
        self.experiment_metadata.iso_request.comment = self.iso_request_comment
        self.number_plates = 3
        self.len_pool_set = 10
        self._check_result(is_update_check=True)
        self._check_warning_messages('There are already experiment jobs for ' \
                                     'this metadata!')

    def test_with_compound(self):
        self.iso_request_comment = 'screening with compounds'
        for pos_data in self.iso_layout_values.values():
            if pos_data[0] == 205200: pos_data[0] = 277700
            if pos_data[0] == 205201: pos_data[0] = 277701
            if pos_data[1] is not None: pos_data[1] = 45
        self._continue_setup('screen_with_compound.xls')
        self._check_result()
        self._check_warning_messages('Attention! There are compounds among ' \
             'your control molecule design pools. We have found the ' \
             'following stock concentrations: 277700 (11,603,070.7 nM), ' \
             '277701 (13,475,389.1 nM)')
        self._check_warning_messages('Attention! You floating pool set for ' \
             'the floating (sample) positions consists of compounds. ' \
             'For compounds, we assume a stock concentration of ' \
             '5,000,000 nM. Some of the compounds in the set have a ' \
             'different stock concentration: 283697 (10,000,000.0 nM), ' \
             '283702 (10,000,000.0 nM), 283774 (10,000,000.0 nM)')

    def test_unsupported_type(self):
        self._test_unsupported_type()

    def test_invalid_experiment_metadata(self):
        self._test_invalid_experiment_metadata()

    def test_invalid_requester(self):
        self._test_invalid_requester()

    def test_missing_ticket_number(self):
        self._test_missing_ticket_number()

    def test_invalid_experiment_design(self):
        self._test_invalid_experiment_design(
                                        'screen_invalid_experiment_design.xls')

    def test_missing_iso_request_sheet(self):
        self._test_missing_iso_request_sheet('screen_missing_iso_request.xls')

    def test_invalid_iso_request(self):
        self._test_invalid_iso_request('screen_invalid_iso_request.xls')

    def test_robot_support_determiner_failure(self):
        self._continue_setup('screen_support_determiner_failure.xls')
        self._test_and_expect_errors('Error when trying to determine ' \
                                     'mastermix support.')

    def test_invalid_pool_set(self):
        self._test_invalid_pool_set('screen_invalid_molecule_design_set.xls')

    def test_missing_pool_set(self):
        self._test_missing_pool_set('screen_missing_molecule_design_set.xls')

    def test_mismatching_molecule_types(self):
        self._continue_setup('screen_mismatching_molecule_type.xls')
        self._test_and_expect_errors('The molecule type of the floating ' \
                'position samples (miRNA Inhibitor) and the molecule type ' \
                'of the controls (siRNA) do not match!')

    def test_no_floatings_but_md_set(self):
        self._test_no_floatings_but_md_set('screen_no_floatings_but_md_set.xls')

    def test_worklist_generation_failure(self):
        self._test_worklist_generation_failure(
                                    'screen_worklist_generation_failure.xls')

    def test_different_rack_shapes(self):
        self._continue_setup('screen_different_rack_shapes.xls')
        self._test_and_expect_errors('The plate format for experiment design ' \
                        'and ISO do not match (ISO plate layout: 8x12, ' \
                        'experiment design: 16x24).')

    def test_update_converter_error(self):
        self._test_update_converter_error()

    def test_update_changed_plate_set_label(self):
        self._test_update_changed_plate_set_label()

    def test_update_changed_iso_layout(self):
        self._test_update_changed_iso_layout()

    def test_update_different_number_design_racks(self):
        self._test_update_different_number_design_racks()

    def test_update_different_design_rack_labels(self):
        self._test_update_different_design_rack_labels()

    def test_update_different_number_trp_sets(self):
        self._test_update_different_number_trp_sets()

    def test_update_different_rack_position_sets(self):
        self._test_update_different_rack_position_sets()

    def test_update_different_tags(self):
        self._test_update_different_tags()


class ExperimentMetadataGeneratorLibraryTestCase(
                                    ExperimentMetadataGeneratorTestCase):

    def set_up(self):
        ExperimentMetadataGeneratorTestCase.set_up(self)
        self.experiment_type_id = EXPERIMENT_SCENARIOS.LIBRARY
        self.update_file = 'update_library_with_isos.xls'
        self.generator_cls = ExperimentMetadataGeneratorLibrary
        self.number_experiment_design_wls = 4
        self.number_rack_wls = 0
        self.iso_request_comment = 'with mastermix support'
        self.iso_volume = 4
        self.iso_concentration = 1270
        self.optimem_df = 9.1
        self.reagent_name = 'RNAiMax'
        self.reagent_dil_factor = 1400
        self.final_concentration = 10
        # pos label, values: pool md
        self.iso_layout_values = dict(
                B2=330001, B15=330001, I10=330001, I22=330001,
                D2=205200, D15=205200, K10=205200, K22=205200,
                F2='mock', F15='mock', M10='mock', M22='mock',
                H2='untreated', H15='untreated',
                    O10='untreated', O22='untreated')

    def tear_down(self):
        ExperimentMetadataGeneratorTestCase.tear_down(self)
        del self.iso_volume
        del self.iso_concentration
        del self.optimem_df
        del self.reagent_name
        del self.reagent_dil_factor
        del self.final_concentration

    def _test_and_expect_errors(self, msg=None):
        ExperimentMetadataGeneratorTestCase._test_and_expect_errors(self,
                                                                    msg=msg)
        self.assert_is_none(self.tool.get_library())
        self.assert_is_none(self.tool.get_parameter_values())

    def _check_source_layout(self):
        tf_layout = self.tool.get_source_layout()
        none_replacer = TransfectionPosition.NONE_REPLACER
        self.assert_is_not_none(tf_layout)
        self.assert_equal(len(tf_layout), 292)
        investigated_pools = []
        for rack_pos, tf_pos in tf_layout.iterpositions():
            if not tf_pos.is_floating:
                pool_id = self.iso_layout_values[rack_pos.label]
                self.assert_equal(pool_id, tf_pos.molecule_design_pool_id)
                investigated_pools.append(rack_pos.label)
            if tf_pos.is_untreated:
                self.assert_is_none(tf_pos.iso_volume)
                self.assert_is_none(tf_pos.iso_concentration)
                self.assert_is_none(tf_pos.optimem_dil_factor)
                self.assert_equal(tf_pos.reagent_name, none_replacer)
                self.assert_equal(tf_pos.reagent_dil_factor, none_replacer)
                self.assert_equal(tf_pos.final_concentration, none_replacer)
                continue
            elif tf_pos.is_mock:
                self.assert_equal(tf_pos.final_concentration, none_replacer)
                self.assert_is_none(tf_pos.iso_concentration)
            else:
                self.assert_equal(tf_pos.final_concentration,
                                  self.final_concentration)
                self.assert_equal(tf_pos.iso_concentration,
                                  self.iso_concentration)
            self.assert_equal(tf_pos.iso_volume, self.iso_volume)
            self.assert_equal(tf_pos.optimem_dil_factor, self.optimem_df)
            self.assert_equal(tf_pos.reagent_name, self.reagent_name)
            self.assert_equal(tf_pos.reagent_dil_factor,
                              self.reagent_dil_factor)
        self.assert_equal(len(investigated_pools), len(self.iso_layout_values))
        self.assert_equal(sorted(investigated_pools),
                          sorted(self.iso_layout_values.keys()))
        # check the library
        lib = self.tool.get_library()
        self.assert_is_not_none(lib)
        self.assert_equal(lib.label, 'poollib')
        # check the layout value dict
        lv = self.tool.get_parameter_values()
        self.assert_is_not_none(lv)
        self.assert_equal(lv[TransfectionParameters.FINAL_CONCENTRATION],
                          self.final_concentration)
        self.assert_equal(lv[TransfectionParameters.REAGENT_NAME],
                          self.reagent_name)
        self.assert_equal(lv[TransfectionParameters.REAGENT_DIL_FACTOR],
                          self.reagent_dil_factor)
        self.assert_equal(lv[TransfectionParameters.OPTIMEM_DIL_FACTOR],
                          self.optimem_df)

    def _check_experiment_design_tag(self, em):
        cell_tag1 = Tag(self.ed_domain, 'cell line', 'Line 1')
        cell_tag2 = Tag(self.ed_domain, 'cell line', 'Line 2')
        for design_rack in em.experiment_design.design_racks:
            pos_set1 = design_rack.layout.get_positions_for_tag(cell_tag1)
            pos_set2 = design_rack.layout.get_positions_for_tag(cell_tag2)
            if design_rack.label == '1':
                self.assert_equal(len(pos_set1), 308)
                self.assert_equal(len(pos_set2), 0)
            else:
                self.assert_equal(len(pos_set1), 0)
                self.assert_equal(len(pos_set2), 308)

    def test_result(self):
        self._continue_setup()
        self._check_result()

    def test_result_no_mastermix_support(self):
        self._continue_setup('valid_library_no_mastermix_support.xls')
        self.iso_request_comment = 'no mastermix support'
        self.final_concentration = 5
        self.optimem_df = 18.1
        self.number_experiment_design_wls = 2
        self._check_result()
        self._check_warning_messages('Robot support for mastermix ' \
                                     'preparation is disabled')

    def test_result_with_compound(self):
        pos_labels = []
        for pos_label, pool_id in self.iso_layout_values.iteritems():
            if pool_id == 330001: pos_labels.append(pos_label)
        for pos_label in pos_labels:
            self.iso_layout_values[pos_label] = 277700
        self._continue_setup('library_with_compound.xls')
        self._check_result()
        self._check_warning_messages('Attention! There are compounds among ' \
                                     'your control molecule design pools')

    def test_result_update_blocked_ISO_request(self):
        self._continue_setup_update(self.update_file, create_iso=True,
                                    create_experiment=False)
        self._check_result(is_update_check=True)
        self._check_warning_messages('The ISO generation for this experiment ' \
                                     'metadata has already started!')

    def test_unsupported_type(self):
        self._test_unsupported_type()

    def test_invalid_experiment_metadata(self):
        self._test_invalid_experiment_metadata()

    def test_invalid_requester(self):
        self._test_invalid_requester()

    def test_missing_ticket_number(self):
        self._test_missing_ticket_number()

    def test_invalid_experiment_design(self):
        self._test_invalid_experiment_design(
                                        'library_invalid_experiment_design.xls')

    def test_missing_iso_request_sheet(self):
        self._test_missing_iso_request_sheet('library_missing_iso_request.xls')

    def test_invalid_iso_request(self):
        self._test_invalid_iso_request('library_invalid_iso_request.xls')

    def test_robot_support_determiner_failure(self):
        self._continue_setup('library_support_determiner_failure.xls')
        self._test_and_expect_errors('Error when trying to determine ' \
                                     'mastermix support.')

    def test_with_pool_set(self):
        self._test_with_pool_set('library_with_pool_set.xls')

    def test_worklist_generation_failure(self):
        self._test_worklist_generation_failure(
                                    'library_worklist_generation_failure.xls')

    def test_different_rack_shapes(self):
        self._continue_setup('library_different_rack_shapes.xls')
        self._test_and_expect_errors('The plate format for experiment design ' \
                        'and ISO do not match (ISO plate layout: 16x24, ' \
                        'experiment design: 8x12).')

    def test_update_converter_error(self):
        self._test_update_converter_error()

    def test_update_changed_plate_set_label(self):
        self._test_update_changed_plate_set_label()

    def test_update_changed_iso_layout(self):
        self._test_update_changed_iso_layout()

    def test_update_different_number_design_racks(self):
        self._test_update_different_number_design_racks()

    def test_update_different_design_rack_labels(self):
        self._test_update_different_design_rack_labels()

    def test_update_different_number_trp_sets(self):
        self._test_update_different_number_trp_sets()

    def test_update_different_rack_position_sets(self):
        self._test_update_different_rack_position_sets()

    def test_update_different_tags(self):
        self._test_update_different_tags()



class ExperimentMetdadataGeneratorManualTestCase(
                                    ExperimentMetadataGeneratorTestCase):

    def set_up(self):
        ExperimentMetadataGeneratorTestCase.set_up(self)
        self.experiment_type_id = EXPERIMENT_SCENARIOS.MANUAL
        self.update_file = 'update_manual_with_iso.xls'
        self.generator_cls = ExperimentMetadataGeneratorManual
        self.number_experiment_design_wls = 0
        self.number_rack_wls = 2
        self.iso_request_comment = 'manual test case'
        # pos label, values: md, iso vol, iso conc, reagent name, reagent df
        self.iso_layout_values = dict(
                            B2=(205200, 20, 5000, None, None),
                            C2=(205201, 10, 5000, None, None),
                            D2=(205202, 10, 5000, None, None))

    def _check_experiment_design_tag(self, em):
        cell_tag1 = Tag(self.ed_domain, 'cell line', 'Line 1')
        cell_tag2 = Tag(self.ed_domain, 'cell line', 'Line 2')
        for design_rack in em.experiment_design.design_racks:
            pos_set1 = design_rack.layout.get_positions_for_tag(cell_tag1)
            pos_set2 = design_rack.layout.get_positions_for_tag(cell_tag2)
            if design_rack.label == '1':
                self.assert_equal(len(pos_set1), 10)
                self.assert_equal(len(pos_set2), 0)
            else:
                self.assert_equal(len(pos_set1), 0)
                self.assert_equal(len(pos_set2), 10)

    def test_result(self):
        self._continue_setup()
        self._check_result()

    def test_result_update_blocked_ISO_request(self):
        self._continue_setup_update(self.update_file, create_iso=True,
                                    create_experiment=False)
        self._check_result(is_update_check=True)
        self._check_warning_messages('The ISO generation for this experiment ' \
                                     'metadata has already started!')

    def test_result_update_blocked_experiment_design(self):
        second_file = self.VALID_FILES[self.experiment_type_id]
        self._continue_setup_update(second_file, create_iso=True,
                                    create_experiment=True)
        self.iso_request_comment = 'changed comment'
        self.experiment_metadata.iso_request.comment = self.iso_request_comment
        self._check_result(is_update_check=True)
        self._check_warning_messages('There are already experiment jobs for ' \
                                     'this metadata!')

    def test_with_compound(self):
        self.iso_request_comment = 'manual with compound'
        self.iso_layout_values['C2'] = (277700, 20, 1000000, None, None)
        self._continue_setup('manual_with_compound.xls')
        self._check_result()
        self._check_warning_messages('Attention! There are compounds among ' \
                                     'your control molecule design pools.')

    def test_unsupported_type(self):
        self._test_unsupported_type()

    def test_invalid_experiment_metadata(self):
        self._test_invalid_experiment_metadata()

    def test_invalid_requester(self):
        self._test_invalid_requester()

    def test_missing_ticket_number(self):
        self._test_missing_ticket_number()

    def test_invalid_experiment_design(self):
        self._test_invalid_experiment_design(
                                        'manual_invalid_experiment_design.xls')

    def test_missing_iso_request_sheet(self):
        self._test_missing_iso_request_sheet('manual_missing_iso_sheet.xls')

    def test_invalid_iso_request(self):
        self._test_invalid_iso_request('manual_invalid_iso_request.xls')

    def test_iso_volume_too_low(self):
        self._continue_setup('manual_iso_volume_too_low.xls')
        self._test_and_expect_errors('The minimum ISO volume you can order ' \
                                     'is 1 ul.')

    def test_no_floatings_but_md_set(self):
        self._continue_setup('manual_no_floatings_but_md_set.xls')
        self._test_and_expect_errors('There are molecule design pools for ' \
                    'floating positions specified. Floating positions are ' \
                    'not allowed for manual optimisation experiments!')

    def test_association_failure(self):
        self._continue_setup('manual_association_failure.xls')
        self._test_and_expect_errors('Error when trying to associate ISO ' \
                                     'layout and design rack layouts.')

    def test_update_converter_error(self):
        self._test_update_converter_error()

    def test_update_changed_plate_set_label(self):
        self._test_update_changed_plate_set_label()

    def test_update_changed_iso_layout(self):
        self._test_update_changed_iso_layout()

    def test_update_different_number_design_racks(self):
        self._test_update_different_number_design_racks()

    def test_update_different_design_rack_labels(self):
        self._test_update_different_design_rack_labels()

    def test_update_different_number_trp_sets(self):
        self._test_update_different_number_trp_sets()

    def test_update_different_rack_position_sets(self):
        self._test_update_different_rack_position_sets()

    def test_update_different_tags(self):
        self._test_update_different_tags()


class ExperimentMetadataGeneratorIsoLessTestCase(#pylint: disable=W0223
                                    ExperimentMetadataGeneratorTestCase):
    """
    This test case is special because we do not have an ISO request, ISO
    layout or worklists.
    """

    def set_up(self):
        ExperimentMetadataGeneratorTestCase.set_up(self)
        self.experiment_type_id = EXPERIMENT_SCENARIOS.ISO_LESS
        self.generator_cls = ExperimentMetadataGeneratorIsoless

    def test_result(self):
        self._continue_setup()
        em = self.tool.get_result()
        self.assert_is_not_none(em)
        # check attributes
        self.assert_equal(em.number_replicates, self.number_replicates)
        self.assert_equal(em.label, self.label)
        self.assert_is_not_none(em.experiment_design)
        self.assert_equal(em.ticket_number, self.ticket_number)
        self.assert_is_none(em.iso_request)
        self.assert_is_none(em.molecule_design_pool_set)
        self.assert_is_none(em.experiment_design.worklist_series)
        for design_rack in em.experiment_design.design_racks:
            self.assert_is_none(design_rack.worklist_series)

    def test_unsupported_type(self):
        self._test_unsupported_type()

    def test_invalid_experiment_metadata(self):
        self._test_invalid_experiment_metadata()

    def test_invalid_requester(self):
        self._test_invalid_requester()

    def test_missing_ticket_number(self):
        self._test_missing_ticket_number()

    def test_invalid_experiment_design(self):
        self._test_invalid_experiment_design(
                                        'isoless_invalid_experiment_design.xls')

    def test_update_different_number_design_racks(self):
        self._test_update_different_number_design_racks()

    def test_update_different_design_rack_labels(self):
        self._test_update_different_design_rack_labels()

    def test_update_different_number_trp_sets(self):
        self._test_update_different_number_trp_sets()

    def test_update_different_rack_position_sets(self):
        self._test_update_different_rack_position_sets()

    def test_update_different_tags(self):
        self._test_update_different_tags()


class ExperimentMetadataGeneratorOrderTestCase(
                                    ExperimentMetadataGeneratorTestCase):

    def set_up(self):
        ExperimentMetadataGeneratorTestCase.set_up(self)
        self.update_file = 'update_order_with_isos.xls'
        self.experiment_type_id = EXPERIMENT_SCENARIOS.ORDER_ONLY
        self.generator_cls = ExperimentMetadataGeneratorOrder
        self.iso_request_comment = 'ISO request without experiment'
        # pos label, values: md, iso vol, iso conc, reagent name, reagent df
        self.iso_layout_values = dict(
                B2=[205201, 1, 50000, None, None],
                B4=[330001, 1, 10000, None, None],
                B6=[333803, 1, 5000000, None, None],
                B8=[1056000, 1, 10000, None, None],
                B10=[180202, 1, 50000, None, None])

    def _check_experiment_design_tag(self, experiment_metadata):
        pass # no experiment design

    def test_result(self):
        self._continue_setup()
        self._check_result()
        # check additional tag from ISO sheet
        irl = self.tool.return_value.iso_request.iso_layout
        add_tag = Tag('transfection', 'molecule_type', 'siRNA pool')
        self._has_tag(irl, add_tag)
        self._check_warning_messages('Attention! There are compounds among ' \
                                     'your control molecule design pools.')

    def test_result_update(self):
        self._continue_setup_update(self.update_file, create_iso=True,
                                    create_experiment=False)
        self._check_result(is_update_check=True)
        irl = self.tool.return_value.iso_request.iso_layout
        ori_tag = Tag('transfection', 'molecule_type', 'siRNA pool')
        new_tag = Tag('transfection', 'molecule_type', 'pool of siRNAs')
        self._has_tag(irl, ori_tag, expect_true=False)
        self._has_tag(irl, new_tag)
        self._check_warning_messages('The ISO generation for this experiment ' \
                                     'metadata has already started!')

    def test_unsupported_type(self):
        self._test_unsupported_type()

    def test_invalid_experiment_metadata(self):
        self._test_invalid_experiment_metadata()

    def test_invalid_requester(self):
        self._test_invalid_requester()

    def test_missing_ticket_number(self):
        self._test_missing_ticket_number()

    def test_missing_iso_request_sheet(self):
        self._test_missing_iso_request_sheet('order_missing_iso_sheet.xls')

    def test_invalid_iso_request(self):
        self._test_invalid_iso_request('order_invalid_iso_request.xls')

    def test_iso_volume_too_low(self):
        self._continue_setup('order_iso_volume_too_low.xls')
        self._test_and_expect_errors('The minimum ISO volume you can order ' \
             'is 1 ul. For some positions, you have ordered less: ' \
             '1056000 (B8, 0.5 ul), 180202 (B10, 0.5 ul), 333803 (B6, 0.5 ul)')

    def test_with_pool_set(self):
        self._test_with_pool_set('order_with_pool_set.xls')

    def test_update_converter_error(self):
        self._test_update_converter_error()

    def test_update_changed_plate_set_label(self):
        self._test_update_changed_plate_set_label()

    def test_update_changed_iso_layout(self):
        self._test_update_changed_iso_layout()
