"""
Tools involved in lab ISO generation.

"""
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.tools.iso.jobcreator import IsoJobCreator
from thelma.automation.tools.iso.lab.base import LABELS
from thelma.automation.tools.iso.lab.planner import LabIsoBuilder
from thelma.automation.tools.iso.lab.planner import LabIsoPlanner
from thelma.models.iso import ISO_TYPES
from thelma.models.liquidtransfer import PlannedWorklist
from thelma.models.liquidtransfer import WorklistSeries


__docformat__ = 'reStructuredText en'

__all__ = ['LabIsoJobCreator',
           'LabIsoWorklistSeriesGenerator']


class LabIsoJobCreator(IsoJobCreator):
    """
    ISO job creator for stock samples creation ISOs.

    **Return Value:** :class:`thelma.models.job.IsoJob` with all new ISOs
    """
    _ISO_TYPE = ISO_TYPES.LAB

    def __init__(self, iso_request, job_owner, number_isos,
                       excluded_racks=None, requested_tubes=None,
                       logging_level=None, add_default_handlers=None):
        """
        Constructor:

        :param iso_request: The ISO request that will take up the ISOs.
        :type iso_request: :class:`thelma.models.iso.IsoRequest` subclass

        :param job_owner: The job owner will be set as user for the ISO job.
        :type job_owner: :class:`thelma.models.user.User`

        :param number_isos: The number of ISOs ordered.
        :type number_isos: :class:`int`

        :param excluded_racks: A list of barcodes from stock racks that shall
            not be used for stock sample picking.
        :type excluded_racks: A list of rack barcodes

        :param requested_tubes: A list of barcodes from stock tubes that are
            supposed to be used.
        :type requested_tubes: A list of tube barcodes.

        :param logging_level: the desired minimum log level
        :type log_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: *None*

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *None*
        """
        IsoJobCreator.__init__(self, iso_request=iso_request,
                               job_owner=job_owner, number_isos=number_isos,
                               excluded_racks=excluded_racks,
                               requested_tubes=requested_tubes,
                               logging_level=logging_level,
                               add_default_handlers=add_default_handlers)

        #: The :class:`LabIsoBuilder` used to generate the ISOs.
        self._builder = None

    def reset(self):
        IsoJobCreator.reset(self)
        self._builder = None

    def _get_isos(self):
        """
        The data is first collected in a builder which is then used to create
        all required entities.
        """
        self._get_builder()
        if not self.has_errors():
            self._isos = self._builder.create_isos()
        if not self.has_errors() and self.iso_request.worklist_series is None:
            self.__create_worklists_series()

    def _get_builder(self):
        """
        Generates the ISO builder that will than be used to create ISOs,
        worklist series (if there is none so far) and ISO job preparation
        plates.
        The planner also runs the optimizer that picks tube candidates.
        """
        planner = LabIsoPlanner(log=self.log, iso_request=self.iso_request,
                                number_isos=self.number_isos,
                                excluded_racks=self.excluded_racks,
                                requested_tubes=self.requested_tubes)
        self._builder = planner.get_result()

        if self._builder is None:
            msg = 'Error when generate ISO builder!'
            self.add_error(msg)

    def __create_worklists_series(self):
        """
        Assumes that there is no worklist series for the ISO request so far.
        If the worklist series is empty (happens if all ISO request positions
        can directly be derived from the stock) it is not attached to the
        ISO request.
        """
        generator = LabIsoWorklistSeriesGenerator(log=self.log,
                                                  builder=self._builder)
        worklist_series = generator.get_result()

        if worklist_series is None:
            msg = 'Error when trying to generate worklist series.'
            self.add_error(msg)
        elif len(worklist_series) > 0:
            self.iso_request.worklist_series = worklist_series

    def _create_iso_job_racks(self):
        """
        In case of lab ISOs there might be ISO job preparation plates.
        """
        self._builder.create_job_preparation_plates()


