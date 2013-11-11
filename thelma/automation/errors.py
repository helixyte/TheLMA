"""
:Date: May 2011
:Author: AAB, berger at cenix-bioscience dot com
"""
from thelma import LogEvent
from thelma import ThelmaLog
from thelma.automation.utils.base import get_trimmed_string
import logging

__docformat__ = 'reStructuredText en'

__all__ = ['EventRecording',
           ]


class EventRecording(object):
    """
    This is the abstract base class for all classes recording errors
    and events.
    """
    #: A name passed by the object used to identify the log.
    NAME = None
    #: All events having a level equal or larger than this will be regarded as
    #: error
    ERROR_THRESHOLD = ThelmaLog.ERROR_THRESHOLD
    #
    logging_level = None
    """
    Available options are:

        + logging.CRITICAL  :       severity 50
        + logging.ERROR     :       severity 40
        + logging.WARNING   :       severity 30
        + logging.INFO      :       severity 20
        + logging.DEBUG     :       severity 10
        + logging.NOTSET    :
          (parent logger level or all events (if no parent available))

        All log events having at least the given severity will be logged.
        It can be adjusted with the :func:`set_log_ecording_level` function.
    """ #pylint: disable=W0105

    def __init__(self, log,
                 logging_level=None,
                 add_default_handlers=False):
        """
        Constructor:

        :param log: The ThelmaLog you want to write in. If the
            log is None, the object will create a new log.
        :type log: :class:`ThelmaLog`
        :param logging_level: the desired minimum log level
        :type log_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING
        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *False*
        """
        #: The log recording errors and events.
        self.log = None

        if log is None:
            # This is to fool pylint. If we use getLogger directly, it thinks
            # the logger is a logging.Logger instance and complains about
            # missing method names.
            get_fn = getattr(logging, 'getLogger')
            self.log = get_fn(self.__class__.__module__ + '.' +
                              self.__class__.__name__)
            if not logging_level is None:
                self.log.setLevel(logging_level)
        else:
            self.log = log

        # TODO: do we still need that?
        if add_default_handlers and len(self.log.handlers) < 1:
            self._add_default_handlers()
