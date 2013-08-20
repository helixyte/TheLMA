"""
:Date: 02 aug 2011
:Author: AAB, berger at cenix-bioscience dot com
"""

from thelma import ThelmaLog
from thelma.automation.errors import EventRecording
from thelma.automation.tools.semiconstants import clear_semiconstant_caches
from thelma.automation.tools.semiconstants import initialize_semiconstant_caches

__docformat__ = 'reStructuredText en'

__all__ = ['BaseAutomationTool']


class BaseAutomationTool(EventRecording):
    """
    This is an abstract base class. For all helper and automation tools.
    Its main purpose is to provide logging and registration attributes.
    """

    #: The name of the automation tool.
    NAME = None

    def __init__(self, log=None,
                 logging_level=None,
                 add_default_handlers=False,
                 depending=True):
        """
        Constructor:

        :param log: The ThelmaLog you want to write into. If the
            log is None, the object will create a new log.
        :type log: :class:`thelma.ThelmaLog`

        :param logging_level: defines the least severe level of logging
                    event the log will record

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`

        :param depending: Defines whether a tool can be initialized directly
            (*False*) of if it is always called by other tools (*True*).
            Depending tools cannot initialize and reset logs but must
            return a external one.
        :type depending: :class:`bool`
        :default depending: *True*
        """
        EventRecording.__init__(self, log, logging_level, add_default_handlers)

        #: Defines whether a tool can be initialized directly (*False*) of if
        #: it is always called by other tools (*True*). Depending tools cannot
        #: initialize and reset logs but must return a external one.
        self.__depending = depending
        if self.__depending:
            self._check_input_class('log', log, ThelmaLog)
        else:
            initialize_semiconstant_caches()

        #: The object to be passed as result.
        self.return_value = None

    def run(self):
        """
        Runs the tool.
        """
        raise NotImplementedError('Abstract method.')

    def get_result(self, run=True):
        """
        Returns the return value.

        :param run: Determines whether the tool shall call the
                :func:`run` method (it can also be called separately).
        :type run: :class:`boolean`
        :default run: *True*
        """
        if run == True:
            try:
                self.run()
            finally:
                if not self.__depending:
                    clear_semiconstant_caches()
        return self.return_value

    def reset(self):
        """
        Resets the tool's :attr:`log`, its :attr:`return_value`.
        """
        self._error_count = 0
        self.return_value = None
        if not self.__depending:
            self.reset_log()
            initialize_semiconstant_caches()
        self.add_info('Reset ...')

    def _get_additional_value(self, value):
        """
        This function can be used, if there are additional value to be returned
        to external tool besides the actual return value. The function makes
        sure the value is only return if the :attr:`return_value` of the tool
        is not none (i.e. the tool has run and completed without errors).
        """
        if self.return_value is None: return None
        return value

    def __str__(self):
        return '<Tool %s, errors: %i>' % (self.NAME, self.log.error_count)

