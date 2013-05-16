"""
Miscellaneous utilities.
"""
import datetime
import pytz
import tzlocal

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
