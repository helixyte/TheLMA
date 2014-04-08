"""
Miscellaneous utilities.
"""
from everest.interfaces import IUserMessageNotifier
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.threadlocal import get_current_registry
import datetime
import logging
import pytz
import tzlocal
import os

__docformat__ = 'reStructuredText en'
__all__ = ['as_utc_time',
           'get_utc_time',
           'localize_time',
           ]


def get_utc_time():
    """
    Returns the current time as a timezone aware datetime object with the
    time zone set to UTC.

    :returns: :class:`datetime.datetime`
    """
    return datetime.datetime.now(pytz.UTC)


def as_utc_time(timestamp):
    """
    Converts the given timezone unaware datetime object to a timezone
    aware one with the time zone set to UTC.

    :param timestamp: :class:`datetime.datetime` object to convert
    """
    return tzlocal.get_localzone().localize(timestamp).astimezone(pytz.utc)


def localize_time(timestamp):
    """
    Converts the given timezone aware datetime object to a new datetime
    object with your local timezone.

    :param timestamp: :class:`datetime.datetime` object to localize
    :returns: :class:`datetime.datetime`
    """
    return timestamp.astimezone(tzlocal.get_localzone())


class ToolRunnerBase(object):

    def __init__(self, tool,
                 error_message_prefix='', warning_message_prefix=''):
        self._tool = tool
        self.__error_message_prefix = error_message_prefix
        self.__warning_message_prefix = warning_message_prefix

    def run(self):
        raise NotImplementedError('Abstract method.')

    def _get_error_messages(self):
        msgs = self._tool.get_messages(logging_level=logging.ERROR)
        return self.__error_message_prefix + " -- ".join(msgs)

    def _get_warning_messages(self):
        return self.__warning_message_prefix \
               + " -- ".join(self._tool.get_messages(logging.WARNING))


class ToolRunner(ToolRunnerBase):
    def run(self):
        try:
            result = self._tool.get_result()
        except Exception, err:
            raise HTTPBadRequest("Unknown server error.%s(%s)."
                                 % (os.linesep, str(err)))
        if result is None:
            raise HTTPBadRequest(self._get_error_messages())
        warnings = self._get_warning_messages()
        if len(warnings) > 0:
            reg = get_current_registry()
            msg_notifier = reg.getUtility(IUserMessageNotifier)
            msg_notifier.notify(warnings)
        return result


class TracToolRunner(ToolRunnerBase):
    def run(self):
        self._tool.run()
        if not self._tool.transaction_completed():
            raise HTTPBadRequest(self._get_error_messages())


def run_tool(tool, error_prefix='', warning_prefix=''):
    tool_runner = ToolRunner(tool,
                             error_message_prefix=error_prefix,
                             warning_message_prefix=warning_prefix)
    return tool_runner.run()


def run_trac_tool(trac_tool, error_prefix='', warning_prefix=''):
    tool = TracToolRunner(trac_tool,
                          error_message_prefix=error_prefix,
                          warning_message_prefix=warning_prefix)
    tool.run()
