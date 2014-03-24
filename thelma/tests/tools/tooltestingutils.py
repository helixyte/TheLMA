"""
Utils for tool testing.
"""

from pkg_resources import resource_filename # pylint: disable=E0611,F0401
from pyramid.threadlocal import get_current_registry
from thelma import ThelmaLog
from thelma.automation.semiconstants import clear_semiconstant_caches
from thelma.automation.semiconstants import initialize_semiconstant_caches
from tractor import create_wrapper_for_ticket_creation
from thelma.automation.tools.metadata.generation \
    import ExperimentMetadataGenerator
from thelma.automation.tools.writers import LINEBREAK_CHAR
from thelma.automation.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.utils.base import get_converted_number
from thelma.interfaces import IMoleculeDesignPool
from thelma.interfaces import ITractor
from thelma.models.rack import RackPosition
from thelma.models.racklayout import RackLayout
from thelma.models.sample import StockSample
from thelma.models.tagging import Tag
from thelma.models.tagging import TaggedRackPositionSet
from thelma.models.utils import get_user
from thelma.testing import ThelmaModelTestCase
from tractor.api import DummyTractor
import logging
import zipfile


CONF_FILE = 'thelma:tests/tools/logging.conf'


class TestingLog(ThelmaLog):
    """
    A log that directs all messages to the console.
    """

    def __init__(self):
        ThelmaLog.__init__(self, 'tool_tester', log_level=logging.WARNING)


class SilentLog(ThelmaLog):
    """
    A log that receives log messages but does not store them.
    """
    def __init__(self):
        ThelmaLog.__init__(self, 'silent_tool_tester',
                           log_level=logging.WARNING)
        self.addHandler(logging.NullHandler())


class FileComparisonUtils(object):
    """
    Methods for file comparison.
    """

    @classmethod
    def convert_to_list(cls, csv_line):
        value_list = []
        tokens = []
        if ',' in csv_line: tokens = csv_line.split(',')
        if ';' in csv_line: tokens = csv_line.split(';')
        for token in tokens:
            token = token.strip()
            if token.startswith('"'): token = token[1:]
            if token.endswith('"'): token = token[:-1]
            if token.endswith('.0'): token = token[:-2]
            value_list.append(token)
        return value_list

    @classmethod
    def convert_stream(cls, stream):
        file_content = stream.read()
        stripped_lines = cls.convert_content(file_content)
        return stripped_lines

    @classmethod
    def convert_content(cls, file_content):
        stripped_lines = []
        linebreak_char = LINEBREAK_CHAR
        if not linebreak_char in file_content:
            linebreak_char = '\n'
        for r_line in file_content.split(linebreak_char):
            r_line.strip()
            if len(r_line) < 1: continue
            stripped_lines.append(r_line)
        return stripped_lines


