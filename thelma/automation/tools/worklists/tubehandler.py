"""
Classes for tubehandler (XL20) related tasks.
"""
from StringIO import StringIO

from thelma.automation.handlers.tubehandler import XL20OutputParserHandler
from thelma.automation.tools.base import BaseTool
from thelma.automation.tools.writers import CsvColumnParameters
from thelma.automation.tools.writers import CsvWriter
from thelma.automation.utils.base import add_list_map_element
from thelma.models.rack import TubeRack
from thelma.models.tubetransfer import TubeTransfer
from thelma.models.tubetransfer import TubeTransferWorklist
from thelma.models.user import User
from thelma.utils import get_utc_time


__docformat__ = 'reStructuredText en'

__all__ = ['TubeTransferData',
           'BaseXL20WorklistWriter',
           'XL20WorklistWriter',
           'TubeTransferExecutor']


class TubeTransferData(object):
    """
    A helper class mimicking a :class:`TubeTransfer` entity.
    Since often we do not have entities when creating a XL20 worklist stream,
    but only barcodes, this class works gets along with barcodes insteads of
    tubes and racks.
    """
    def __init__(self, tube_barcode, src_rack_barcode, src_pos,
                 trg_rack_barcode, trg_pos):
        """
        Constructor.

        :param str tube_barcode: The barcode of the tube to be moved.
        :param str src_rack_barcode: The barcode of the donor rack.
        :param src_pos: The rack position of the tube in the source rack.
        :type src_pos: :class:`thelma.models.rack.RackPosition`
        :param str trg_rack_barcode: The barcode of the receiver rack.
        :param trg_pos: The rack position of the tube in the target rack.
        :type trg_pos: :class:`thelma.models.rack.RackPosition`
        """
        #: The barcode of the tube to be moved.
        self.tube_barcode = tube_barcode
        #: The barcode of the donor rack.
        self.src_rack_barcode = src_rack_barcode
        #: The label of the rack position of the tube within the donor rack.
        self.src_pos = src_pos
        #: The barcode of the receiver rack.
        self.trg_rack_barcode = trg_rack_barcode
        #: The label of the new rack position of the tube (within the receiver
        #: rack).
        self.trg_pos = trg_pos

    @classmethod
    def from_tube_transfer(cls, tube_transfer):
        """
        Factory method creating :class:`TubeTransferData` object from a
        :class:`TubeTransfer` entity.

        :param tube_transfer: The tube transfer entity.
        :type tube_transfer: :class:`thelma.models.tubetransfer.TubeTransfer`
        :rtype: :class:`TubeTransferData`
        """
        return TubeTransferData(tube_transfer.tube.barcode,
                                tube_transfer.source_rack.barcode,
                                tube_transfer.source_position,
                                tube_transfer.target_rack.barcode,
                                tube_transfer.target_position)

    def __str__(self):
        return self.tube_barcode

    def __repr__(self):
        str_format = '<%s %s donated from: %s (%s), going to: %s (%s)>'
        params = (self.__class__.__name__, self.tube_barcode,
                  self.src_rack_barcode, self.src_pos.label,
                  self.trg_rack_barcode, self.trg_pos.label)
        return str_format % params


