import logging


class LogEvent(Exception):
    """
    Abstract Log Event Class for parsing-related issues.
    LogEvents are meant to be stored in the ThelmaLog
    initialized by the Handler object.
    """

    def __init__(self, name, message, is_exception=True):
        """
        :param message: explanation of the event
        :type message: :class:`string`
        :param name: The name of the tool which creates the event.
        :type name: :class:`str`
        :param is_exception: defines whether the object initializes the
                :class:`Exception` superclass (default: \'True\')
        :type is_exception: :class:`boolean`
        """
        if is_exception:
            Exception.__init__(self, message)
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
    """ .. : _log

    Logs the events occurring during a parsing event.
    """

    #: All events having a level equal or larger than this will be regarded as
    #: error
    ERROR_THRESHOLD = 40

    def __init__(self, tool_name, log_level=logging.NOTSET):
        """
        :param str name: the name for the logger
        :param log_level: the desired minimum log level
        :type log_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        """
        logging.Logger.__init__(self, tool_name, level=log_level)
        self.error_count = 0
        # a list of tuples with a severity and message
        self.__msg_stack = []

    def reset(self):
        """
        Resets the error count to 0.
        """
        self.add_info('Log reset.')
        self.error_count = 0
        self.__msg_stack = []

    def add_record(self, log_level, log_msg):
        """
        Adds record to the log.

        :param log_level: The severity of the event.
        :type log_level: :mod:`logging` logging level (:class:`int`)
        :param log_msg: The logging message.
        :type log_msg: :class:`string`
        """
        self.log(log_level, log_msg)
        if log_level >= self.ERROR_THRESHOLD:
            self.error_count += 1
        self.__msg_stack.append((log_level, log_msg))

    def add_critical(self, critical):
        """
        Adds the given error to the log (as CRITICAL level event)
        and raises the :py:attr:`error_count`.

        :param critical: :class:`Exception` or
                         :class:`LogEvent` or
                         exception message (:class:`string`)
        """
        log_message = self.__get_log_event_string(critical)
        self.add_record(logging.CRITICAL, log_message)

    def add_error(self, error):
        """
        Adds the given error to the log (as ERROR level event)
        and raises the :py:attr:`error_count`.

        :param error: :class:`Exception` or
                      :class:`LogEvent` or
                      exception message (:class:`string`)
        """
        log_message = self.__get_log_event_string(error)
        self.add_record(logging.ERROR, log_message)

    def add_warning(self, warning):
        """
        Adds the given warning to the log (as WARNING level event)

        :param warning: a :py:class:`LogEvent`
                        or a warning message (:class:`string`)
        """
        log_message = self.__get_log_event_string(warning)
        self.add_record(logging.WARNING, log_message)

    def add_info(self, info):
        """
        Adds the given info to the log (as INFO level event)

        :param info: :py:class:`LogEvent` or info message
                    (:py:class:`string`)
        """
        log_message = self.__get_log_event_string(info)
        self.add_record(logging.INFO, log_message)

    def add_debug(self, debug):
        """
        Adds the given info to the log (as DEBUG level event)

        :param debug: :py:class:`LogEvent`
                       or info message (:class:`string`)
        """
        log_message = self.__get_log_event_string(debug)
        self.add_record(logging.DEBUG, log_message)

    def get_messages(self, logging_level=logging.WARNING):
        """
        Returns the messages having the given severity level or more.
        """

        messages = []
        for lv, log_event in self.__msg_stack:
            if lv >= logging_level:
                messages.append(str(log_event))
        return messages

    def __get_log_event_string(self, log_item):
        """
        Obtains the message of an log_item if it is not already a string.
        """
        if isinstance(log_item, str) or isinstance(log_item, unicode):
            return log_item
        elif isinstance(log_item, LogEvent):
            return log_item.tostring()
        else:
            return log_item.message

# Set our ThelmaLogger class as the default for the logging subsystem.
logging.setLoggerClass(ThelmaLog)