class ToolsAndUtilsTestCase(ThelmaModelTestCase):

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        initialize_semiconstant_caches()
        self.tool = None
        self.user = None
        self.executor_user = None
        self.pool_map = dict()
        self.supplier = self._create_organization(name='testsupplier')

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.tool
        del self.user
        del self.executor_user
        del self.pool_map
        del self.supplier
        clear_semiconstant_caches()

    def _create_tool(self):
        self.tool = None

    def _get_pool(self, pool_id):
        if not isinstance(pool_id, int): return pool_id
        if self.pool_map.has_key(pool_id):
            return self.pool_map[pool_id]
        pool = self._get_entity(IMoleculeDesignPool, str(pool_id))
        if pool is None:
            raise ValueError('Unknown pool ID: %s' % (pool_id))
        self.pool_map[pool_id] = pool
        return pool

    def _create_test_sample(self, container, pool, volume,
                            target_conc, is_stock_sample=False):
        # vol in ul, conc in nM
        vol = volume / VOLUME_CONVERSION_FACTOR
        if is_stock_sample:
            conc = target_conc / CONCENTRATION_CONVERSION_FACTOR
            sample = StockSample(volume=vol, container=container,
                             molecule_design_pool=pool,
                             supplier=self.supplier,
                             molecule_type=pool.molecule_type,
                             concentration=conc)
            container.sample = sample
        else:
            sample = container.make_sample(vol)
        if not pool is None and len(sample.sample_molecules) < 1:
            md_conc = target_conc / pool.number_designs \
                      / CONCENTRATION_CONVERSION_FACTOR
            for md in pool:
                mol = self._create_molecule(molecule_design=md,
                                            supplier=self.supplier)
                sample.make_sample_molecule(molecule=mol, concentration=md_conc)
        return sample

    def _compare_tag_sets(self, exp_tags, tag_set):
        self.assert_equal(len(exp_tags), len(tag_set))
        for tag in tag_set:
            self.assert_true(isinstance(tag, Tag))
            if not tag in exp_tags:
                msg = 'Tag "%s" is missing in the expected tag set (%s).' \
                      % (tag, exp_tags)
                raise AssertionError(msg)

    def _compare_pos_sets(self, exp_positions, pos_set):
        self.assert_equal(len(exp_positions), len(pos_set))
        exp_pos_labels = set()
        for pos in exp_positions:
            if isinstance(pos, RackPosition):
                exp_pos_labels.add(pos.label.lower())
            else:
                exp_pos_labels.add(pos.lower())
        for pos in pos_set:
            self.assert_true(isinstance(pos, RackPosition))
            if not pos.label.lower() in exp_pos_labels:
                msg = 'Position %s is missing in the expected set (%s).' \
                      % (pos.label, exp_pos_labels)
                raise AssertionError(msg)

    def _compare_sample_volume(self, sample, exp_volume_in_ul,
                               sample_info=None):
        if sample is None and not sample_info is None:
            msg = 'The sample for %s is missing!' % (sample_info)
            raise AssertionError(msg)
        vol = sample.volume * VOLUME_CONVERSION_FACTOR
        diff = exp_volume_in_ul - vol
        if diff < -0.1 or diff > 0.1:
            if sample_info is None:
                self.assert_equal(exp_volume_in_ul, vol)
            else:
                msg = 'Unexpected volume in %s!\nExpected: %s ul\nFound: %s ul' \
                      % (sample_info, get_converted_number(exp_volume_in_ul),
                         get_converted_number(vol))
                raise AssertionError(msg)

    def _compare_transfer_volume(self, planned_transfer, exp_volume_in_ul):
        vol = planned_transfer.volume * VOLUME_CONVERSION_FACTOR
        self.assert_equal(exp_volume_in_ul, vol)

    def _compare_sample_and_pool(self, sample, md_pool, conc=None,
                                 sample_info=None):
        pool_md_ids = []
        for md in md_pool.molecule_designs:
            pool_md_ids.append(md.id)
        sample_ids = []
        for sm in sample.sample_molecules:
            sample_ids.append(sm.molecule.molecule_design.id)
            if not conc is None:
                sm_conc = sm.concentration * CONCENTRATION_CONVERSION_FACTOR
                if sample_info is None:
                    self.assert_true((sm_conc - conc) < 0.1)
                    self.assert_true((sm_conc - conc) > -0.1)
                else:
                    diff = sm_conc - conc
                    if diff < -0.1 or diff > 0.1:
                        msg = 'The molecule design concentrations for ' \
                              'pool %i (%s) differ.\nExpected: %s\n' \
                              'Found: %s' % (md_pool.id, sample_info,
                               conc, sm_conc)
                        raise AssertionError(msg)
        if sample_info is not None:
            if not sorted(pool_md_ids) == sorted(sample_ids):
                msg = 'The molecule designs for pool %i (%s) differ.\n' \
                      'Expected: %s\nFound: %s' % (md_pool.id, sample_info,
                       '-'.join([str(i) for i in pool_md_ids]),
                       '-'.join([str(i) for i in sample_ids]))
                raise AssertionError(msg)
        else:
            self.assert_equal(sorted(pool_md_ids), sorted(sample_ids))

    def _has_tag(self, trp_sets_or_rack_rack_layout, tag, expect_true=True):
        if isinstance(trp_sets_or_rack_rack_layout, TaggedRackPositionSet):
            trp_sets = trp_sets_or_rack_rack_layout
        elif isinstance(trp_sets_or_rack_rack_layout, RackLayout):
            trp_sets = trp_sets_or_rack_rack_layout.tagged_rack_position_sets
        else:
            raise TypeError('Expect TaggedRackPositionSet list or RackLayout!')
        has_tag = False
        for trps in trp_sets:
            for trps_tag in trps.tags:
                if tag == trps_tag:
                    has_tag = True
                    break
            if has_tag: break
        if expect_true:
            self.assert_true(has_tag)
        else:
            self.assert_false(has_tag)

    def _test_and_expect_errors(self, msg=None):
        self._create_tool()
        result = self.tool.get_result()
        self.assert_is_none(result)
        if not msg is None: self._check_error_messages(msg)

    def _expect_error(self, error_cls, callable_obj, exp_msg, *args, **kw):
        try:
            callable_obj(*args, **kw)
        except StandardError as e:
            if not isinstance(e, error_cls):
                msg = 'Wrong error class. Expected: %s, got: %s. \nMsg: %s' \
                      % (error_cls.__name__, e.__class__.__name__, str(e))
                raise AssertionError(msg)
            got_msg = str(e)
            if not exp_msg in got_msg:
                msg = 'Unable to find expected message.\nExpected: "%s".' \
                      '\nFound: "%s".' % (exp_msg, got_msg)
                raise AssertionError(msg)
        else:
            raise AssertionError('No error has been raised!')

    def _check_error_messages(self, exp_msg):
        errors = self.tool.get_messages(logging.ERROR)
        error_msgs = '\n'.join(errors)
        if not exp_msg in error_msgs:
            msg = 'Could not find error message.\nExpected: %s\nFound: %s' \
                  % (exp_msg, error_msgs)
            raise AssertionError(msg)

    def _check_warning_messages(self, exp_msg):
        warnings = '\n'.join(self.tool.get_messages())
        if not exp_msg in warnings:
            msg = 'Could not find warning message.\nExpected: %s\nFound: %s' \
                  % (exp_msg, warnings)
            raise AssertionError(msg)

    def _check_executed_transfer(self, et, expected_type):
        self.assert_equal(et.transfer_type, expected_type)
        self.assert_equal(et.user, self.executor_user)
        self.assert_is_not_none(et.timestamp)

    def _compare_layout_value(self, exp_value, attr_name, pool_pos,
                               layout_name):
        found_value = getattr(pool_pos, attr_name)
        pos_label = pool_pos.rack_position.label
        if attr_name == 'molecule_design_pool':
            exp_value = self._get_pool(exp_value)
        elif attr_name == 'transfer_targets':
            exp_value.sort()
            found_value.sort()
        if not exp_value == found_value:
            msg = 'The values for the %s attribute of position %s in ' \
                  'layout %s are not equal.\nExpected: %s.\nFound: %s.' \
                  % (attr_name, pos_label, layout_name, exp_value, found_value)
            raise AssertionError(msg)


class FileReadingTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.stream = None
        self.VALID_FILE = None
        self.TEST_FILE_PATH = None

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        try:
            del self.stream
        except AttributeError:
            pass
        del self.VALID_FILE
        del self.TEST_FILE_PATH

    def _continue_setup(self, file_name=None):
        self.__read_file(file_name)

    def _test_invalid_file(self, file_name, msg):
        self._continue_setup(file_name)
        self._test_and_expect_errors(msg)

    def __read_file(self, file_name):
        if file_name is None: file_name = self.VALID_FILE
        complete_file = self.TEST_FILE_PATH + file_name
        file_name = complete_file.split(':')
        f = resource_filename(*file_name) # pylint: disable=W0142
        try:
            stream = open(f, 'rb')
            self.stream = stream.read()
        except IOError:
            raise IOError('Unable to find file "%s"' % (complete_file))
        finally:
            if not stream is None: stream.close()


class ParsingTestCase(FileReadingTestCase):

    _PARSER_CLS = None

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.log = TestingLog()

    def tear_down(self):
        FileReadingTestCase.tear_down(self)
        del self.log

    def _continue_setup(self, file_name=None):
        FileReadingTestCase._continue_setup(self, file_name)
        self._create_tool()

    def _test_if_result(self):
        self._continue_setup()
        self.assert_is_none(self.tool.parser)
        no_result = self.tool.get_result(run=False)
        self.assert_is_none(no_result)
        self.assert_is_none(self.tool.parser)
        result = self.tool.get_result()
        self.assert_is_not_none(result)
        self.assert_equal(self.tool.parser.__class__, self._PARSER_CLS)


class ExperimentMetadataReadingTestCase(FileReadingTestCase):

    def set_up(self):
        FileReadingTestCase.set_up(self)
        self.experiment_metadata = None
        self.em_requester = get_user('it')
        self.raise_error = True # raises an error if the experiment metadata
        # reading fails

    def tear_down(self):
        FileReadingTestCase.tear_down(self)
        del self.experiment_metadata
        del self.raise_error

    def _continue_setup(self, file_name=None):
        FileReadingTestCase._continue_setup(self, file_name=file_name)
        if self.experiment_metadata is None:
            self._set_experiment_metadadata()
            generator = self.__read_experiment_metadata_file()
            return generator

    def _set_experiment_metadadata(self):
        raise NotImplementedError('Abstract method')

    def __read_experiment_metadata_file(self):
        em_generator = ExperimentMetadataGenerator.create(stream=self.stream,
                       experiment_metadata=self.experiment_metadata,
                       requester=self.em_requester, log=SilentLog())
        self.experiment_metadata = em_generator.get_result()
        if self.raise_error: self.assert_is_not_none(self.experiment_metadata)
        return em_generator


class TracToolTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.tractor_api = None
        self.set_up_as_add_on()

    def set_up_as_add_on(self):
        self.tractor_api = self.get_tractor_api()
        self.check_tractor_api(self.tractor_api)

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        self.tear_down_as_add_on()

    def tear_down_as_add_on(self):
        del self.tractor_api

    @classmethod
    def get_tractor_api(cls):
        reg = get_current_registry()
        return reg.getUtility(ITractor)

    @classmethod
    def check_tractor_api(cls, tractor_api):
        if not isinstance(tractor_api, DummyTractor):
            raise TypeError('The tractor API used for testing is not ' \
                            'a dummy!')

    def _get_ticket(self):
        ticket_wrapper = create_wrapper_for_ticket_creation(
                            summary='test_ticket', description='test ticket')
        return self.tractor_api.create_ticket(notify=True,
                                 ticket_wrapper=ticket_wrapper)

    def _test_and_expect_errors(self, msg=None):
        self._create_tool()
        self.tool.send_request()
        self.assert_false(self.tool.transaction_completed())
        if not msg is None: self._check_error_messages(msg)


class FileCreatorTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.WL_PATH = None

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.WL_PATH

    def _get_expected_file_stream(self, csv_file_name):
        wl_file = self.WL_PATH + csv_file_name
        file_name = wl_file.split(':')
        f = resource_filename(*file_name) # pylint: disable=W0142
        stream = open(f, 'rb')
        return stream

    def _compare_csv_file_stream(self, tool_stream, csv_file_name,
                                 ignore_columns=None):
        exp_stream = self._get_expected_file_stream(csv_file_name)
        tool_lines = FileComparisonUtils.convert_stream(tool_stream)
        exp_lines = FileComparisonUtils.convert_stream(exp_stream)
        self.assert_equal(len(tool_lines), len(exp_lines))
        for i in range(len(tool_lines)):
            t_lin = FileComparisonUtils.convert_to_list(tool_lines[i])
            e_lin = FileComparisonUtils.convert_to_list(exp_lines[i])
            if not ignore_columns is None:
                for column_index in ignore_columns:
                    del t_lin[column_index]
                    del e_lin[column_index]
            self.assert_equal(t_lin, e_lin)

    def _compare_csv_file_content(self, tool_content, csv_file_name):
        exp_stream = self._get_expected_file_stream(csv_file_name)
        tool_lines = FileComparisonUtils.convert_content(tool_content)
        exp_lines = FileComparisonUtils.convert_stream(exp_stream)
        self.assert_equal(len(tool_lines), len(exp_lines))
        for i in range(len(tool_lines)):
            t_lin = FileComparisonUtils.convert_to_list(tool_lines[i])
            te_lin = FileComparisonUtils.convert_to_list(exp_lines[i])
            self.assert_equal(t_lin, te_lin)

    def _compare_txt_file_content(self, tool_content, txt_file_name,
                                  ignore_lines=None):
        exp_stream = self._get_expected_file_stream(txt_file_name)
        tool_lines = FileComparisonUtils.convert_content(tool_content)
        exp_lines = FileComparisonUtils.convert_stream(exp_stream)
        if ignore_lines is None:
            self.assert_equal(len(tool_lines), len(exp_lines))
        for i in range(len(tool_lines)):
            if not ignore_lines is None and i in ignore_lines: continue
            t_lin = tool_lines[i].strip()
            e_lin = exp_lines[i].strip()
            self.assert_equal(t_lin, e_lin)

    def _compare_txt_file_content_without_order(self, tool_content,
                                                txt_file_name):
        exp_stream = self._get_expected_file_stream(txt_file_name)
        tool_lines = FileComparisonUtils.convert_content(tool_content)
        exp_lines = FileComparisonUtils.convert_stream(exp_stream)
        self.assert_equal(len(tool_lines), len(exp_lines))
        for t_lin in tool_lines: self.assert_true(t_lin in exp_lines)
        for e_lin in exp_lines: self.assert_true(e_lin in tool_lines)

    def _compare_txt_file_stream(self, tool_stream, txt_file_name,
                                 ignore_lines=None):
        tool_content = tool_stream.read()
        self._compare_txt_file_content(tool_content, txt_file_name,
                                       ignore_lines)

    def _get_zip_archive(self, zip_stream):
        return zipfile.ZipFile(zip_stream, 'a', zipfile.ZIP_DEFLATED, False)
