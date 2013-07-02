"""
Classes related to rack scanning tasks and data. \'Rack Scanning\' refers
to a device that records the tube barcodes for each position of a 96-well stock
rack.

AAB
"""
from datetime import datetime
from datetime import timedelta
from everest.entities.utils import get_root_aggregate
from thelma.automation.handlers.rackscanning import RackScanningLayout
from thelma.automation.handlers.rackscanning import \
                                        CenixRackScanningParserHandler
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.tools.worklists.tubehandler import TubeTransferData
from thelma.automation.tools.worklists.tubehandler import TubeTransferExecutor
from thelma.automation.tools.writers import TxtWriter
from thelma.automation.tools.writers import read_zip_archive
from thelma.interfaces import IRack
from thelma.models.rack import TubeRack
from thelma.models.tubetransfer import TubeTransfer
from thelma.models.user import User
from thelma.utils import get_utc_time
import logging
import os
import glob

__docformat__ = "reStructuredText en"

__all__ = ['RackScanningAdjuster',
           'RackScanningReportWriter']



class RackScanningAdjuster(BaseAutomationTool):
    """
    The adjuster compares the content of rack scanning files with the actual
    data of the racks as stored in the DB. If there are differences, it
    generates a tube handler worklist (type: CONTAINER_TRANSFER) and an
    overview file. The tube handler worklist can be executed as well
    (depending on user input).

    Steps:

        1. Parse rack scanning files (conversion into
           :class:`RackScanningLayout` instances). The timestamp of the files
           must not be older than :attr:`MAX_FILE_AGE`.
        2. Fetch tube racks from the DB and convert them into
           :class:`RackScanningLayout` instances.
        3. Search for differences and store them. If there are none: stop here.
           Also make sure all tubes are present both in the files and in the
           racks.
        4. Create report file for overview.
           If execution is not requested: Stop here.
        5. Generates tube transfers that would adjust the DB so that it
           matches the rack scanning file data.
        6. Execute planned worklist.

    **Return Value:** dict with one overview file (:attr:STREAM_KEY) and
        a list of tube transfers (:attr:`WORKLIST_KEY)
    """

    NAME = 'Rack Scanning Adjuster'

    #: Key of the overview file stream in the return value map.
    STREAM_KEY = 'overview'
    #: Key of the planned worklist in the return values map.
    WORKLIST_KEY = 'worklist'

    #: The maximum age a rack scanning timestamp may have.
    MAX_FILE_AGE = 1 # days

    def __init__(self, rack_scanning_files, adjust_database=False, user=None,
                 logging_level=logging.WARNING, add_default_handlers=False):
        """
        Constructor:

        :param rack_scanning_files The rack scanning stream, either
            a single rack scanning file, as zip archive or as directory path
            (if containing several files).

        :param adjust_database: Shall the DB be adjusted (*True*) or do
            you only want to have a report (*False*)?
        :type adjust_database: :class:`bool`
        :default adjust_database: *False*

        :param user: The user who wants to update the DB - must not be *None* if
            :attr:`adjust_database` is *True*.
        :type user: :class:`thelma.models.user.User`
        :default user: *None*

        :param logging_level: defines the least severe level of logging
                    event the log will record

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        """
        BaseAutomationTool.__init__(self, logging_level=logging_level,
                                    add_default_handlers=add_default_handlers,
                                    depending=False)

        #: The rack scanning stream (single file, zip archive or directory -
        #: in case of an directory, :attr:`is_directory` must be *True*).
        self.rack_scanning_files = rack_scanning_files

        #: Shall the DB be adjusted or do you only want to have a report?
        self.adjust_database = adjust_database
        #: The user who wants to update the database.
        self.user = user

        #: The rack scanning layouts resulting from the file parsing mapped
        #: onto rack barcodes.
        self.__file_layouts = None
        #: The rack scanning layouts created from the DB racks mapped
        #: onto rack barcodes.
        self.__db_layouts = None
        #: The rack entities mapped onto barcodes.
        self.__racks = None
        #: The tube entities mapped onto barcodes.
        self.__tubes = None

        #: The stream for the overview file.
        self.__overview_stream = None
        #: The tube transfers for the DB adjustment.
        self.__tube_transfers = None
        #: The tube transfer worklist (only for *True* :attr:`adjust_database`).
        self.__tube_transfer_worklist = None

        #: The allowed maximum age of a file stream as :class:`timedelta`.
        self.__max_age = None
        #: The current time as datetime.
        self.__now = None
        #: The tube transfer data for the differences found.
        self.__differences = None

    def reset(self):
        """
        Resets all values except for initialisation values.
        """
        BaseAutomationTool.reset(self)
        self.__file_layouts = dict()
        self.__db_layouts = dict()
        self.__racks = dict()
        self.__tubes = dict()
        self.__overview_stream = None
        self.__tube_transfers = []
        self.__tube_transfer_worklist = None
        self.__max_age = None
        self.__now = None
        self.__differences = []

    def get_overview_stream(self):
        """
        Returns the stream of the generated overviw (report) file.
        """
        if self.return_value is None: return None
        return self.return_value[self.STREAM_KEY]

    def get_tube_transfer_worklist(self):
        """
        Returns the tube transfer worklist (or *None* if the database update
        has been disabled or there are errors in the run).
        """
        if self.return_value is None: return None
        return self.return_value[self.WORKLIST_KEY]

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Start rack scanning adjust run ...')

        self.__check_input()
        if not self.has_errors(): self.__parse_scanning_files()
        if not self.has_errors(): self.__fetch_rack_data()
        if not self.has_errors(): self.__find_differences()
        if not self.has_errors(): self.__write_report_stream()
        if not self.has_errors() and self.adjust_database:
            self.__convert_tube_transfers()
            self.__execute_transfers()
        if not self.has_errors():
            self.return_value = {self.STREAM_KEY : self.__overview_stream,
                        self.WORKLIST_KEY : self.__tube_transfer_worklist}
            self.add_info('Run completed.')

    def __check_input(self):
        """
        Checks the initialisation values ...
        """
        self.add_debug('Check input values ...')

        if self.rack_scanning_files is None:
            msg = 'The rack scanning stream is None!'
            self.add_error(msg)

        if self._check_input_class('"adjust DB" flag', self.adjust_database,
                                   bool):
            if self.adjust_database:
                self._check_input_class('user', self.user, User)

    def __parse_scanning_files(self):
        """
        Parses the scanning file(s). The result are stored in
        :attr:`__file_layouts`.
        """
        self.add_debug('Parse scanning files ...')

        self.__max_age = timedelta(days=self.MAX_FILE_AGE)
        self.__now = get_utc_time()

        file_map = self.__get_files_from_directory()
        if file_map is None and not self.has_errors():
            file_map = read_zip_archive(zip_stream=self.rack_scanning_files)

        if not file_map is None:
            for fn, stream in file_map.iteritems():
                self.__parse_rack_scanning_file(stream, fn)
        elif not self.has_errors():
            try:
                stream = open(self.rack_scanning_files, 'r')
            except IOError:
                stream = self.rack_scanning_files
            self.__parse_rack_scanning_file(stream)

    def __get_files_from_directory(self):
        """
        Generates a file map with the file names as keys and streams as values
        from the specified directory.
        """
        realpath = os.path.realpath(self.rack_scanning_files)
        if not os.path.isdir(realpath):
            return None

        file_dir = os.path.realpath(self.rack_scanning_files)
        file_map = dict()
        for fn in glob.glob("%s/*.txt" % (file_dir)):
            strm = open(fn, 'r')
            file_map[fn] = strm

        if len(file_map) < 1:
            msg = 'There are no *.TXT files in the specified directory!'
            self.add_error(msg)
            return None

        return file_map

    def __parse_rack_scanning_file(self, stream, file_name=None):
        """
        Converts the file stream and stores the resulting rack scanning
        layout. Also checks the validity of the file time stamp.
        """
        parser_handler = CenixRackScanningParserHandler(log=self.log,
                                                        stream=stream)
        rs_layout = parser_handler.get_result()

        if rs_layout is None:
            msg = 'Error when trying to parse rack scanning file.'
            if not file_name is None:
                msg = msg[:-1] + ' "%s".' % (file_name)
            self.add_error(msg)
        else:
            age = (self.__now - rs_layout.timestamp)
            if age > self.__max_age:
                if file_name is None:
                    name_term = ''
                else:
                    name_term = 'for file %s ' % (file_name)
                msg = 'The layout %sis older than %s days (age: %i days, %i ' \
                      'hours).' % (name_term, self.__max_age.days, age.days,
                                   age.seconds / 3600)
                self.add_warning(msg)
            self.__file_layouts[rs_layout.rack_barcode] = rs_layout

    def __fetch_rack_data(self):
        """
        Fetches the racks for the rack scanning files from the database
        and converts them into layouts (stored in :attr:`__db_layouts`).
        """
        self.add_debug('Fetch rack data from database ...')

        missing_racks = []
        wrong_type = []

        rack_agg = get_root_aggregate(IRack)
        for barcode in self.__file_layouts.keys():
            rack = rack_agg.get_by_slug(barcode)
            if rack is None:
                missing_racks.append(barcode)
            elif not isinstance(rack, TubeRack):
                info = '%s (%s)' % (barcode, rack.__class__.__name__)
                wrong_type.append(info)
            else:
                self.__racks[barcode] = rack
                self.__db_layouts[barcode] = RackScanningLayout.from_rack(rack)

        if len(missing_racks) > 0:
            missing_racks.sort()
            msg = 'Could not find database records for the following rack ' \
                  'barcodes: %s.' % (', '.join(missing_racks))
            self.add_error(msg)
        if len(wrong_type) > 0:
            wrong_type.sort()
            msg = 'The following rack are no tube racks: %s.' \
                   % (', '.join(wrong_type))
            self.add_error(msg)

    def __find_differences(self):
        """
        Determines tubes that have different positions in both layouts and
        stores :class:`TubeTransferData` objects for them.
        """
        self.add_debug('Find differences ...')

        found_tubes = set()
        missing_in_db = []
        missing_in_file = []

        for rack_barcode, file_layout in self.__file_layouts.iteritems():
            for rack_pos, file_barcode in file_layout.iterpositions():
                found_tubes.add(file_barcode)
                db_layout = self.__db_layouts[rack_barcode]
                db_barcode = db_layout.get_barcode_for_position(rack_pos)
                if db_barcode == file_barcode: continue
                db_rack_barcode, db_pos = self.__find_db_location_for_tube(
                                                                file_barcode)
                if db_rack_barcode is None:
                    missing_in_db.append(file_barcode)
                else:
                    tt = TubeTransferData(tube_barcode=file_barcode,
                                    src_rack_barcode=db_rack_barcode,
                                    src_pos=db_pos,
                                    trg_rack_barcode=rack_barcode,
                                    trg_pos=rack_pos)
                    self.__differences.append(tt)

        for db_layout in self.__db_layouts.values():
            for tube_barcode in db_layout.get_tube_barcodes():
                if not tube_barcode in found_tubes:
                    missing_in_file.append(tube_barcode)

        all_racks = sorted(self.__db_layouts.keys())
        if len(missing_in_db) > 0:
            missing_in_db.sort()
            msg = 'Some tubes from the rack scanning file(s) have not been ' \
                  'found in the database records of the investigated racks: ' \
                  '%s. Investigated racks: %s.' % (', '.join(missing_in_db),
                                                   ', '.join(all_racks))
            self.add_error(msg)
        if len(missing_in_file) > 0:
            missing_in_file.sort()
            msg = 'Some tube expected in the investigated racks have not ' \
                  'been found in the rack scanning file(s): %s. Investigated ' \
                  'racks: %s.' % (', '.join(missing_in_file),
                                  ', '.join(all_racks))
            self.add_error(msg)

        if not self.has_errors() and len(self.__differences) < 1:
            msg = 'The content of rack scanning file(s) matches the status ' \
                  'of the racks in the database. There is nothing to update.'
            self.add_error(msg)
        else:
            self.__check_feasibility()

    def __find_db_location_for_tube(self, tube_barcode):
        """
        Finds the current position of a tube.
        """
        for rack_barcode, db_layout in self.__db_layouts.iteritems():
            rack_pos = db_layout.get_position_for_barcode(tube_barcode)
            if not rack_pos is None:
                return rack_barcode, rack_pos

        return None, None

    def __check_feasibility(self):
        """
        The tubehandler cannot handle situations in which the target position
        of is at the same the source position for another tube. The
        :class:`TubeTransferExecutor` cannot handle this either because we
        do not insist of an order to execute the transfers and might
        cause inconsistencies.
        """
        self.add_debug('Check feasibility ...')

        duplicate_positions = []
        source_positions = set()
        for tt in self.__differences:
            src_hash = '%s-%s' % (tt.src_rack_barcode, tt.src_pos.label)
            source_positions.add(src_hash)
        for tt in self.__differences:
            trg_hash = '%s-%s' % (tt.trg_rack_barcode, tt.trg_pos.label)
            if trg_hash in source_positions:
                info = '%s (%s)' % (tt.trg_rack_barcode, tt.trg_pos.label)
                duplicate_positions.append(info)

        if len(duplicate_positions) > 0:
            duplicate_positions.sort()
            msg = 'Some positions are both source position of one rack and ' \
                  'target positions of another rack. Move the referring ' \
                  'tubes, repeat the rack-scanning and re-run the process, ' \
                  'please. Details: %s.' % (duplicate_positions)
            self.add_error(msg)

    def __write_report_stream(self):
        """
        Writes the stream of the overview file.
        """
        self.add_debug('Write report file stream ...')

        writer = RackScanningReportWriter(tube_transfers=self.__differences,
                        rack_barcodes=self.__file_layouts.keys(), log=self.log)
        self.__overview_stream = writer.get_result()

        if self.__overview_stream is None:
            msg = 'Error when trying to write report file stream.'
            self.add_error(msg)

    def __convert_tube_transfers(self):
        """
        Converts the tube transfer data objects into entities. For this sake,
        we also have to get the referring tubes.
        """
        self.add_debug('Convert tube transfers into entities ...')

        for tt in self.__differences:
            source_position = tt.src_pos
            source_rack = self.__racks[tt.src_rack_barcode]
            tube = None
            for container in source_rack.containers:
                if container.location.position == source_position:
                    tube = container
                    break
            tube_transfer = TubeTransfer(tube=tube, source_rack=source_rack,
                    source_position=source_position, target_position=tt.trg_pos,
                    target_rack=self.__racks[tt.trg_rack_barcode])
            self.__tube_transfers.append(tube_transfer)

    def __execute_transfers(self):
        """
        Updates the tube locations and generates a
        :class:`thelma.models.tubetransfer.TubeTransferWorklist` entity.
        """
        self.add_debug('Execute transfers ...')

        executor = TubeTransferExecutor(tube_transfers=self.__tube_transfers,
                                        user=self.user, log=self.log)
        self.__tube_transfer_worklist = executor.get_result()

        if self.__tube_transfer_worklist is None:
            msg = 'Error when trying to update tube locations.'
            self.add_error(msg)


