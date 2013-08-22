"""
Tubehandler related tools in lab ISO processing.

AAB
"""
from thelma.automation.tools.base import BaseAutomationTool
from everest.entities.utils import get_root_aggregate
from thelma.interfaces import ITubeRack

__docformat__ = 'reStructuredText en'

__all__ = []


class LabIsoXL20WorklistGenerator(BaseAutomationTool):
    """
    This tool generates a zip archive that contains worklists for the tube
    handler (XL20) and some overview and report files. If the
    :param:`include_dummy_output` flag is set, an additional file containing
    the output from the XL20 dummy writer is added.

    At this, it generate stock rack entities and conducts checks on DB level.
    The output is a zip archive

    **Return Value:** A zip archive with two files (worklist and report);
    """

    #: The entity class supported by this generator.
    _ENTITY_CLS = None

    def __init__(self, entity, destination_rack_barcode_map,
                 excluded_racks=None, requested_tubes=None,
                 include_dummy_output=False,
                 logging_level=None, add_default_handlers=None):
        """
        Constructor:

        :param entity: The ISO or the ISO job for which to generate the files
            and the racks.

        :param destination_rack_barcode_map: The barcodes for the destination
            racks (the rack the tubes shall be transferred to).
        :type destination_rack_barcode_map: map of barcodes
            (:class:`basestring`) mapped onto sector indices.

        :param excluded_racks: A list of barcodes from stock racks that shall
            not be used for molecule design picking.
        :type excluded_racks: A list of rack barcodes

        :param requested_tubes: A list of barcodes from stock tubes that are
            supposed to be used.
        :type requested_tubes: A list of rack barcodes.

        :param include_dummy_output: Flag indicating if the
            `thelma.tools.dummies.XL20Dummy` output writer should be run
            at the end of the worklist generation. The resulting output file
            is then included in the zip file.
        :type include_dummy_output: :class:`bool`
        :default include_dummy_output: *False*

        :param logging_level: the desired minimum log level
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *False*
        """
        BaseAutomationTool.__init__(self, logging_level=logging_level,
                                 add_default_handlers=add_default_handlers,
                                 depending=False)

        #: The ISO or the ISO job for which to generate the files and the racks.
        self.entity = entity
        #: The barcodes of the racks the tubes shall be transferred to.
        self.destination_rack_map = destination_rack_barcode_map

        #: A list of barcodes from stock racks that shall not be used for
        #: molecule design picking.
        self.excluded_racks = excluded_racks
        if excluded_racks is None: self.excluded_racks = []
        #: A list of barcodes from stock tubes that are supposed to be used.
        self.requested_tubes = requested_tubes
        if requested_tubes is None: self.requested_tubes = []
        #: Flag indicating if the file from the dummy output writer should be
        #: included in the output zip file.
        self.include_dummy_output = include_dummy_output

        #: Maps tube racks onto barcodes (required for stock racks).
        self._barcode_map = None

        #: The zip stream wrapped around the two files.
        self.__zip_stream = None

    def reset(self):
        BaseAutomationTool.reset(self)
        self._barcode_map = dict()
        self.__zip_stream = None

    def run(self):
        self.reset()
        self.add_info('Start planning XL20 run ...')

        self._check_input()


    def _check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input values ...')

        self._check_input_class('entity', self.entity, self._ENTITY_CLS)
        self._check_input_class('"include dummy output" flag',
                                self.include_dummy_output, bool)

        if self._check_input_class('destination rack barcode map',
                                   self.destination_rack_map, dict):
            for sector_index, barcode in self.destination_rack_map.iteritems():
                if not self._check_input_class('sector index', sector_index,
                                               int): break
                if not self._check_input_class('rack barcode', barcode,
                                               basestring): break
            if not len(self.destination_rack_map) > 0:
                msg = 'There are no barcodes in the destination rack map!'
                self.add_error(msg)

        if self._check_input_class('excluded racks list',
                                       self.excluded_racks, list):
            for excl_rack in self.excluded_racks:
                if not self._check_input_class('excluded rack barcode',
                                               excl_rack, basestring): break

        if self._check_input_class('requested tubes list',
                                       self.requested_tubes, list):
            for req_tube in self.requested_tubes:
                if not self._check_input_class('requested tube barcode',
                                               req_tube, basestring): break

    def __get_tube_racks(self):
        """
        Fetches the tube racks for the passed barcodes from the DB.
        """
        self.add_debug('Fetch racks for barcodes ...')

        non_empty = []
        tube_rack_agg = get_root_aggregate(ITubeRack)

        for barcode in self.destination_rack_map.values():
            if len(barcode) < 1: continue
            rack = tube_rack_agg.get_by_slug(barcode)
            if rack is None:
                msg = 'Rack %s has not been found in the DB!' % (barcode)
                self.add_error(msg)
            elif len(rack.containers) > 0:
                non_empty.append(barcode)
            else:
                self._barcode_map[barcode] = rack

        if len(non_empty) > 0:
            non_empty.sort()
            msg = 'The following racks you have chosen are not empty: %s.' \
                  % (', '.join(non_empty))
            self.add_error(msg)

#    def
