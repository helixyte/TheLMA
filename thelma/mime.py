"""
MIME types for TheLMA.

Created on Apr 23, 2013.
"""
from everest.interfaces import IMime
from everest.mime import ZipMime
from everest.mime import register_mime_type
from zope.interface import provider # pylint: disable=E0611,F0401


__docformat__ = 'reStructuredText en'
__all__ = ['BioMicroLabXl20TextOutputMime',
           'ExperimentZippedWorklistMime',
           'IBioMicroLabXl20TextOutputMime',
           'IsoJobZippedWorklistMime',
           'IsoZippedWorklistMime',
           ]


# interface pylint: disable=W0232
class IBioMicroLabXl20TextOutputMime(IMime):
    """Interface for BioMicroLab XL20 text output mime type."""
# pylint: enable=W0232


@provider(IBioMicroLabXl20TextOutputMime)
class BioMicroLabXl20TextOutputMime(object):
    mime_type_string = 'text/vnd.biomicrolab.xl20.output'
    file_extension = '.txt'
    representer_name = 'xl20-output'


register_mime_type(BioMicroLabXl20TextOutputMime)


class ExperimentZippedWorklistMime(ZipMime):
    mime_type_string = 'thelma+zip;type=ExperimentMember'


class IsoZippedWorklistMime(ZipMime):
    mime_type_string = 'thelma+zip;type=IsoMember'


class IsoJobZippedWorklistMime(ZipMime):
    mime_type_string = 'thelma+zip;type=IsoJobMember'
