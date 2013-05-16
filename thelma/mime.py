"""
Created on Apr 23, 2013.
"""
from everest.interfaces import IMime
from everest.mime import register_mime_type
from zope.interface import classProvides as class_provides # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['BioMicroLabXl20TextOutputMime',
           'IBioMicroLabXl20TextOutputMime',
           ]


# interface pylint: disable=W0232
class IBioMicroLabXl20TextOutputMime(IMime):
    """Interface for BioMicroLab XL20 text output mime type."""
# pylint: enable=W0232


class BioMicroLabXl20TextOutputMime(object):
    class_provides(IBioMicroLabXl20TextOutputMime)
    mime_type_string = 'text/vnd.biomicrolab.xl20.output'
    file_extension = '.txt'
    representer_name = 'xl20-output'


register_mime_type(BioMicroLabXl20TextOutputMime)
