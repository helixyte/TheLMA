"""
PutExperimentMetadataMemberView

TR
"""

from StringIO import StringIO
from everest.interfaces import IUserMessageNotifier
from everest.resources.utils import resource_to_url
from everest.views.putmember import PutMemberView
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.httpexceptions import HTTPOk
from pyramid.threadlocal import get_current_registry
from thelma.automation.tools.metadata.generation import \
    ExperimentMetadataGenerator
from thelma.automation.tools.metadata.uploadreport import \
    ExperimentMetadataReportUploader
from thelma.models.experiment import ExperimentMetadata
from thelma.models.utils import get_current_user
import logging


__docformat__ = 'reStructuredText en'

__all__ = ['PutExperimentMetadataMemberView',
           ]

class PutExperimentMetadataMemberView(PutMemberView):
    """
    A View for processing PUT requests to update experiment metadata

    The client sends a PUT request containing binary contents of an XLS file
    to update a representation of an ExperimentMetadataMember
    Resource. If the request is successful, the server responds with a status
    code of 200.

    See http://bitworking.org/projects/atom/rfc5023.html#edit-via-PUT
    """

    __logger = logging.getLogger(__name__)
    __generator = None

    def _extract_request_data(self):
        if self.request.content_type == 'application/vnd.xls':
            data = self.__extract_from_xls(self.request.body)
        else:
            data = PutMemberView._extract_request_data(self)
        return data

    def _process_request_data(self, data):
        initial_name = self.context.__name__
        self.context.update(data)
        if isinstance(data, ExperimentMetadata):
            # This is a new entity extracted from XLS.
            # Now that we have all new information, generate links and upload
            # to Trac.
            url = self.request.application_url + '/public//LOUICe.html#' \
                  + self.context.path
            if self.context.iso_request is None:
                iso_url = "No ISO for this experiment metadata."
            else:
                iso_url = self.request.application_url \
                          + '/public//LOUICe.html#' \
                          + self.context.iso_request.path
            trac_tool = ExperimentMetadataReportUploader(
                                                generator=self.__generator,
                                                experiment_metadata_link=url,
                                                iso_request_link=iso_url)
            trac_tool.send_request()
            if not trac_tool.transaction_completed():
                errors = trac_tool.get_messages(logging_level=logging.ERROR)
                raise HTTPBadRequest(" -- ".join(errors)).exception
        current_name = self.context.__name__
        self.request.response_status = self._status(HTTPOk)
        # FIXME: add conflict detection # pylint: disable=W0511
        if initial_name != current_name:
            self.request.response_headerlist = \
                [('Location',
                  resource_to_url(self.context, request=self.request))]
        return {'context' : self.context}

    def __extract_from_xls(self, request_body):
        if len(request_body) == 0:
            raise HTTPBadRequest("Request's body is empty!").exception
        stream = StringIO(request_body)
        experiment_metadata = self.context.get_entity()
        user = get_current_user()
        source = stream.read()
        generator = ExperimentMetadataGenerator.create(
                                    stream=source,
                                    experiment_metadata=experiment_metadata,
                                    requester=user)
        new_entity = generator.get_result()
        warnings = generator.get_messages(logging.WARNING)
        if new_entity == None:
            self.__logger.error('PUT Request errors:\n%s' % generator.log)
            msg = '--'.join(generator.get_messages(logging.ERROR))
            raise HTTPBadRequest('Could not parse file: \n' + msg).exception
        elif len(warnings) > 0:
            reg = get_current_registry()
            msg_notifier = reg.getUtility(IUserMessageNotifier)
            msg_notifier.notify(" -- ".join(warnings))
        stream.seek(0)
        self.__generator = generator
        return new_entity
