"""
Testing the thelma log.

AAB
"""
from thelma.automation.errors import ErrorRecording
from thelma.testing import ThelmaModelTestCase
from thelma.tests.tools.tooltestingutils import TestingLog
import logging


class ErrorRecordingExampleClass(ErrorRecording):

    NAME = 'testtool'

    DEBUG_MSG_IN = 'debug_msg'
    INFO_MSG_IN = 'info_msg'
    WARN_MSG_IN = 'warning_msg'
    ERR_MSG_IN = 'error_msg'
    CRIT_MSG_IN = 'critical_error_msg'

    DEBUG_MSG_OUT = '%s - %s' % (NAME, DEBUG_MSG_IN)
    INFO_MSG_OUT = '%s - %s' % (NAME, INFO_MSG_IN)
    WARN_MSG_OUT = '%s - %s' % (NAME, WARN_MSG_IN)
    ERR_MSG_OUT = '%s - %s' % (NAME, ERR_MSG_IN)
    CRIT_MSG_OUT = '%s - %s' % (NAME, CRIT_MSG_IN)


    def __init__(self):
        ErrorRecording.__init__(self, TestingLog(), logging.WARNING, False)
        self.nested = None

    def run(self):
        self.add_debug(self.DEBUG_MSG_IN)
        self.add_info(self.INFO_MSG_IN)
        self.add_warning(self.WARN_MSG_IN)
        self.add_error(self.ERR_MSG_IN)
        self.add_critical_error(self.CRIT_MSG_IN)


class NestedErrorRecordingExampleClass(ErrorRecording):

    NAME = 'nestedtesttool'

    WARN_MSG_OUT = '%s - %s' % (NAME, ErrorRecordingExampleClass.WARN_MSG_IN)
    ERR_MSG_OUT = '%s - %s' % (NAME, ErrorRecordingExampleClass.ERR_MSG_IN)
    CRIT_MSG_OUT = '%s - %s' % (NAME, ErrorRecordingExampleClass.CRIT_MSG_IN)

    def __init__(self, log):
        ErrorRecording.__init__(self, log)

    def run(self):
        self.add_warning(ErrorRecordingExampleClass.WARN_MSG_IN)
        self.add_error(ErrorRecordingExampleClass.ERR_MSG_IN)
        self.add_critical_error(ErrorRecordingExampleClass.CRIT_MSG_IN)