#        elif log is None and not add_default_handlers:
#            self.__add_null_handler()

        #: The errors that have occurred within the tool.
        self._error_count = 0

        #: As soon this is set to *True* errors and warnings will not be
        #: recorded anymore.
        #: However, the execution of running methods is still aborted.
        #: Use :func:`disable_error_and_warning_recording` to activate.
        self._disable_err_warn_rec = False
        #: If this is set to *True* the execution of methods is aborted
        #: silently.
        self._abort_execution = False

    def disable_error_and_warning_recording(self):
        """
        Use this method to disable recording of error and warning events.
        In cases of errors, method execution will still be aborted, though.
        """
        self._disable_err_warn_rec = True

    def get_messages(self, logging_level=logging.WARNING):
        """
        Returns the log's messages having the given severity level or more.
        """
        return self.log.get_messages(logging_level)

    def has_errors(self):
        """
        Checks if the log has recorded errors (ThelmaLog types: ERROR and
        CRITICAL).

        :return: 0 (\'False\') if the parsing was completed without errors
                 or the number of errors detected (\'True\')
        :rtype: :class:`int` (:class:`boolean`)
        """
        return (self._error_count > 0 or self._abort_execution)

    def reset_log(self):
        """
        Replaces the current log by a new one.
        """
        self.log.reset()
        self._error_count = 0
        self._abort_execution = False

    def set_log_recording_level(self, log_level):
        """
        Sets the threshold :py:attr:`LOGGING_LEVEL` of the log.

        :param log_level: the desired minimum log level
        :type log_level: int (or LOGGING_LEVEL as
                         imported from :py:mod:`logging`)
        """
        self.log.level = log_level

    def _add_default_handlers(self):
        """
        Generates handlers that are added automatically upon initialisation.
        """
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        stream_handler.setFormatter(formatter)
        self.add_log_handler(stream_handler)

    def __add_null_handler(self):
        """
        Adds a null handler to the object (if not log has passed and the
        default handlers are not to be initialised).
        """
        self.add_log_handler(logging.NullHandler())

    def add_critical_error(self, error_msg):
        """
        Converts the given message to an :class:`LogEvent`
        (level: CRITICAL), adds it to the :py:attr:`log` (class:`ThelmaLog`)
        and raises the log's :attr:`error_count` of the log.

        :param error_msg: an error message
        :type error_msg: :class:`string`

        """
        evt = LogEvent(self.NAME, error_msg)
        if not self._disable_err_warn_rec: self.log.add_critical(evt)
        self._adjust_error_count(logging.CRITICAL)

    def add_error(self, error_msg):
        """
        Converts the given message to an :class:`LogEvent`
        (level: ERROR), adds it to the :py:attr:`log` (class:`ThelmaLog`)
        and raises the log's :attr:`error_count` of the log.

        :param error_msg: an error message
        :type error_msg: :class:`string`
        """
        evt = LogEvent(self.NAME, error_msg)
        if not self._disable_err_warn_rec: self.log.add_error(evt)
        self._adjust_error_count(logging.ERROR)

    def add_warning(self, warning_msg):
        """
        Converts the given message to an :class:`LogEvent`
        (level: WARNING) and adds it to the :py:attr:`log` (class:`ThelmaLog`).

        :param warning_msg: a warning message
        :type warning_msg: :class:`string`
        """
        evt = LogEvent(self.NAME, warning_msg,
                       is_exception=False)
        if not self._disable_err_warn_rec: self.log.add_warning(evt)
        self._adjust_error_count(logging.WARNING)

    def add_info(self, info_msg):
        """
        Converts the given message to an :class:`LogEvent`
        (level: INFO) and adds it to the :py:attr:`log` (class:`ThelmaLog`).

        :param info_msg: a warning message
        :type info_msg: :class:`string`
        """
        evt = LogEvent(self.NAME, info_msg, is_exception=False)
        self.log.add_info(evt)
        self._adjust_error_count(logging.INFO)

    def add_debug(self, debug_msg):
        """
        Converts the given message to an :class:`LogEvent`
        (level: DEBUG) and adds it to the :py:attr:`log` (class:`ThelmaLog`).

        :param debug_msg: a warning message
        :type debug_msg: :class:`string`
        """
        evt = LogEvent(self.NAME, debug_msg, is_exception=False)
        self.log.add_debug(evt)
        self._adjust_error_count(logging.DEBUG)

    def add_log_event(self, log_event, log_level):
        """
        Adds an already existing LogEvent object to the :attr:`log`.

        :param log_event: A log event.
        :type log_event: :class:`log_event`
        :param log_level: The severity of the event.
        :type log_level: :class:`int` (logging severity value).
        """
        self._adjust_error_count(log_level)
        self.log.add_record(log_level, log_event.tostring())

    def _adjust_error_count(self, logging_level):
        """
        Increases the tools error count if the severity of a logging level
        is equal or above the :attr:`ERROR_THRESHOLD`.
        """
        if logging_level >= self.ERROR_THRESHOLD:
            if not self._disable_err_warn_rec:
                self._error_count += 1
            self._abort_execution = True

    def add_log_handlers(self, handlers):
        """
        Adds handlers to the parsing log.

        :param handlers: the desired handlers
        :type handlers: list of :py:class:`logging.Handler` objects
        """
        for handler in handlers:
            self.log.addHandler(handler)

    def add_log_handler(self, handler):
        """
        Adds handlers to the parsing log.

        :param handlers: the desired handler
        :type handlers: list of :py:class:`logging.Handler` objects
        """
        self.log.addHandler(handler)

    def _check_input_class(self, name, obj, exp_class):
        """
        Checks whether a objects has the expected class and raises an
        error, if applicable.

        :param name: The name under which the object shall be referenced.
        :type name: :class:`str`

        :param obj: The object to be tested.
        :type obj: any

        :param exp_class: The expected class.
        :type exp_class: any
        """
        if not isinstance(obj, exp_class):
            msg = 'The %s must be a %s object (obtained: %s).' \
                  % (name, exp_class.__name__, obj.__class__.__name__)
            self.add_error(msg)
            return False
        return True

    def _check_input_list_classes(self, item_name, list_obj, item_cls,
                                  may_be_empty=False):
        """
        Checks whether a list and the objects it contains have the expected
        class and a length of at least 1 and records an error, if applicable.

        :param item_name: The name under which a list item shall be referenced
            in the error message.
        :type item_name: :class:`str

        :param list_obj: The list to be tested.
        :type list_obj: :class:`list`

        :param item_cls: The expected class for the list items.
        :type item_cls: any

        :param may_be_empty: May the list be empty?
        :type may_be_empty: :class:`bool`
        :default may_be_empty: *False*
        """
        list_name = '%s list' % (item_name)
        if not self._check_input_class(list_name, list_obj, list):
            return False

        for item in list_obj:
            if not self._check_input_class(item_name, item, item_cls):
                return False
        if len(list_obj) < 1 and not may_be_empty:
            msg = 'The %s is empty!' % (list_name)
            self.add_error(msg)
            return False

        return True

    def _check_input_map_classes(self, map_obj, map_name, key_name, key_cls,
                                 value_name, value_cls, may_be_empty=False):
        """
        Checks whether a maps and the objects it contains have the expected
        class and a length of at least 1 and records an error, if applicable.

        :param map_obj: The map to be tested.
        :type map_obj: :class:`dict`

        :param map_name: The name under which the map shall be referenced
            in the error message.
        :type map_name: :class:`str

        :param key_name: The name under which a map key item be referenced
            in the error message.
        :type key_name: :class:`str

        :param value_name: The name under which a mape value shall be
            referenced in the error message.
        :type value_name: :class:`str

        :param key_cls: The expected class for the map keys.
        :type key_cls: any

        :param value_cls: The expected class for the map values.
        :type value_cls: any

        :param may_be_empty: May the list be empty?
        :type may_be_empty: :class:`bool`
        :default may_be_empty: *False*
        """
        if not self._check_input_class(map_name, map_obj, dict):
            return False

        for k, v in map_obj.iteritems():
            if not self._check_input_class(key_name, k, key_cls):
                return False
            if not self._check_input_class(value_name, v, value_cls):
                return False

        if len(map_obj) < 1 and not may_be_empty:
            msg = 'The %s is empty!' % (map_name)
            self.add_error(msg)
            return False

        return True

    def _run_and_record_error(self, meth, base_msg, error_types=None, **kw):
        """
        Convenience method that runs a method and catches errors of the
        specified class. The error messages are recorded along with the
        base msg.

        :param meth: The method to be called.

        :param base_msg: This message is put in front of the potential error
            message. If the message is *None* there is no error recorded.
        :type base_msg: :class:`str`

        :param error_types: Error classes that shall be caught.
        :type error_types: iterable
        :default error_type: *None* (catches AttributeError, ValueError and
            TypeError)

        :return: The method return value or *None* (in case of exception)
        """
        if base_msg is not None:
            filler = ': '
            if base_msg.endswith(filler):
                filler = ''
            elif base_msg.endswith(':'):
                filler = ' '
            base_msg += filler
        if error_types is None:
            error_types = {ValueError, TypeError, AttributeError}
        elif isinstance(error_types, StandardError):
            error_types = set([error_types])

        return meth(**kw)
