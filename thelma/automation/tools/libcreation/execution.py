#"""
#Tools involved the execution of library creation worklists.
#
#AAB
#"""
#from everest.entities.utils import get_root_aggregate
#from thelma.automation.tools.base import BaseAutomationTool
#from thelma.automation.tools.libcreation.base import LibraryBaseLayoutConverter
#from thelma.automation.tools.libcreation.base import LibraryLayout
#from thelma.automation.tools.libcreation.base import LibraryLayoutConverter
#from thelma.automation.tools.libcreation.base import NUMBER_SECTORS
#from thelma.automation.tools.libcreation.generation \
#    import LibraryCreationWorklistGenerator
#from thelma.automation.tools.libcreation.writer \
#    import LibraryCreationWorklistWriter
#from thelma.automation.tools.semiconstants import PIPETTING_SPECS_NAMES
#from thelma.automation.tools.semiconstants import RESERVOIR_SPECS_NAMES
#from thelma.automation.tools.semiconstants import get_384_rack_shape
#from thelma.automation.tools.semiconstants import get_96_rack_shape
#from thelma.automation.tools.semiconstants import get_positions_for_shape
#from thelma.automation.tools.semiconstants import get_reservoir_spec
#from thelma.automation.tools.utils.racksector import QuadrantIterator
#from thelma.automation.tools.utils.racksector import RackSectorTranslator
#from thelma.automation.tools.utils.racksector import get_sector_positions
#from thelma.automation.tools.worklists.series import ContainerDilutionJob
#from thelma.automation.tools.worklists.series import ContainerTransferJob
#from thelma.automation.tools.worklists.series import RackTransferJob
#from thelma.automation.tools.worklists.series import SeriesExecutor
#from thelma.interfaces import ITubeRack
#from thelma.models.iso import ISO_STATUS
#from thelma.models.iso import StockSampleCreationIso
#from thelma.models.liquidtransfer import ExecutedWorklist
#from thelma.models.rack import TubeRack
#from thelma.models.user import User
#import logging
#
#__docformat__ = 'reStructuredText en'
#
#__all__ = ['LibraryCreationExecutor',
#           'LibraryCreationStockRackVerifier',
#           'LibraryCreationBufferWorklistTransferJobCreator']
#
##TODO: create stock samples
#
#class LibraryCreationExecutor(BaseAutomationTool):
#    """
#    Executes the worklist file for a pool stock sample creation ISO (including
#    tube handler worklists). This comprises:
#
#        - tube handler worklist execution (requires file upload)
#        - execution of all worklist files
#
#    :Note: The stock samples for the pool are created externally.
#
#    **Return Value:** the updated ISO
#    """
#
#    NAME = 'LibraryCreationXL20Executor'
#
#    def __init__(self, library_creation_iso, user):
#        """
#        Constructor:
#
#        :param stock_sample_creation_iso: The pool stock sample creation ISO
#            for which to execute the worklists.
#        :type stock_sample_creation_iso:
#            :class:`thelma.models.iso.StockSampleCreationIso`
#        :param user: The user conducting the execution.
#        :type user: :class:`thelma.models.user.User`
#        """
#        BaseAutomationTool.__init__(self, depending=False)
#        #: The stock sample creation ISO for which to execute the worklists.
#        self.stock_sample_creation_iso = stock_sample_creation_iso
#        #: The user conducting the execution.
#        self.user = user
#
#        #: The library layout for this ISO.
#        self.__library_layout = None
#        #: Maps library position onto sector indices.
#        self.__library_sectors = None
#
#        #: The ISO sample stock racks mapped onto sector indices.
#        self.__sample_stock_racks = None
#        #: Maps tube racks (for 1 molecule design stock racks) onto sector
#        #: indices.
#        self.__stock_rack_map = None
#
#        #: The library source (preparation) plates (plate entities) mapped
#        #: onto sector indices.
#        self.__library_source_plates = None
#
#        #: The executed stock transfer worklists (mapped onto job indices;
#        #: refers to transfer from single molecule design to pool stock rack).
#        #: Required for reporting.
#        self.__stock_transfer_worklists = None
#
#        #: The transfer jobs for the series executor.
#        self.__transfer_jobs = None
#        #: The indices for the rack transfer jobs mapped onto the worklist
#        #: they belong to.
#        self.__rack_transfer_indices = None
#        #: Position with transfers but without library position (96-well,
#        #: mapped onto sectors).
#        self.__ignore_positions_96 = None
#
#    def reset(self):
#        BaseAutomationTool.reset(self)
#        self.__library_layout = None
#        self.__library_sectors = None
#        self.__sample_stock_racks = dict()
#        self.__stock_rack_map = dict()
#        self.__library_source_plates = dict()
#        self.__stock_transfer_worklists = dict()
#        self.__transfer_jobs = dict()
#        self.__rack_transfer_indices = dict()
#        self.__ignore_positions_96 = dict()
#
#    def run(self):
#        """
#        Executes the library creation worklists.
#        """
#        self.reset()
#        self.add_info('Start execution ...')
#
#        self.__check_input()
#        if not self.has_errors(): self.__get_library_layout()
#        if not self.has_errors():
#            self.__get_sample_stock_racks()
#            self.__get_library_source_plates()
#        if not self.has_errors(): self.__verify_single_md_stock_racks()
#        if not self.has_errors(): self.__find_ignored_positions()
#        if not self.has_errors(): self.__create_buffer_transfer_jobs()
#        if not self.has_errors(): self.__create_stock_transfer_jobs()
#        if not self.has_errors(): self.__create_preparation_transfer_jobs()
#        if not self.has_errors(): self.__create_aliquot_transfer_jobs()
#        if not self.has_errors(): self.__execute_transfer_jobs()
#        if not self.has_errors():
#            self.stock_sample_creation_iso.status = ISO_STATUS.DONE
#            self.return_value = self.stock_sample_creation_iso
#            self.add_info('Transfer execution completed.')
#
#    def get_executed_stock_worklists(self):
#        """
#        Returns the executed worklists that *deal with the stock transfer*
#        (for stock transfer reporting).
#        """
#        if self.return_value is None: return None
#        return self.__stock_transfer_worklists
#
#    def get_working_layout(self):
#        """
#        Returns the working layout containing the molecule design pool ID data
#        (for reporting).
#        """
#        if self.return_value is None: return None
#        return self.__library_layout
#
#    @property
#    def entity(self):
#        """
#        Returns the ISO. Required for reporting.
#        """
#        return self.stock_sample_creation_iso
#
#    def __check_input(self):
#        """
#        Checks the initialisation values.
#        """
#        self.add_debug('Check input values ...')
#
#        if self._check_input_class('stock sample creation ISO',
#                        self.stock_sample_creation_iso, StockSampleCreationIso):
#            status = self.stock_sample_creation_iso.status
#            if not status == ISO_STATUS.QUEUED:
#                msg = 'Unexpected ISO status: "%s"' % (status)
#                self.add_error(msg)
#
#        self._check_input_class('user', self.user, User)
#
#    def __get_library_layout(self):
#        """
#        Fetches the library layout and sorts its positions into quadrants.
#        """
#        self.add_debug('Fetch library layout ...')
#
#        converter = LibraryLayoutConverter(log=self.log,
#                        rack_layout=self.stock_sample_creation_iso.rack_layout)
#        self.__library_layout = converter.get_result()
#
#        if self.__library_layout is None:
#            msg = 'Error when trying to convert library layout.'
#            self.add_error(msg)
#        else:
#            self.__library_sectors = QuadrantIterator.sort_into_sectors(
#                                    working_layout=self.__library_layout,
#                                    number_sectors=NUMBER_SECTORS)
#            del_sectors = []
#            for sector_index, positions in self.__library_sectors.iteritems():
#                if len(positions) < 1: del_sectors.append(sector_index)
#            for sector_index in del_sectors:
#                del self.__library_sectors[sector_index]
#
#    def __get_sample_stock_racks(self):
#        """
#        Fetches the ISO sample stock racks and the single molecule stock racks
#        (barcodes are found in the worklist labels).
#        """
#        self.add_debug('Fetch stock racks')
#
#        writer_cls = LibraryCreationWorklistWriter
#        tube_rack_agg = get_root_aggregate(ITubeRack)
#        not_found = []
#
#        for issr in self.stock_sample_creation_iso.iso_sector_stock_racks:
#            self.__sample_stock_racks[issr.sector_index] = issr
#            label = issr.planned_worklist.label
#            starting_index = len(writer_cls.SAMPLE_STOCK_WORKLIST_LABEL)
#            barcode_str = label[starting_index:]
#            barcodes = barcode_str.split(writer_cls.\
#                                         SAMPLE_STOCK_WORKLIST_DELIMITER)
#            racks = []
#            for barcode in barcodes:
#                rack = tube_rack_agg.get_by_slug(barcode)
#                if rack is None:
#                    not_found.append(barcode)
#                else:
#                    racks.append(rack)
#            self.__stock_rack_map[issr.sector_index] = racks
#
#        if len(not_found) > 0:
#            msg = 'The following single molecule design source stock racks ' \
#                  'have not been found in the DB: %s!' \
#                  % (', '.join(sorted(not_found)))
#            self.add_error(msg)
#
#    def __get_library_source_plates(self):
#        """
#        Fetches the library source plates for this ISO and maps them onto
#        sector indices.
#        """
#        self.add_debug('Get library source plates ...')
#
#        for lsp in self.stock_sample_creation_iso.library_source_plates:
#            self.__library_source_plates[lsp.sector_index] = lsp.plate
#
#    def __verify_single_md_stock_racks(self):
#        """
#        Makes sure we have all the molecule designs present and in the right
#        positions and no additional tubes in the single molecule design
#        stock racks.
#        """
#        verifier = LibraryCreationStockRackVerifier(log=self.log,
#                                        library_layout=self.__library_layout,
#                                        stock_racks=self.__stock_rack_map)
#        compatible = verifier.get_result()
#
#        if compatible is None:
#            msg = 'Error in the verifier!'
#            self.add_error(msg)
#        elif not compatible:
#            msg = 'The stock racks with the single molecule designs are not ' \
#                  'compatible to the expected layout!'
#            self.add_error(msg)
#
#    def __find_ignored_positions(self):
#        """
#        Finds positions that are planned in the worklists but which are not
#        in the library layout (because there were not enough pools during
#        optimization). The positions are found by comparison with the
#        base layout.
#        """
#        self.add_debug('Find empty plate positions ...')
#
#        for sector_index in self.__library_sectors.keys():
#            self.__ignore_positions_96[sector_index] = []
#
#        converter = LibraryBaseLayoutConverter(log=self.log,
#                rack_layout=self.library_creation_iso.iso_request.iso_layout)
#        base_layout = converter.get_result()
#
#        if base_layout is None:
#            msg = 'Error when trying to convert library base layout.'
#            self.add_error(msg)
#        elif not len(base_layout) == len(self.__library_layout):
#            lib_positions = self.__library_layout.get_positions()
#            ignore_positions_384 = []
#            for rack_pos in base_layout.get_positions():
#                if not rack_pos in lib_positions:
#                    ignore_positions_384.append(rack_pos)
#            self.__find_ignored_sector_positions(ignore_positions_384)
#
#    def __find_ignored_sector_positions(self, ignore_positions_384):
#        """
#        Converts the position in the ignored position list for the 384-well
#        layout into 96-well position.
#
#        Positions for sectors that are not required (might be the case on the
#        last plate) are not checked.
#        """
#        for sector_index in range(NUMBER_SECTORS):
#            if not self.__library_sectors.has_key(sector_index): continue
#            sector_positions = get_sector_positions(sector_index=sector_index,
#                            rack_shape=get_384_rack_shape(),
#                            number_sectors=NUMBER_SECTORS)
#            translator = RackSectorTranslator(number_sectors=NUMBER_SECTORS,
#                        source_sector_index=sector_index,
#                        target_sector_index=0,
#                        enforce_type=RackSectorTranslator.ONE_TO_MANY)
#            for sector_pos in sector_positions:
#                if sector_pos in ignore_positions_384:
#                    rack_pos_96 = translator.translate(sector_pos)
#                    self.__ignore_positions_96[sector_index].append(rack_pos_96)
#
#    def __create_buffer_transfer_jobs(self):
#        """
#        Creates the transfer jobs for the buffer worklists.
#        """
#        self.add_debug('Create buffer transfer jobs ...')
#
#        stock_racks = dict()
#        for sector_index, issr in self.__sample_stock_racks.iteritems():
#            rack = issr.rack
#            stock_racks[sector_index] = rack
#
#        creator = LibraryCreationBufferWorklistTransferJobCreator(log=self.log,
#                                library_creation_iso=self.library_creation_iso,
#                                pool_stock_racks=stock_racks,
#                                ignored_positions=self.__ignore_positions_96)
#        self.__transfer_jobs = creator.get_result()
#
#        if self.__transfer_jobs is None:
#            msg = 'Unable to get buffer transfer jobs!'
#            self.add_error(msg)
#
#    def __create_stock_transfer_jobs(self):
#        """
#        Creates the transfer jobs for the pool creation. We do not need
#        to regard potential empty (ignored) positions here, because the
#        worklist creation is already base on the library layout.
#        """
#        self.add_debug('Create pool creation transfer jobs ...')
#
#        current_index = max(self.__transfer_jobs.keys())
#
#        for sector_index, issr in self.__sample_stock_racks.iteritems():
#            racks = self.__stock_rack_map[sector_index]
#            for rack in racks:
#                current_index += 1
#                ctj = ContainerTransferJob(index=current_index,
#                        planned_worklist=issr.planned_worklist,
#                        target_rack=issr.rack,
#                        source_rack=rack,
#                        pipetting_specs=PIPETTING_SPECS_NAMES.BIOMEK)
#                ctj.min_transfer_volume = 1
#                self.__transfer_jobs[current_index] = ctj
#                self.__stock_transfer_worklists[current_index] = None
#
#    def __create_preparation_transfer_jobs(self):
#        """
#        Creates the transfer jobs for the rack transfers (transfer from pool
#        stock racks to preparation (source) plates).
#        """
#        self.add_debug('Create preparation transfer jobs ...')
#
#        current_index = max(self.__transfer_jobs.keys())
#        worklist_series = self.library_creation_iso.iso_request.worklist_series
#
#        marker = LibraryCreationWorklistGenerator.\
#                 STOCK_TO_PREP_TRANSFER_WORKLIST_LABEL[2:]
#        rt_worklist = None
#        rack_transfer = None
#        for worklist in worklist_series:
#            if not marker in worklist.label: continue
#            if len(worklist.planned_transfers) != 1:
#                msg = 'The worklist for the transfer from pool stock ' \
#                      'rack preparation plate has an unexpected length: ' \
#                      '%i (expected: 1).' % (len(worklist.planned_transfers))
#                self.add_error(msg)
#            else:
#                rack_transfer = worklist.planned_transfers[0]
#                rt_worklist = worklist
#            break
#
#        if self.has_errors():
#            pass
#        elif rack_transfer is None:
#            msg = 'Unable to find worklist for the transfer from pool stock ' \
#                  'racks to library source (prepraration) plates.'
#            self.add_error(msg)
#        else:
#            job_indices = []
#            for sector_index, issr in self.__sample_stock_racks.iteritems():
#                stock_rack = issr.rack
#                prep_plate = self.__library_source_plates[sector_index]
#                current_index += 1
#                rtj = RackTransferJob(index=current_index,
#                                      planned_rack_transfer=rack_transfer,
#                                      target_rack=prep_plate,
#                                      source_rack=stock_rack)
#                self.__transfer_jobs[current_index] = rtj
#                job_indices.append(current_index)
#
#            self.__rack_transfer_indices[rt_worklist] = job_indices
#
#    def __create_aliquot_transfer_jobs(self):
#        """
#        Creates the transfer jobs for the rack transfers (transfer from
#        preparation (source) plates to aliquot plates).
#        """
#        self.add_debug('Create preparation transfer jobs ...')
#
#        aliquot_plates = dict()
#        for iap in self.library_creation_iso.iso_aliquot_plates:
#            plate = iap.plate
#            aliquot_plates[plate.label] = plate
#
#        current_index = max(self.__transfer_jobs.keys())
#        worklist_series = self.library_creation_iso.iso_request.worklist_series
#        marker = LibraryCreationWorklistGenerator.\
#                 PREP_TO_ALIQUOT_TRANSFER_WORKLIST_LABEL[2:]
#
#        aliquot_worklist = None
#        for worklist in worklist_series:
#            if marker in worklist.label:
#                aliquot_worklist = worklist
#                continue
#
#        if aliquot_worklist is None:
#            msg = 'Unable to find worklist for the transfer to the aliquot ' \
#                  'plates.'
#            self.add_error(msg)
#
#        else:
#            job_indices = []
#
#            for label in sorted(aliquot_plates.keys()):
#                plate = aliquot_plates[label]
#                for rack_transfer in aliquot_worklist.planned_transfers:
#                    current_index += 1
#                    sector_index = rack_transfer.target_sector_index
#                    if not self.__library_sectors.has_key(sector_index):
#                        continue
#                    prep_plate = self.__library_source_plates[sector_index]
#                    rtj = RackTransferJob(index=current_index,
#                                planned_rack_transfer=rack_transfer,
#                                target_rack=plate, source_rack=prep_plate)
#                    self.__transfer_jobs[current_index] = rtj
#                    job_indices.append(current_index)
#
#            self.__rack_transfer_indices[aliquot_worklist] = job_indices
#
#    def __execute_transfer_jobs(self):
#        """
#        Executes the transfer jobs. The executed worklists for container
#        dilutions and transfer are created by the tool, the executed worklists
#        for rack transfers have to be created here.
#        """
#        self.add_debug('Execute transfer job ...')
#
#        executor = SeriesExecutor(transfer_jobs=self.__transfer_jobs.values(),
#                                  user=self.user, log=self.log)
#        executed_items = executor.get_result()
#
#        if executed_items is None:
#            msg = 'Error during serial transfer execution.'
#            self.add_error(msg)
#        else:
#            self.__create_executed_worklists_for_rack_transfers(executed_items)
#            for job_index in self.__stock_transfer_worklists.keys():
#                executed_wl = executed_items[job_index]
#                self.__stock_transfer_worklists[job_index] = executed_wl
#
#    def __create_executed_worklists_for_rack_transfers(self, executed_items):
#        """
#        Creates the executed worklists for the rack transfer jobs.
#        """
#        self.add_debug('Create executed rack transfer worklists ...')
#
#        for worklist, indices in self.__rack_transfer_indices.iteritems():
#            executed_worklist = ExecutedWorklist(planned_worklist=worklist)
#            for i in indices:
#                ert = executed_items[i]
#                executed_worklist.executed_transfers.append(ert)
#
#
#class LibraryCreationStockRackVerifier(BaseAutomationTool):
#    """
#    This tools verifies whether the single molecule design stock racks of
#    a library creation ISO (after rearrangment of stock tubes) are compliant
#    to the library layout of the passed ISO.
#
#    **Return Value:** boolean
#    """
#    NAME = 'Library Creation Stock Rack Verifier'
#
#    def __init__(self, library_layout, stock_racks, log):
#        """
#        Constructor:
#
#        :param library_layout: Contains the pool and molecule design data.
#        :type library_layout: :class:`LibraryLayout`
#
#        :param stock_racks: The stock racks for each sector.
#        :type stock_racks: lists of racks mapped onto sector indices
#
#        :param log: The log to write into.
#        :type log: :class:`thelma.ThelmaLog`
#        """
#        BaseAutomationTool.__init__(self, log=log)
#
#        #: Contains the pool and molecule design data.
#        self.library_layout = library_layout
#        #: The stock racks for each sector (lists) mapped onto sector indices.
#        self.stock_racks = stock_racks
#
#        #: The rack shape of a stock rack (96 wells).
#        self.stock_rack_shape = None
#
#    def reset(self):
#        BaseAutomationTool.reset(self)
#        self.stock_rack_shape = get_96_rack_shape()
#
#    def run(self):
#        self.reset()
#        self.add_info('Start ISO sample stock rack verification ...')
#
#        self.__check_input()
#
#        if not self.has_errors():
#
#            self.return_value = True
#            for sector_index, racks in self.stock_racks.iteritems():
#                is_valid = self.__is_valid_sector(sector_index, racks)
#                if not is_valid:
#                    self.return_value = False
#
#        if not self.has_errors():
#            self.add_info('Verification completed.')
#
#    def __check_input(self):
#        """
#        Checks the initialisation values.
#        """
#        self.add_debug('Check input values ...')
#
#        self._check_input_class('library layout', self.library_layout,
#                                LibraryLayout)
#        if self._check_input_class('stock rack map', self.stock_racks, dict):
#            for sector_index, racks in self.stock_racks.iteritems():
#                if not self._check_input_class('sector index', sector_index,
#                                               int): break
#                if not self._check_input_class('rack list', racks, list): break
#
#    def __is_valid_sector(self, sector_index, racks):
#        """
#        Compares the molecule designs in one rack sector with the data
#        from the library layout.
#        """
#        translated_positions = self.__get_translation_map(sector_index)
#        exp_pools = self.__get_expected_pools(translated_positions)
#        exp_mds = dict()
#        for md_pool in exp_pools.values():
#            for md in md_pool:
#                if not exp_mds.has_key(md):
#                    exp_mds[md] = 1
#                else:
#                    exp_mds[md] += 1
#
#        additional_mds = []
#        missing_mds = []
#        mismatching_mds = []
#
#        for rack in racks:
#            checked_positions = set()
#            for tube in rack.containers:
#                rack_pos_96 = tube.location.position
#                checked_positions.add(rack_pos_96)
#                sample = tube.sample
#                if sample is None or len(sample.sample_molecules) < 1:
#                    if exp_pools.has_key(rack_pos_96):
#                        exp_pool = exp_pools[rack_pos_96]
#                        md_ids = '-'.join([str(md.id) for md in exp_pool])
#                        info = '%s in %s (exp: %s)' % (rack_pos_96.label,
#                               rack.barcode, md_ids)
#                        missing_mds.append(str(info))
#                        for md in exp_pool:
#                            exp_mds[md] -= 1
#                            if exp_mds[md] == 0:
#                                del exp_mds[md]
#                    continue
#                mds = []
#                for sm in sample.sample_molecules:
#                    mds.append(sm.molecule.molecule_design)
#                found_md_str = '-'.join([str(md.id) for md in mds])
#                if not exp_pools.has_key(rack_pos_96):
#                    info = '%s in %s (found: %s)' % (rack_pos_96.label,
#                            rack.barcode, found_md_str)
#                    additional_mds.append(str(info))
#                    continue
#                exp_pool = exp_pools[rack_pos_96]
#                for md in mds:
#                    if not md in exp_pool.molecule_designs:
#                        exp_id_str = '-'.join([str(md.id) for md in exp_pool])
#                        info = '%s in %s (expected: %s, found: %s)' % (
#                                rack_pos_96.label, rack.barcode, exp_id_str,
#                                found_md_str)
#                        mismatching_mds.append(str(info))
#                    else:
#                        exp_mds[md] -= 1
#                        if exp_mds[md] == 0:
#                            del exp_mds[md]
#
#            if not len(checked_positions) == len(exp_pools):
#                for rack_pos, exp_pool in exp_pools.iteritems():
#                    if rack_pos in checked_positions: continue
#                    md_ids = '-'.join([str(md.id) for md in exp_pool])
#                    info = '%s in %s (exp: %s)' % (rack_pos.label,
#                           rack.barcode, md_ids)
#                    missing_mds.append(str(info))
#
#        for md in exp_mds.keys():
#            info = '%i' % (md.id)
#            missing_mds.append(info)
#
#        is_valid = True
#        if len(missing_mds) > 0:
#            msg = 'There are some molecule designs missing in the prepared ' \
#                  'stock racks for sector %i: %s.' % (sector_index + 1,
#                                                      sorted(missing_mds))
#            self.add_error(msg)
#            is_valid = False
#        if len(additional_mds) > 0:
#            msg = 'The stock racks for sector %i contain molecule designs ' \
#                  'that should not be there: %s.' % (sector_index + 1,
#                                                     sorted(additional_mds))
#            self.add_error(msg)
#            is_valid = False
#        if len(mismatching_mds) > 0:
#            msg = 'Some molecule designs in the stock racks or sector %i ' \
#                  'do not match the expected ones: %s.' % (sector_index + 1,
#                                                    sorted(mismatching_mds))
#            self.add_error(msg)
#
#        return is_valid
#
#    def __get_translation_map(self, sector_index):
#        """
#        Returns the 96-well position corresponding to the position in
#        a particular 384-well sector.
#        """
#        positions = dict()
#        translator = RackSectorTranslator(number_sectors=NUMBER_SECTORS,
#                    source_sector_index=sector_index,
#                    target_sector_index=0,
#                    enforce_type=RackSectorTranslator.MANY_TO_ONE)
#        for rack_pos_96 in get_positions_for_shape(self.stock_rack_shape):
#            rack_pos_384 = translator.translate(rack_pos_96)
#            positions[rack_pos_96] = rack_pos_384
#
#        return positions
#
#    def __get_expected_pools(self, translated_positions):
#        """
#        Returns the pools and molecule designs expected for a particular rack
#        sector.
#        """
#        pool_map = dict()
#        for rack_pos_96, rack_pos_384 in translated_positions.iteritems():
#            lib_pos = self.library_layout.get_working_position(rack_pos_384)
#            if not lib_pos is None:
#                pool_map[rack_pos_96] = lib_pos.pool
#
#        return pool_map
#
#
#class LibraryCreationBufferWorklistTransferJobCreator(BaseAutomationTool):
#    """
#    Creates the transfer jobs (all container dilutions) for the non-CyBio
#    worklists of the library creation (buffer dilutions).
#
#    **Return Value:** transfer jobs mapped onto job indices.
#    """
#
#    NAME = 'Library Creation Buffer Worklist Transfer Job Creator'
#
#    #: The barcode for the buffer source reservoir.
#    BUFFER_RESERVOIR_BARCODE = 'buffer_reservoir'
#
#    def __init__(self, log, library_creation_iso, pool_stock_racks,
#                 ignored_positions):
#        """
#        Constructor:
#
#        :param log: The log to write into.
#        :type log: :class:`thelma.ThelmaLog`
#
#        :param library_creation_iso: The library creation ISO for which to
#            generate the transfer jobs.
#        :type library_creation_iso:
#            :class:`thelma.models.library.LibraryCreationIso`
#
#        :param pool_stock_racks: The pool stock racks mapped onto sector
#            indices (these racks have to have empty tubes in defined positions).
#        :type pool_stock_racks: :class:`thelma.models.rack.TubeRack`
#
#        :param ignored_positions: Target positions that shall be ignored
#            during worklist execution (because there is no library position
#            for them). Regard that sectors which are not omitted completely
#            are not stored in the list (the sector index as key is missing).
#            In contrast, sectors without ignored positions have empty
#            lists as values.
#        :type ignored_positions: :class:`dict` (rack position list mapped
#            onto sector indices).
#        """
#        BaseAutomationTool.__init__(self, log=log)
#
#        #: The library creation ISO for which to create the transfer jobs.
#        self.library_creation_iso = library_creation_iso
#        #: The barcodes for the pool stock racks racks.
#        self.pool_stock_racks = pool_stock_racks
#        #: Target positions that shall be ignored during worklist execution
#        #: (because there is no library position for them) mapped onto
#        #: sector indices. Regard that sectors which are not omitted completely
#        #: are not stored in the list (the sector index as key is missing). In
#        #: contrast, sectors without ignored positions have empty lists as
#        #: values.
#        self.ignored_positions = ignored_positions
#
#        #: The worklists of the ISO worklist series mapped onto indices.
#        self.__worklist_map = None
#        #: The library source plates mapped onto sector indices.
#        self.__source_plates = None
#
#        #: The transfer jobs to create mapped onto job indices.
#        self.__transfer_jobs = None
#
#    def reset(self):
#        BaseAutomationTool.reset(self)
#        self.__worklist_map = dict()
#        self.__source_plates = dict()
#        self.__transfer_jobs = dict()
#
#    def run(self):
#        """
#        Creates the transfer jobs.
#        """
#        self.reset()
#        self.add_debug('Create transfer jobs ...')
#
#        self.__check_input()
#        if not self.has_errors(): self.__create_worklist_map()
#        if not self.has_errors(): self.__create_stock_buffer_transfer_jobs()
#        if not self.has_errors(): self.__get_library_source_plates()
#        if not self.has_errors(): self.__create_source_buffer_transfer_jobs()
#        if not self.has_errors():
#            self.return_value = self.__transfer_jobs
#            self.add_info('Transfer job creation completed.')
#
#    def __check_input(self):
#        """
#        Checks the initialisation values.
#        """
#        self._check_input_class('library creation ISO',
#                                self.library_creation_iso, LibraryCreationIso)
#        if self._check_input_class('pool stock rack map', self.pool_stock_racks,
#                                   dict):
#            for sector_index, rack in self.pool_stock_racks.iteritems():
#                if not self._check_input_class('sector index', sector_index,
#                                               int): break
#                if not self._check_input_class('pool stock rack', rack,
#                                               TubeRack): break
#            if not len(self.pool_stock_racks) > 0:
#                msg = 'There are no racks in the pool stock rack map!'
#                self.add_error(msg)
#
#        if self._check_input_class('ignored positions map',
#                                   self.ignored_positions, dict):
#            for si, positions in self.ignored_positions.iteritems():
#                if not self._check_input_class('sector index', si, int): break
#                if not self._check_input_class('position list', positions,
#                                               list): break
#
#    def __create_worklist_map(self):
#        """
#        Maps on worklists onto worklists indices.
#        """
#
#        worklist_series = self.library_creation_iso.iso_request.worklist_series
#        if worklist_series is None:
#            msg = 'Unable to find worklist series!'
#            self.add_error(msg)
#        else:
#            for worklist in worklist_series:
#                self.__worklist_map[worklist.index] = worklist
#
#    def __create_stock_buffer_transfer_jobs(self):
#        """
#        All jobs are container dilution job. The worklist are determined by
#        name.
#        """
#        self.add_debug('Create stock buffer transfer jobs ...')
#
#        job_index = 0
#        rs_quarter = get_reservoir_spec(RESERVOIR_SPECS_NAMES.QUARTER_MODULAR)
#        sorted_indices = sorted(self.__worklist_map.keys())
#
#        wl_marker = LibraryCreationWorklistGenerator.\
#                                LIBRARY_STOCK_BUFFER_WORKLIST_LABEL[2:-2]
#        for i in sorted_indices:
#            worklist_index = sorted_indices[i]
#            worklist = self.__worklist_map[worklist_index]
#            if not wl_marker in worklist.label: continue
#            sector_index = int(worklist.label[-1]) - 1
#            if not self.ignored_positions.has_key(sector_index): continue
#            pool_stock_rack = self.pool_stock_racks[sector_index]
#            cdj = ContainerDilutionJob(index=job_index,
#                        planned_worklist=worklist,
#                        target_rack=pool_stock_rack,
#                        reservoir_specs=rs_quarter,
#                        source_rack_barcode=self.BUFFER_RESERVOIR_BARCODE,
#                        ignored_positions=self.ignored_positions[sector_index],
#                        pipetting_specs=PIPETTING_SPECS_NAMES.BIOMEK)
#            self.__transfer_jobs[job_index] = cdj
#            job_index += 1
#
#        if not len(self.__transfer_jobs) == len(self.pool_stock_racks):
#            msg = 'Some stock buffer worklists are missing! Expected ' \
#                  'number: %i, found: %i.' % (len(self.pool_stock_racks),
#                                              len(self.__transfer_jobs))
#            self.add_error(msg)
#
#    def __get_library_source_plates(self):
#        """
#        Maps library source plates (plate entity) onto sector indices.
#        """
#        for lsp in self.library_creation_iso.library_source_plates:
#            self.__source_plates[lsp.sector_index] = lsp.plate
#
#    def __create_source_buffer_transfer_jobs(self):
#        """
#        All jobs are container dilution jobs. The worklsits are determined
#        by name.
#        """
#        self.add_debug('Create source plate buffer transfer jobs ...')
#
#        job_index = len(self.__transfer_jobs)
#        rs_quarter = get_reservoir_spec(RESERVOIR_SPECS_NAMES.QUARTER_MODULAR)
#        sorted_indices = sorted(self.__worklist_map.keys())
#
#        wl_marker = LibraryCreationWorklistGenerator.\
#                    LIBRARY_PREP_BUFFER_WORKLIST_LABEL[2:-2]
#        for i in sorted_indices:
#            worklist_index = sorted_indices[i]
#            worklist = self.__worklist_map[worklist_index]
#            if not wl_marker in worklist.label: continue
#            sector_index = int(worklist.label[-1]) - 1
#            if not self.ignored_positions.has_key(sector_index): continue
#            source_plate = self.__source_plates[sector_index]
#            cdj = ContainerDilutionJob(index=job_index,
#                       planned_worklist=worklist,
#                       target_rack=source_plate,
#                       reservoir_specs=rs_quarter,
#                       source_rack_barcode=self.BUFFER_RESERVOIR_BARCODE,
#                       ignored_positions=self.ignored_positions[sector_index],
#                       pipetting_specs=PIPETTING_SPECS_NAMES.BIOMEK)
#            self.__transfer_jobs[job_index] = cdj
#            job_index += 1
#
#        exp_length = len(self.__source_plates) + len(self.pool_stock_racks)
#        if not len(self.__transfer_jobs) == exp_length:
#            msg = 'Some source buffer worklists are missing! Expected ' \
#                  'number: %i, found: %i.' % (len(self.__source_plates),
#                        len(self.__transfer_jobs) - len(self.pool_stock_racks))
#            self.add_error(msg)