class LabIsoWorklistSeriesGenerator(BaseAutomationTool):
    """
    Uses a :class:`LabIsoBuilder` to generate the worklist series for an
    lab ISO generation process.

    **Return Value:** :class:`thelma.models.liquidtransfer.WorklistSeries`
    """

    NAME = 'Lab ISO Worklist Series Generator'

    def __init__(self, log, builder):
        """
        Constructor

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`

        :param builder: The builder contains all ISO plate layouts.
        :type builder: :class:`LabIsoBuilder`
        """
        BaseAutomationTool.__init__(self, log=log)

        #: The builder contains all ISO plate layouts.
        self.builder = builder
        #: The ticket number is part of worklist labels.
        self.__ticket_number = None

        #: The worklist series for the ISO request.
        self.__worklist_series = None

        #: The layouts mapped onto plate markers.
        self.__layout_map = None
        #: The plate markers for the layouts in order of prepraration.
        self.__ordered_plate_markers = None

    def reset(self):
        BaseAutomationTool.reset(self)
        self.__ticket_number = None
        self.__worklist_series = None
        self.__layout_map = None
        self.__ordered_plate_markers = []

    def run(self):
        self.reset()
        self.add_info('Generate worklist series ...')

        self.__check_input()
        if not self.has_errors():
            self.__worklist_series = WorklistSeries()
            self.__sort_layouts()
            self.__create_buffer_worklists()
        if not self.has_errors():
            self.return_value = self.__worklist_series
            self.add_info('Worklist series generation completed.')

    def __check_input(self):
        """
        Checks the input values.
        """
        if self._check_input_class('ISO builder', self.builder, LabIsoBuilder):
            self.__ticket_number = self.builder.ticket_number

    def __sort_layouts(self):
        """
        Job plates come first, aliquot plates come last. If there are several
        plates for a role, they are sorted by name.
        """
        self.__layout_map = self.builder.get_all_layouts()
        self.__sort_and_store_layout_map(self.builder.job_layouts)
        self.__sort_and_store_layout_map(self.builder.preparation_layouts)
        self.__ordered_plate_markers.append(LABELS.ROLE_ALIQUOT)

    def __sort_and_store_layout_map(self, layout_map):
        """
        Helper functions sorting layouts in a map by name and storing them.
        """
        for plate_marker in sorted(layout_map.keys()):
            self.__ordered_plate_markers.append(plate_marker)

    def __create_buffer_worklists(self):
        """
        Creates the dilution worklists for all layouts. The order is the order
        of the worklists.
        """
        dilution_map = self.builder.planned_dilutions

        for plate_marker in self.__ordered_plate_markers:
            worklist_label = self.__create_worklist_label(plate_marker)
            if not dilution_map.has_key(plate_marker): continue
            planned_dilutions = dilution_map[plate_marker]
            self.__create_worklist(worklist_label, planned_dilutions)

    def __create_transfer_worklist(self):
        """
        The order of the transfer worklists is more complicated than with
        the dilutions. We start with the starting wells of each layouts and
        create a new worklist for each generation within the plate. Only
        if all intraplate generations are processed we start the worklist
        to the next plate.
        """
        inter_map = self.builder.interplate_transfers
        intra_map = self.builder.intraplate_transfers

        for plate_marker in self.__ordered_plate_markers:
            if intra_map.has_key(plate_marker):
                intra_transfers = intra_map[plate_marker]
                self.__create_intraplate_worklists(plate_marker,
                                                   intra_transfers)
            if plate_marker == LABELS.ROLE_ALIQUOT: break
            if inter_map.has_key(plate_marker):
                inter_transfers = inter_map[plate_marker]
                self.__create_interplate_worklists(plate_marker,
                                                   inter_transfers)

    def __create_intraplate_worklists(self, plate_marker, transfer_map):
        """
        Creates the intraplate transfer worklists for the passed plate marker.
        The worklists are generated in order of the intraplate ancestor count.
        """
        for ancestor_count in sorted(transfer_map.keys()):
            pts = transfer_map[ancestor_count]
            worklist_label = self.__create_worklist_label(plate_marker,
                                                          plate_marker)
            self.__create_worklist(worklist_label, pts)

    def __create_interplate_worklists(self, source_plate_marker, transfer_map):
        """
        Creates the interplate transfer worklists for the passed source plate
        marker. The worklists are generated in order of the target plate
        markers.
        """
        index_map = dict()
        for trg_plate_marker in transfer_map.keys():
            i = self.__ordered_plate_markers.index(trg_plate_marker)
            index_map[i] = trg_plate_marker

        for i in sorted(index_map.keys()):
            trg_plate_marker = transfer_map[i]
            worklist_label = self.__create_worklist_label(trg_plate_marker,
                                                          source_plate_marker)
            pts = transfer_map[trg_plate_marker]
            self.__create_worklist(worklist_label, pts)

    def __create_worklist_label(self, target_plate_marker,
                                source_plate_marker=None):
        """
        Convenience function returning the label for the next worklist.
        """
        worklist_number = self.__get_current_worklist_number()
        return LABELS.create_worklist_label(ticket_number=self.__ticket_number,
                    worklist_number=worklist_number,
                    target_plate_marker=target_plate_marker,
                    source_plate_marker=source_plate_marker)

    def __create_worklist(self, worklist_label, planned_transfers):
        """
        Convenience function generating a worklist and adding it to the
        worklist series. The indices for the worklists are subsequent numbers.
        """
        worklist = PlannedWorklist(label=worklist_label,
                                   planned_transfers=planned_transfers)
        worklist_number = self.__get_current_worklist_number()
        self.__worklist_series.add_worklist(worklist_number, worklist)

    def __get_current_worklist_number(self):
        """
        Returns the number for the next worklist (current series length + 1).
        """
        return len(self.__worklist_series) + 1
