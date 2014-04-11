"""
PutExperimentMetadataMemberView

TR
"""
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.httpexceptions import HTTPOk

from everest.resources.utils import resource_to_url
from everest.views.putmember import PutMemberView
from thelma.automation.tools.metadata.generation import \
    ExperimentMetadataGenerator
from thelma.automation.tools.metadata.uploadreport import \
    ExperimentMetadataReportUploader
from thelma.models.experiment import ExperimentMetadata
from thelma.models.utils import get_current_user
from thelma.utils import run_tool
from thelma.utils import run_trac_tool


__docformat__ = 'reStructuredText en'
__all__ = ['PutExperimentMetadataMemberView',
           ]


class PutExperimentMetadataMemberView(PutMemberView):
    """
    Specialized PUT member view for experiment metadata.

    The client sends a PUT request containing binary contents of an XLS file
    to update an ExperimentMetadataMember resource.
    """
    def __init__(self, resource, request, **kw):
        PutMemberView.__init__(self, resource, request, **kw)
        self.__generator = None

    def _extract_request_data(self):
        if self.request.content_type == 'application/vnd.xls':
            data = self.__extract_from_xls(self.request.body)
            # The freshly created entity needs an ID for subsequent updates.
            data.id = self.context.id
        else:
            data = PutMemberView._extract_request_data(self)
        return data

    def _process_request_data(self, data):
        initial_name = self.context.__name__
        self.context.update(data)
        if isinstance(data, ExperimentMetadata):
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
            run_trac_tool(trac_tool)
        # FIXME: add conflict detection # pylint: disable=W0511
        if initial_name != self.context.__name__:
            self.request.response_headerlist = \
                [('Location',
                  resource_to_url(self.context, request=self.request))]
        self.request.response_status = self._status(HTTPOk)
        return {'context' : self.context}

    def __extract_from_xls(self, request_body):
        if len(request_body) == 0:
            raise HTTPBadRequest("Request's body is empty!")
        experiment_metadata = self.context.get_entity()
        user = get_current_user()
        generator = ExperimentMetadataGenerator.create(
                                    stream=request_body,
                                    experiment_metadata=experiment_metadata,
                                    requester=user)
        new_entity = run_tool(generator)
        # Store this for later.
        self.__generator = generator
        return new_entity
