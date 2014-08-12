"""
This module deals with the creation of ISO jobs. It can be used for all
ISO types.

AAB
"""
from thelma.automation.tools.base import BaseTool
from thelma.automation.utils.base import is_valid_number
from thelma.models.iso import ISO_TYPES
from thelma.models.iso import IsoRequest
from thelma.models.iso import LabIsoRequest
from thelma.models.iso import StockSampleCreationIsoRequest
from thelma.models.job import IsoJob
from thelma.models.user import User


__docformat__ = 'reStructuredText en'

__all__ = ['IsoJobCreator',
           'IsoProvider']


class IsoJobCreator(BaseTool):
    """
    Creates, copies or populates ISOs for an ISO request and summarises them
    in an ISO job. The class is abstract - however, sub class only need to
    provide the :class:`IsoProvider` class.

    **Return Value:** :class:`thelma.models.job.IsoJob` with all new ISOs
    """
    NAME = 'ISO Job Creator'
    #: The supported ISO type (see :class:`thelma.models.iso.ISO_TYPES`).
    _ISO_TYPE = None
    __ISO_REQUEST_CLS = {ISO_TYPES.LAB : LabIsoRequest,
            ISO_TYPES.STOCK_SAMPLE_GENERATION : StockSampleCreationIsoRequest}

    def __init__(self, iso_request, job_owner, number_isos,
                 excluded_racks=None, requested_tubes=None, parent=None):
        """
        Constructor.

        :param iso_request: The ISO request that will take up the ISOs.
        :type iso_request: :class:`thelma.models.iso.IsoRequest` subclass
        :param job_owner: The job owner will be set as user for the ISO job.
        :type job_owner: :class:`thelma.models.user.User`
        :param int number_isos: The number of ISOs ordered (positive number).
        :param excluded_racks: A list of barcodes from stock racks that shall
            not be used for stock sample picking.
        :type excluded_racks: A list of rack barcodes
        :param requested_tubes: A list of barcodes from stock tubes that are
            supposed to be used.
        :type requested_tubes: A list of tube barcodes.
        """
        BaseTool.__init__(self, parent=parent)
        #: The ISO request that will take up the ISOs.
        self.iso_request = iso_request
        #: The job owner will be set as user for the ISO job.
        self.job_owner = job_owner
        #: The number of ISOs ordered.
        self.number_isos = number_isos
        #: A list of barcodes from stock racks that shall not be used for
        #: stock sample (molecule design pool) picking.
        self.excluded_racks = excluded_racks
        if excluded_racks is None:
            self.excluded_racks = []
        if requested_tubes is None:
            requested_tubes = []
        #: A list of barcodes from stock tubes that are supposed to be used
        #: (for fixed positions).
        self.requested_tubes = requested_tubes
        #: The ISOs for the new job.
        self._isos = None
        #: The new ISO job.
        self._iso_job = None

    def reset(self):
        BaseTool.reset(self)
        self._isos = None
        self._iso_job = None

    def run(self):
        self.reset()
        self.add_info('Start ISO job generation ...')

        self._check_input()
        if not self.has_errors():
            self._get_isos()
        if not self.has_errors():
            self.__create_iso_job()
        if not self.has_errors():
            self.return_value = self._iso_job
            self.add_info('ISO job generation completed.')

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check initialisation values ...')
        self._check_input_class('ISO request', self.iso_request,
                                self.__ISO_REQUEST_CLS[self._ISO_TYPE])
        self._check_input_class('job owner', self.job_owner, User)
        if not is_valid_number(self.number_isos, is_integer=True):
            msg = 'The number of ISOs order must be a positive integer ' \
                  '(obtained: %s).' % (self.number_isos)
            self.add_error(msg)
        self._check_input_list_classes('excluded rack', self.excluded_racks,
                                       basestring, may_be_empty=True)
        self._check_input_list_classes('requested tube', self.requested_tubes,
                                       basestring, may_be_empty=True)

    def _get_isos(self):
        """
        Creates or populates the request number of ISOs (depending on the
        ISO type).
        """
        raise NotImplementedError('Abstract method.')

    def _get_iso_provider_keywords(self):
        """
        Returns the keyword dictionary for the ISO providing tool.
        """
        return dict(iso_request=self.iso_request,
                    number_isos=self.number_isos,
                    excluded_racks=self.excluded_racks,
                    requested_tubes=self.requested_tubes,
                    parent=self)

    def __create_iso_job(self):
        """
        Creates an :class:`IsoJob` summarizing the ISOs. The label for
        the job is derived from the ISO request label.
        """
        self.add_debug('Create ISO job ...')
        job_label = self._get_job_label()
        number_stock_racks = self._get_number_stock_racks()
        worklist_series = self._create_iso_job_worklist_series()
        self._iso_job = IsoJob(job_label, self.job_owner, self._isos,
                               number_stock_racks,
                               worklist_series=worklist_series)
        self._create_iso_job_racks()

    def _get_job_label(self):
        """
        Returns the label for the new job.
        """
        raise NotImplementedError('Abstract method.')

    def _get_number_stock_racks(self):
        """
        Returns the (maximum) number of stock racks expected for this ISO job.
        """
        raise NotImplementedError('Abstract method.')

    def _create_iso_job_racks(self):
        """
        Creates plates and ISOs specific to an ISO job. By default we do not
        create any racks.
        """
        pass

    def _create_iso_job_worklist_series(self):
        """
        Creates the worklist series containing the worklists that are specific
        to the ISO job. By default, there is no worklist series.
        """
        return None