class RackScanningReportWriter(TxtWriter):
    """
    This class generates a report summarising the result of the adjuser run.

    **Return Value:** file stream (TXT format)
    """
    NAME = 'Rack Scanning Report Writer'

    #: The main headline of the file.
    BASE_MAIN_HEADER = 'Stock Condense Worklist Generation Report / %s / %s'

    #: The header of the rack list section.
    RACKS_HEADER = 'Involved Racks'
    #: This line presents the number of racks.
    RACK_COUNT_LINE = 'Number of racks: %i'
    #: The header for the tube list section.
    TUBES_HEADER = 'Tubes to be Updated'
    #: A data line presenting a tube that needs to be updated.
    TUBE_BASE_LINE = '%s (rack scanner: %s (%s), DB: %s (%s))'
    #: This line presents the number of tubes.
    TUBE_COUNT_LINE = 'Number of tubes: %i'

    def __init__(self, rack_barcodes, tube_transfers, log):
        """
        Constructor:

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`

        :param rack_barcodes: A list of the racks that have been scanned.
        :type rack_barcodes: :class:`list`

        :param tube_transfers: The tube transfers scheduled by the
            RackScanningAdjuster.
        :type tube_transfers: :class:`list` of :class:`TubeTransferData` objects
        """
        TxtWriter.__init__(self, log=log)

        #: The racks that have been scanned.
        self.rack_barcodes = rack_barcodes
        #: The scheduled tube transfers.
        self.tube_transfers = tube_transfers

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input values ...')

        if self._check_input_class('rack barcode list', self.rack_barcodes,
                                   list):
            for barcode in self.rack_barcodes:
                if not self._check_input_class('rack barcode', barcode,
                                               basestring): break

        if self._check_input_class('tube transfer list', self.tube_transfers,
                                   list):
            for tt in self.tube_transfers:
                if not self._check_input_class('tube transfer', tt,
                                               TubeTransferData): break

    def _write_stream_content(self):
        """
        Generates and writes the stream content (2 sections).
        """
        self.add_debug('Write content ...')

        self.__write_main_headline()
        self.__write_rack_section()
        self.__write_tube_section()

    def __write_main_headline(self):
        """
        Writes the main head line.
        """
        now = datetime.now()
        date_string = now.strftime('%d.%m.%Y')
        time_string = now.strftime('%H:%M')
        main_headline = self.BASE_MAIN_HEADER % (date_string, time_string)
        self._write_headline(main_headline, underline_char='=',
                             preceding_blank_lines=0, trailing_blank_lines=0)

    def __write_rack_section(self):
        """
        Writes the INVOLVED RACKS section.
        """
        self._write_headline(self.RACKS_HEADER)

        rack_lines = []
        self.rack_barcodes.sort()
        for barcode in self.rack_barcodes: rack_lines.append(barcode)
        rack_lines.append('')
        rack_lines.append(self.RACK_COUNT_LINE % (len(self.rack_barcodes)))

        self._write_body_lines(rack_lines)

    def __write_tube_section(self):
        """
        Writes the TUBES TO MOVE section.
        """
        self._write_headline(self.TUBES_HEADER)

        tube_lines = []
        tts = sorted(self.tube_transfers, cmp=lambda tt1, tt2:
                                    cmp(tt1.tube_barcode, tt2.tube_barcode))
        for tube_transfer in tts:
            tube_line = self.TUBE_BASE_LINE % (tube_transfer.tube_barcode,
                    tube_transfer.trg_rack_barcode, tube_transfer.trg_pos.label,
                    tube_transfer.src_rack_barcode, tube_transfer.src_pos.label)
            tube_lines.append(tube_line)

        tube_lines.append('')
        tube_lines.append(self.TUBE_COUNT_LINE % (len(self.tube_transfers)))

        self._write_body_lines(tube_lines)
