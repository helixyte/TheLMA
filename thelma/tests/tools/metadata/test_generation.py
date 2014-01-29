"""
Tests the tool involved in experiment metadata generation.
AAB Aug 08, 2011
"""

from datetime import date
from thelma.interfaces import IMoleculeDesignLibrary
from thelma.automation.handlers.experimentdesign \
    import ExperimentDesignParserHandler
from thelma.automation.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.semiconstants import get_96_rack_shape
from thelma.automation.semiconstants import get_experiment_metadata_type
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.semiconstants import get_reservoir_specs_deep_96
from thelma.automation.semiconstants import get_reservoir_specs_standard_384
from thelma.automation.semiconstants import get_reservoir_specs_standard_96
from thelma.automation.tools.metadata.base import TransfectionParameters
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
    import ExperimentMetadataGeneratorOrder
from thelma.automation.tools.metadata.generation \
import ExperimentMetadataGeneratorScreen
from thelma.automation.utils.iso import IsoRequestParameters
from thelma.interfaces import IPlate
from thelma.interfaces import ISubproject
from thelma.interfaces import IUser
from thelma.models.experiment import ExperimentMetadata
from thelma.models.iso import ISO_TYPES
from thelma.models.rack import RackPositionSet
from thelma.models.racklayout import RackLayout
from thelma.models.tagging import Tag
from thelma.models.tagging import TaggedRackPositionSet
from thelma.models.utils import get_user
from thelma.tests.tools.tooltestingutils import FileReadingTestCase


