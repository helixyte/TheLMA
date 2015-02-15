"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

.. currentmodule:: thelma.entities.tubetransfer

This handler converts the result of the tubehandler output file parser
(:class:`XL20OutputParser`) into a list of :class:`TubeTransfer` entities

AAB
"""
from everest.entities.utils import get_root_aggregate
from thelma.tools.handlers.base import BaseParserHandler
from thelma.tools.parsers.tubehandler import XL20OutputParser
from thelma.tools.semiconstants import get_rack_position_from_label
from thelma.interfaces import ITubeRack
from thelma.entities.tubetransfer import TubeTransfer

__docformat__ = 'reStructuredText en'

__all__ = ['XL20OutputParserHandler']


class XL20OutputParserHandler(BaseParserHandler):
    """
    Converts the results of the :class:`XL20OutputParser` into a list of
    :class:`TubeTransfer` entities.

    **Return Value:** :class:`list` of :class:`TubeTransfer` entities
    """
    NAME = 'XL20 Output File Parser Handler'

    _PARSER_CLS = XL20OutputParser

    def __init__(self, stream, parent=None):
        BaseParserHandler.__init__(self, stream=stream, parent=parent)
        #: The tube transfer entities created.
        self.__tube_transfers = None
        #: Maps racks onto rack barcodes.
        self.__racks = None
        #: The aggregate used to find the rack for a rack barcode.
        self.__rack_agg = None
        #: The earliest of all timestamps in the robot log file.
        self.__timestamp = None
        #: Intermediate error storage.
        self.__unknown_racks = None
        self.__missing_tube = None
        self.__mismatching_tube = None
        self.__invalid_pos_label = None

    def reset(self):
        BaseParserHandler.reset(self)
        self.__tube_transfers = []
        self.__racks = dict()
        self.__rack_agg = get_root_aggregate(ITubeRack)
        self.__timestamp = None
        self.__unknown_racks = []
        self.__missing_tube = []
        self.__mismatching_tube = []
        self.__invalid_pos_label = []

    def get_timestamp(self):
        """
        Returns the timestamp (used for tube transfer worklists).
        """
        if self.return_value is None: return None
        return self.__timestamp

    def _convert_results_to_entity(self):
        """
        Converts the parsing results into a list of :class:`TubeTransfer`
        entities.
        """
        self.add_info('Convert parser results ...')

        self.__convert_parsing_containers()
        self.__record_messages()
        if not self.has_errors():
            self.return_value = self.__tube_transfers
            self.add_info('Conversion completed.')

    def __convert_parsing_containers(self):
        """
        Converts the parsing containers of the parser into entities.
        """

        for transfer_container in self.parser.xl20_transfers:
            src_rack = self.__get_rack_for_barcode(
                                    transfer_container.source_rack_barcode)
            src_pos = self.__get_rack_position(
                                    transfer_container.source_position_label)
            trg_rack = self.__get_rack_for_barcode(
                                    transfer_container.target_rack_barcode)
            trg_pos = self.__get_rack_position(
                                    transfer_container.target_position_label)
            tube = self.__get_tube_from_rack(transfer_container.tube_barcode,
                                    src_rack, src_pos)

            if self.__timestamp is None:
                self.__timestamp = transfer_container.timestamp
            else:
                self.__timestamp = min(transfer_container.timestamp,
                                       self.__timestamp)

            kw = dict(tube=tube, source_rack=src_rack, target_rack=trg_rack,
                      source_position=src_pos, target_position=trg_pos)
            if None in kw.values(): continue
            tt = TubeTransfer(**kw)
            self.__tube_transfers.append(tt)

    def __record_messages(self):
        """
        Records warnings and errors that occurred during the conversion.
        """
        self.add_debug('Record warnings and errors ...')

        if len(self.__unknown_racks) > 0:
            msg = 'Could not find a database record for the following rack ' \
                  'barcodes: %s.' % (', '.join(sorted(self.__unknown_racks)))
            self.add_error(msg)

        if len(self.__missing_tube) > 0:
            self.__missing_tube.sort()
            msg = 'Some tubes have not been found at the positions at which ' \
                  'they were expected: %s.' % (', '.join(self.__missing_tube))
            self.add_error(msg)

        if len(self.__mismatching_tube) > 0:
            msg = 'Some positions contain unexpected tubes: %s.' \
                  % (' -- '.join(sorted(self.__mismatching_tube)))
            self.add_error(msg)

        if len(self.__invalid_pos_label) > 0:
            msg = 'The following position labels are invalid: %s.' \
                   % (', '.join(sorted(self.__invalid_pos_label)))
            self.add_error(msg)

    def __get_rack_for_barcode(self, barcode):
        """
        Fetches the rack for the given barcode from the cache or the
        aggregate.
        """
        if self.__racks.has_key(barcode):
            return self.__racks[barcode]
        elif barcode in self.__unknown_racks:
            return None

        rack = self.__rack_agg.get_by_slug(barcode)
        if rack is None: self.__unknown_racks.append(barcode)
        return rack

    def __get_rack_position(self, label):
        """
        Returns the rack position of the given label or records an error.
        """
        try:
            rack_pos = get_rack_position_from_label(label)
        except ValueError:
            self.__invalid_pos_label.append(label)
            return None
        else:
            return rack_pos

    def __get_tube_from_rack(self, tube_barcode, rack, rack_pos):
        """
        Fetches the tube from the given location and checks whether it is
        the expected one.
        """
        if rack is None or rack_pos is None: return None

        try:
            wanted_tube = rack.container_positions[rack_pos]
        except KeyError:
            info = '%s (%s %s)' % (tube_barcode, rack.barcode,
                                   rack_pos.label)
            self.__missing_tube.append(info)
            return None

        if not wanted_tube.barcode == tube_barcode:
            info = '%s in %s (found: %s, expected: %s)' % (rack_pos.label,
                    rack.barcode, wanted_tube.barcode, tube_barcode)
            self.__mismatching_tube.append(info)

        return wanted_tube
