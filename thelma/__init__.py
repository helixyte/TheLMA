import logging
from pyramid.compat import string_types


class LogEvent(object):
    """
    Abstract Log Event Class for parsing-related issues.
    LogEvents are meant to be stored in the ThelmaLog
    initialized by the Handler object.
    """

    def __init__(self, name, message):
        """
        :param message: explanation of the event
        :type message: :class:`string`
        :param name: The name of the tool which creates the event.
        :type name: :class:`str`
        """
#        if is_exception:
#            Exception.__init__(self, message)
        #: The message to be recorded.
        self.message = message
        #: The name of the tool which has created the event.
        self.tool_name = name

    def tostring(self):
        """
        Allows external objects (such the log) to get an LogEvent's
        message.
        """
        return self.__str__()

    def __str__(self):
        return '%s - %s' % (self.tool_name, self.message)


class ThelmaLog(logging.Logger):
    """
    Custom logger for TheLMA.
    """
    def add_critical(self, critical):
        """
        Adds the given error to the log (as CRITICAL level event)
        and raises the :py:attr:`error_count`.

        :param critical: :class:`Exception` or
                         :class:`LogEvent` or
                         exception message (:class:`string`)
        """
        log_message = self.__get_log_event_string(critical)
        self.log(logging.CRITICAL, log_message)

    def add_error(self, error):
        """
        Adds the given error to the log (as ERROR level event)
        and raises the :py:attr:`error_count`.

        :param error: :class:`Exception` or
                      :class:`LogEvent` or
                      exception message (:class:`string`)
        """
        log_message = self.__get_log_event_string(error)
        self.log(logging.ERROR, log_message)

    def add_warning(self, warning):
        """
        Adds the given warning to the log (as WARNING level event)

        :param warning: a :py:class:`LogEvent`
                        or a warning message (:class:`string`)
        """
        log_message = self.__get_log_event_string(warning)
        self.log(logging.WARNING, log_message)

    def add_info(self, info):
        """
        Adds the given info to the log (as INFO level event)

        :param info: :py:class:`LogEvent` or info message
                    (:py:class:`string`)
        """
        log_message = self.__get_log_event_string(info)
        self.log(logging.INFO, log_message)

    def add_debug(self, debug):
        """
        Adds the given info to the log (as DEBUG level event)

        :param debug: :py:class:`LogEvent`
                       or info message (:class:`string`)
        """
        log_message = self.__get_log_event_string(debug)
        self.log(logging.DEBUG, log_message)

    def __get_log_event_string(self, log_item):
        """
        Obtains the message of an log_item if it is not already a string.
        """
        if isinstance(log_item, string_types):
            result = log_item
        elif isinstance(log_item, LogEvent):
            result = log_item.tostring()
        else:
            result = log_item.message
        return result

# Set our ThelmaLogger class as the default for the logging subsystem.
logging.setLoggerClass(ThelmaLog)