class _ExperimentMetadataGeneratorTestCase(FileReadingTestCase):

    _TEST_FILE_SUBDIRECTORY = ''
    _GENERATOR_CLS = ExperimentMetadataGenerator

    def set_up(self):
        FileReadingTestCase.set_up(self)
        self.TEST_FILE_PATH = 'thelma:tests/tools/metadata/generator/%s/' \
                               % (self._TEST_FILE_SUBDIRECTORY)
        self.VALID_FILE = 'valid_file.xls'
        self.experiment_type_id = None
        self.update_file = None
        self.experiment_metadata = None
        self.user = get_user('it')
        self.user = self._get_entity(IUser, 'sachse')
        # other setup values
        self.label = 'em_generator_test'
        self.number_replicates = 3
        self.ticket_number = 123
        # result values
        self.number_experiment_design_wls = None
        self.number_rack_wls = None
        self.expected_ir_data = dict(number_aliquots=1, comment='',
                 expected_number_isos=1, requester=self.user,
                 delivery_date=date(2016, 9, 17), process_job_first=True,
                 iso_plate_reservoir_specs=get_reservoir_specs_standard_96(),
                 molecule_design_library=None, label='',
                 iso_type=ISO_TYPES.LAB)
        self.len_pool_set = 0
        # pos label - pool, pos_type, iso vol, iso conc, final conc,
        # reagent name, reagent df, optimem dil factor
        self.ir_layout_values = None

    def tear_down(self):
        FileReadingTestCase.tear_down(self)
        del self.update_file
        del self.experiment_metadata
        del self.experiment_type_id
        del self.label
        del self.ticket_number
        del self.number_experiment_design_wls
        del self.number_rack_wls
        del self.len_pool_set
        del self.ir_layout_values

    def _create_tool(self):
        self.tool = ExperimentMetadataGenerator.create(stream=self.stream,
                            experiment_metadata=self.experiment_metadata,
                            requester=self.user)

    def _create_tool_without_factory(self):
        #pylint: disable=E1102
        self.tool = self._GENERATOR_CLS(stream=self.stream,
                            experiment_metadata=self.experiment_metadata,
                            requester=self.user)
        #pylint: enable=E1102

    def _continue_setup(self, file_name=None):
        FileReadingTestCase._continue_setup(self, file_name)
        if self.experiment_metadata is None:
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
        self._continue_setup(second_file)
        if create_tool: self._create_tool()

    def __create_metadata(self):
        em_type = get_experiment_metadata_type(self.experiment_type_id)
        self.experiment_metadata = ExperimentMetadata(label=self.label,
                    subproject=self._get_entity(ISubproject),
                    number_replicates=self.number_replicates,
                    experiment_metadata_type=em_type,
                    ticket_number=self.ticket_number)

    def __create_iso(self):
        self._create_lab_iso(
                iso_request=self.experiment_metadata.lab_iso_request)

    def __create_experiment(self, plate, plate_specs):
        experiment = self._create_experiment(source_rack=plate,
                destination_rack_specs=plate_specs,
                experiment_design=self.experiment_metadata.experiment_design)
        self._create_experiment_job(experiments=[experiment])

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
            self.__check_design_rack_final_concentrations(em)
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
        iso_request = em.lab_iso_request
        if self.tool.HAS_ISO_REQUEST:
            self.assert_is_not_none(iso_request)
            for attr_name, exp_value in self.expected_ir_data.iteritems():
                tool_value = getattr(iso_request, attr_name)
                if not exp_value == tool_value:
                    msg = 'The %s for the ISO request differ.\nExpected: %s\n' \
                          'Found: %s.' % (attr_name, exp_value, tool_value)
                    raise AssertionError(msg)
            self.assert_is_none(iso_request.worklist_series)
        else:
            self.assert_is_none(iso_request)
        if self.len_pool_set == 0:
            self.assert_is_none(iso_request.molecule_design_pool_set)
        else:
            self.assert_equal(len(iso_request.molecule_design_pool_set),
                              self.len_pool_set)

    def __check_worklists_series(self, em):
        ed_series = em.experiment_design.worklist_series
        if self.number_experiment_design_wls == 0:
            self.assert_is_none(ed_series)
        else:
            self.assert_equal(len(ed_series), self.number_experiment_design_wls)
        for design_rack in em.experiment_design.experiment_design_racks:
            rack_series = design_rack.worklist_series
            if self.number_rack_wls == 0:
                self.assert_is_none(rack_series)
            else:
                self.assert_equal(len(rack_series), self.number_rack_wls)

    def _check_source_layout(self):
        tf_layout = self.tool.get_source_layout()
        self.assert_is_not_none(tf_layout)
        self.assert_equal(len(tf_layout), len(self.ir_layout_values))
        attrs = dict(molecule_design_pool=0, position_type=1, iso_volume=2,
                     iso_concentration=3, final_concentration=4,
                     reagent_name=5, reagent_dil_factor=6,
                     optimem_dil_factor=7)
        for rack_pos, tf_pos in tf_layout.iterpositions():
            result_data = self.ir_layout_values[rack_pos.label]
            for attr_name, result_index in attrs.iteritems():
                exp_value = result_data[result_index]
                if attr_name == 'molecule_design_pool':
                    exp_value = self._get_pool(exp_value)
                if not getattr(tf_pos, attr_name) == exp_value:
                    msg = 'Different value for attribute %s in position %s.\n' \
                          'Found: %s\nExpected: %s' % (attr_name,
                           rack_pos.label, getattr(tf_pos, attr_name),
                           exp_value)
                    raise AssertionError(msg)

    def __check_design_rack_final_concentrations(self, em):
        fcs = self.tool.get_final_concentrations()
        self.assert_is_not_none(fcs)
        design_racks = em.experiment_design.experiment_design_racks
        self.assert_equal(len(fcs), len(design_racks))
        pool_predicate = TransfectionParameters.MOLECULE_DESIGN_POOL\
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
                tags = design_rack.rack_layout.get_tags_for_position(rack_pos)
                if not self.experiment_type_id \
                                            == EXPERIMENT_SCENARIOS.SCREENING:
                    all_predicates = set()
                    for tag in tags: all_predicates.add(tag.predicate)
                    self.assert_true(pool_predicate in all_predicates)
                if final_conc is None: continue
                fc_tag = Tag(fc_domain, fc_predicate, final_conc)
                self.assert_true(fc_tag in tags)

    def __check_association_layouts(self, em):
        al = self.tool.get_association_layouts()
        self.assert_is_not_none(al)
        design_racks = em.experiment_design.experiment_design_racks
        self.assert_equal(len(al), len(design_racks))
        md_predicate = TransfectionParameters.\
                       MOLECULE_DESIGN_POOL.replace('_', ' ')
        for design_rack in design_racks:
            tf_layout = al[design_rack.label]
            md_positions = []
            for rack_pos in design_rack.rack_layout.get_positions():
                tags = design_rack.rack_layout.get_tags_for_position(rack_pos)
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
        FileReadingTestCase._test_and_expect_errors(self, msg=msg)
        self.assert_is_none(self.tool.get_source_layout())
        self.assert_is_none(self.tool.get_association_layouts())
        self.assert_is_none(self.tool.get_final_concentrations())

    def _test_unsupported_type(self):
        self._continue_setup()
        kw = dict(stream=self.stream, requester=self.user,
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

    def _test_invalid_input_values(self):
        self._continue_setup()
        self.__test_invalid_requester()
        self.__test_missing_ticket_number()
        self.__test_invalid_experiment_metadata()

    def __test_invalid_requester(self):
        ori_user = self.user
        self.user = None
        self._test_and_expect_errors('The requester must be a User object')
        self.user = ori_user

    def __test_missing_ticket_number(self):
        self.experiment_metadata.ticket_number = None
        self._test_and_expect_errors('Unable to find ticket number!')
        self.experiment_metadata.ticket_number = self.ticket_number

    def __test_invalid_experiment_metadata(self):
        self.experiment_metadata = None
        self._create_tool_without_factory()
        em = self.tool.get_result()
        self.assert_is_none(em)
        self._check_error_messages('The experiment metadata must be a ' \
                                   'ExperimentMetadata object')
        self.assert_is_none(self.tool.get_source_layout())
        kw = dict(stream=self.stream, requester=self.user,
                  experiment_metadata=self.experiment_metadata)
        # pylint: disable=W0142
        self.assert_raises(ValueError, ExperimentMetadataGenerator.create, **kw)
        # pylint: enable=W0142

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

    def _test_no_floatings_but_pool_set(self, file_name):
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
        self.experiment_metadata.lab_iso_request.rack_layout = \
                                        RackLayout(shape=get_96_rack_shape())
        self._test_and_expect_errors('Error when trying to convert ' \
                                     'ISO layout of the existing ISO request.')

    def _test_update_changed_number_aliquots(self):
        self._continue_setup_update(self.update_file, create_iso=True,
                                    create_experiment=False, create_tool=False)
        self.experiment_metadata.lab_iso_request.number_aliquots = 3
        self._test_and_expect_errors('The current file upload would change ' \
                    'some properties of the ISO request which must not be ' \
                    'altered anymore')
        self._check_error_messages('number of aliquots')

    def _test_update_changed_plate_set_label(self):
        self._continue_setup_update(self.update_file, create_iso=True,
                                    create_experiment=False, create_tool=False)
        self.experiment_metadata.lab_iso_request.label = 'changed'
        self._test_and_expect_errors('The current file upload would change ' \
                    'some properties of the ISO request which must not be ' \
                    'altered anymore')
        self._check_error_messages('plate set label')

    def _test_update_changed_iso_request_layout(self, use_reagent_name=True):
        self._continue_setup_update(self.update_file, create_iso=True,
                                    create_experiment=False, create_tool=False)
        if use_reagent_name:
            parameter = TransfectionParameters.REAGENT_NAME
            new_value = 'compleetly different'
        else:
            parameter = IsoRequestParameters.ISO_VOLUME
            new_value = '9999999'

        validator = TransfectionParameters.create_validator_from_parameter(
                                        parameter)
        for tag in self.experiment_metadata.lab_iso_request.rack_layout.\
                                    get_tags():
            if validator.has_alias(tag.predicate):
                tag.value = new_value
                break
        self._test_and_expect_errors('The current file upload would change ' \
                    'some properties of the ISO request which must not be ' \
                    'altered anymore')
        self._check_error_messages('ISO request layout')

    def _test_update_different_number_design_racks(self):
        self._continue_setup_update(self.VALID_FILE, create_iso=True,
                                    create_experiment=True, create_tool=False)
        del self.experiment_metadata.experiment_design.experiment_design_racks[0]
        self._test_and_expect_errors('The current file upload would change ' \
                    'some properties of the experiment design. The ' \
                    'experiment design must not be altered anymore')
        self._check_error_messages('different number of design racks')

    def _test_update_different_design_rack_labels(self):
        self._continue_setup_update(self.VALID_FILE, create_iso=True,
                                    create_experiment=True, create_tool=False)
        self.experiment_metadata.experiment_design.\
                                experiment_design_racks[0].label = '10'
        self._test_and_expect_errors('The current file upload would change ' \
                    'some properties of the experiment design. The ' \
                    'experiment design must not be altered anymore')
        self._check_error_messages('different design rack labels')

    def _test_update_different_number_trp_sets(self):
        self._continue_setup_update(self.VALID_FILE, create_iso=True,
                                    create_experiment=True, create_tool=False)
        for dr in self.experiment_metadata.experiment_design.\
                                                experiment_design_racks:
            tag = Tag('some', 'unimportant', 'tag')
            rack_pos = get_rack_position_from_label('A1')
            rps = RackPositionSet.from_positions(positions=[rack_pos])
            trps = TaggedRackPositionSet(tags=set([tag]), rack_position_set=rps,
                                         user=self.user)
            dr.rack_layout.tagged_rack_position_sets.append(trps)
            break
        self._test_and_expect_errors('The current file upload would change ' \
                    'some properties of the experiment design. The ' \
                    'experiment design must not be altered anymore')
        self._check_error_messages('different number of tag sets')

    def _test_update_different_rack_position_sets(self):
        self._continue_setup_update(self.VALID_FILE, create_iso=True,
                                    create_experiment=True, create_tool=False)
        for dr in self.experiment_metadata.experiment_design.\
                                                        experiment_design_racks:
            for trps in dr.rack_layout.tagged_rack_position_sets:
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
        self._continue_setup_update(self.VALID_FILE, create_iso=True,
                                    create_experiment=True, create_tool=False)
        for dr in self.experiment_metadata.experiment_design.\
                                                    experiment_design_racks:
            for trps in dr.rack_layout.tagged_rack_position_sets:
                tag = Tag('some', 'unimportant', 'tag')
                trps.tags.add(tag)
                break
            break
        self._test_and_expect_errors('The current file upload would change ' \
                    'some properties of the experiment design. The ' \
                    'experiment design must not be altered anymore')
        self._check_error_messages('different tags')


class ExperimentMetadataGeneratorOptiTestCase(
                                        _ExperimentMetadataGeneratorTestCase):

    _TEST_FILE_SUBDIRECTORY = 'opti'
    _GENERATOR_CLS = ExperimentMetadataGeneratorOpti

    def set_up(self):
        _ExperimentMetadataGeneratorTestCase.set_up(self)
        self.experiment_type_id = EXPERIMENT_SCENARIOS.OPTIMISATION
        self.expected_ir_data['comment'] = 'autogenerated layout'
        self.number_experiment_design_wls = 2
        self.number_rack_wls = 2
        self.update_file = 'update_with_isos.xls'
        # pos label - pool, pos_ type, iso vol, iso conc, final conc,
        # reagent name, reagent df, optimem dil factor
        self.ir_layout_values = dict(
                A1=[205200, 'fixed', 3.2, 560, 10, 'mix1', 1400, 4],
                B1=[330001, 'fixed', 4.2, 420, 10, 'mix1', 1400, 3],
                C1=['mock', 'mock', 5.4, None, None, 'mix1', 1400, 4],
                D1=[205200, 'fixed', 3.2, 1120, 20, 'mix1', 1400, 4],
                E1=[330001, 'fixed', 4.2, 840, 20, 'mix1', 1400, 3],
                F1=[205200, 'fixed', 3.2, 560, 10, 'mix1', 2800, 4],
                G1=['mock', 'mock', 5.4, None, None, 'mix1', 2800, 4],
                H1=[205200, 'fixed', 3.2, 1120, 20, 'mix1', 2800, 4],
                A2=[205200, 'fixed', 3.2, 560, 10, 'sol2', 700, 4],
                B2=[330001, 'fixed', 4.2, 420, 10, 'sol2', 700, 3],
                C2=['mock', 'mock', 5.4, None, None, 'sol2', 700, 4],
                D2=[205200, 'fixed', 3.2, 1120, 20, 'sol2', 700, 4],
                E2=[330001, 'fixed', 4.2, 840, 20, 'sol2', 700, 3],
                F2=[205200, 'fixed', 3.2, 560, 10, 'sol2', 1400, 4],
                G2=['mock', 'mock', 5.4, None, None, 'sol2', 1400, 4],
                H2=[205200, 'fixed', 3.2, 1120, 20, 'sol2', 1400, 4])

    def _check_experiment_design_tag(self, em):
        cell_tag = Tag(ExperimentDesignParserHandler.TAG_DOMAIN, 'cell line',
                       'default')
        for design_rack in em.experiment_design.experiment_design_racks:
            pos_set = design_rack.rack_layout.get_positions_for_tag(cell_tag)
            if design_rack.label == '1':
                expected_length = 36
            else:
                expected_length = 24
            self.assert_equal(len(pos_set), expected_length)

    def _continue_setup_update(self, second_file, create_iso,
        create_experiment, create_tool=True):
        self.expected_ir_data['label'] = self.label
        self.expected_ir_data['delivery_date'] = None
        _ExperimentMetadataGeneratorTestCase._continue_setup_update(self,
                        second_file, create_iso, create_experiment, create_tool)

    def test_result(self):
        # standard case, autogenerated layout
        self._continue_setup()
        self.expected_ir_data['label'] = self.experiment_metadata.label
        self.expected_ir_data['delivery_date'] = None
        self._check_result()
        self.assert_true(self.tool.supports_mastermix)
        self._check_warning_messages('You did not specify an ISO request ' \
            'layout. The system will try to generate the layout by itself.')

    def test_result_with_layout(self):
        # standard case, user-defined layout
        for pos_data in self.ir_layout_values.values():
            if pos_data[2] == None: pos_data[2] = 'None'
            if pos_data[1] == 'mock': pos_data[3] = 'None'
        self.expected_ir_data['label'] = 'opti_w_layout'
        self.expected_ir_data['comment'] = 'opti with layout'
        self._continue_setup('valid_file_layout.xls')
        self._check_result()
        # test additional ISO request layout tag
        irl = self.tool.return_value.lab_iso_request.rack_layout
        add_tag = Tag('transfection', 'sample type', 'pos')
        self._has_tag(irl, add_tag)

    def test_result_layout_without_fc(self):
        # standard case, user-defined layout but no final concentrations
        for pos_data in self.ir_layout_values.values():
            if pos_data[1] == 'mock': pos_data[3] = 'None'
        self.ir_layout_values['B2'][4] = 20
        self.ir_layout_values['B2'][3] = 840
        self.ir_layout_values['E2'][4] = 10
        self.ir_layout_values['E2'][3] = 420
        self.expected_ir_data['label'] = 'opti_layout_fc'
        self.expected_ir_data['comment'] = 'opti with layout'
        self._continue_setup('valid_file_layout_without_fc.xls')
        self._check_result()

    def test_result_layout_with_values(self):
        # standard case with ISO values and deepwell warning
        # mastermix compatible
        self.ir_layout_values['C1'] = \
                        ['mock', 'mock', 60, None, None, 'mix1', 1400, 4]
        self.ir_layout_values['G1'] = \
                        ['mock', 'mock', 60, None, None, 'mix1', 2800, 4]
        self.ir_layout_values['C2'] = \
                        ['mock', 'mock', 60, None, None, 'sol2', 700, 4]
        self.ir_layout_values['G2'] = \
                        ['mock', 'mock', 60, None, None, 'sol2', 1400, 4]
        self.expected_ir_data['label'] = 'layout_w_vals'
        self.expected_ir_data['comment'] = 'opti with layout'
        self.expected_ir_data['iso_plate_reservoir_specs'] = \
                        get_reservoir_specs_deep_96()
        self._continue_setup('valid_file_layout_with_values.xls')
        self._check_result()
        self._check_warning_messages('Use deep well plates for the ISO ' \
                    'plate. The volumes for the mastermix preparation will ' \
                    'exceed 250 ul.')

    def test_result_layout_no_mastermix_support(self):
        self.number_experiment_design_wls = 0
        self.expected_ir_data['label'] = 'opti_no_mm'
        self.expected_ir_data['comment'] = 'opti with layout'
        for pos_label in ('B1', 'B2', 'E1', 'E2'):
            self.ir_layout_values[pos_label][2] = 3
        self._continue_setup('valid_file_no_mastermix_support.xls')
        self._check_result()
        self.assert_false(self.tool.supports_mastermix)
        self._check_warning_messages('The following volumes are not ' \
                            'sufficient to provide mastermix for all target ' \
                            'wells in the cell plate')

    def test_result_layout_with_floatings(self):
        # no robot support, jobs are processed last
        self.number_experiment_design_wls = 0
        self.len_pool_set = 3
        self.expected_ir_data['label'] = 'with_floats'
        self.expected_ir_data['comment'] = 'opti with layout and floatings'
        self.expected_ir_data['process_job_first'] = False
        self.expected_ir_data['iso_plate_reservoir_specs'] = \
                                            get_reservoir_specs_standard_384()
        self.ir_layout_values = dict(
                B2=[205200, 'fixed', 7, 45000, 5, 'mix1', 140, 4],
                B3=[205201, 'fixed', 7, 45000, 10, 'mix1', 140, 4],
                D2=['md_001', 'floating', 7, 45000, 15, 'mix1', 140, 4],
                D3=['md_002', 'floating', 7, 45000, 15, 'mix1', 140, 4],
                D4=['md_003', 'floating', 7, 45000, 15, 'mix1', 140, 4],
                D5=['md_004', 'floating', 7, 45000, 15, 'mix1', 140, 4],
                F2=['mock', 'mock', 7, 'None', 'mock', 'mix1', 140, 4])
        self._continue_setup('valid_file_layout_floatings.xls')
        self._check_result()
        self.assert_false(self.tool.supports_mastermix)

    def test_result_update_blocked_ISO_request(self):
        self._continue_setup_update(self.update_file, create_iso=True,
                                    create_experiment=False)
        self._check_result(is_update_check=True)
        self._check_warning_messages('The ISO generation for this experiment ' \
                                     'metadata has already started!')

    def test_result_update_blocked_experiment_design(self):
        self._continue_setup_update(self.VALID_FILE, create_iso=True,
                                    create_experiment=True)
        new_comment = 'changed comment'
        self.expected_ir_data['comment'] = new_comment
        self.experiment_metadata.lab_iso_request.comment = new_comment
        self._check_result(is_update_check=True)
        self._check_warning_messages('There are already experiment jobs for ' \
                                     'this metadata!')

    def test_with_compound(self):
        self.expected_ir_data['comment'] = 'opti with compound'
        self.expected_ir_data['label'] = 'opti_w_compounds'
        for pos_data in self.ir_layout_values.values():
            if pos_data[3] == None: pos_data[3] = 'None'
        self.ir_layout_values['B1'] = \
                [277700, 'fixed', 3.2, 560, 10, 'mix1', 1400, 4]
        self.ir_layout_values['E1'] = \
                [277700, 'fixed', 3.2, 1120, 20, 'mix1', 1400, 4]
        self.ir_layout_values['B2'] = \
                [277700, 'fixed', 3.2, 560, 10, 'sol2', 700, 4]
        self.ir_layout_values['E2'] = \
                [277700, 'fixed', 3.2, 1120, 20, 'sol2', 700, 4]
        self._continue_setup('with_compound.xls')
        self._check_result()
        self._check_warning_messages('Attention! There are compounds among ' \
                                     'your control molecule design pools.')

    def test_unsupported_type(self):
        self._test_unsupported_type()

    def test_invalid_input_values(self):
        self._test_invalid_input_values()

    def test_invalid_experiment_design(self):
        self._test_invalid_experiment_design('invalid_experiment_design.xls')

    def test_invalid_iso_request_sheet(self):
        self._continue_setup('invalid_iso_request.xls')
        self._test_and_expect_errors('There are errors in the ISO sheet.')

    def test_transfection_layout_finder_failure(self):
        self._continue_setup('finder_failure.xls')
        self._test_and_expect_errors('Could not obtain an ISO source layout ' \
                                     'from experiment design.')

    def test_invalid_pool_set(self):
        self._test_invalid_pool_set('invalid_pool_set.xls')

    def test_missing_pool_set(self):
        self._test_missing_pool_set('missing_pool_set.xls')

    def test_no_floatings_but_pool_set(self):
        self._test_no_floatings_but_pool_set('no_floatings_but_pool_set.xls')

    def test_associator_error(self):
        self._continue_setup('associator_error.xls')
        self._test_and_expect_errors('Error when trying to associate ISO ' \
                                     'source layout and design racks.')

    def test_ambigous_source_well(self):
        self._continue_setup('ambigous_source_well.xls')
        self._test_and_expect_errors('Each position in the ISO request ' \
                'layout must have a unique combination of the following ' \
                'factor levels')

    def test_above_stock_concentration(self):
        self._continue_setup('above_stock_concentration.xls')
        self._test_and_expect_errors('You have tried to order ISO ' \
                    'concentrations that are larger than the maximum ' \
                    'concentration')

    def test_robot_support_determiner_failure(self):
        self._continue_setup('support_determiner_failure.xls')
        self._test_and_expect_errors('Error when trying to determine ' \
                                     'mastermix support.')

    def test_worklist_generation_failure(self):
        self._test_worklist_generation_failure(
                                            'worklist_generation_failure.xls')

    def test_update_converter_error(self):
        self._test_update_converter_error()

    def test_update_changed_plate_set_label(self):
        self._test_update_changed_plate_set_label()

    def test_update_changed_iso_request_layout(self):
        self._test_update_changed_iso_request_layout()

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
                                    _ExperimentMetadataGeneratorTestCase):

    _TEST_FILE_SUBDIRECTORY = 'screen'
    _GENERATOR_CLS = ExperimentMetadataGeneratorScreen

    def set_up(self):
        _ExperimentMetadataGeneratorTestCase.set_up(self)
        self.experiment_type_id = EXPERIMENT_SCENARIOS.SCREENING
        self.update_file = 'update_with_isos.xls'
        self.number_rack_wls = 0
        self.expected_ir_data['label'] = 'screen_test'
        self.expected_ir_data['expected_number_isos'] = 4
        self.expected_ir_data['number_aliquots'] = 2
        self.expected_ir_data['comment'] = \
                                    'screening layout mastermix compatible'
        self.expected_ir_data['iso_plate_reservoir_specs'] = \
                                    get_reservoir_specs_standard_384()
        self.len_pool_set = 13
        self.number_experiment_design_wls = 4
        # pos label - pool, pos_type, iso vol, iso conc, final conc,
        # reagent name, reagent df, optimem dil factor
        self.ir_layout_values = dict(
            B3=[205200, 'fixed', 5, 560, 10, 'mix1', 140, 4],
            B4=[205200, 'fixed', 5, 1120, 20, 'mix1', 140, 4],
            B5=['md_001', 'floating', 5, 560, 10, 'mix1', 140, 4],
            B6=['md_001', 'floating', 5, 1120, 20, 'mix1', 140, 4],
            C3=[205201, 'fixed', 5, 560, 10, 'mix1', 140, 4],
            C4=[205201, 'fixed', 5, 1120, 20, 'mix1', 140, 4],
            C5=['md_002', 'floating', 5, 560, 10, 'mix1', 140, 4],
            C6=['md_002', 'floating', 5, 1120, 20, 'mix1', 140, 4],
            D3=[205200, 'fixed', 5, 560, 10, 'mix1', 140, 4],
            D4=[205200, 'fixed', 5, 1120, 20, 'mix1', 140, 4],
            D5=['md_003', 'floating', 5, 560, 10, 'mix1', 140, 4],
            D6=['md_003', 'floating', 5, 1120, 20, 'mix1', 140, 4],
            E3=[205201, 'fixed', 5, 560, 10, 'mix1', 140, 4],
            E4=[205201, 'fixed', 5, 1120, 20, 'mix1', 140, 4],
            E5=['md_004', 'floating', 5, 560, 10, 'mix1', 140, 4],
            E6=['md_004', 'floating', 5, 1120, 20, 'mix1', 140, 4],
            F3=['mock', 'mock', 5, 'None', 'None', 'mix1', 140, 4],
            F4=['mock', 'mock', 5, 'None', 'None', 'mix1', 140, 4],
            F5=['untreated', 'untreated', 'untreated', 'None', None,
                'untreated', 'untreated', None],
            F6=['untransfected', 'untransfected', 'untransfected',
                'None', None, 'untransfected', 'untransfected', None])

    def _check_experiment_design_tag(self, em):
        ed_domain = ExperimentDesignParserHandler.TAG_DOMAIN
        cell_tag1 = Tag(ed_domain, 'cell line', 'Line 1')
        cell_tag2 = Tag(ed_domain, 'cell line', 'Line 2')
        for design_rack in em.experiment_design.experiment_design_racks:
            pos_set1 = design_rack.rack_layout.get_positions_for_tag(cell_tag1)
            pos_set2 = design_rack.rack_layout.get_positions_for_tag(cell_tag2)
            if design_rack.label == '1':
                self.assert_equal(len(pos_set1), 20)
                self.assert_equal(len(pos_set2), 0)
            else:
                self.assert_equal(len(pos_set1), 0)
                self.assert_equal(len(pos_set2), 20)

    def test_result(self):
        # standard case, jobs go first
        self._continue_setup()
        self._check_result()
        self.assert_true(self.tool.supports_mastermix)

    def test_result_no_mastermix_support(self):
        for pos_data in self.ir_layout_values.values():
            if pos_data[0] in ('mock', 'untreated', 'untransfected'):
                pos_data[3] = None
                pos_data[4] = None
        self.number_experiment_design_wls = 2
        self.expected_ir_data['label'] = 'screen_no_mm'
        self.expected_ir_data['comment'] = \
                                    'screening layout no mastermix support'
        for result_data in self.ir_layout_values.values():
            if not TransfectionParameters.is_untreated_type(result_data[1]):
                result_data[2] = 1
        self._continue_setup('valid_file_no_mastermix_support.xls')
        self._check_result()
        self.assert_false(self.tool.supports_mastermix)
        self._check_warning_messages('Robot support is disabled now')

    def test_result_controls_last(self):
        pos_data_b4 = self.ir_layout_values['B4']
        self.ir_layout_values['B4'] = self.ir_layout_values['C3']
        self.ir_layout_values['C3'] = pos_data_b4
        pos_data_d4 = self.ir_layout_values['D4']
        self.ir_layout_values['D4'] = self.ir_layout_values['E3']
        self.ir_layout_values['E3'] = pos_data_d4
        self.expected_ir_data['label'] = 'scr_job_last'
        self.expected_ir_data['process_job_first'] = False
        self.expected_ir_data['comment'] = 'screening layout samples first'
        self._continue_setup('valid_file_controls_last.xls')
        self._check_result()

    def test_result_no_floatings(self):
        # 384 layout but no floating positions
        for pos_label in ('B5', 'B6', 'D5', 'D6'):
            pos_data = self.ir_layout_values[pos_label]
            pos_data[0] = 205202
            pos_data[1] = 'fixed'
        for pos_label in ('C5', 'C6', 'E5', 'E6'):
            pos_data = self.ir_layout_values[pos_label]
            pos_data[0] = 205203
            pos_data[1] = 'fixed'
        self.expected_ir_data['label'] = 'scr_no_floats'
        self.expected_ir_data['comment'] = 'screening layout without floatings'
        self.expected_ir_data['expected_number_isos'] = 1
        self.len_pool_set = 0
        self._continue_setup('valid_file_no_floatings.xls')
        self._check_result()

    def test_result_different_molecule_types(self):
        # siRNA and miRNAs, they have different optimem dilution factors, too
        for pos_data in self.ir_layout_values.values():
            if pos_data[0] == 205201:
                pos_data[0] = 330001
        self.expected_ir_data['label'] = 'scr_diff_mts'
        self.expected_ir_data['comment'] = 'screening layout different mts'
        self._continue_setup('valid_file_different_mts.xls')
        self._check_result()
        self._check_warning_messages('The OptiMem dilution factor for ' \
            'all positions has been set to 4, which is the default factor ' \
            'for the molecule type of the floating positions, although ' \
            'some fixed positions have different default factors: 3 ' \
            '(pools: 330001). If this is not suitable for your experiment, ' \
            'do not use robot-support for mastermix preparation.')

    def test_result_update_blocked_ISO_request(self):
        self._continue_setup_update(self.update_file, create_iso=True,
                                    create_experiment=False)
        self._check_result(is_update_check=True)
        self._check_warning_messages('The ISO generation for this experiment ' \
                                     'metadata has already started!')

    def test_result_update_blocked_experiment_design(self):
        self._continue_setup_update('update_with_experiments.xls',
                                    create_iso=True, create_experiment=True)
        new_comment = 'changed comment'
        self.expected_ir_data['comment'] = new_comment
        self.expected_ir_data['expected_number_isos'] = 3
        self.experiment_metadata.lab_iso_request.comment = new_comment
        self.len_pool_set = 10
        self._check_result(is_update_check=True)
        self._check_warning_messages('There are already experiment jobs for ' \
                                     'this metadata!')

    def test_with_compound(self):
        self.expected_ir_data['comment'] = 'screening with compounds'
        for pos_data in self.ir_layout_values.values():
            if pos_data[0] == 205200: pos_data[0] = 277700
            if pos_data[0] == 205201: pos_data[0] = 277701
        self._continue_setup('with_compound.xls')
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

    def test_invalid_input_values(self):
        self._test_invalid_input_values()

    def test_invalid_experiment_design(self):
        self._test_invalid_experiment_design('invalid_experiment_design.xls')

    def test_missing_iso_request_sheet(self):
        self._test_missing_iso_request_sheet('missing_iso_request.xls')

    def test_invalid_iso_request(self):
        self._test_invalid_iso_request('invalid_iso_request.xls')

    def test_robot_support_determiner_failure(self):
        self._continue_setup('support_determiner_failure.xls')
        self._test_and_expect_errors('Error when trying to determine ' \
                                     'mastermix support.')

    def test_invalid_pool_set(self):
        self._test_invalid_pool_set('invalid_pool_set.xls')

    def test_missing_pool_set(self):
        self._test_missing_pool_set('missing_pool_set.xls')

    def test_no_floatings_but_pool_set(self):
        self._test_no_floatings_but_pool_set('no_floatings_but_pool_set.xls')

    def test_worklist_generation_failure(self):
        self._test_worklist_generation_failure(
                                            'worklist_generation_failure.xls')

    def test_different_rack_shapes(self):
        self._continue_setup('different_rack_shapes.xls')
        self._test_and_expect_errors('The plate format for experiment design ' \
                        'and ISO do not match (ISO plate layout: 8x12, ' \
                        'experiment design: 16x24).')

    def test_update_converter_error(self):
        self._test_update_converter_error()

    def test_update_changed_plate_set_label(self):
        self._test_update_changed_plate_set_label()

    def test_update_changed_iso_request_layout(self):
        self._test_update_changed_iso_request_layout()

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
                                    _ExperimentMetadataGeneratorTestCase):

    _TEST_FILE_SUBDIRECTORY = 'library'
    _GENERATOR_CLS = ExperimentMetadataGeneratorLibrary

    def set_up(self):
        _ExperimentMetadataGeneratorTestCase.set_up(self)
        self.experiment_type_id = EXPERIMENT_SCENARIOS.LIBRARY
        self.update_file = 'update_with_isos.xls'
        self.number_experiment_design_wls = 4
        self.number_rack_wls = 0
        self.expected_ir_data['label'] = self.label
        self.expected_ir_data['comment'] = 'with mastermix support'
        self.expected_ir_data['iso_plate_reservoir_specs'] = \
                                        get_reservoir_specs_standard_384()
        lib = self._get_entity(IMoleculeDesignLibrary, 'poollib')
        self.expected_ir_data['molecule_design_library'] = lib
        self.iso_volume = 4
        self.iso_concentration = 1270
        self.optimem_df = 9.1
        self.reagent_name = 'RNAiMax'
        self.reagent_dil_factor = 1400
        self.final_concentration = 10
        # pos label, values: pool md
        self.ir_layout_values = dict(
                B2=330001, B15=330001, I10=330001, I22=330001,
                D2=205200, D15=205200, K10=205200, K22=205200,
                F2='mock', F15='mock', M10='mock', M22='mock',
                H2='untreated', H15='untreated',
                    O10='untreated', O22='untreated')

    def tear_down(self):
        _ExperimentMetadataGeneratorTestCase.tear_down(self)
        del self.iso_volume
        del self.iso_concentration
        del self.optimem_df
        del self.reagent_name
        del self.reagent_dil_factor
        del self.final_concentration

    def _test_and_expect_errors(self, msg=None):
        _ExperimentMetadataGeneratorTestCase._test_and_expect_errors(self,
                                                                    msg=msg)
        self.assert_is_none(self.tool.get_library())
        self.assert_is_none(self.tool.get_parameter_values())

    def _check_source_layout(self):
        tf_layout = self.tool.get_source_layout()
        self.assert_is_not_none(tf_layout)
        self.assert_equal(len(tf_layout), 292)
        investigated_pools = []
        for rack_pos, tf_pos in tf_layout.iterpositions():
            if not tf_pos.is_library:
                pool_id = self.ir_layout_values[rack_pos.label]
                self.assert_equal(pool_id, tf_pos.molecule_design_pool_id)
                investigated_pools.append(rack_pos.label)
            if tf_pos.is_untreated_type:
                self.assert_is_none(tf_pos.iso_volume)
                self.assert_is_none(tf_pos.iso_concentration)
                self.assert_is_none(tf_pos.optimem_dil_factor)
                pos_type = tf_pos.position_type
                self.assert_equal(tf_pos.reagent_name, pos_type)
                self.assert_equal(tf_pos.reagent_dil_factor, pos_type)
                self.assert_equal(tf_pos.final_concentration, pos_type)
                continue
            elif tf_pos.is_mock:
                self.assert_equal(tf_pos.final_concentration,
                                  tf_pos.position_type)
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
        self.assert_equal(len(investigated_pools), len(self.ir_layout_values))
        self.assert_equal(sorted(investigated_pools),
                          sorted(self.ir_layout_values.keys()))
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
        ed_domain = ExperimentDesignParserHandler.TAG_DOMAIN
        cell_tag1 = Tag(ed_domain, 'cell line', 'Line 1')
        cell_tag2 = Tag(ed_domain, 'cell line', 'Line 2')
        for design_rack in em.experiment_design.experiment_design_racks:
            pos_set1 = design_rack.rack_layout.get_positions_for_tag(cell_tag1)
            pos_set2 = design_rack.rack_layout.get_positions_for_tag(cell_tag2)
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
        self._continue_setup('valid_file_no_mastermix_support.xls')
        self.expected_ir_data['comment'] = 'no mastermix support'
        self.final_concentration = 5
        self.optimem_df = 18.1
        self.number_experiment_design_wls = 2
        self._check_result()
        self._check_warning_messages('Robot support for mastermix ' \
                                     'preparation is disabled')

    def test_result_with_compound(self):
        pos_labels = []
        for pos_label, pool_id in self.ir_layout_values.iteritems():
            if pool_id == 330001: pos_labels.append(pos_label)
        for pos_label in pos_labels:
            self.ir_layout_values[pos_label] = 277700
        self._continue_setup('with_compound.xls')
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

    def test_invalid_input_values(self):
        self._test_invalid_input_values()

    def test_invalid_experiment_design(self):
        self._test_invalid_experiment_design('invalid_experiment_design.xls')

    def test_missing_iso_request_sheet(self):
        self._test_missing_iso_request_sheet('missing_iso_request.xls')

    def test_invalid_iso_request(self):
        self._test_invalid_iso_request('invalid_iso_request.xls')

    def test_robot_support_determiner_failure(self):
        self._continue_setup('support_determiner_failure.xls')
        self._test_and_expect_errors('Error when trying to determine ' \
                                     'mastermix support.')

    def test_with_pool_set(self):
        self._test_with_pool_set('with_pool_set.xls')

    def test_worklist_generation_failure(self):
        self._test_worklist_generation_failure(
                                            'worklist_generation_failure.xls')

    def test_different_rack_shapes(self):
        self._continue_setup('different_rack_shapes.xls')
        self._test_and_expect_errors('The plate format for experiment design ' \
                        'and ISO do not match (ISO plate layout: 16x24, ' \
                        'experiment design: 8x12).')

    def test_update_converter_error(self):
        self._test_update_converter_error()

    def test_update_changed_iso_request_layout(self):
        self._test_update_changed_iso_request_layout()

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
                                    _ExperimentMetadataGeneratorTestCase):

    _TEST_FILE_SUBDIRECTORY = 'manual'
    _GENERATOR_CLS = ExperimentMetadataGeneratorManual

    def set_up(self):
        _ExperimentMetadataGeneratorTestCase.set_up(self)
        self.experiment_type_id = EXPERIMENT_SCENARIOS.MANUAL
        self.update_file = 'update_with_iso.xls'
        self.number_experiment_design_wls = 0
        self.number_rack_wls = 0
        self.expected_ir_data['label'] = 'man_test'
        self.expected_ir_data['comment'] = 'manual test case'
        self.expected_ir_data['iso_plate_reservoir_specs'] = \
                                            get_reservoir_specs_standard_96()
        # pos label - pool, pos_type, iso vol, iso conc, final conc,
        # reagent name, reagent df, optimem dil factor
        self.ir_layout_values = dict(
                B2=[205200, 'fixed', 10, 5000, None, None, None, None],
                B3=[205200, 'fixed', 1, 50000, None, None, None, None],
                C2=[330001, 'fixed', 20, 5000, None, None, None, None],
                D2=[1056000, 'fixed', 20, 5000, None, None, None, None])

    def _check_experiment_design_tag(self, em):
        ed_domain = ExperimentDesignParserHandler.TAG_DOMAIN
        cell_tag1 = Tag(ed_domain, 'cell line', 'Line 1')
        cell_tag2 = Tag(ed_domain, 'cell line', 'Line 2')
        for design_rack in em.experiment_design.experiment_design_racks:
            pos_set1 = design_rack.rack_layout.get_positions_for_tag(cell_tag1)
            pos_set2 = design_rack.rack_layout.get_positions_for_tag(cell_tag2)
            if design_rack.label == '1':
                self.assert_equal(len(pos_set1), 10)
                self.assert_equal(len(pos_set2), 0)
            else:
                self.assert_equal(len(pos_set1), 0)
                self.assert_equal(len(pos_set2), 10)

    def test_result(self):
        self._continue_setup()
        self._check_result()

    def test_result_volume_warning(self):
        self.expected_ir_data['iso_plate_reservoir_specs'] = \
                                                get_reservoir_specs_deep_96()
        self.ir_layout_values['B2'][2] = 5000
        self._continue_setup('valid_file_vol_warning.xls')
        self._check_result()
        self._check_warning_messages('The maximum ISO volume you have ' \
            'ordered (5000 ul) does not fit into the standard plates types ' \
            '(assumed here: Deepwell 96-well plate). Talk to the stock ' \
            'management, please.')

    def test_result_update_blocked_ISO_request(self):
        self._continue_setup_update(self.update_file, create_iso=True,
                                    create_experiment=False)
        self._check_result(is_update_check=True)
        self._check_warning_messages('The ISO generation for this experiment ' \
                                     'metadata has already started!')

    def test_result_update_blocked_experiment_design(self):
        self._continue_setup_update(self.VALID_FILE, create_iso=True,
                                    create_experiment=True)
        new_comment = 'changed comment'
        self.expected_ir_data['comment'] = new_comment
        self.experiment_metadata.lab_iso_request.comment = new_comment
        self._check_result(is_update_check=True)
        self._check_warning_messages('There are already experiment jobs for ' \
                                     'this metadata!')

    def test_with_compound(self):
        self.expected_ir_data['comment'] = 'manual with compound'
        self.ir_layout_values['C2'] = \
                        [277700, 'fixed', 20, 1000000, None, None, None, None]
        self._continue_setup('with_compound.xls')
        self._check_result()
        self._check_warning_messages('Attention! There are compounds among ' \
                                     'your control molecule design pools.')

    def test_unsupported_type(self):
        self._test_unsupported_type()

    def test_invalid_input_values(self):
        self._test_invalid_input_values()

    def test_invalid_experiment_design(self):
        self._test_invalid_experiment_design('invalid_experiment_design.xls')

    def test_missing_iso_request_sheet(self):
        self._test_missing_iso_request_sheet('missing_iso_sheet.xls')

    def test_invalid_iso_request(self):
        self._test_invalid_iso_request('invalid_iso_request.xls')

    def test_iso_volume_too_low(self):
        self._continue_setup('iso_volume_too_low.xls')
        self._test_and_expect_errors('The minimum ISO volume you can order ' \
                                     'is 1 ul.')

    def test_no_floatings_but_pool_set(self):
        self._continue_setup('no_floatings_but_pool_set.xls')
        self._test_and_expect_errors('There are molecule design pools for ' \
                    'floating positions specified. Floating positions are ' \
                    'not allowed for manual optimisation experiments!')

    def test_association_failure(self):
        self._continue_setup('association_failure.xls')
        self._test_and_expect_errors('Error when trying to associate ISO ' \
                                     'layout and design rack layouts.')

    def test_update_converter_error(self):
        self._test_update_converter_error()

    def test_update_changed_plate_set_label(self):
        self._test_update_changed_plate_set_label()

    def test_update_changed_iso_request_layout(self):
        self._test_update_changed_iso_request_layout(use_reagent_name=False)

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
                                    _ExperimentMetadataGeneratorTestCase):
    """
    This test case is special because we do not have an ISO request, ISO
    layout or worklists.
    """

    _TEST_FILE_SUBDIRECTORY = 'isoless'
    _GENERATOR_CLS = ExperimentMetadataGeneratorIsoless

    def set_up(self):
        _ExperimentMetadataGeneratorTestCase.set_up(self)
        self.experiment_type_id = EXPERIMENT_SCENARIOS.ISO_LESS

    def test_result(self):
        self._continue_setup()
        em = self.tool.get_result()
        self.assert_is_not_none(em)
        # check attributes
        self.assert_equal(em.number_replicates, self.number_replicates)
        self.assert_equal(em.label, self.label)
        self.assert_is_not_none(em.experiment_design)
        self.assert_equal(em.ticket_number, self.ticket_number)
        self.assert_is_none(em.lab_iso_request)
        self.assert_is_none(em.molecule_design_pool_set)
        self.assert_is_none(em.experiment_design.worklist_series)
        for design_rack in em.experiment_design.experiment_design_racks:
            self.assert_is_none(design_rack.worklist_series)

    def test_unsupported_type(self):
        self._test_unsupported_type()

    def test_invalid_input_values(self):
        self._test_invalid_input_values()

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
                                    _ExperimentMetadataGeneratorTestCase):

    _TEST_FILE_SUBDIRECTORY = 'order'
    _GENERATOR_CLS = ExperimentMetadataGeneratorOrder

    def set_up(self):
        _ExperimentMetadataGeneratorTestCase.set_up(self)
        self.update_file = 'update_with_isos.xls'
        self.experiment_type_id = EXPERIMENT_SCENARIOS.ORDER_ONLY
        self.expected_ir_data['label'] = 'all_sorts_of_pools'
        self.expected_ir_data['comment'] = 'ISO request without experiment'
        self.expected_ir_data['iso_plate_reservoir_specs'] = \
                                            get_reservoir_specs_standard_96()
        # pos label - pool, pos_type, iso vol, iso conc, final conc,
        # reagent name, reagent df, optimem dil factor
        self.ir_layout_values = dict(
                B2=[205201, 'fixed', 1, 50000, None, None, None, None],
                B4=[330001, 'fixed', 1, 10000, None, None, None, None],
                B6=[333803, 'fixed', 1, 5000000, None, None, None, None],
                B8=[1056000, 'fixed', 1, 10000, None, None, None, None],
                B10=[180202, 'fixed', 1, 100000, None, None, None, None])

    def _check_experiment_design_tag(self, experiment_metadata):
        pass # no experiment design

    def test_result(self):
        self._continue_setup()
        self._check_result()
        # check additional tag from ISO sheet
        irl = self.tool.return_value.lab_iso_request.rack_layout
        add_tag = Tag('transfection', 'molecule_type', 'siRNA pool')
        self._has_tag(irl, add_tag)
        self._check_warning_messages('Attention! There are compounds among ' \
                                     'your control molecule design pools.')

    def test_result_update(self):
        self._continue_setup_update(self.update_file, create_iso=True,
                                    create_experiment=False)
        self._check_result(is_update_check=True)
        irl = self.tool.return_value.lab_iso_request.rack_layout
        ori_tag = Tag('transfection', 'molecule_type', 'siRNA pool')
        new_tag = Tag('transfection', 'molecule_type', 'pool of siRNAs')
        self._has_tag(irl, ori_tag, expect_true=False)
        self._has_tag(irl, new_tag)
        self._check_warning_messages('The ISO generation for this experiment ' \
                                     'metadata has already started!')

    def test_unsupported_type(self):
        self._test_unsupported_type()

    def test_invalid_input_values(self):
        self._test_invalid_input_values()

    def test_missing_iso_request_sheet(self):
        self._test_missing_iso_request_sheet('missing_iso_sheet.xls')

    def test_invalid_iso_request(self):
        self._test_invalid_iso_request('invalid_iso_request.xls')

    def test_iso_volume_too_low(self):
        self._continue_setup('iso_volume_too_low.xls')
        self._test_and_expect_errors('The minimum ISO volume you can order ' \
             'is 1 ul. For some positions, you have ordered less: ' \
             '1056000 (B8, 0.5 ul), 180202 (B10, 0.5 ul), 333803 (B6, 0.5 ul)')

    def test_with_pool_set(self):
        self._test_with_pool_set('with_pool_set.xls')

    def test_update_converter_error(self):
        self._test_update_converter_error()

    def test_update_changed_plate_set_label(self):
        self._test_update_changed_plate_set_label()

    def test_update_changed_iso_request_layout(self):
        self._test_update_changed_iso_request_layout(use_reagent_name=False)
