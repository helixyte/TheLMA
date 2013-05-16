"""
Created on Apr 23, 2013.
"""
from StringIO import StringIO
from everest.interfaces import IUserMessageNotifier
from everest.representers.base import ResourceRepresenter
from everest.resources.utils import get_member_class
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.threadlocal import get_current_registry
import logging
from thelma.mime import BioMicroLabXl20TextOutputMime
from thelma.models.utils import get_current_user
from thelma.automation.tools.worklists.tubehandler import XL20Executor

__docformat__ = 'reStructuredText en'
__all__ = ['Xl20OutputRepresenter',
           ]


class ExternalParserResourceRepresenter(ResourceRepresenter):
    """
    Representer that uses an external parser to convert incoming
    representations to resources.
    """
    content_type = None
    parser_factory = None
    def __init__(self, resource_class, parser_factory):
        """
        :param resource_class: the class of the resource to generate from
            incoming representations
        :param parser_factory: a callable that generates a new parser. All
            options set with the :meth:`configure` method are passed to the
            factory call.
        """
        ResourceRepresenter.__init__(self, resource_class)
        self.__parser_factory = parser_factory
        self.__parser_options = {}

    @classmethod
    def create_from_resource(cls, rc):
        return cls(get_member_class(rc), cls.parser_factory)

    def from_stream(self, stream):
        data_el = self.data_from_stream(stream)
        return self.resource_from_data(data_el)

    def data_from_stream(self, stream):
        parser = self.__parser_factory(stream, **self.__parser_options)
        result = parser.get_result()
        errors = parser.get_messages(logging.ERROR)
        if len(errors) > 0:
            msg = '--'.join(errors)
            raise HTTPBadRequest('Could not parse file:\n%s' % msg).exception
        warnings = parser.get_messages(logging.WARNING)
        if len(warnings) > 0:
            reg = get_current_registry()
            msg_notifier = reg.get_utility(IUserMessageNotifier)
            msg_notifier.notify(" -- ".join(warnings))
        return result

    def data_from_representation(self, representation):
        stream = StringIO(representation)
        return self.data_from_stream(stream)

    def resource_from_data(self, data):
        return self.resource_class.create_from_entity(data)

    def configure(self, options=None):
        if not options is None:
            self.__parser_options.update(options)

    # All methods dealing with the resource -> representation conversion are
    # not implemented. We call the base class methods to raise a
    # NotImplementedError while faking implementations to trick pylint.

    def to_stream(self, resource, stream):
        ResourceRepresenter.to_stream(self, resource, stream)

    def representation_from_data(self, data):
        ResourceRepresenter.representation_from_data(self, data)

    def data_from_resource(self, resource):
        ResourceRepresenter.data_from_resource(self, resource)


class Xl20OutputRepresenter(ExternalParserResourceRepresenter):
    content_type = BioMicroLabXl20TextOutputMime

    @classmethod
    def parser_factory(cls, stream, **kw):
        user = get_current_user()
        return XL20Executor(output_file_stream=stream, user=user, **kw)