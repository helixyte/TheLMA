"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

:Date: May 2011
:Author: AAB, berger at cenix-bioscience dot com
"""
import logging

from pyramid.compat import native_


__docformat__ = 'reStructuredText en'
__all__ = ['MessageRecorder',
           ]


class MessageRecorder(object):
    """
    Abstract base class for all message recording classes.

    The message recorder passes on all messages to the logging framework. In
    addition, it keeps a stack of all messages recorded during its lifetime.
    """
    #: A name passed by the object used to group the recorded messages.
    NAME = None

    def __init__(self, parent=None):
        """
        Constructor.

        :param parent: An event recorder to use instead of this one to record
          all events.
        :type parent: :class:`MessageRecorder`
        """
        #: The number of errors that have been recorded.
        self._error_count = 0
        #: As soon this is set to *True* errors and warnings will not be
        #: recorded anymore.
        #: However, the execution of running methods is still aborted.
        #: Use :func:`disable_error_and_warning_recording` to activate.
        self._disable_err_warn_rec = False
        #: If this is set to *True* :meth:`has_errors` will return `True`
        #: in the next call.
        self.abort_execution = False
        #: The message stack of this recorder. This will only contain
        #: messages if this is a root recorder (i.e., :param:`parent` is
        #: `None`).
        self._message_stack = []
        #
        if parent is None:
            # This is a root recorder - create a logger for it.
            self._root_recorder = self
            self._is_root = True
            # This is to fool pylint. If we use getLogger directly, it thinks
            # the logger is a logging.Logger instance and complains about
            # missing method names.
            get_fn = getattr(logging, 'getLogger')
            self._logger = get_fn(self.__class__.__module__ + '.' +
                                  self.__class__.__name__)
            self.__name = self.NAME
        else:
            if not isinstance(parent, MessageRecorder):
                raise ValueError('Need to pass in an instance of '
                                 'MessageRecorder as parent.')
            self._root_recorder = parent._root_recorder # pylint:disable=W0212
            self._is_root = False
            self._logger = None
            self.__name = self._root_recorder.name + '->' + self.NAME

    def disable_error_and_warning_recording(self):
        """
        Use this method to disable recording of error and warning events for
        this recorder.

        Should an error happen, method execution will still be aborted.
        """
        self._disable_err_warn_rec = True

    def get_messages(self, logging_level=logging.WARNING):
        """
        Returns all messages having the given severity level or more.
        """
        return [msg
                for (log_lvl, msg) in self._root_recorder._message_stack # pylint:disable=W0212
                if log_lvl >= logging_level]

    def has_errors(self):
        """
        Checks if errors were recorded (logging levels ERROR and
        CRITICAL) or if the attr:`abort_execution` flag was set.
        """
        return self._error_count > 0 or self.abort_execution

    @property
    def error_count(self):
        """
        The number of errors recorded so far.
        """
        if self._is_root:
            err_cnt = self._error_count
        else:
            err_cnt = self._root_recorder.error_count
        return err_cnt

    @property
    def name(self):
        """
        The (read-only) name of this message recorder included as a prefix in
        all messages.

        The name is formed by concatenating the :attr:`NAME` attribute of
        all message reccorders in a calling hierarchy.
        """
        return self.__name

    def reset(self):
        """
        Resets this recorder.
        """
        self._error_count = 0
        self.abort_execution = False
        self._message_stack = []

    def add_critical_error(self, message):
        """
        Records a critical error.

        :param str message: Message to record.
        """
        self.__record_message(logging.CRITICAL, message)

    def add_error(self, message):
        """
        Records an error.

        :param str message: Message to record.
        """
        self.__record_message(logging.ERROR, message)

    def add_warning(self, message):
        """
        Records a warning.

        :param str message: Message to record.
        """
        self.__record_message(logging.WARNING, message)

    def add_info(self, message):
        """
        Records an info message.

        :param str message: Message to record.
        """
        self.__record_message(logging.INFO, message)

    def add_debug(self, message):
        """
        Records a debug message.

        :param str message: Message to record.
        """
        self.__record_message(logging.DEBUG, message)

    def __record_message(self, logging_level, message):
        do_record = True
        if logging_level >= logging.ERROR:
            do_record = not self._disable_err_warn_rec
            if do_record:
                self._error_count += 1
            self.abort_execution = True
        if do_record:
            msg = "%s - %s" % (self.__name, native_(message))
            evt = (logging_level, msg)
             # pylint:disable=W0212
            self._root_recorder._message_stack.append(evt)
            self._root_recorder._logger.log(*evt)
            # pylint:enable=W0212