class BaseXL20WorklistWriter(CsvWriter):
    """
    This tool writes a worklist for the XL20 (tube handler). The
    :func:`_store_column_values` function can be customised at will.

    **Return Value:** the XL20 worklist as stream
    """
    #: The index of the source rack column.
    SOURCE_RACK_INDEX = 0
    #: The header for the source rack column.
    SOURCE_RACK_HEADER = 'Source Rack'
    #: The index of the source position column.
    SOURCE_POSITION_INDEX = 1
    #: The header of the source position column.
    SOURCE_POSITION_HEADER = 'Source Position'
    #: The index for the tube barcode column.
    TUBE_BARCODE_INDEX = 2
    #: The header for the tube barcode column.
    TUBE_BARCODE_HEADER = 'Tube Barcode'
    #: The index for the destination rack column.
    DEST_RACK_INDEX = 3
    #: The header for the destination rack column.
    DEST_RACK_HEADER = 'Destination Rack'
    #: The index for the destination position column.
    DEST_POSITION_INDEX = 4
    #: The header for the destination position column.
    DEST_POSITION_HEADER = 'Destination Position'

    def __init__(self, parent=None):
        CsvWriter.__init__(self, parent=parent)
        #: The values for the source rack column.
        self._source_rack_values = None
        #: The values for the source position column.
        self._source_position_values = None
        #: The values of the tube barcode column.
        self._tube_barcode_values = None
        #: The values of the destination rack column.
        self._dest_rack_values = None
        #: The values of the destination position column.
        self._dest_position_values = None

    def reset(self):
        """
        Resets all attributes except the initialization values.
        """
        CsvWriter.reset(self)
        self._source_rack_values = []
        self._source_position_values = []
        self._tube_barcode_values = []
        self._dest_rack_values = []
        self._dest_position_values = []

    def _init_column_map_list(self):
        """
        Creates the :attr:`_column_map_list`
        """
        self._check_input()
        if not self.has_errors():
            self._store_column_values()
        if not self.has_errors():
            self.__generate_columns()

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        raise NotImplementedError('Abstract method.')

    def _store_column_values(self):
        """
        Stores the column values.
        """
        raise NotImplementedError('Abstract method.')

    def __generate_columns(self):
        """
        Generates the columns for the report.
        """
        self.add_debug('Generate columns ...')
        src_rack_column = CsvColumnParameters.create_csv_parameter_map(
                    self.SOURCE_RACK_INDEX, self.SOURCE_RACK_HEADER,
                    self._source_rack_values)
        src_pos_column = CsvColumnParameters.create_csv_parameter_map(
                    self.SOURCE_POSITION_INDEX, self.SOURCE_POSITION_HEADER,
                    self._source_position_values)
        tube_barcode_column = CsvColumnParameters.create_csv_parameter_map(
                    self.TUBE_BARCODE_INDEX, self.TUBE_BARCODE_HEADER,
                    self._tube_barcode_values)
        dest_rack_column = CsvColumnParameters.create_csv_parameter_map(
                    self.DEST_RACK_INDEX, self.DEST_RACK_HEADER,
                    self._dest_rack_values)
        dest_pos_column = CsvColumnParameters.create_csv_parameter_map(
                    self.DEST_POSITION_INDEX, self.DEST_POSITION_HEADER,
                    self._dest_position_values)
        self._column_map_list = [src_rack_column, src_pos_column,
                                 tube_barcode_column, dest_rack_column,
                                 dest_pos_column]


class XL20WorklistWriter(BaseXL20WorklistWriter):
    """
    An XL20 worklist writer that generates a XL20 worklist file using a list
    of :class:`TubeTransfer` or :class:`TubeTransferData` items. The writer
    can be run without further adjustments.

    **Return Value:** the XL20 worklist as stream
    """
    NAME = 'XL20 Worklist Writer'

    def __init__(self, tube_transfers, parent=None):
        """
        Constructor.

        :param tube_transfer: A list of :class:`TubeTransfer` instances.
        :type tube_transfer: :class:`list`
        """
        BaseXL20WorklistWriter.__init__(self, parent=parent)
        #: A list of :class:`TubeTransfer` or :class:`TubeTransferData`
        #: instances.
        self.tube_transfers = tube_transfers
        #: The tube transfers as :class:`TubeTransferData`.
        self._tube_transfer_data = None

    def _check_input(self):
        """
        Checks the initialization values.
        """
        if self._check_input_class('tube transfer list', self.tube_transfers,
                                   list):
            all_tt_data = []
            for tt in self.tube_transfers:
                if isinstance(tt, TubeTransferData):
                    all_tt_data.append(tt)
                elif isinstance(tt, TubeTransfer):
                    conv_tt = TubeTransferData.from_tube_transfer(tt)
                    all_tt_data.append(conv_tt)
                else:
                    msg = 'The tube transfer must be a %s or a %s type ' \
                          '(obtained: %s).' % (TubeTransfer.__name__,
                            TubeTransferData.__name__, tt.__class__.__name__)
                    self.add_error(msg)
                    break
            self._tube_transfer_data = all_tt_data

    def _store_column_values(self):
        """
        Stores the column values.
        """
        self.add_debug('Store column values ...')
        src_rack_map = dict()
        for tube_transfer in self._tube_transfer_data:
            add_list_map_element(src_rack_map, tube_transfer.src_rack_barcode,
                                 tube_transfer)
        src_racks = sorted(src_rack_map.keys())
        for src_rack in src_racks:
            tube_barcodes = sorted(src_rack_map[src_rack],
                                   cmp=lambda tt1, tt2: cmp(tt1.tube_barcode,
                                                            tt2.tube_barcode))
            for tube_transfer in tube_barcodes:
                self._source_rack_values.append(src_rack)
                self._source_position_values.append(tube_transfer.src_pos.label)
                self._tube_barcode_values.append(tube_transfer.tube_barcode)
                self._dest_rack_values.append(tube_transfer.trg_rack_barcode)
                self._dest_position_values.append(tube_transfer.trg_pos.label)