class ErrorRecordingTestCase(ThelmaModelTestCase):

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.test_class = ErrorRecordingExampleClass()
        self.test_class.run()
        self.DEBUG_MSG_IN = ErrorRecordingExampleClass.DEBUG_MSG_IN
        self.DEBUG_MSG_OUT = ErrorRecordingExampleClass.DEBUG_MSG_OUT
        self.INFO_MSG_IN = ErrorRecordingExampleClass.INFO_MSG_IN
        self.INFO_MSG_OUT = ErrorRecordingExampleClass.INFO_MSG_OUT
        self.WARN_MSG_IN = ErrorRecordingExampleClass.WARN_MSG_IN
        self.WARN_MSG_OUT = ErrorRecordingExampleClass.WARN_MSG_OUT
        self.ERR_MSG_IN = ErrorRecordingExampleClass.ERR_MSG_IN
        self.ERR_MSG_OUT = ErrorRecordingExampleClass.ERR_MSG_OUT
        self.CRIT_MSG_IN = ErrorRecordingExampleClass.CRIT_MSG_IN
        self.CRIT_MSG_OUT = ErrorRecordingExampleClass.CRIT_MSG_OUT

        self.ALL = [self.DEBUG_MSG_OUT, self.INFO_MSG_OUT, self.WARN_MSG_OUT,
                    self.ERR_MSG_OUT, self.CRIT_MSG_OUT]

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.test_class
        del self.DEBUG_MSG_IN
        del self.DEBUG_MSG_OUT
        del self.INFO_MSG_IN
        del self.INFO_MSG_OUT
        del self.WARN_MSG_IN
        del self.WARN_MSG_OUT
        del self.ERR_MSG_IN
        del self.ERR_MSG_OUT
        del self.CRIT_MSG_IN
        del self.CRIT_MSG_OUT
        del self.ALL

    def test_has_errors(self):
        self.assert_true(self.test_class.has_errors())
        self.assert_equal(self.test_class.has_errors(), 2)

    def test_get_messages(self):
        debug_msgs = self.test_class.get_messages(logging.DEBUG)
        self.assert_equal(len(debug_msgs), 5)
        for msg in self.ALL: self.assert_true(msg in debug_msgs)
        info_msgs = self.test_class.get_messages(logging.INFO)
        self.assert_equal(len(info_msgs), 4)
        self.assert_true(self.INFO_MSG_OUT in info_msgs)
        self.assert_false(self.DEBUG_MSG_OUT in info_msgs)
        warn_msgs = self.test_class.get_messages(logging.WARNING)
        self.assert_equal(len(warn_msgs), 3)
        self.assert_true(self.WARN_MSG_OUT in warn_msgs)
        self.assert_false(self.INFO_MSG_OUT in warn_msgs)
        err_msgs = self.test_class.get_messages(logging.ERROR)
        self.assert_equal(len(err_msgs), 2)
        self.assert_true(self.ERR_MSG_OUT in err_msgs)
        self.assert_false(self.WARN_MSG_OUT in err_msgs)
        crit_msgs = self.test_class.get_messages(logging.CRITICAL)
        self.assert_equal(len(crit_msgs), 1)
        self.assert_true(self.CRIT_MSG_OUT in crit_msgs)
        self.assert_false(self.ERR_MSG_OUT in crit_msgs)
        no_msgs = self.test_class.get_messages(60)
        self.assert_equal(len(no_msgs), 0)

    def test_reset_log(self):
        self.assert_true(self.test_class.has_errors())
        messages1 = self.test_class.get_messages(logging.WARNING)
        self.assert_equal(len(messages1), 3)
        self.test_class.reset_log()
        self.assert_false(self.test_class.has_errors())
        messages2 = self.test_class.get_messages(logging.WARNING)
        self.assert_equal(len(messages2), 0)

    def test_add_critical(self):
        messages1 = self.test_class.get_messages(logging.CRITICAL)
        self.assert_equal(self.test_class.has_errors(), 2)
        self.assert_equal(len(messages1), 1)
        self.assert_true(self.CRIT_MSG_OUT in messages1)
        msg2 = 'crit2'
        self.test_class.add_critical_error(msg2)
        messages2 = self.test_class.get_messages(logging.CRITICAL)
        self.assert_equal(self.test_class.has_errors(), 3)
        self.assert_equal(len(messages2), 2)
        self.assert_true(self.CRIT_MSG_OUT in messages2)
        event_msg = '%s - %s' % (ErrorRecordingExampleClass.NAME, msg2)
        self.assert_true(event_msg in messages2)

    def test_add_error(self):
        messages1 = self.test_class.get_messages(logging.ERROR)
        self.assert_equal(self.test_class.has_errors(), 2)
        self.assert_equal(len(messages1), 2)
        self.assert_true(self.ERR_MSG_OUT in messages1)
        msg2 = 'err2'
        self.test_class.add_error(msg2)
        messages2 = self.test_class.get_messages(logging.ERROR)
        self.assert_equal(self.test_class.has_errors(), 3)
        self.assert_equal(len(messages2), 3)
        self.assert_true(self.ERR_MSG_OUT in messages2)
        event_msg = '%s - %s' % (ErrorRecordingExampleClass.NAME, msg2)
        self.assert_true(event_msg in messages2)

    def test_add_warning(self):
        messages1 = self.test_class.get_messages(logging.WARNING)
        self.assert_equal(self.test_class.has_errors(), 2)
        self.assert_equal(len(messages1), 3)
        self.assert_true(self.WARN_MSG_OUT in messages1)
        msg2 = 'warn2'
        self.test_class.add_warning(msg2)
        messages2 = self.test_class.get_messages(logging.WARNING)
        self.assert_equal(self.test_class.has_errors(), 2)
        self.assert_equal(len(messages2), 4)
        self.assert_true(self.WARN_MSG_OUT in messages2)
        event_msg = '%s - %s' % (ErrorRecordingExampleClass.NAME, msg2)
        self.assert_true(event_msg in messages2)

    def test_add_info(self):
        messages1 = self.test_class.get_messages(logging.INFO)
        self.assert_equal(self.test_class.has_errors(), 2)
        self.assert_equal(len(messages1), 4)
        self.assert_true(self.INFO_MSG_OUT in messages1)
        msg2 = 'info2'
        self.test_class.add_info(msg2)
        messages2 = self.test_class.get_messages(logging.INFO)
        self.assert_equal(self.test_class.has_errors(), 2)
        self.assert_equal(len(messages2), 5)
        self.assert_true(self.INFO_MSG_OUT in messages1)
        event_msg = '%s - %s' % (ErrorRecordingExampleClass.NAME, msg2)
        self.assert_true(event_msg in messages2)

    def test_add_debug(self):
        messages1 = self.test_class.get_messages(logging.DEBUG)
        self.assert_equal(self.test_class.has_errors(), 2)
        self.assert_equal(len(messages1), 5)
        self.assert_true(self.DEBUG_MSG_OUT in messages1)
        msg2 = 'debug2'
        self.test_class.add_debug(msg2)
        messages2 = self.test_class.get_messages(logging.DEBUG)
        self.assert_equal(self.test_class.has_errors(), 2)
        self.assert_equal(len(messages2), 6)
        self.assert_true(self.DEBUG_MSG_OUT in messages2)
        event_msg = '%s - %s' % (ErrorRecordingExampleClass.NAME, msg2)
        self.assert_true(event_msg in messages2)

    def test_nested_errors(self):
        m1 = self.test_class.get_messages(logging.WARNING)
        self.assert_true(self.test_class.has_errors())
        self.assert_equal(len(m1), 3)
        self.test_class.reset_log()
        m2 = self.test_class.get_messages(logging.WARNING)
        self.assert_false(self.test_class.has_errors())
        self.assert_equal(len(m2), 0)
        nested = NestedErrorRecordingExampleClass(self.test_class.log)
        m3 = self.test_class.get_messages(logging.WARNING)
        self.assert_false(self.test_class.has_errors())
        self.assert_equal(len(m3), 0)
        nested.run()
        m4 = self.test_class.get_messages(logging.WARNING)
        self.assert_false(self.test_class.has_errors())
        self.assert_equal(len(m4), 3)
        self.test_class.run()
        m5 = self.test_class.get_messages(logging.WARNING)
        self.assert_true(self.test_class.has_errors())
        self.assert_equal(len(m5), 6)
        nested.run()
        m6 = self.test_class.get_messages(logging.WARNING)
        self.assert_true(self.test_class.has_errors())
        self.assert_equal(len(m6), 9)
