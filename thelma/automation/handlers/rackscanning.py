"""
This handler converts the results of the rack scanning parser into a
:class:`RackScanningLayout` object.

AAB
"""
from re import match
from thelma.automation.handlers.base import BaseParserHandler
from thelma.automation.parsers.rackscanning import RackScanningParser
from thelma.automation.semiconstants import get_96_rack_shape
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.entities.rack import RACK_BARCODE_REGEXP
from thelma.entities.rack import RACK_POSITION_REGEXP
from thelma.entities.rack import TubeRack
from thelma.utils import get_utc_time

__docformat__ = 'reStructuredText en'

__all__ = ['AnyRackScanningParserHandler',
           'CenixRackScanningParserHandler',
           'RackScanningLayout',
           ]


class _RackScanningParserHandler(BaseParserHandler):
    """
    Converts the results of the :class:`RackScanningParser` into a
    :class:`RackScanningLayout` object.

    **Return Value:** :class:`RackScanningLayout`
    """
    NAME = 'Rack Scanning Output File Parser Handler'

    _PARSER_CLS = RackScanningParser

    def __init__(self, stream, parent=None):
        BaseParserHandler.__init__(self, stream=stream, parent=parent)
        #: The rack scanning layout.
        self.__rs_layout = None
        #: Intermediate error storage.
        self.__invalid_labels = None
        self.__position_out_of_range = None
        self.__duplicate_positions = None
        self.__duplicate_tubes = None

    def reset(self):
        """
        Resets all values except for the initialisation values.
        """
        BaseParserHandler.reset(self)
        self.__rs_layout = None
        self.__invalid_labels = []
        self.__position_out_of_range = []
        self.__duplicate_positions = set()
        self.__duplicate_tubes = set()

    def _initialize_parser(self):
        """
        Initialises the parser.
        """
        self.parser = RackScanningParser(self.stream, parent=self)

    def _check_rack_barcode(self):
        """
        Checks the validity of the parsed barcode.
        """
        raise NotImplementedError('Abstract method.')

    def _convert_results_to_entity(self):
        """
        Converts the parsing results into a :class:`RackScanningLayout`
        (no entity class).
        """
        self.add_info('Convert parser results ...')
        self._check_rack_barcode()
        if not self.has_errors():
            self.__rs_layout = RackScanningLayout(
                                rack_barcode=self.parser.rack_barcode,
                                timestamp=self.parser.timestamp)
            self.__add_positions()
            self.__record_errors()
        if not self.has_errors():
            self.return_value = self.__rs_layout
            self.add_info('Conversion completed.')

    def __add_positions(self):
        """
        Checks position map of the parser and stores the data.
        """
        self.add_debug('Check and store position data ...')

        for pos_label, tube_barcode in self.parser.position_map.iteritems():

            if not match(RACK_POSITION_REGEXP, pos_label):
                self.__invalid_labels.append(pos_label)
                continue
            rack_pos = get_rack_position_from_label(pos_label)

            valid_values = True
            if rack_pos in self.__rs_layout.get_positions():
                self.__duplicate_positions.add(pos_label)
                valid_values = False
            if tube_barcode in self.__rs_layout.get_tube_barcodes():
                self.__duplicate_tubes.add(tube_barcode)
                valid_values = False

            if not valid_values: continue
            if tube_barcode is None: continue
            try:
                self.__rs_layout.add_position(rack_pos, tube_barcode)
            except IndexError:
                self.__position_out_of_range.append(pos_label)

    def __record_errors(self):
        """
        Records the errors that have been found during the conversion.
        """
        if len(self.__invalid_labels) > 0:
            self.__invalid_labels.sort()
            msg = 'There are invalid labels in the file: %s.' \
                   % (self.__invalid_labels)
            self.add_error(msg)

        if len(self.__duplicate_positions) > 0:
            error_list = list(self.__duplicate_positions)
            error_list.sort()
            msg = 'Some position are specified multiple times: %s!' \
                  % (self.__duplicate_positions)
            self.add_error(msg)

        if len(self.__duplicate_tubes) > 0:
            error_list = list(self.__duplicate_tubes)
            error_list.sort()
            msg = 'Some tubes appear multiple times: %s!' % (error_list)
            self.add_error(msg)

        if len(self.__position_out_of_range) > 0:
            self.__position_out_of_range.sort()
            msg = 'Some positions specified in the file are out of the range ' \
                  'of a 96-well plate: %s.' % (self.__position_out_of_range)
            self.add_error(msg)


class CenixRackScanningParserHandler(_RackScanningParserHandler):
    def _check_rack_barcode(self):
        self.add_debug('Check rack barcode ...')
        rack_barcode = self.parser.rack_barcode
        if match(RACK_BARCODE_REGEXP, rack_barcode) is None:
            msg = 'The barcode of the scanned rack (%s) does not ' \
                  'match the rack barcode pattern!' % (rack_barcode)
            self.add_error(msg)


class AnyRackScanningParserHandler(_RackScanningParserHandler):
    def _check_rack_barcode(self):
        self.add_debug('Check rack barcode ...')
        rack_barcode = self.parser.rack_barcode
        if not isinstance(rack_barcode, basestring):
            msg = 'The barcode of the scanned rack must be a string.'
            self.add_error(msg)