# TODO: reactivate
#        try:
#            return_value = meth(**kw)
#        except StandardError as e:
#            if e.__class__ in error_types and not base_msg is None:
#                self.add_error(base_msg + str(e))
#            else:
#                return None
#        else:
#            return return_value

    def _get_joined_str(self, item_list, is_strs=True, sort_items=True,
                        separator=', '):
        """
        Helper method converting the passed list into a joined string, separated
        by comma (default). By default, the elements are sorted before
        conversion. This is handy i.e. when printing error messages.

        :param item_list: The recorded events in a list.
        :type item_list: :class:`list` or iterable that can be converted into
            a list

        :param is_strs: If not the items must be converted first.
            Without conversion the join method will raise an error.
        :type is_strs: :class:`bool`
        :default is_strs: *True*

        :param sort_items: Shall the items be sorted?
        :type sort_items: :class:`bool`
        :default sort_items: *True*

        :param separator: The string to use for the joining.
        :type separator: :class:`str`
        :default separator: comma and 1 whitespace
        """
        if not isinstance(item_list, list):
            item_list = list(item_list)
        if sort_items: item_list.sort()
        if is_strs:
            item_strs = item_list
        else:
            item_strs = []
            for item in item_list: item_strs.append(get_trimmed_string(item))

        return separator.join(item_strs)

    def _get_joined_map_str(self, item_map, str_pattern='%s (%s)',
                            all_strs=True, sort_lists=True, separator=' - '):
        """
        Helper method converting the passed map into a joined string, separated
        by comma (default). By default, the elements of the lists are sorted
        before conversion (map keys are always sorted).
        This is handy i.e. when printing error messages.

        If the map values are iterables, :func:`_get_joined_str` is used to
        generate a string for the list.

        :param item_map: The recorded events in a map.
        :type item_map: :class:`map` having iterables as values

        :param str_pattern: Is used to convert key-value pairs into a string.
            The first placeholder is used by the key, the second by the joined
            string value.
        :type str_pattern: :class:`str` with 2 string placeholders
        :default str_pattern: *%s (%s)*

        :param all_strs: Are the value list items strings (only applicable
            if the value is an iterable)?  If not the items must be
            converted first. Without conversion the join method will
            raise an error.
        :type all_strs: :class:`bool`
        :default all_strs: *True*

        :param sort_lists: Shall the values items in be sorted?
            (only applicable if the value is an iterable)
        :type sort_lists: :class:`bool`
        :default sort_lists: *True*

        :param separator: The string to use for the joining the key-value
            strings.
        :type separator: :class:`str`
        :default separator: whitespace, dash, whitespace
        """
        details = []
        for k in sorted(item_map.keys()):
            v = item_map[k]
            if isinstance(v, (list, set, dict, tuple)):
                v_str = self._get_joined_str(v, is_strs=all_strs,
                                             sort_items=sort_lists)
            else:
                v_str = str(v)
            details_str = str_pattern % (get_trimmed_string(k), v_str)
            details.append(details_str)

        return separator.join(details)
