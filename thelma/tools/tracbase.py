"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Base classes for trac support (via tractor integration).

AAB
"""

from xmlrpclib import Fault
from xmlrpclib import ProtocolError

from pyramid.threadlocal import get_current_registry

from thelma.tools.base import BaseTool
from thelma.interfaces import ITractor


__docformat__ = 'reStructuredText en'
__all__ = ['BaseTracTool',
           ]


class BaseTracTool(BaseTool): # still abstract pylint:disable=W0223
    """
    A base class for tools that send trac requests.
    """
    #: Specifies whether owner, reported and people in the cc shall receive an
    #: email notification.
    NOTIFY = True

    def __init__(self, parent=None):
        BaseTool.__init__(self, parent=parent)
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
        BaseTool.reset(self)
        self.was_successful = False

    def _submit(self, tractor_method, kw):
        """
        Convenience method that runs a tractor submission method and catches
        and records errors.

        :param tractor_method: The method to be called.

        :param kw: The keyword dictionary for the method.
        :type kwL :class:`dict`

        :return: The method return value or *None* (in case of exception).
        """
        try:
            value = tractor_method(**kw)
        except ProtocolError, err:
            self.add_error(err.errmsg)
            return None
        except Fault, fault:
            msg = 'Fault %s: %s' % (fault.faultCode, fault.faultString)
            self.add_error(msg)
            return None
        else:
            return value

    def transaction_completed(self):
        """
        Returns *True* if the tool is error-free and the transcation has been
        completed successfully (:attr:`was_succesful` is *True*).
        """
        return self.was_successful and not self.has_errors()

    def __str__(self):
        return '<TracTool %s, errors: %i>' % (self.NAME, self.error_count)

