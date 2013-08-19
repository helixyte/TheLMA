"""
Base classes for trac support (via tractor integration).

AAB
"""



from pyramid.threadlocal import get_current_registry
from thelma.automation.errors import EventRecording
from thelma import ThelmaLog
from thelma.interfaces import ITractor
import logging


__docformat__ = 'reStructuredText en'
__all__ = ['BaseTracTool',
           ]


class BaseTracTool(EventRecording):
    """
    A base class for tools that send trac requests.
    """

    #: Specifies whether owner, reported and people in the cc shall receive an
    #: email notification.
    NOTIFY = True

    def __init__(self, log=None, logging_level=logging.WARNING,
                 add_default_handlers=False, depending=True):
        """
        Constructor:

        :param log: The ThelmaLog you want to write in. If the
            log is None, the object will create a new log.
        :param logging_level: the desired minimum log level
        :type log_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING
        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *False*
        :param depending: Defines whether the tool is called by other tools
            or whether it can run on its own (depending tools cannot initialize
            and reset logs).
        :type depending: :class:`bool`
        :default depending: *True*
        """
        ErrorRecording.__init__(self, log=log,
                                logging_level=logging_level,
                                add_default_handlers=add_default_handlers)

        #: Defines whether a tool can be initialized directly (*False*) of if
        #: it is always called by other tools (*True*). Depending tools cannot
        #: initialize and reset logs but must return a external one.
        self.depending = depending
        if depending:
            self._check_input_class('log', log, ThelmaLog)

        reg = get_current_registry()
        self.tractor_api = reg.getUtility(ITractor)

        #: The value return of the :func:`send_request` method.
        self.return_value = None

        #: Is set to *True*, if all Trac request have been completed
        #: successfully.
        self.was_successful = False

    def reset(self):
        """
        Resets all attributes except for instantiation arguments.
        """
        self.add_info('Reset trac tool ...')
        if not self.depending: self.reset_log()
        self.was_successful = False
        self.return_value = None

    def send_request(self):
        """
        Sends the request the trac tool is designed for.
        """
        self.add_error('Abstract method.')
        return None

    def transaction_completed(self):
        """
        Returns *True* if the tool is error-free and the transcation has been
        completed successfully (:attr:`was_succesful` is *True*).
        """
        return self.was_successful and not self.has_errors()

    def __str__(self):
        return '<TracTool %s, errors: %i>' % (self.NAME, self.log.error_count)

