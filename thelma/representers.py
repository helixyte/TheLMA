"""
Created on Apr 23, 2013.
"""
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
        Constructor.

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
    def create_from_resource_class(cls, resource_class):
        return cls(get_member_class(resource_class), cls.parser_factory)

    def data_from_stream(self, stream):
        parser = self.__parser_factory(stream, **self.__parser_options)
        result = parser.get_result()
        errors = parser.get_messages(logging_level=logging.ERROR)
        if len(errors) > 0:
            msg = '--'.join(errors)
            raise HTTPBadRequest('Could not parse file:\n%s' % msg).exception
        warnings = parser.get_messages(logging_level=logging.WARNING)
        if len(warnings) > 0:
            reg = get_current_registry()
            msg_notifier = reg.get_utility(IUserMessageNotifier)
            msg_notifier.notify(" -- ".join(warnings))
        return result

    def resource_from_data(self, data, resource=None):
        if not resource is None:
            raise NotImplementedError('Updating not implemented.')
        return self.resource_class.create_from_entity(data)

    def configure(self, options=None):
        if not options is None:
            self.__parser_options.update(options)

    # All methods dealing with the resource -> representation conversion are
    # not implemented. We call the base class methods to raise a
    # NotImplementedError while faking implementations to trick pylint.

    def data_to_stream(self, resource, stream):
        ResourceRepresenter.data_to_stream(self, resource, stream)

    def data_from_resource(self, resource):
        ResourceRepresenter.data_from_resource(self, resource)


class Xl20OutputRepresenter(ExternalParserResourceRepresenter):
    content_type = BioMicroLabXl20TextOutputMime

    @classmethod
    def parser_factory(cls, stream, **kw):
        user = get_current_user()
        return XL20Executor(output_file_stream=stream, user=user, **kw)