class TubeTransferExecutor(BaseTool):
    """
    Executes passed tube transfers.

    **Return Value:** The executed :class:`TubeTransferWorklist`
    """
    NAME = 'Tube Transfer Executor'

    def __init__(self, tube_transfers, user, parent=None):
        """
        Constructor.

        :param list tube_transfer: A list of :class:`TubeTransfer` entities
            to execute.
        :type tube_transfer: :class:`list`
        :param user: The user conducting the update.
        :type user: :class:`thelma.models.user.User`
        """
        BaseTool.__init__(self, parent=parent)
        #: The tube transfer entities to execute.
        self.tube_transfers = tube_transfers
        #: The user conducting the update.
        self.user = user
        #: The tubes of each rack mapped onto rack positions (racks as
        #: barcodes).
        self.__rack_containers = None

    def reset(self):
        BaseTool.reset(self)
        self.__rack_containers = dict()

    def run(self):
        self.reset()
        self.add_info('Start tube transfer execution ...')
        self.__check_input()
        if not self.has_errors():
            self.__scan_racks()
        if not self.has_errors():
            self.__check_transfers()
        if not self.has_errors():
            self.__update_tube_locations()
        if not self.has_errors():
            self.return_value = TubeTransferWorklist(user=self.user,
                                        tube_transfers=self.tube_transfers,
                                        timestamp=get_utc_time())
            self.add_info('Tube transfer executor run completed.')

    def __check_input(self):
        # Checks the initialization values.
        self.add_debug('Check input values ...')
        if self._check_input_class('tube transfer list', self.tube_transfers,
                                   list):
            for tt in self.tube_transfers:
                if not self._check_input_class('tube transfer', tt,
                                               TubeTransfer): break
        self._check_input_class('user', self.user, User)

    def __scan_racks(self):
        # Maps the tube of each rack onto its rack position (to simplify
        # access at later stage).
        self.add_debug('Scan involved racks ...')
        racks = set()
        for tt in self.tube_transfers:
            racks.add(tt.source_rack)
            racks.add(tt.target_rack)
        for rack in racks: self.__search_rack_tubes(rack)

    def __search_rack_tubes(self, rack):
        # Searches the tubes of the given rack and stores them.
        barcode = rack.barcode
        if not isinstance(rack, TubeRack):
            msg = 'Rack %s is not a tube rack (but a %s).' \
                   % (barcode, rack.__class__.__name__)
            self.add_error(msg)
        elif not self.__rack_containers.has_key(barcode):
            tube_map = dict()
            for tube in rack.containers:
                tube_map[tube.location.position] = tube
            self.__rack_containers[barcode] = tube_map

    def __check_transfers(self):
        # Makes sure that each transfer is executable.
        self.add_debug('Check transfers ...')
        occupied_trg_position = []
        deviating_src_position = []
        for tt in self.tube_transfers:
            tube_barcode = tt.tube.barcode
            src_pos = tt.source_position
            src_rack_barcode = tt.source_rack.barcode
            src_tube_map = self.__rack_containers[src_rack_barcode]
            if not src_tube_map.has_key(src_pos):
                info = '%s in rack %s (expected tube: %s, no tube found)' \
                        % (src_pos.label, src_rack_barcode, tube_barcode)
                deviating_src_position.append(info)
            else:
                found_src_tube = src_tube_map[src_pos]
                if not found_src_tube.barcode == tube_barcode:
                    info = '%s in rack %s (expected tube: %s, found: %s)' \
                           % (src_pos.label, src_rack_barcode, tube_barcode,
                              found_src_tube.barcode)
                    deviating_src_position.append(info)
            trg_pos = tt.target_position
            trg_rack_barcode = tt.target_rack.barcode
            trg_tube_map = self.__rack_containers[trg_rack_barcode]
            if trg_tube_map.has_key(trg_pos):
                found_trg_tube = trg_tube_map[trg_pos]
                info = '%s in rack %s (scheduled for: %s, tube found: %s)' \
                        % (trg_pos.label, trg_rack_barcode, tube_barcode,
                           found_trg_tube.barcode)
                occupied_trg_position.append(info)
        if len(deviating_src_position) > 0:
            deviating_src_position.sort()
            msg = 'Some rack positions did not contain the expected tubes: ' \
                  '%s.' % (self._get_joined_str(deviating_src_position,
                                                separator=' - '))
            self.add_error(msg)
        if len(occupied_trg_position) > 0:
            occupied_trg_position.sort()
            msg = 'Some transfer target positions are not empty: %s.' \
                  % (self._get_joined_str(occupied_trg_position,
                                          separator=' - '))
            self.add_error(msg)

    def __update_tube_locations(self):
        # Updates the container locations and the container lists of the
        # affected tubes and racks.
        self.add_debug('Update tube locations ...')
        non_empty = []
        for tt in self.tube_transfers:
            tube = tt.tube
            # we do not need to check the source rack and positions
            # because this data has just been retrieved
            trg_rack = tt.target_rack
            trg_pos = tt.target_position
            if not trg_rack.is_empty(trg_pos):
                info = '%s (target position: %s (%s), found there: %s)' % \
                        (tube.barcode, trg_pos.label, trg_rack.barcode,
                         trg_rack.container_locations[trg_pos].barcode)
                non_empty.append(info)
                continue
        if len(non_empty) > 0:
            msg = 'Some tube target positions are not empty: %s!' \
                  % (', '.join(sorted(non_empty)))
            self.add_error(msg)
        else:
            for tt in self.tube_transfers:
                tube = tt.tube
                tt.source_rack.remove_tube(tube)
                tt.target_rack.add_tube(tube=tube, position=tt.target_position)


