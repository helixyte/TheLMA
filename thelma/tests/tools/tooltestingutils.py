"""
Utils for tool testing.
"""

from logging import config
from pkg_resources import resource_filename # pylint: disable=E0611,F0401
from pyramid.threadlocal import get_current_registry
from thelma import ThelmaLog
from thelma.automation.tools.semiconstants import clear_semiconstant_caches
from thelma.automation.tools.semiconstants import initialize_semiconstant_caches
from thelma.models.racklayout import RackLayout
from thelma.automation.tools.metadata.generation import ExperimentMetadataGenerator
from thelma.models.utils import get_user
from thelma.automation.tools.worklists.base \
    import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.tools.worklists.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.writers import LINEBREAK_CHAR
from thelma.interfaces import IMoleculeDesignPool
from thelma.interfaces import ITractor
from thelma.models.rack import RackPosition
from thelma.models.rack import RackPositionSet
from thelma.models.tagging import Tag
from thelma.models.tagging import TaggedRackPositionSet
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
        ThelmaLog.__init__(self, 'tool_tester', logging.WARNING)
        self.add_default_handlers()

    def add_default_handlers(self):
        """
        Generates handlers that are added automatically upon initialization.
        """

        file_name = CONF_FILE.split(':')
        conf_file = resource_filename(*file_name) # pylint: disable=W0142
        config.fileConfig(conf_file)
        logger = logging.getLogger('tooltesting')
        handlers = logger.handlers
        for handler in handlers:
            self.addHandler(handler)


class SilentLog(ThelmaLog):
    """
    A log that receives log messages but does not store them.
    """
    def __init__(self):
        ThelmaLog.__init__(self, 'silent_tool_tester', logging.WARNING)
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
        self.tool = None
        self.user = None
        self.executor_user = None
        self.pool_map = dict()

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.tool
        del self.user
        del self.executor_user
        del self.pool_map
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

    def _compare_tag_sets(self, exp_tags, tag_set):
        self.assert_equal(len(exp_tags), len(tag_set))
        for tag in tag_set:
            self.assert_true(isinstance(tag, Tag))
            self.assert_true(tag in exp_tags)

    def _compare_pos_sets(self, exp_positions, pos_set):
        self.assert_equal(len(exp_positions), len(pos_set))
        for pos in pos_set:
            self.assert_true(isinstance(pos, RackPosition))
            self.assert_true(pos in exp_positions)

    def _compare_sample_volume(self, sample, exp_volume_in_ul):
        vol = sample.volume * VOLUME_CONVERSION_FACTOR
        self.assert_equal(exp_volume_in_ul, vol)

    def _compare_transfer_volume(self, planned_transfer, exp_volume_in_ul):
        vol = planned_transfer.volume * VOLUME_CONVERSION_FACTOR
        self.assert_equal(exp_volume_in_ul, vol)

    def _compare_sample_and_pool(self, sample, md_pool, conc=None):
        pool_md_ids = []
        for md in md_pool.molecule_designs:
            pool_md_ids.append(md.id)
        sample_ids = []
        for sm in sample.sample_molecules:
            sample_ids.append(sm.molecule.molecule_design.id)
            if not conc is None:
                sm_conc = sm.concentration * CONCENTRATION_CONVERSION_FACTOR
                self.assert_true((sm_conc - conc) < 0.1)
                self.assert_true((sm_conc - conc) > -0.1)
        self.assert_equal(len(pool_md_ids), len(sample_ids))
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

    def _create_test_trp_set(self, tag_list, rack_positions):
        rps = RackPositionSet.from_positions(rack_positions)
        return TaggedRackPositionSet(set(tag_list), rps, self.user)

    def _test_and_expect_errors(self, msg=None):
        self._create_tool()
        result = self.tool.get_result()
        self.assert_is_none(result)
        if not msg is None: self._check_error_messages(msg)

    def _check_error_messages(self, msg):
        errors = self.tool.get_messages(logging.ERROR)
        error_msgs = ' '.join(errors)
        self.assert_true(msg in error_msgs)

    def _check_warning_messages(self, msg):
        warnings = ' '.join(self.tool.get_messages())
        self.assert_true(msg in warnings)

    def _check_executed_transfer(self, et, expected_type):
        self.assert_equal(et.type, expected_type)
        self.assert_equal(et.user, self.executor_user)
        self.assert_is_not_none(et.timestamp)


class FileReadingTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.stream = None
        self.VALID_FILE = None
        self.TEST_FILE_PATH = None

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.stream
        del self.VALID_FILE
        del self.TEST_FILE_PATH
        clear_semiconstant_caches()

    def _continue_setup(self, file_name=None):
        initialize_semiconstant_caches()
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
        except IOError:
            raise IOError('Unable to find file "%s"' % (complete_file))
        else:
            self.stream = stream.read()
            stream.close()


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

    def tear_down(self):
        FileReadingTestCase.tear_down(self)
        del self.experiment_metadata

    def _continue_setup(self, file_name=None):
        FileReadingTestCase._continue_setup(self, file_name=file_name)
        if self.experiment_metadata is None:
            self._set_experiment_metadadata()
            self.__read_experiment_metadata_file()

    def _set_experiment_metadadata(self):
        raise NotImplementedError('Abstract method')

    def __read_experiment_metadata_file(self):
        em_generator = ExperimentMetadataGenerator.create(stream=self.stream,
                      experiment_metadata=self.experiment_metadata,
                      requester=self.em_requester)
        self.experiment_metadata = em_generator.get_result()
        self.assert_is_not_none(self.experiment_metadata)


class TracToolTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.tractor_api = self.get_tractor_api()
        self.check_tractor_api(self.tractor_api)

    @classmethod
    def get_tractor_api(cls):
        reg = get_current_registry()
        return reg.getUtility(ITractor)

    @classmethod
    def check_tractor_api(cls, tractor_api):
        if not isinstance(tractor_api, DummyTractor):
            raise ValueError('The tractor API used for testing is not ' \
                             'a dummy!')

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

    def _get_expected_worklist_stream(self, csv_file_name):
        wl_file = self.WL_PATH + csv_file_name
        file_name = wl_file.split(':')
        f = resource_filename(*file_name) # pylint: disable=W0142
        stream = open(f, 'rb')
        return stream

    def _compare_csv_file_stream(self, tool_stream, csv_file_name):
        exp_stream = self._get_expected_worklist_stream(csv_file_name)
        tool_lines = FileComparisonUtils.convert_stream(tool_stream)
        exp_lines = FileComparisonUtils.convert_stream(exp_stream)
        self.assert_equal(len(tool_lines), len(exp_lines))
        for i in range(len(tool_lines)):
            t_lin = FileComparisonUtils.convert_to_list(tool_lines[i])
            e_lin = FileComparisonUtils.convert_to_list(exp_lines[i])
            self.assert_equal(t_lin, e_lin)

    def _compare_csv_file_content(self, tool_content, csv_file_name):
        exp_stream = self._get_expected_worklist_stream(csv_file_name)
        tool_lines = FileComparisonUtils.convert_content(tool_content)
        exp_lines = FileComparisonUtils.convert_stream(exp_stream)
        self.assert_equal(len(tool_lines), len(exp_lines))
        for i in range(len(tool_lines)):
            t_lin = FileComparisonUtils.convert_to_list(tool_lines[i])
            te_lin = FileComparisonUtils.convert_to_list(exp_lines[i])
            self.assert_equal(t_lin, te_lin)

    def _compare_txt_file_content(self, tool_content, txt_file_name,
                                  ignore_lines=None):
        exp_stream = self._get_expected_worklist_stream(txt_file_name)
        tool_lines = FileComparisonUtils.convert_content(tool_content)
        exp_lines = FileComparisonUtils.convert_stream(exp_stream)
        self.assert_equal(len(tool_lines), len(exp_lines))
        for i in range(len(tool_lines)):
            if not ignore_lines is None and i in ignore_lines: continue
            t_lin = tool_lines[i].strip()
            e_lin = exp_lines[i].strip()
            self.assert_equal(t_lin, e_lin)

    def _compare_txt_file_content_without_order(self, tool_content,
                                                txt_file_name):
        exp_stream = self._get_expected_worklist_stream(txt_file_name)
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
