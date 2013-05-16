"""
Paster command to initialize the model (without creating a WSGI app) for
basic unit tests.

FOG May 20, 2011
"""

from paste.script.command import Command #pylint: disable=F0401, E0611
from paste.script.command import get_commands #pylint: disable=F0401, E0611
from paste.script.command import invoke #pylint: disable=F0401, E0611
from paste.script.command import parser #pylint: disable=F0401, E0611
import sys

__docformat__ = 'reStructuredText en'

__author__ = 'F Oliver Gathmann'
__date__ = '$Date: 2011-11-10 12:55:22 +0100 (Thu, 10 Nov 2011) $'
__revision__ = '$Rev: 12254 $'
__source__ = '$URL:: http://svn/cenix/TheLMA/trunk/thelma/commands/initmodel.#$'

__all__ = ['InitializeModel',
           ]


class InitializeModel(Command):
    """Sets up the TheLMA model.

    Usage::
        $ paster initmodel TheLMA.ini thelma
    """
    summary = __doc__.splitlines()[0]
    usage = '\n'.join(__doc__.splitlines()[1:])
    group_name = 'thelma'

    def command(self):
        # Need to run the initdb command first.
        cmd = get_commands()['initdb'].load()
        options, args = parser.parse_args(sys.argv[1:])
        invoke(cmd, 'initdb', options, args[1:])