class RackScanningLayout(object):
    """
    Stores the tube barcodes for a complete 96-well tube rack.

    :Note: This is no subclass of :class:`WorkingPosition`
    """

    def __init__(self, rack_barcode, timestamp):
        """
        Constructor
        """
        #: The barcode of the scanned rack.
        self.rack_barcode = rack_barcode
        #: The timestamp of the scanning file.
        self.timestamp = timestamp

        #: The shape of the layout (:class:`thelma.entities.rack.RackShape`)
        self.shape = get_96_rack_shape()
        #: Maps tube barcodes onto rack positions.
        self._position_map = dict()

    @classmethod
    def from_rack(cls, tube_rack):
        """
        Creates a :class:`RackScanningLayout` using the data of a the passed
            rack.

        :param tube_rack: The tube rack to create the layout for.
        :type tube_rack: :class:`thelma.entities.rack.TubeRack`
        :raises TypeError: If the tube rack is the wrong type (incl. other
            rack types).
        :return: :class:`RackScanningLayout`
        """
        if not isinstance(tube_rack, TubeRack):
            msg = 'The tube rack must be a %s type (obtained: %s).' \
                  % (TubeRack.__class__.__name__, tube_rack.__class__.__name__)
            raise TypeError(msg)
        rsl = RackScanningLayout(rack_barcode=tube_rack.barcode,
                                 timestamp=get_utc_time())
#        for tube in tube_rack.containers:
#            rack_pos = tube.location.position
#            rsl.add_position(rack_pos, tube.barcode)
        for location in tube_rack.container_locations.values():
            rsl.add_position(location.position, location.container.barcode)
        return rsl

    def add_position(self, rack_position, tube_barcode):
        """
        Adds the values to the position map.

        :param rack_position: The rack position.
        :type rack_position: :class:`thelma.entities.rack.RackPosition`.

        :param tube_barcode: The tube barcode.
        :type tube_barcode: :class:`basestring`.

        :raise ValueError: If rack position or tube barcode are already present.
        :raise IndexError: If the rack position is out of the rack shape range.
        """
        if self._position_map.has_key(rack_position):
            raise ValueError('Duplicate rack position %s' % (rack_position))
        elif not self.shape.contains_position(rack_position):
            msg = 'The passed rack position (%s) is out of the rack shape ' \
                  'range (%s)!' % (rack_position, self.shape.name)
            raise IndexError(msg)
        if tube_barcode in self._position_map.values():
            raise ValueError('Duplicate tube barcode "%s"' % (tube_barcode))

        self._position_map[rack_position] = tube_barcode

    def get_barcode_for_position(self, rack_position):
        """
        Returns the tube barcode for the given position (or None).

        :param rack_position: The rack position.
        :type rack_position: :class:`thelma.entities.rack.RackPosition`.
        :return: The tube barcode or None.
        """
        if not self._position_map.has_key(rack_position): return None
        return self._position_map[rack_position]

    def get_positions(self):
        """
        Returns all stored rack positions.
        """
        return self._position_map.keys()

    def get_tube_barcodes(self):
        """
        Returns all stored tube barcodes.
        """
        return self._position_map.values()

    def get_position_for_barcode(self, tube_barcode):
        """
        Return the rack position for the passed tube barcode (or *None*).

        :param tube_barcode: The barcode of a tube.
        :type tube_barcode: :class:`str`

        :return: The position of the tube within the layout.
        :rtype: :class:`thelma.entities.rack.RackPosition`
        """
        for rack_pos, stored_barcode in self._position_map.iteritems():
            if stored_barcode == tube_barcode: return rack_pos

        return None

    def iterpositions(self):
        """
        Returns the content of the position map.
        """
        return self._position_map.iteritems()

    def diff(self, other):
        """
        Compares this rack scanning layout with another rack scanning layout
        and returns a list of mismatches between the two (empty if there are
        no differences).

        :returns: list of triples containing the position, the expected
            barcode (or `None`), and the found barcode (or `None`) for each
            mismatch.
        """
        found_tubes = set()
        mismatches = []
        for pos, self_barcode in self.iterpositions():
            found_tubes.add(self_barcode)
            other_barcode = other.get_barcode_for_position(pos)
            if self_barcode == other_barcode:
                continue
            else:
                mismatches.append((pos, self_barcode, other_barcode))
        for pos, other_barcode in other.iterpositions():
            if other_barcode in found_tubes:
                continue
            else:
                mismatches.append((pos, None, other_barcode))
        return mismatches

    def __len__(self):
        return len(self._position_map)

    def __eq__(self, other):
        """
        Equality is only based on position map data.
        """
        if not isinstance(other, self.__class__): return False
        if not len(self._position_map) == len(other): return False
        for rack_pos, tube_barcode in self._position_map.iteritems():
            if not tube_barcode == other.get_barcode_for_position(rack_pos):
                return False
        return True

    def __ne__(self, other):
        return not (self.__eq__(other))

    def __str__(self):
        return self.__class__.__name__

    def __repr__(self):
        str_format = '<%s rack barcode: %s, number of positions: %i>'
        params = (self.__class__.__name__, self.rack_barcode,
                  len(self._position_map))
        return str_format % params
