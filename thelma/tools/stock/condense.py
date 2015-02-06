"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

These classes deal with stock condense.
At this, stock tubes are moved to other stock racks in order to produce empty
stock racks that can be used for ISO generation.

AAB
"""
from StringIO import StringIO
from datetime import datetime

from everest.repositories.rdb import Session
from thelma.tools.semiconstants import get_96_rack_shape
from thelma.tools.semiconstants import get_positions_for_shape
from thelma.tools.semiconstants import get_rack_position_from_indices
from thelma.tools.base import SessionTool
from thelma.tools.stock.base import RackLocationQuery
from thelma.tools.stock.base import STOCK_ITEM_STATUS
from thelma.tools.stock.base import STOCK_TUBE_SPECS
from thelma.tools.stock.base import get_stock_rack_size
from thelma.tools.stock.base import get_stock_tube_specs_db_term
from thelma.tools.worklists.tubehandler import TubeTransferData
from thelma.tools.worklists.tubehandler import XL20WorklistWriter
from thelma.tools.writers import TxtWriter
from thelma.tools.writers import create_zip_archive
from thelma.tools.utils.base import CustomQuery
from thelma.tools.utils.base import add_list_map_element
from thelma.tools.utils.base import create_in_term_for_db_queries
from thelma.tools.utils.base import get_trimmed_string
from thelma.tools.utils.base import sort_rack_positions


__docformat__ = "reStructuredText en"
__all__ = ['StockCondenser',
           'STOCK_CONDENSE_ROLES',
           'StockCondenseRack',
           'CondenseRackQuery',
           'RackContainerQuery',
           'StockCondenseReportWriter']


class StockCondenser(SessionTool):
    """
    This tools generates worklists for the XL20 tubehandler. The worklist
    aim to moved racks between stock rack in such a way that racks with
    less tubes are empty and rack with few (but not none) empty positions
    are filled.
    The resulting empty racks can be used for ISO generation.

    The output of this tool is a zip stream with 2 files: One XL20 worklist
    and one report file as overview.

    Steps:
        1. Run query determining the number of stock tubes per rack
        2. Associate racks based on tube counts
           (here we have to round, in the first we look for racks that have
            match exactly, in the second, we may split tubes)
        3. Get tube data (barcodes and positions)
        4. Complete association data
        5. Get location for the racks (for report)
        6. Generate XL20 worklist
        7. Generate report file
        8. Generate zip stream

    **Return Value:** A zip archive with two files (worklist and report)
    """

    NAME = 'Stock Condenser'

    #: The file name of the XL20 worklist file.
    WORKLIST_FILE_NAME = 'stock_condense_XL20_worklist.csv'
    #: The file name of the XL20 report file.
    REPORT_FILE_NAME = 'stock_condense_generation_report.txt'

    def __init__(self, racks_to_empty=None, excluded_racks=None, parent=None):
        """
        Constructor.

        :param int racks_to_empty: The number of empty racks the run shall
            result in (optional).
        :param excluded_racks: A list of barcodes from stock racks that shall
            not be used.
        :type excluded_racks: A list or set of rack barcodes
        """
        SessionTool.__init__(self, parent=parent)
        #: The number of empty racks the run shall result in (optional).
        self.racks_to_empty = racks_to_empty
        #: A list of barcodes from stock racks that shall not be used.
        self.excluded_racks = excluded_racks
        if excluded_racks is None: self.excluded_racks = []
        #: The number of positions in a stock rack.
        self.__stock_rack_size = None
        #: Maps :class:`StockCondenseRack` objects onto tube counts.
        self.__tube_count_map = None
        #: Maps donor racks onto rack barcodes.
        self.__donor_racks = None
        #: Maps receiver racks onto rack barcodes.
        self.__receiver_racks = None
        #: Do we look for exact tube count matches? (*True* for thie first
        #: iteration of association, *False* for the second).
        self.__look_for_exact_matches = None
        #: Shall we stop looking for rack associations?
        self.__stop_associations = None
        #: The scheduled tube transfers sorted by donator rack (ATTENTION:
        #: stores :class:`TubeTransferData` objects, no :class:`TubeTransfer`
        #: entities.
        self.__tube_transfers = None
        #: The stream for the worklist file.
        self.__worklist_stream = None
        #: The stream for the report file.
        self.__report_stream = None
        #: The zip stream containing the two files.
        self.__zip_stream = None

    def reset(self):
        """
        Resets all values except for initialisation values.
        """
        SessionTool.reset(self)
        self.__stock_rack_size = get_stock_rack_size()
        self.__tube_count_map = None
        self.__donor_racks = dict()
        self.__receiver_racks = dict()
        self.__look_for_exact_matches = True
        self.__stop_associations = False
        self.__tube_transfers = []
        self.__worklist_stream = None
        self.__report_stream = None
        self.__zip_stream = None

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Start stock condense run ...')
        self.__check_input()
        if not self.has_errors():
            self.__initialize_session()
            self.__generate_tube_count_map()
        if not self.has_errors():
            self.__associate_racks()
        if not self.has_errors():
            self.__fetch_tube_data()
        if not self.has_errors():
            self.__create_tube_transfers()
        if not self.has_errors():
            self.__fetch_location_data()
        if not self.has_errors():
            self.__write_files()
        if not self.has_errors():
            self.__create_zip_archive()
            self.return_value = self.__zip_stream
            self.add_info('Stock condense file generation completed.')

    def __initialize_session(self):
        # Initializes a session for ORM operations.
        self.__session = Session()

    def __check_input(self):
        # Checks the initialisation values.
        self.add_debug('Check input values ...')
        if not self.racks_to_empty is None:
            if self._check_input_class('number of racks to empty',
                                       self.racks_to_empty, int):
                if not self.racks_to_empty > 0:
                    msg = 'The number of racks to empty must be positive ' \
                          '(obtained: %i)!' % (self.racks_to_empty)
                    self.add_error(msg)
        if isinstance(self.excluded_racks, list):
            self.excluded_racks = set(self.excluded_racks)
        if not isinstance(self.excluded_racks, set):
            msg = 'The excluded racks must be passed as list or set ' \
                  '(obtained: %s)!' % (self.excluded_racks.__class__.__name__)
            self.add_error(msg)
        else:
            for excl_rack in self.excluded_racks:
                if not self._check_input_class('excluded rack barcode',
                                               excl_rack, basestring): break

    def __generate_tube_count_map(self):
        # Generates the :attr:`__tube_count_map` using the
        # :class:`StockCondenseQuery`.
        self.add_debug('Run rack query ...')
        try:
            query = CondenseRackQuery()
            self._run_query(query, 'Error when running rack query: ')
            if not self.has_errors():
                self.__tube_count_map = query.get_query_results()
                if len(self.__tube_count_map) < 0:
                    msg = 'The rack query did not return any racks!'
                    self.add_error(msg)
        finally:
            CondenseRackQuery.shut_down()

    def __associate_racks(self):
        # Associates donor and receiver racks.
        self.add_debug('Associate racks ...')
        # first round (exact matches only)
        self.__run_association_round()
        if not self.__stop_associations:
            self.__look_for_exact_matches = False
            self.__run_association_round()
        if self.racks_to_empty is not None and \
                                self.racks_to_empty > len(self.__donor_racks):
            msg = 'Unable to empty the requested number of racks (%i) ' \
                  'because there are not enough racks available. The ' \
                  'current run will result in %i empty racks!' \
                  % (self.racks_to_empty, len(self.__donor_racks))
            self.add_warning(msg)

    def __run_association_round(self):
        # Runs one association round.
        while len(self.__tube_count_map) > 0:
            if self.__stop_associations: break
            if not self.racks_to_empty is None and \
                        len(self.__donor_racks) >= self.racks_to_empty:
                self.__stop_associations = True
                break
            tube_counts = self.__tube_count_map.keys()
            tube_counts.sort()
            tube_count = tube_counts[0]
            if tube_count > (self.__stock_rack_size / 2):
                break
            condense_racks = self.__tube_count_map[tube_count]
            potential_donor = condense_racks.pop()
            if len(condense_racks) == 0:
                del self.__tube_count_map[tube_count]
            if potential_donor.rack_barcode in self.excluded_racks:
                continue
            found_associations = self.__find_rack_association(potential_donor)
            if not found_associations:
                add_list_map_element(self.__tube_count_map, tube_count,
                                     potential_donor)
                break

    def __find_rack_association(self, donor_rack):
        # Initialises a donor rack and finds the receiver racks for it.
        receiver_racks = dict()
        associations = dict() # receiver barcode, num tubes
        # check
        remaining_tubes = donor_rack.tube_count
        while remaining_tubes > 0:
            receiver = None
            while receiver is None:
                receiver_candidate = self.__find_receiver_rack(remaining_tubes)
                if receiver_candidate is None:
                    break
                if receiver_candidate.rack_barcode in self.excluded_racks:
                    continue
                receiver = receiver_candidate
            if receiver is None:
                return False
            if receiver.role is None:
                occupied_positions = receiver.tube_count
            else:
                occupied_positions = receiver.resulting_tube_count
            free_positions = self.__stock_rack_size - occupied_positions
            transferred_tubes = min(free_positions, remaining_tubes)
            associations[receiver.rack_barcode] = transferred_tubes
            remaining_tubes -= transferred_tubes
            receiver_racks[receiver.rack_barcode] = receiver
        # record
        donor_rack.set_role(STOCK_CONDENSE_ROLES.DONOR)
        for receiver_barcode, num_tubes in associations.iteritems():
            receiver = receiver_racks[receiver_barcode]
            if receiver.role is None:
                receiver.set_role(STOCK_CONDENSE_ROLES.RECEIVER)
            donor_rack.add_rack_association(rack_barcode=receiver_barcode,
                                              number_tubes=num_tubes)
            receiver.add_rack_association(number_tubes=num_tubes,
                                    rack_barcode=donor_rack.rack_barcode)
            self.__receiver_racks[receiver_barcode] = receiver
            resulting_receiver_tubes = receiver.resulting_tube_count
            if resulting_receiver_tubes < self.__stock_rack_size:
                add_list_map_element(self.__tube_count_map,
                                     resulting_receiver_tubes, receiver)

        self.__donor_racks[donor_rack.rack_barcode] = donor_rack
        return True

    def __find_receiver_rack(self, donor_tube_count):
        # Finds a rack to take up tubes of a donor rack.
        # try to find an excat match
        receiver_tube_count = self.__stock_rack_size - donor_tube_count
        receiver = self.__get_rack_for_tube_count(receiver_tube_count)
        if not receiver is None:
            return receiver
        if self.__look_for_exact_matches:
            return None
        # are there any racks left?
        if len(self.__tube_count_map) < 1:
            self.__stop_associations = True
            if not self.racks_to_empty is None:
                msg = 'There are not enough racks to take up the tubes for ' \
                      'the requested number of racks (emptied racks so far: ' \
                      '%i)!' % (len(self.__donor_racks))
                self.add_error(msg)
            return None
        # try to find a rack with less free positions
        while receiver_tube_count < self.__stock_rack_size:
            receiver_tube_count += 1
            if receiver_tube_count == self.__stock_rack_size: # no rack
                break
            receiver = self.__get_rack_for_tube_count(receiver_tube_count)
            if not receiver is None:
                return receiver
        # take a rack with more free positions
        # There is at least one rack left ...
        receiver_tube_count = self.__stock_rack_size - donor_tube_count
        while receiver_tube_count > 0:
            receiver_tube_count -= 1
            receiver = self.__get_rack_for_tube_count(receiver_tube_count)
            if not receiver is None:
                return receiver
        return None

    def __get_rack_for_tube_count(self, tube_count):
        # Obtains a rack for a certain tube count (to be used as receiver
        # racks). The element is removed from the pool.
        if self.__tube_count_map.has_key(tube_count):
            receiver_list = self.__tube_count_map[tube_count]
            receiver = receiver_list.pop()
            if len(receiver_list) < 1:
                receiver_list = None
                del self.__tube_count_map[tube_count]
            result = receiver
        else:
            result = None
        return result

    def __fetch_tube_data(self):
        # Finds the barcodes and positions for the tube of the picked racks
        # (using the:class:`RackContainerQuery`).
        self.add_debug('Get tube data ...')
        query = RackContainerQuery(donor_racks=self.__donor_racks.values(),
                            receiver_racks=self.__receiver_racks.values())
        self._run_query(query, base_error_msg='Error when trying to fetch ' \
                                              'tube data for racks: ')
        if not self.has_errors():
            mismatching_tubes = query.mismatching_tubes
            if len(mismatching_tubes) > 0:
                mismatching_tubes.sort()
                msg = 'Some stock racks contain tubes that do not match the ' \
                      'definition of a stock tube (status: %s, tube ' \
                      'specs: %s). The tubes have been ignored and the ' \
                      'referring rack have been processed as without the ' \
                      'tubes. Check the racks, please, or repeat the ' \
                      'worklist generation while excluding the racks. ' \
                      'Details: %s.' % (STOCK_ITEM_STATUS, STOCK_TUBE_SPECS,
                                        mismatching_tubes)
                self.add_warning(msg)

    def __create_tube_transfers(self):
        # Creates the tube transfers.
        self.add_debug('Schedule tube transfers ...')
        for donor_barcode, donor_rack in self.__donor_racks.iteritems():
            src_positions = sort_rack_positions(
                                    rack_positions=donor_rack.tubes.keys())
            transfer_count = 0
            for receiver_barcode, number_tubes in donor_rack.\
                                                associated_racks.iteritems():
                receiver_rack = self.__receiver_racks[receiver_barcode]
                free_positions = sort_rack_positions(
                                    receiver_rack.get_positions_without_tube())
                for i in range(number_tubes):
                    src_pos = src_positions[i + transfer_count]
                    trg_pos = free_positions[i]
                    tube_barcode = donor_rack.tubes[src_pos]
                    tt_data = TubeTransferData(tube_barcode=tube_barcode,
                                    src_rack_barcode=donor_barcode,
                                    src_pos=src_pos,
                                    trg_rack_barcode=receiver_barcode,
                                    trg_pos=trg_pos)
                    self.__tube_transfers.append(tt_data)
                transfer_count += number_tubes

    def __fetch_location_data(self):
        # Fetches the barcoded locations for the racks using the
        # :class:`RackLocationQuery`.
        self.add_debug('Fetch barcoded locations ...')
        all_racks = dict()
        for rack_barcode, scr in self.__donor_racks.iteritems():
            all_racks[rack_barcode] = scr
        for rack_barcode, scr in self.__receiver_racks.iteritems():
            all_racks[rack_barcode] = scr
        query = RackLocationQuery(rack_barcodes=all_racks.keys())
        self._run_query(query, 'Error when trying to find rack locations ' \
                               'in the DB: ')
        if not self.has_errors():
            location_map = query.get_query_results()
            for rack_barcode, location_str in location_map.iteritems():
                if location_str is None:
                    continue
                all_racks[rack_barcode].location = location_str

    def __write_files(self):
        # Writes the streams for two files (worklist and report).
        self.add_debug('Write files ...')
        worklist_writer = XL20WorklistWriter(self.__tube_transfers,
                                             parent=self)
        self.__worklist_stream = worklist_writer.get_result()
        if self.__worklist_stream is None:
            msg = 'Error when trying to write XL20 worklist!'
            self.add_error(msg)
        report_writer = StockCondenseReportWriter(self.__donor_racks,
                                                  self.__receiver_racks,
                                                  list(self.excluded_racks),
                                                  self.racks_to_empty,
                                                  parent=self)
        self.__report_stream = report_writer.get_result()
        if self.__report_stream is None:
            msg = 'Error when trying to generate stock condense overview.'
            self.add_error(msg)

    def __create_zip_archive(self):
        # Creates and fills the zip archive (adds files).
        self.add_info('Writes files into zip stream ...')
        self.__zip_stream = StringIO()
        zip_map = dict()
        zip_map[self.WORKLIST_FILE_NAME] = self.__worklist_stream
        zip_map[self.REPORT_FILE_NAME] = self.__report_stream
        create_zip_archive(zip_stream=self.__zip_stream, stream_map=zip_map)


class STOCK_CONDENSE_ROLES(object):
    """
    Potential functions of a rack during stock condense.
    """
    #: donor racks pass all of there tubes to receiver racks. After the
    #: execution stock condense they remain empty.
    DONOR = 'donor'
    #: Receiver racks take up tubes from donor racks.
    RECEIVER = 'receiver'


class StockCondenseRack(object):
    """
    A helper class storing the relevant data of a stock condense rack.
    """
    def __init__(self, rack_barcode, tube_count):
        """
        Constructor.

        :Note: Do not initialise directly but use

        :param str rack_barcode: The barcode of the rack.
        :param int tube_count: The current number of stock tubes in this rack.
        """
        #: The barcode of the rack.
        self.rack_barcode = rack_barcode
        #: The current number of stock tubes in this rack.
        self.tube_count = tube_count
        #: The role of the rack (donor or receiver).
        self.__role = None
        #: The barcodes of the associated racks and the number of tubes the
        #: referring rack will get or provide (:class:`dict`).
        self.__associated_racks = dict()
        #: The barcodes of the residing tube (to be added in the second query;
        #: :class:`StockCondenseTube`) mapped onto rack positions.
        self.tubes = dict()
        #: Name and index of the current barcoded location of the rack.
        self.location = None

    @property
    def role(self):
        """
        The role of the rack (donor or receiver).
        """
        return self.__role

    @property
    def resulting_tube_count(self):
        """
        The number of tubes after executed stock condense.

        :raises AttributeError: If the role has not been set yet.
        """
        associated_tube_count = sum(self.__associated_racks.values())
        if self.__role == STOCK_CONDENSE_ROLES.DONOR:
            return self.tube_count - associated_tube_count
        elif self.__role == STOCK_CONDENSE_ROLES.RECEIVER:
            return self.tube_count + associated_tube_count
        else:
            raise AttributeError('Stock condense racks without role ' \
                                 'must not have associations!')

    @property
    def associated_racks(self):
        """
        The barcodes of the associated racks and the number of tubes the
        referring rack will get or provide (:class:`dict`).
        """
        return self.__associated_racks

    def set_role(self, role):
        """
        Sets the role of the rack (donor or receiver).

        :raises AttributeError: If the role has already been set before.
        """
        if not self.__role is None:
            raise AttributeError('The role has been set before!')

        self.__role = role

    def add_rack_association(self, rack_barcode, number_tubes):
        """
        Adds another rack association (requires the :attr:`role` to be set).

        :param str rack_barcode: The barcode of the associated rack.
        :param int number_tubes: The number of tubes that will be donated to or
            received by this rack.
        :raises AttributeError: If the role has not been set yet.
        :raises ValueError: If there is already an association for this rack.
        """
        if self.__role is None:
            raise AttributeError('Stock condense racks without role ' \
                                 'must not have associations!')
        if self.__associated_racks.has_key(rack_barcode):
            raise ValueError('Rack "%s" is already associated with this rack!' \
                             % (rack_barcode))
        self.__associated_racks[rack_barcode] = number_tubes

    def add_tube(self, rack_position, tube_barcode):
        """
        Adds the barcode for the tube at the given position.

        :raise ValueError: If there is already a tube at this position.
        """
        if self.tubes.has_key(rack_position):
            msg = 'There is already a tube at position %s of rack %s!' \
                   % (rack_position.label, self.rack_barcode)
            raise ValueError(msg)
        self.tubes[rack_position] = tube_barcode

    def get_positions_without_tube(self):
        """
        Returns the positions in the rack that are not occupied at the moment.
        """
        shape_96 = get_96_rack_shape()
        free_positions = []
        for rack_pos in get_positions_for_shape(shape_96):
            if not self.tubes.has_key(rack_pos):
                free_positions.append(rack_pos)
        return free_positions

    def __str__(self):
        return '%s, %i tubes' % (self.rack_barcode, self.tube_count)

    def __repr__(self):
        str_format = '<%s %s: %s, tube count: %s, number remaining tubes: %s>'
        params = (self.__class__.__name__, self.__role, self.rack_barcode,
                  self.tube_count, self.resulting_tube_count)
        return str_format % params


class CondenseRackQuery(CustomQuery):
    """
    Runs the first query (number of tubes per stock rack) and converts the
    results into :class:`StockCondenseRack` objects.

    There might only be one object at a time (singleton-like).
    """
    _instance = None

    QUERY_TEMPLATE = \
    'SELECT DISTINCT x.rack_barcode AS rack_barcode, ' \
                    'x.desired_count AS tube_count ' \
    'FROM container, container_barcode, containment, container_specs, ' \
       '(SELECT rack.rack_id, rack.barcode as rack_barcode,  ' \
               'rack_specs.number_rows, rack_specs.number_columns, ' \
               'count(container.container_id) as desired_count ' \
        'FROM rack, containment, container, container_specs, rack_specs ' \
        'WHERE rack.rack_id = containment.holder_id ' \
        'AND rack.rack_specs_id = rack_specs.rack_specs_id ' \
        'AND container.container_id = containment.held_id ' \
        'AND container.container_specs_id =  ' \
                            'container_specs.container_specs_id ' \
        'AND container_specs.name in %s ' \
        'AND container.item_status = \'%s\' ' \
        'GROUP BY rack_id, rack.barcode, rack_specs.number_rows,  ' \
                'rack_specs.number_columns ' \
        'HAVING count(container.container_id) > 0) AS x ' \
    'WHERE container.container_id = containment.held_id ' \
    'AND containment.holder_id = x.rack_id ' \
    'AND container.container_specs_id = container_specs.container_specs_id ' \
    'AND container.container_id = container_barcode.container_id ' \
    'AND container_specs.name in %s ' \
    'AND container.item_status = \'%s\' ' \
    'AND x.desired_count < %i ' \
    'ORDER BY x.desired_count DESC, x.rack_barcode '

    #: The query result column (required to parse the query results).
    COLUMN_NAMES = ('rack_barcode', 'tube_count')
    #: The index of the rack barcode within the query result.
    RACK_BARCODE_INDEX = 0
    #: The index of the tube count within the query result.
    TUBE_COUNT_INDEX = 1

    RESULT_COLLECTION_CLS = dict

    def __new__(self):
        """
        Fetches the current instance of this class or get a creates a one
        if there is none.

        :raises ValueError: If there is already an instance present.
        """
        if self._instance is None:
            self._instance = object.__new__(self)
            return self._instance
        else:
            raise ValueError('There is already an instance of this class!')

    @classmethod
    def shut_down(cls):
        """
        Deletes the current :attr:`_instance`.
        """
        cls._instance = None

    def _get_params_for_sql_statement(self):
        tube_specs = get_stock_tube_specs_db_term()
        return (tube_specs, STOCK_ITEM_STATUS, tube_specs, STOCK_ITEM_STATUS,
                get_stock_rack_size())

    def _store_result(self, result_record):
        rack_barcode = result_record[self.RACK_BARCODE_INDEX]
        tube_count = result_record[self.TUBE_COUNT_INDEX]
        scr = StockCondenseRack(rack_barcode=rack_barcode,
                                tube_count=tube_count)
        add_list_map_element(self._results, tube_count, scr)

    def __str__(self):
        return self.__class__.__name__

    def __repr__(self):
        return self.__class__.__name__


class RackContainerQuery(CustomQuery):
    """
    Runs the second query (getting the tube information for each rack).
    The results are added to the :class:`StockCondenseRack` objects.
    """
    QUERY_TEMPLATE = \
        'SELECT r.barcode AS rack_barcode, rc.row AS row_index, ' \
            'rc.col AS column_index, cb.barcode AS tube_barcode, ' \
            'c.item_status AS tube_status, cs.name AS tube_specs_name ' \
        'FROM container c, container_barcode cb, containment rc, rack r, ' \
            'container_specs cs ' \
        'WHERE c.container_id = rc.held_id ' \
        'AND c.container_specs_id = cs.container_specs_id ' \
        'AND c.container_id = cb.container_id ' \
        'AND rc.holder_id = r.rack_id ' \
        'AND r.barcode IN %s ' \
        'ORDER BY r.barcode'

    #: The query result column (required to parse the query results).
    COLUMN_NAMES = ('rack_barcode', 'row_index', 'column_index',
                     'tube_barcode', 'tube_status', 'tube_specs_name')
    #: The index of the rack barcode within the query result.
    RACK_BARCODE_INDEX = 0
    #: The index of the row index within the query result.
    ROW_INDEX_INDEX = 1
    #: The index of the column index within the query result.
    COLUMN_INDEX_INDEX = 2
    #: The index of the tube barcode within the query result.
    TUBE_BARCODE_INDEX = 3
    #: The index of the tube status within the query result.
    TUBE_STATUS_INDEX = 4
    #: The index of the tube specs name within the query result.
    TUBE_SPECS_NAME_INDEX = 5

    def __init__(self, donor_racks, receiver_racks):
        """
        Constructor.

        :param donor_racks: The donor racks mapped onto rack barcodes.
        :type donor_racks: :class:`list` or iterable
        :param receiver_racks: The receiver racks mapped onto rack barcodes.
        :type receiver_racks: :class:`list` or iterable
        """
        CustomQuery.__init__(self)
        #: All stock condense racks mapped onto rack barcodes.
        self.rack_map = dict()
        for donor_rack in donor_racks:
            self.rack_map[donor_rack.rack_barcode] = donor_rack
        for receiver_rack in receiver_racks:
            self.rack_map[receiver_rack.rack_barcode] = receiver_rack
        #: Stores data about found tubes that do not match the stock constraints
        self.mismatching_tubes = []

    def _get_params_for_sql_statement(self):
        rack_term = create_in_term_for_db_queries(self.rack_map.keys(),
                                                  as_string=True)
        return (rack_term)

    def _store_result(self, result_record):
        rack_barcode = result_record[self.RACK_BARCODE_INDEX]
        scr = self.rack_map[rack_barcode]
        rack_pos = get_rack_position_from_indices(
                            row_index=result_record[self.ROW_INDEX_INDEX],
                            column_index=result_record[self.COLUMN_INDEX_INDEX])
        tube_barcode = result_record[self.TUBE_BARCODE_INDEX]
        tube_status = result_record[self.TUBE_STATUS_INDEX]
        if not tube_status == STOCK_ITEM_STATUS:
            info = '%s (status: %s, rack: %s)' \
                    % (str(tube_barcode), tube_status, rack_barcode)
            self.mismatching_tubes.append(info)
            return None
        tube_specs_name = result_record[self.TUBE_SPECS_NAME_INDEX]
        if not tube_specs_name in STOCK_TUBE_SPECS:
            info = '%s (tube specs: %s, rack: %s)' \
                    % (str(tube_barcode), tube_specs_name, rack_barcode)
            self.mismatching_tubes.append(info)
            return None
        scr.add_tube(rack_pos, tube_barcode)

    def __repr__(self):
        str_format = '<%s number of racks: %s>'
        params = (self.__class__.__name__, len(self.rack_map))
        return str_format % params


class StockCondenseReportWriter(TxtWriter):
    """
    This class generates a report and overview file summarising the
    condense run.

    **Return Value:** file stream (TXT format)
    """
    NAME = 'Stock Condense Report Writer'
    #: The main headline of the file.
    BASE_MAIN_HEADER = 'Stock Condense Worklist Generation Report / %s / %s'
    #: The header text for the general section.
    GENERAL_HEADER = 'General Settings'
    #: This line presents the number of racks to empty (user input).
    RACK_TO_EMTPTY_LINE = 'Racks to empty (user input): %s'
    #: Is added of there was no user input for the number of racks to empty.
    NOT_SPECIFIED_MARKER = 'not specified'
    #: The line presents the total number of tubes moved.
    TUBES_MOVED_LINE = 'Number of tubes to move: %i'
    #: The header text for the donor rack section.
    DONOR_HEADER = 'Donating Racks'
    #: The header text for the receiver rack section.
    RECEIVER_HEADER = 'Receiving Racks'
    #: This line presents the number of racks.
    COUNT_LINE = 'Number of racks: %i'
    #: Use when the location of a rack is unknown.
    UNKNOWN_MARKER = 'unknown'
    #: The header text for the excluded racks section.
    EXCLUDED_RACKS_HEADER = 'Excluded Racks'
    #: Is used if there are no exlcuded racks.
    NO_EXCLUDED_RACKS_MARKER = 'no excluded racks'

    def __init__(self, donor_racks, receiver_racks, excluded_racks,
                 racks_to_empty, parent=None):
        """
        Constructor.

        :param dict donor_racks: The donor racks mapped onto rack barcodes.
        :param dict receiver_racks: The receiver racks mapped onto rack
            barcodes.
        :param list excluded_racks: Barcodes from racks that should not be
            used.
        :param int racks_to_empty: The number of empty racks the run shall
            result in.
        """
        TxtWriter.__init__(self, parent=parent)
        #: The donor racks mapped onto rack barcodes.
        self.donor_racks = donor_racks
        #: The receiver racks mapped onto rack barcodes.
        self.receiver_racks = receiver_racks
        #: Barcodes from racks that shall not be used.
        self.excluded_racks = excluded_racks
        #: The number of empty racks the run shall result in (optional).
        self.racks_to_empty = racks_to_empty

    def _check_input(self):
        """
        Checks if the tools has obtained correct input values.
        """
        self.add_debug('Check input values ...')
        if not self.racks_to_empty is None:
            self._check_input_class('number of racks to empty',
                                    self.racks_to_empty, int)
        if self._check_input_class('donor map', self.donor_racks, dict):
            for barcode, scr in self.donor_racks.iteritems():
                if not self._check_input_class('donor rack barcode', barcode,
                                               basestring): break
                if not self._check_input_class('donor rack', scr,
                                               StockCondenseRack): break
        if self._check_input_class('receiver map', self.receiver_racks, dict):
            for barcode, scr in self.receiver_racks.iteritems():
                if not self._check_input_class('receiver rack barcode', barcode,
                                               basestring): break
                if not self._check_input_class('receiver rack', scr,
                                               StockCondenseRack): break
        if self._check_input_class('excluded racks list', self.excluded_racks,
                                   list):
            for rack_barcode in self.excluded_racks:
                if not self._check_input_class('excluded rack barcode',
                                        rack_barcode, basestring): break

    def _write_stream_content(self):
        """
        Writes into the streams.
        """
        self.add_debug('Write stream ...')
        self.__write_main_headline()
        self.__write_general_section()
        self.__write_condense_racks_section(self.DONOR_HEADER,
                                           self.donor_racks)
        self.__write_condense_racks_section(self.RECEIVER_HEADER,
                                           self.receiver_racks)
        self.__write_excluded_racks_section()

    def __write_main_headline(self):
        # Writes the main head line.
        now = datetime.now()
        date_string = now.strftime('%d.%m.%Y')
        time_string = now.strftime('%H:%M')
        main_headline = self.BASE_MAIN_HEADER % (date_string, time_string)
        self._write_headline(main_headline, underline_char='=',
                             preceding_blank_lines=0, trailing_blank_lines=1)

    def __write_general_section(self):
        # Writes the GENERAL section.
        self._write_headline(self.GENERAL_HEADER, preceding_blank_lines=1)
        if self.racks_to_empty is None:
            rack_line = self.RACK_TO_EMTPTY_LINE % (self.NOT_SPECIFIED_MARKER)
        else:
            rack_line = self.RACK_TO_EMTPTY_LINE \
                                    % (get_trimmed_string(self.racks_to_empty))
        total_transfer_count = 0
        for scr in self.donor_racks.values():
            for transfer_count in scr.associated_racks.values():
                total_transfer_count += transfer_count
        moved_tubes_line = self.TUBES_MOVED_LINE % (total_transfer_count)
        general_lines = [rack_line, moved_tubes_line]
        self._write_body_lines(general_lines)

    def __write_condense_racks_section(self, header, rack_map):
        # Writes the DONOR RACKS or the RECEIVER RACKS section.
        self._write_headline(header)
        rack_lines = []
        barcodes = rack_map.keys()
        barcodes.sort()
        for rack_barcode in barcodes:
            scr = rack_map[rack_barcode]
            loc_info = self.UNKNOWN_MARKER
            if not scr.location is None: loc_info = scr.location
            num_transfers = sum(scr.associated_racks.values())
            scr_line = '%s (%s, %i tubes)' \
                                % (rack_barcode, loc_info, num_transfers)
            rack_lines.append(scr_line)
        rack_lines.append(' ')
        rack_lines.append(self.COUNT_LINE % (len(rack_map)))
        self._write_body_lines(rack_lines)

    def __write_excluded_racks_section(self):
        # Writes the excluded racks section.
        self._write_headline(self.EXCLUDED_RACKS_HEADER)
        if len(self.excluded_racks) < 1:
            lines = [self.NO_EXCLUDED_RACKS_MARKER]
        else:
            lines = []
            for rack_barcode in self.excluded_racks:
                lines.append(rack_barcode)
        self._write_body_lines(line_list=lines)
