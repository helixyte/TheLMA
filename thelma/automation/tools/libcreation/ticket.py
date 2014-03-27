#"""
#Trac tools dealing with library creation tickets
#
#AAB
#"""
#from thelma.automation.tools.base import BaseAutomationTool
#from thelma.automation.tools.iso.uploadreport import StockTransferReportUploader
#from thelma.automation.tools.libcreation.base import LibraryLayout
#from thelma.automation.tools.libcreation.base import NUMBER_SECTORS
#from thelma.automation.tools.libcreation.execution \
#    import LibraryCreationExecutor
#from thelma.automation.tools.semiconstants import get_384_rack_shape
#from thelma.automation.tools.stock.base import STOCKMANAGEMENT_USER
#from thelma.automation.tools.utils.base import VOLUME_CONVERSION_FACTOR
#from thelma.automation.tools.utils.base import add_list_map_element
#from thelma.automation.tools.utils.base import get_trimmed_string
#from thelma.automation.tools.utils.racksector import RackSectorTranslator
#from thelma.automation.tools.writers import CsvColumnParameters
#from thelma.automation.tools.writers import CsvWriter
#from thelma.automation.tracbase import BaseTracTool
#from thelma.models.iso import IsoSampleStockRack
#from thelma.models.library import LibraryCreationIso
#from thelma.models.library import MoleculeDesignLibrary
#from thelma.models.liquidtransfer import ExecutedWorklist
#from thelma.models.racklayout import RackLayout
#from thelma.models.user import User
#from tractor import AttachmentWrapper
#from tractor import create_wrapper_for_ticket_creation
#from tractor.ticket import SEVERITY_ATTRIBUTE_VALUES
#from tractor.ticket import TYPE_ATTRIBUTE_VALUES
#from xmlrpclib import Fault
#from xmlrpclib import ProtocolError
#import logging
#
#__docformat__ = 'reStructuredText en'
#
#__all__ = ['LibraryCreationTicketGenerator',
#           'LibraryCreationIsoCreator',
#           'LibraryCreationTicketWorklistUploader',
#           'LibraryCreationStockLogFileWriter',
#           'LibraryCreationStockTransferReporter']
#
#
#class LibraryCreationTicketGenerator(BaseTracTool):
#    """
#    Creates an library creation trac ticket for a new ISO.
#
#    **Return Value:** ticket ID
#    """
#    NAME = 'Library Creation Ticket Creator'
#    #: The value for the ticket summary (title).
#    SUMMARY = 'Library Creation ISO'
#    #: The description for the empty ticket.
#    DESCRIPTION_TEMPLATE = "Autogenerated ticket for library creation ISO " \
#                           "'''%s'''.\n\nLayout number: %i\n\n"
#    #: The value for ticket type.
#    TYPE = TYPE_ATTRIBUTE_VALUES.TASK
#    #: The value for the ticket's severity.
#    SEVERITY = SEVERITY_ATTRIBUTE_VALUES.NORMAL
#    #: The value for the ticket cc.
#    CC = STOCKMANAGEMENT_USER
#    #: The value for the ticket's component.
#    COMPONENT = 'Logistics'
#
#    def __init__(self, requester, iso_label, layout_number, parent=None):
#        """
#        Constructor.
#
#        :param requester: The user who will be owner and reporter of the ticket.
#        :type requester: :class:`thelma.models.user.User`
#        :param str iso_label: The label of the ISO this ticket belongs to.
#        :param int layout_number: References the library layout the ISO is
#            created for.
#        """
#        BaseTracTool.__init__(self, parent=parent)
#        #: The user who will be owner and reporter of the ticket (corresponds
#        #: the requester of the ISO request).
#        self.requester = requester
#        #: The label of the ISO this ticket belongs to.
#        self.iso_label = iso_label
#        #: References the library layout the ISO is created for.
#        self.layout_number = layout_number
#        #: The ticket wrapper storing the value applied to the ticket.
#        self._ticket = None
#
#    def reset(self):
#        BaseTracTool.reset(self)
#        self._ticket = None
#
#    def get_ticket_id(self):
#        """
#        Sends a request and returns the ticket ID generated by the trac.
#        """
#        self.send_request()
#        return self.return_value
#
#    def send_request(self):
#        """
#        Prepares and sends the Trac ticket creation request.
#        """
#        self.reset()
#        self.add_info('Create ISO request ticket ...')
#
#        self.__check_input()
#        if not self.has_errors(): self.__create_ticket_wrapper()
#        if not self.has_errors(): self.__submit_request()
#
#    def __check_input(self):
#        """
#        Checks the initialisation values.
#        """
#        self.add_debug('Check input ...')
#
#        self._check_input_class('requester', self.requester, User)
#        self._check_input_class('ISO label', self.iso_label, basestring)
#        self._check_input_class('layout number', self.layout_number, int)
#
#    def __create_ticket_wrapper(self):
#        """
#        Creates the ticket wrapper to be sent.
#        """
#        self.add_debug('Create ticket wrapper ...')
#
#        description = self.DESCRIPTION_TEMPLATE % (self.iso_label,
#                                                   self.layout_number)
#
#        self._ticket = create_wrapper_for_ticket_creation(
#                                summary=self.SUMMARY,
#                                description=description,
#                                reporter=self.requester.directory_user_id,
#                                owner=self.requester.directory_user_id,
#                                component=self.COMPONENT,
#                                cc=self.CC,
#                                type=self.TYPE,
#                                severity=self.SEVERITY)
#
#    def __submit_request(self):
#        """
#        Submits the request to the trac.
#        """
#        self.add_debug('Send request ...')
#
#        try:
#            ticket_id = self.tractor_api.create_ticket(notify=self.NOTIFY,
#                                                ticket_wrapper=self._ticket)
#        except ProtocolError, err:
#            self.add_error(err.errmsg)
#        except Fault, fault:
#            msg = 'Fault %s: %s' % (fault.faultCode, fault.faultString)
#            self.add_error(msg)
#        else:
#            self.return_value = ticket_id
#            self.add_info('Ticket created (ID: %i).' % (ticket_id))
#            self.was_successful = True
#
#
#class LibraryCreationIsoCreator(BaseAutomationTool):
#    """
#    Creates ticket and ISO for a library creation ISO.
#    Before running the tool will check whether there are already ISOs for
#    this ISO request. The tool will create the remaining ISOs (using the
#    number of plates in the ISO request as target number).
#
#    IMPORTANT: This tool must not launch warnings or be interrupted, otherwise
#        some or all tickets will be created multiple times.
#
#    **Return Value:** The updated molecule design library (incl. Isos).
#    """
#    NAME = 'Library Creation ISO Creator'
#
#    #: Name pattern for library creation ISO labels. The placeholders are
#    #: the library name and the layout number.
#    ISO_LABEL_PATTERN = '%s-%s'
#
#    def __init__(self, molecule_design_library):
#        """
#        Constructor:
#
#        :param molecule_design_library: The molecule design library for which to
#            generate the ISOs.
#        :type molecule_design_library:
#            :class:`thelma.models.library.MoleculeDesignLibrary`
#        """
#        BaseAutomationTool.__init__(self, depending=False)
#        #: The molecule design library for which to generate an ISO.
#        self.molecule_design_library = molecule_design_library
#
#        #: The ISO request is an attribute of the library.
#        self.__iso_request = None
#        #: The number of ISOs created (for checking reasons).
#        self.__new_iso_counter = None
#
#    def reset(self):
#        BaseAutomationTool.reset(self)
#        self.__iso_request = None
#        self.__new_iso_counter = 0
#
#    def run(self):
#        """
#        Creates tickets and ISOs.
#        """
#        self.reset()
#        self.add_info('Start ISO generation ...')
#
#        self.__check_input()
#        if not self.has_errors():
#            self.__create_isos()
#        if not self.has_errors():
#            self.return_value = self.molecule_design_library
#            self.add_info('%i ISOs have been created.' % (
#                                                    self.__new_iso_counter))
#
#    def __check_input(self):
#        if self._check_input_class('molecule design library',
#                        self.molecule_design_library, MoleculeDesignLibrary):
#            self.__iso_request = self.molecule_design_library.iso_request
#
#
#    def __create_isos(self):
#        """
#        Creates the ISOs. At this the tool checks whether there are already
#        ISOs at the ISO request. The tool add ISOs until the number of plates
#        (ISO request attribute) is reached.
#        """
#        self.add_debug('Create ISOs ...')
#
#        iso_count = len(self.__iso_request.isos)
#        libname = self.molecule_design_library.label
#
#        if iso_count >= self.__iso_request.number_plates:
#            msg = 'The ISOs have already been created.'
#            self.add_error(msg)
#            return
#
#        for i in range(iso_count, self.__iso_request.number_plates):
#            layout_number = i + 1
#            iso_label = self.ISO_LABEL_PATTERN % (libname, layout_number)
#            ticket_creator = LibraryCreationTicketGenerator(
#                                self.__iso_request.requester,
#                                iso_label, layout_number, parent=self)
#            ticket_number = ticket_creator.get_ticket_id()
#            if ticket_number is None:
#                msg = 'Error when trying to generate ISO "%s".' % (iso_label)
#                self.add_error(msg)
#                break
#            else:
#                LibraryCreationIso(
#                         ticket_number=ticket_number,
#                         layout_number=layout_number,
#                         label=iso_label,
#                         iso_request=self.__iso_request,
#                         rack_layout=RackLayout(shape=get_384_rack_shape()))
#                self.__new_iso_counter += 1
#
#
#class LibraryCreationTicketWorklistUploader(BaseTracTool):
#    """
#    Uses the worklist files the generated by the
#    :class:`LibraryCreationWorklistWriter` and sends them to the ticket
#    of the library creation ISO.
#    """
#
#    NAME = 'Library Creation Ticket Worklist Uploader'
#
#    #: File name for the zip file in the Trac.
#    FILE_NAME = '%s-%i_robot_worklists.zip'
#    #: The description for the attachment.
#    DESCRIPTION = 'Tube handler, CyBio and buffer dilution worklists.'
#
#    #: Shall existing replacements with the same name be overwritten?
#    REPLACE_EXISTING_ATTACHMENTS = True
#
#    def __init__(self, library_creation_iso, file_map):
#        """
#        Constructor:
#
#        :param library_creation_iso: The library creation ISO the worklists
#            belong to (also contains the ticket ID).
#        :type library_creation_iso:
#            :class:`thelma.models.library.LibraryCreationIso`
#
#        :param file_map: The streams for the worklists files mapped onto
#            file names.
#        :type file_map: :class:`dict`
#        """
#        BaseTracTool.__init__(self, depending=False)
#
#        #: The library creation ISO the worklists belong to (also contains
#        #: the ticket ID).
#        self.library_creation_iso = library_creation_iso
#        #: The streams for the worklists files mapped onto file names.
#        self.file_map = file_map
#
#    def send_request(self):
#        """
#        Sends the request.
#        """
#        self.reset()
#        self.add_info('Prepare request ...')
#
#        self.__check_input()
#        if not self.has_errors(): self.__prepare_and_submit()
#
#    def __check_input(self):
#        """
#        Checks the initialisation values.
#        """
#        self.add_debug('Check input values ...')
#
#        self._check_input_class('library creation ISO',
#                                self.library_creation_iso, LibraryCreationIso)
#
#        if self._check_input_class('file map', self.file_map, dict):
#            for fn in self.file_map.keys():
#                if not self._check_input_class('file name', fn,
#                                               basestring): break
#
#    def __prepare_and_submit(self):
#        """
#        Submits the request.
#        """
#        fn = self.FILE_NAME % (self.library_creation_iso.iso_request.\
#                               plate_set_label,
#                               self.library_creation_iso.layout_number)
#        attachment = AttachmentWrapper(content=self.file_map,
#                                       file_name=fn,
#                                       description=self.DESCRIPTION)
#        ticket_id = self.library_creation_iso.ticket_number
#
#        try:
#            trac_fn = self.tractor_api.add_attachment(ticket_id=ticket_id,
#                        attachment=attachment,
#                        replace_existing=self.REPLACE_EXISTING_ATTACHMENTS)
#        except ProtocolError, err:
#            self.add_error(err.errmsg)
#        except Fault, fault:
#            msg = 'Fault %s: %s' % (fault.faultCode, fault.faultString)
#            self.add_error(msg)
#        else:
#            self.return_value = trac_fn
#            msg = 'Robot worklists have been uploaded successfully.'
#            self.add_info(msg)
#            self.was_successful = True
#
#
#class LibraryCreationStockTransferReporter(StockTransferReportUploader):
#
#    EXECUTOR_CLS = LibraryCreationExecutor
#
#    BASE_COMMENT = 'A stock transfer has been executed by %s ' \
#                   '(see file: attachment:%s).\n\n' \
#                   'Type: %s\n\n' \
#                   'Library source (preparation) plates (quadrants):\n%s.\n'
#
#    def _set_ticket_id(self):
#        """
#        The ticket ID is attached to the library creation ISO.
#        """
#        self._ticket_number = self.executor.entity.ticket_number
#
#    def _get_task_type(self):
#        """
#        All library members are samples.
#        """
#        return self.TYPE_SAMPLES
#
#    def _get_plate_str(self):
#        """
#        The plate string looks different, we have one plate per quadrant
#        (instead of one plate for ISO).
#        """
#        racks = dict()
#        for issr in self.executor.entity.iso_sample_stock_racks:
#            racks[issr.sector_index] = issr.rack.barcode
#        rack_data = []
#        for sector_index in sorted(racks.keys()):
#            rack_str = '%s (Q%s)' % (racks[sector_index], (sector_index + 1))
#            rack_data.append(rack_str)
#        return ', '.join(rack_data)
#
#    def _get_log_file_writer(self):
#        """
#        For library creation ISOs we use a special writer, the
#        :class:`LibraryCreationStockLogFileWriter`.
#        """
#        sample_stock_racks = dict()
#        for issr in self.executor.entity.iso_sample_stock_racks:
#            sample_stock_racks[issr.sector_index] = issr
#        writer = LibraryCreationStockLogFileWriter(
#                    self._working_layout, self._executed_worklists,
#                    sample_stock_racks, parent=self)
#        return writer
#
#
#class LibraryCreationStockLogFileWriter(CsvWriter):
#    """
#    Creates a log file after each library creation stock transfer. The log
#    file contains molecule design pools, molecule designs, stock tube barcodes
#    and volumes and the barcode and positions in the target rack.
#
#    **Return Value:** file stream (CSV format)
#    """
#    NAME = 'Library Creation Stock Transfer Log File Writer'
#    #: The index for the library molecule design pool ID column.
#    LIBRARY_POOL_INDEX = 0
#    #: The header for the library molecule design pool ID column.
#    LIBRARY_POOL_HEADER = 'Library Pool ID'
#    #: The index for the single molecule design pool ID column.
#    MOLECULE_DESIGN_INDEX = 1
#    #: The header for the molecule design pool ID column.
#    MOLECULE_DESIGN_HEADER = 'Molecule Design ID'
#    #: The index for the tube barcode column.
#    TUBE_BARCODE_INDEX = 2
#    #: The header for the tube barcode column.
#    TUBE_BARCODE_HEADER = 'Stock Tube Barcode'
#    #: The index for the volume column.
#    VOLUME_INDEX = 3
#    #: The header for the volume column.
#    VOLUME_HEADER = 'Volume (ul)'
#    #: The index for the target rack barcode column.
#    TARGET_RACK_BARCODE_INDEX = 4
#    #: The header for the target rack barcode column.
#    TARGET_RACK_BARCODE_HEADER = 'Target Rack Barcode'
#    #: The index for the target position column.
#    TARGET_POSITION_INDEX = 5
#    #: The header for the target position column.
#    TARGET_POSITION_HEADER = 'Target Position'
#
#    def __init__(self, library_layout, executed_worklists,
#                 sample_stock_racks, parent=None):
#        """
#        Constructor.
#
#        :param library_layout: The working_layout containing the molecule
#            design pool data.
#        :type library_layout: :class:`LibraryLayout`
#        :param executed_worklists: The executed worklists that have been
#            generated by the executor (mapped onto transfer job indices).
#        :type executed_worklists: :class:`dict`
#        """
#        CsvWriter.__init__(self, parent=parent)
#        #: The executed worklists that have been generated by the executor
#        #: (mapped onto transfer job indices).
#        self.executed_worklists = executed_worklists
#        #: The working_layout containing the molecule design pool data.
#        self.library_layout = library_layout
#        #: The ISO sample stock racks mapped onto sector indices.
#        self.sample_stock_racks = sample_stock_racks
#        #: The translators for each pool stock rack (lazy initialisation).
#        self.__translators = None
#        #: Stores the values for the library molecule design pool ID column.
#        self.__lib_pool_values = None
#        #: Stores the values for the library molecule design pool ID column.
#        self.__md_values = None
#        #: Stores the values for the tube barcode column.
#        self.__tube_barcode_values = None
#        #: Stores the values for the volume column.
#        self.__volume_values = None
#        #: Stores the values for the target rack barcode column.
#        self.__trg_rack_barcode_values = None
#        #: Stores the values for the target position column.
#        self.__trg_position_values = None
#
#    def reset(self):
#        CsvWriter.reset(self)
#        self.__translators = dict()
#        self.__lib_pool_values = []
#        self.__md_values = []
#        self.__tube_barcode_values = []
#        self.__volume_values = []
#        self.__trg_rack_barcode_values = []
#        self.__trg_position_values = []
#
#    def _init_column_map_list(self):
#        """
#        Creates the :attr:`_column_map_list`
#        """
#        self.add_info('Start log file generation ...')
#
#        self.__check_input()
#        if not self.has_errors(): self.__init_translators()
#        if not self.has_errors(): self.__store_column_values()
#        if not self.has_errors(): self.__generate_column_maps()
#
#    def __check_input(self):
#        # Checks the initialisation values.
#        self.add_debug('Check input values ...')
#        if self._check_input_class('executed worklists map',
#                                   self.executed_worklists, dict):
#            for i, ew in self.executed_worklists.iteritems():
#                if not self._check_input_class('worklist index', i, int): break
#                if not self._check_input_class('executed worklist', ew,
#                                               ExecutedWorklist): break
#        self._check_input_class('library layout', self.library_layout,
#                                LibraryLayout)
#        if self._check_input_class('sample stock racks map',
#                                   self.sample_stock_racks, dict):
#            for sector_index, issr in self.sample_stock_racks.iteritems():
#                if not self._check_input_class('sector index',
#                                               sector_index, int): break
#                if not self._check_input_class('sample stock rack', issr,
#                                               IsoSampleStockRack): break
#
#    def __init_translators(self):
#        # The translators are used to determine the rack position holding
#        # the pool information.
#        for sector_index, issr in self.sample_stock_racks.iteritems():
#            barcode = issr.rack.barcode
#            translator = RackSectorTranslator(number_sectors=NUMBER_SECTORS,
#                                source_sector_index=0,
#                                target_sector_index=sector_index,
#                                enforce_type=RackSectorTranslator.MANY_TO_ONE)
#            self.__translators[barcode] = translator
#
#    def __store_column_values(self):
#        # Store the values for the columns.
#        self.add_debug('Store values ...')
#        target_rack_map = dict()
#        for ew in self.executed_worklists.values():
#            for et in ew.executed_transfers:
#                target_rack_barcode = et.target_container.location.rack.barcode
#                if not target_rack_map.has_key(target_rack_barcode):
#                    target_rack_map[target_rack_barcode] = []
#                target_rack_map[target_rack_barcode].append(et)
#        barcodes = sorted(target_rack_map.keys())
#        well_containers = set()
#        for target_rack_barcode in barcodes:
#            non_single_md_src_pool = []
#            executed_transfers = target_rack_map[target_rack_barcode]
#            pool_map = self.__get_sorted_executed_transfers(executed_transfers,
#                                                            target_rack_barcode)
#            if self.has_errors(): break
#            pools = sorted(pool_map.keys(), cmp=lambda p1, p2:
#                                            cmp(p1.id, p2.id))
#            for pool in pools:
#                ets = pool_map[pool]
#                for et in ets:
#                    self.__lib_pool_values.append(get_trimmed_string(pool.id))
#                    volume = et.planned_transfer.volume \
#                                                    * VOLUME_CONVERSION_FACTOR
#                    self.__volume_values.append(get_trimmed_string(volume))
#                    self.__trg_rack_barcode_values.append(target_rack_barcode)
#                    trg_label = et.planned_transfer.target_position.label
#                    self.__trg_position_values.append(trg_label)
#
#                    src_tube = et.source_container
#                    self.__tube_barcode_values.append(src_tube.barcode)
#                    md_id = self.__get_molecule_design_id(src_tube)
#                    if md_id is None:
#                        info = '%s (rack %s)' % (src_tube.barcode,
#                                                 target_rack_barcode)
#                        non_single_md_src_pool.append(info)
#                    else:
#                        self.__md_values.append(get_trimmed_string(md_id))
#            if len(non_single_md_src_pool) > 0:
#                msg = 'Some source container contain more than one ' \
#                      'molecule design: %s.' % (sorted(non_single_md_src_pool))
#                self.add_error(msg)
#        if len(well_containers) > 0:
#            well_container_list = list(well_containers)
#            well_container_list.sort()
#            msg = 'Some source containers in the worklists are wells: %s!' \
#                   % (well_container_list)
#            self.add_error(msg)
#
#    def __get_sorted_executed_transfers(self, executed_transfers,
#                                        target_rack_barcode):
#        # Sorts the executed transfer of a worklist by molecule design pool
#        # ID.
#        pool_map = dict()
#        no_pools = set()
#        for et in executed_transfers:
#            translator = self.__get_translator(target_rack_barcode)
#            if translator is None: return None
#            rack_pos_96 = et.target_container.location.position
#            rack_pos_384 = translator.translate(rack_pos_96)
#
#            lib_pos = self.library_layout.get_working_position(rack_pos_384)
#            if lib_pos is None:
#                info = '%s (rack %s)' % (rack_pos_96.label, target_rack_barcode)
#                no_pools.add(info)
#                continue
#            pool = lib_pos.pool
#            add_list_map_element(pool_map, pool, et)
#        if len(no_pools) > 0:
#            no_pools_list = list(no_pools)
#            no_pools_list.sort()
#            msg = 'Could not find molecule design pools for the following ' \
#                  'target positions: %s.' % (no_pools_list)
#            self.add_error(msg)
#        return pool_map
#
#    def __get_translator(self, target_rack_barcode):
#        # Determines the sector index for the rack and passed the matching
#        # translator (lazy initialisation).
#        if self.__translators.has_key(target_rack_barcode):
#            return self.__translators[target_rack_barcode]
#        else:
#            msg = 'Unable to determine quadrant for rack "%s".' \
#                   % (target_rack_barcode)
#            self.add_error(msg)
#            return None
#
#    def __get_molecule_design_id(self, tube):
#        # Returns the molecule design for a single molecule design pool stock
#        # tube.
#        sms = tube.sample.sample_molecules
#        if not len(sms) == 1: return None
#        sm = sms[0]
#        return sm.molecule.molecule_design.id
#
#    def __generate_column_maps(self):
#        # Initialises the CsvColumnParameters object for the
#        # :attr:`_column_map_list`.
#        pool_column = CsvColumnParameters(self.LIBRARY_POOL_INDEX,
#                    self.LIBRARY_POOL_HEADER, self.__lib_pool_values)
#        md_column = CsvColumnParameters(self.MOLECULE_DESIGN_INDEX,
#                    self.MOLECULE_DESIGN_HEADER, self.__md_values)
#        tube_column = CsvColumnParameters(self.TUBE_BARCODE_INDEX,
#                    self.TUBE_BARCODE_HEADER, self.__tube_barcode_values)
#        volume_column = CsvColumnParameters(self.VOLUME_INDEX,
#                    self.VOLUME_HEADER, self.__volume_values)
#        rack_barcode_column = CsvColumnParameters(
#                    self.TARGET_RACK_BARCODE_INDEX,
#                    self.TARGET_RACK_BARCODE_HEADER,
#                    self.__trg_rack_barcode_values)
#        rack_position_column = CsvColumnParameters(self.TARGET_POSITION_INDEX,
#                    self.TARGET_POSITION_HEADER, self.__trg_position_values)
#
#        self._column_map_list = [pool_column, md_column, tube_column,
#                                 volume_column, rack_barcode_column,
#                                 rack_position_column]
