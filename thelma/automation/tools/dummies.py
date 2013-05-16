"""
Contains dummy classes for testing purposes.

AAB
"""
from StringIO import StringIO
from datetime import datetime
from thelma.automation.parsers.tubehandler import XL20OutputParser
from thelma.automation.tools.worklists.tubehandler import TubeTransferData
from thelma.automation.tools.worklists.tubehandler import XL20WorklistWriter
from thelma.automation.tools.writers import TxtWriter
import logging


__docformat__ = 'reStructuredText en'

__all__ = ['XL20Dummy']


class XL20Dummy(TxtWriter):
    """
    Mimics the XL20 tubehandler. It consumes the an XL20 worklists and
    returns an XL20 output file. All transfers are assumed to work without
    errors.

    The tubes are not moved in the DB, because in reality the DB would also
    not know about it. There are also no checks involved.

    **Return Value:** file stream (TXT)
    """

    NAME = 'XL20 Tubehandler Dummy'

    def __init__(self, xl20_worklist_stream,
                 logging_level=logging.WARN, add_default_handlers=False):
        """
        Constructor:

        :param xl20_worklist_stream: An XL20 worklist containing the robot
            instructions as stream (e.g. created by the
            :class:`XL20WorklistWriter`).
        :type xl20_worklist_stream: stream (CSV)

        :param logging_level: defines the least severe level of logging
                    event the log will record

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        """
        TxtWriter.__init__(self, logging_level=logging_level,
                                 add_default_handlers=add_default_handlers,
                                 depending=False)

        #: The XL20 worklist containing the robot instructions as stream.
        self.xl20_worklist_stream = xl20_worklist_stream

        #: The tube transfers parsed from the input file as
        #: :class:`TubeTransferData` objects.
        self.tube_transfers = None

    def reset(self):
        TxtWriter.reset(self)
        self.tube_transfers = []

    def _write_stream_content(self):
        """
        First we need to parse the input file, than we write transfer
        records in the output files.
        """

        self.add_info('Run XL20 dummy ...')

        if not self.has_errors(): self.__get_tube_transfers()
        if not self.has_errors(): self.__write_output_records()

    def _check_input(self):
        if not isinstance(self.xl20_worklist_stream, (StringIO, file)):
            msg = 'The input stream must be %s or a %s type (obtained: %s).' \
                  % (StringIO.__name__, file.__name__,
                     self.xl20_worklist_stream.__class__.__name__)
            self.add_error(msg)

    def __get_tube_transfers(self):
        """
        Parses the tube transfers from the worklist file
        (as :class:`TubeTransferData` objects).
        """
        writer_cls = XL20WorklistWriter

        self.xl20_worklist_stream.seek(0)
        lines = self.xl20_worklist_stream.readlines()
        for i in range(len(lines)):
            if i == 0: continue # headers
            line = lines[i]
            line = line.strip()
            if ';' in line:
                tokens = line.split(';')
            elif ',' in line:
                tokens = line.split(',')
            else:
                msg = 'Unknown delimiter: %s' % (line)
                self.add_error(msg)
                break

            if len(tokens) != 5: # TODO: fetch dynamically
                msg = 'Unexpected number of columns: %s' % (line)
                self.add_error(msg)
                break

            src_barcode = self.__get_item(tokens, writer_cls.SOURCE_RACK_INDEX)
            src_pos_label = self.__get_item(tokens,
                                            writer_cls.SOURCE_POSITION_INDEX)
            tube_barcode = self.__get_item(tokens,
                                           writer_cls.TUBE_BARCODE_INDEX)
            target_barcode = self.__get_item(tokens, writer_cls.DEST_RACK_INDEX)
            trg_pos_label = self.__get_item(tokens,
                                            writer_cls.DEST_POSITION_INDEX)
            tt = TubeTransferData(tube_barcode=tube_barcode,
                                  src_rack_barcode=src_barcode,
                                  src_pos=src_pos_label,
                                  trg_rack_barcode=target_barcode,
                                  trg_pos=trg_pos_label)
            self.tube_transfers.append(tt)

    def __get_item(self, tokens, index):
        """
        Fetch a token from a split list and strips it from quote characters.
        """
        item = tokens[index]
        item = item.strip()
        if item.startswith('"'): item = item[1:]
        if item.endswith('"'): item = item[:-1]
        return item

    def __write_output_records(self):
        """
        Creates an output file using the parsed tube transfer data.
        """
        parser_cls = XL20OutputParser
        lines = []

        # line_pattern = join_id,step_number,date,time,src_rack_barcode, \
        #   src_pos,trg_rack_barcode,trg_pos,exp_tube,found_tube,weight,
        #   temperature,errors

        for tt in self.tube_transfers:
            tokens = [''] * parser_cls.NUMBER_COLUMNS
            # timestamp
            now = datetime.now()
            date_str = now.strftime(parser_cls.DATE_FORMAT)
            tokens[parser_cls.DATE_INDEX] = date_str
            time_str = now.strftime(parser_cls.TIME_FORMAT)
            tokens[parser_cls.TIME_INDEX] = time_str
            # tube data
            tokens[parser_cls.SOURCE_RACK_BARCODE_INDEX] = tt.src_rack_barcode
            tokens[parser_cls.SOURCE_POSITION_INDEX] = tt.src_pos
            tokens[parser_cls.TARGET_RACK_BARCODE_INDEX] = tt.trg_rack_barcode
            tokens[parser_cls.TARGET_POSITION_INDEX] = tt.trg_pos
            tokens[parser_cls.EXPECTED_TUBE_BACODE_INDEX] = tt.tube_barcode
            tokens[parser_cls.FOUND_TUBE_BARCODE_INDEX] = tt.tube_barcode

            wline = parser_cls.SEPARATOR.join(tokens)
            lines.append(wline)

        self._write_body_lines(lines)
