"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Library creation ISO execution.
"""
from thelma.tools.semiconstants import RACK_SHAPE_NAMES
from thelma.tools.semiconstants import RESERVOIR_SPECS_NAMES
from thelma.tools.semiconstants import get_positions_for_shape
from thelma.tools.semiconstants import get_reservoir_spec
from thelma.tools.base import BaseTool
from thelma.tools.iso.libcreation.base import LABELS
from thelma.tools.iso.libcreation.base import \
    LibraryLayoutConverter
from thelma.tools.iso.poolcreation.base import \
    StockSampleCreationLayoutConverter
from thelma.tools.worklists.series import RackSampleTransferJob
from thelma.tools.worklists.series import SampleDilutionJob
from thelma.tools.worklists.series import SeriesExecutor
from thelma.entities.iso import ISO_STATUS
from thelma.entities.iso import StockSampleCreationIso
from thelma.entities.liquidtransfer import ExecutedWorklist
from thelma.tools.iso.base import StockTransferWriterExecutor
from thelma.tools.worklists.series import SampleTransferJob
from thelma.entities.library import LibraryPlate


__docformat__ = 'reStructuredText en'
__all__ = ['LibraryCreationIsoExecutor',
           ]


class LibraryCreationIsoExecutor(BaseTool):
    NAME = 'Library Creation Executor'
    #: The barcode for the buffer source reservoir.
    BUFFER_RESERVOIR_BARCODE = 'buffer'

    def __init__(self, iso, user, parent=None):
        """
        Constructor.

        :param iso: library creation ISO to execute.
        :param user: User performing the execution.
        """
        BaseTool.__init__(self, parent=parent)
        self.iso = iso
        self.user = user
        #:
        self.__single_stock_rack_map = None
        #:
        self.__pool_stock_rack_map = None
        #:
        self.__prep_plate_map = None
        #:
        self.__ssc_layout_map = None
        #:
        self.__empty_stock_rack_positions_map = None
        #:
        self.__stock_trf_exc_wl_map = None
        # These are attributes required by the Trac reporter that this
        # executor is passed to.
        self.mode = StockTransferWriterExecutor.MODE_EXECUTE
        self.entity = iso

    def reset(self):
        BaseTool.reset(self)
        self.__single_stock_rack_map = {}
        self.__prep_plate_map = {}
        self.__ssc_layout_map = {}
        self.__empty_stock_rack_positions_map = {}
        self.__stock_trf_exc_wl_map = None

    def run(self):
        self.reset()
        self.add_info('Starting library creation executor.')
        self.__check_input()
        if not self.has_errors():
            self.__build_stock_rack_maps()
        if not self.has_errors():
            self.__build_preparation_plate_map()
        if not self.has_errors():
            transfer_job_map = {}
            self.__build_buffer_transfer_jobs(transfer_job_map)
        if not self.has_errors():
            # We need to keep track of the stock transfer job indices for
            # Trac reporting purposes.
            stock_transfer_jobs = []
            self.__build_stock_transfer_jobs(transfer_job_map,
                                             stock_transfer_jobs)
            self.__stock_trf_exc_wl_map = \
                                        dict.fromkeys(stock_transfer_jobs)
        if not self.has_errors():
            self.__build_aliquot_transfer_jobs(transfer_job_map)
        if not self.has_errors():
            executed_jobs_map = \
                self.__execute_transfer_jobs(transfer_job_map)
        if not self.has_errors() and not self.__pool_stock_rack_map is None:
            self.__create_stock_samples()
        if not self.has_errors():
            self.__create_library_plates()
        if not self.has_errors():
            self.iso.status = ISO_STATUS.DONE
            self.return_value = executed_jobs_map
            self.add_info('Library creation executor finished.')

    def get_working_layout(self):
        """
        Returns the working layout of the library (required by the Trac
        reporter).
        """
        cnv = LibraryLayoutConverter(self.iso.rack_layout,
                                     parent=self)
        return cnv.get_result()

    def get_executed_stock_worklists(self):
        """
        Returns the executed worklists for all stock transfer jobs (required
        by the Trac reporter).
        """
        return self.__stock_trf_exc_wl_map.values()

    def __check_input(self):
        try:
            assert isinstance(self.iso, StockSampleCreationIso) \
                , 'Invalid ISO parameter.'
            assert self.iso.status == ISO_STATUS.QUEUED \
                , 'ISO status must be QUEUED.'
        except AssertionError, err:
            self.add_error(str(err))

    def __build_stock_rack_maps(self):
        for isr in self.iso.iso_sector_stock_racks:
            label_values = LABELS.parse_sector_stock_rack_label(isr.label)
            rack_role = label_values[LABELS.MARKER_RACK_ROLE]
            sector_index = label_values[LABELS.MARKER_SECTOR_INDEX]
            if rack_role == LABELS.ROLE_POOL_STOCK:
                if self.__pool_stock_rack_map is None:
                    self.__pool_stock_rack_map = {}
                self.__pool_stock_rack_map[sector_index] = isr
            elif rack_role == LABELS.ROLE_SINGLE_DESIGN_STOCK:
                # The rack number encodes the single design number.
                rn = label_values.get(LABELS.MARKER_RACK_NUM)
                if not rn is None:
                    sdss_racks = \
                            self.__single_stock_rack_map.get(sector_index)
                    if sdss_racks is None:
                        sdss_racks = \
                            [None] * self.iso.iso_request.number_designs
                        self.__single_stock_rack_map[sector_index] = \
                                                                sdss_racks
                    sdss_racks[rn - 1] = isr
                else:
                    self.__single_stock_rack_map[sector_index] = [isr]
            else:
                msg = 'Invalid rack role "%s".' % rack_role
                self.add_error(msg)
        # Sanity checks.
        if not self.__pool_stock_rack_map is None \
           and not sorted(self.__pool_stock_rack_map.keys()) \
                == sorted(self.__single_stock_rack_map.keys()):
            msg = 'Not all pool stock racks have single design stock ' \
                  'racks or vice versa!'
            self.add_error(msg)
        if not set([len(val)
                    for val in self.__single_stock_rack_map.values()]) \
             == set([self.iso.iso_request.number_designs]):
            msg = 'The number of single design stock racks needs to be ' \
                  'the same in all sectors.'
            self.add_error(msg)

    def __build_preparation_plate_map(self):
        for spp in self.iso.iso_sector_preparation_plates:
            self.__prep_plate_map[spp.sector_index] = spp
            # Record empty positions to ignore later when building the
            # dilution jobs.
            cnv = StockSampleCreationLayoutConverter(spp.rack_layout,
                                                     parent=self)
            ssc_layout = cnv.get_result()
            self.__ssc_layout_map[spp.sector_index] = ssc_layout
            all_poss = get_positions_for_shape(RACK_SHAPE_NAMES.SHAPE_96)
            empty_poss = \
                list(set(all_poss).difference(ssc_layout.get_positions()))
            self.__empty_stock_rack_positions_map[spp.sector_index] = \
                                                                empty_poss

    def __build_buffer_transfer_jobs(self, transfer_job_map):
        self.add_debug('Creating buffer transfer jobs.')
        # The buffer worklists are stored with the ISO request.
        ws = self.iso.iso_request.worklist_series
        rs = get_reservoir_spec(RESERVOIR_SPECS_NAMES.QUARTER_MODULAR)
        has_pool_racks = not self.__pool_stock_rack_map is None
        for wl in ws.get_sorted_worklists():
            sec_idx = wl.index % 4
            job_idx = len(transfer_job_map)
            if has_pool_racks and wl.index < 4:
                # Pool stock rack buffer worklist.
                tgt_iso_rack = self.__pool_stock_rack_map.get(sec_idx)
            elif (has_pool_racks and wl.index < 8) \
                or (not has_pool_racks and wl.index < 4):
                # Preparation plate buffer worklist.
                tgt_iso_rack = self.__prep_plate_map.get(sec_idx)
            else: #
                break
            if tgt_iso_rack is None:
                # The last ISO might not have all sectors used.
                continue
            trf_job = SampleDilutionJob(
                        job_idx,
                        wl,
                        tgt_iso_rack.rack,
                        rs,
                        source_rack_barcode=self.BUFFER_RESERVOIR_BARCODE,
                        ignored_positions=
                            self.__empty_stock_rack_positions_map[sec_idx])
            transfer_job_map[job_idx] = (trf_job, wl)

    def __build_stock_transfer_jobs(self, transfer_job_map,
                                    stock_transfer_jobs):
        self.add_debug('Creating stock transfer jobs.')
        for sec_idx in range(4):
            has_pool_racks = not self.__pool_stock_rack_map is None
            if has_pool_racks:
                prep_src_rack_map = self.__pool_stock_rack_map
            else:
                prep_src_rack_map = \
                    dict([(idx, ssr[0])
                          for (idx, ssr) in
                          self.__single_stock_rack_map.items()])
            psr = prep_src_rack_map.get(sec_idx)
            if psr is None:
                continue
            if has_pool_racks:
                # With pool racks, we have two transfers:
                # sector single stock racks -> sector pool stock rack ->
                # sector preparation plate.
                # The first transfer is a sample transfer job, the second
                # a rack transfer job.
                for sdsr in self.__single_stock_rack_map[sec_idx]:
                    sdsr_wl = sdsr.worklist_series.get_worklist_for_index(0)
                    job_idx = len(transfer_job_map)
                    sdsr_trf_job = SampleTransferJob(job_idx, sdsr_wl,
                                                     psr.rack, sdsr.rack)
                transfer_job_map[job_idx] = (sdsr_trf_job, sdsr_wl)
                # Build the job for the transfer from the preparation plate
                # source rack to the preparation plate.
                psr_wl = psr.worklist_series.get_worklist_for_index(0)
                job_idx = len(transfer_job_map)
                psr_trf_job = \
                    RackSampleTransferJob(job_idx,
                                          psr_wl.planned_liquid_transfers[0],
                                          self.__prep_plate_map[sec_idx].rack,
                                          psr.rack)
            else:
                # Without pool racks, we only have one transfer:
                # sector single stock rack -> sector preparation plate.
                # This transfer is a sample transfer job.
                job_idx = len(transfer_job_map)
                psr_wl = psr.worklist_series.get_worklist_for_index(0)
                job_idx = len(transfer_job_map)
                psr_trf_job = \
                    SampleTransferJob(job_idx, psr_wl,
                                      self.__prep_plate_map[sec_idx].rack,
                                      psr.rack)
            transfer_job_map[job_idx] = (psr_trf_job, psr_wl)
            #
            stock_transfer_jobs.append(job_idx)

    def __build_aliquot_transfer_jobs(self, transfer_job_map):
        self.add_debug('Creating aliquot transfer jobs.')
        ws = self.iso.iso_request.worklist_series
        # The prep -> aliquot worklist is last in the series. The 96 well
        # sector prep plates are copied to the corresponding sector on the
        # 384 well aliquot plates.
        aq_wl = ws.get_sorted_worklists()[-1]
        for plt in aq_wl.planned_liquid_transfers:
            for iap in self.iso.iso_aliquot_plates:
                # Find the prep plate for the target sector.
                ipp = self.__prep_plate_map.get(plt.target_sector_index)
                if ipp is None:
                    continue
                job_idx = len(transfer_job_map)
                aq_trf_job = RackSampleTransferJob(job_idx,
                                                   plt,
                                                   iap.rack,
                                                   ipp.rack)
                transfer_job_map[job_idx] = (aq_trf_job, aq_wl)

    def __execute_transfer_jobs(self, transfer_job_map):
        exc_trf_job_map = dict([(k, v[0])
                                for (k, v) in transfer_job_map.iteritems()])
        se = SeriesExecutor(exc_trf_job_map, self.user, parent=self)
        exc_jobs_map = se.get_result()
        if not se.has_errors():
            # FIXME: This is terrible - we have to manually keep track of
            #        which worklist belongs to which transfer job and create
            #        ExecutedWorklist instances *only* for rack sample
            #        transfer jobs - plus we have to store the executed
            #        worklists for stock transfer jobs separately for
            #        reporting purposes.
            exc_wl_map = {}
            for trf_job_idx, trf_job_data in transfer_job_map.iteritems():
                trf_job, planned_wl = trf_job_data
                exc_data = exc_jobs_map[trf_job_idx]
                if isinstance(trf_job, RackSampleTransferJob):
                    ew = exc_wl_map.get(planned_wl)
                    if ew is None:
                        ew = ExecutedWorklist(planned_worklist=planned_wl)
                        exc_wl_map[planned_wl] = ew
                    ew.executed_liquid_transfers.append(exc_data)
                elif trf_job_idx in self.__stock_trf_exc_wl_map:
                    self.__stock_trf_exc_wl_map[trf_job_idx] = exc_data
        return exc_jobs_map

    def __create_stock_samples(self):
        mismatches = []
        for psr in self.__pool_stock_rack_map.values():
            ssc_layout = self.__ssc_layout_map[psr.sector_index]
            for tube_rack in psr.rack:
                for tube in tube_rack.containers:
                    sample = tube.sample
                    if sample is None:
                        continue
                    rack_pos = tube.location.position
                    ssc_pos = ssc_layout.get_working_position(rack_pos)
                    exp_mds = set([md.id for md in ssc_pos.pool])
                    found_mds = set([sm.molecule.molecule_design_id
                                     for sm in sample.sample_molecules])
                    if found_mds != exp_mds:
                        info = '%s (pool: %s, expected designs: %s, found ' \
                               'designs: %s)' \
                               % (rack_pos, ssc_pos.pool,
                                  '-'.join([str(md) for md in exp_mds]),
                                  '-'.join([str(md) for md in found_mds]))
                        mismatches.append(info)
                    else:
                        sample.convert_so_stock_sample()

    def __create_library_plates(self):
        lib = self.iso.iso_request.molecule_design_library
        layout_number = self.iso.layout_number
        for iso_plate in self.iso.iso_aliquot_plates:
            lp = LibraryPlate(lib, iso_plate.rack, layout_number)
            lib.library_plates.append(lp)