class XL20Executor(BaseTool):
    """
    This tools update the location of tubes using an XL20 output file to
    generate the required :class:`TubeTransfer` entities.

    **Return Value:** The executed :class:`TubeTransferWorklist`.
    """
    NAME = 'XL20 Executor'

    def __init__(self, output_file_stream, user, parent=None):
        """
        Constructor.

        :param output_file_stream: The content of the XL20 output file, as
            :class:`basestring`, file or :class:`StringIO`.
        :param user: The user who wants to update the DB.
        :type user: :class:`thelma.models.user.User`
        """
        BaseTool.__init__(self, parent=parent)
        #: The XL20 output file.
        self.output_file_stream = output_file_stream
        #: The user who wants to update the DB.
        self.user = user
        #: The tube transfers for the DB adjustment.
        self.__tube_transfers = None
        #: The tube transfer worklist (only for *True* :attr:`adjust_database`).
        self.__tube_transfer_worklist = None
        #: The timestamp for the worklist (the earliest timestamp from the file)
        self.__timestamp = None

    def reset(self):
        BaseTool.reset(self)
        self.__tube_transfers = None
        self.__tube_transfer_worklist = None
        self.__timestamp = None

    def run(self):
        self.reset()
        self.add_info('Start run ...')
        self.__check_input()
        if not self.has_errors():
            self.__parse_file()
        if not self.has_errors():
            self.__execute_transfers()
        if not self.has_errors():
            self.return_value = self.__tube_transfer_worklist
            self.add_info('Update completed.')

    def __check_input(self):
        # Checks the initialisation values ...
        self.add_debug('Check input values ...')
        if not isinstance(self.output_file_stream,
                          (file, basestring, StringIO)):
            msg = 'The XL20 output file must be passed as file, basestring ' \
                  'or StringIO object (obtained: %s).' \
                  % (self.output_file_stream.__class__.__name__)
            self.add_error(msg)

        self._check_input_class('user', self.user, User)

    def __parse_file(self):
        # Parses the output file. The parser handler returns a list of
        # :class:`TubeTransfer` entities.
        self.add_debug('Parse file ...')
        parser_handler = XL20OutputParserHandler(self.output_file_stream,
                                                 parent=self)
        self.__tube_transfers = parser_handler.get_result()
        if self.__tube_transfers is None:
            msg = 'Error when trying to parser XL20 output file.'
            self.add_error(msg)
        else:
            self.__timestamp = parser_handler.get_timestamp()

    def __execute_transfers(self):
        # Makes use of the :class:`TubeTransferExecutor.` The timestamp of the
        # generated worklist is overwritten by the file timestamp.
        self.add_debug('Update tube positions ...')
        executor = TubeTransferExecutor(self.__tube_transfers, self.user,
                                        parent=self)
        self.__tube_transfer_worklist = executor.get_result()
        if self.__tube_transfer_worklist is None:
            msg = 'Error when trying to update tube positions.'
            self.add_error(msg)
        else:
            self.__tube_transfer_worklist.timestamp = self.__timestamp