class IsoProvider(BaseTool):
    """
    Creates, copies or populates ISOs for an ISO request. This includes
    tube picking, layout generation and in some cases also worklist generation.

    There are different subclass for the different :class:`ISO_TYPES`.

    **Return Value:** depends on the subclass
    """
    #: The supported ISO type (see :class:`thelma.models.iso.ISO_TYPES`).
    _ISO_TYPE = None
    __ISO_REQUEST_CLS = {ISO_TYPES.LAB : LabIsoRequest,
            ISO_TYPES.STOCK_SAMPLE_GENERATION : StockSampleCreationIsoRequest}

    def __init__(self, iso_request, number_isos,
                 excluded_racks=None, requested_tubes=None, parent=None):
        """
        Constructor.

        :param iso_request: The ISO request containing the ISO layout for the
            ISO (and experiment metadata with the molecule design pools).
        :type iso_request: :class:`thelma.models.iso.IsoRequest`
        :param int number_isos: The number of ISOs ordered.
        :param excluded_racks: A list of barcodes from stock racks that shall
            not be used for stock sample picking.
        :type excluded_racks: A list of rack barcodes
        :param requested_tubes: A list of barcodes from stock tubes that are
            supposed to be used.
        :type requested_tubes: A list of tube barcodes.
        """
        BaseTool.__init__(self, parent=parent)
        #: The ISO request defining the ISO layout
        #: (:class:`thelma.models.iso.IsoRequest`)
        self.iso_request = iso_request
        #: The number of ISOs ordered.
        self.number_isos = number_isos
        #: A list of barcodes from stock racks that shall not be used for
        #: stock sample (molecule design pool) picking.
        self.excluded_racks = excluded_racks
        if excluded_racks is None:
            self.excluded_racks = []
        if requested_tubes is None:
            requested_tubes = []
        #: A list of barcodes from stock tubes that are supposed to be used
        #: (for fixed positions).
        self.requested_tubes = requested_tubes

    def run(self):
        self.add_info('Start ISO request analysis ...')
        self.reset()
        self._check_input()
        if not self.has_errors():
            self._collect_iso_data()
        if not self.has_errors():
            self.add_info('ISO preparation completed.')

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check initialization values ...')
        if self._check_input_class('ISO request', self.iso_request,
                                   IsoRequest):
            iso_type = self.iso_request.iso_type
            if not self.__ISO_REQUEST_CLS.has_key(iso_type):
                msg = 'Unsupported ISO type "%s"!' % (iso_type)
                self.add_error(msg)
            else:
                ir_cls = self.__ISO_REQUEST_CLS[self._ISO_TYPE]
                self._check_input_class('ISO request', self.iso_request,
                                        ir_cls)
        if not is_valid_number(self.number_isos, is_integer=True):
            msg = 'The number of ISOs order must be a positive integer ' \
                  '(obtained: %s).' % (self.number_isos)
            self.add_error(msg)
        self._check_input_list_classes('excluded rack', self.excluded_racks,
                                       basestring, may_be_empty=True)
        self._check_input_list_classes('requested tube', self.requested_tubes,
                                       basestring, may_be_empty=True)

    def _collect_iso_data(self):
        """
        Does the actual generation or population job. Includes tube picking.
        """
        raise NotImplementedError('Abstract method.')
