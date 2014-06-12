"""
Library creation ISO execution.
"""
from thelma.automation.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.semiconstants import RESERVOIR_SPECS_NAMES
from thelma.automation.semiconstants import get_positions_for_shape
from thelma.automation.semiconstants import get_reservoir_spec
from thelma.automation.tools.base import BaseTool
from thelma.automation.tools.iso.libcreation.base import LABELS
from thelma.automation.tools.iso.libcreation.base import \
    LibraryLayoutConverter
from thelma.automation.tools.iso.poolcreation.base import \
    StockSampleCreationLayoutConverter
from thelma.automation.tools.worklists.series import RackSampleTransferJob
from thelma.automation.tools.worklists.series import SampleDilutionJob
from thelma.automation.tools.worklists.series import SeriesExecutor
from thelma.models.iso import ISO_STATUS
from thelma.models.iso import StockSampleCreationIso
from thelma.models.liquidtransfer import ExecutedWorklist


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

        :param iso: `StockSampleCreationIso` to execute.
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
        self.__empty_stock_rack_positions_map = None
        #:
        self.__stock_transfer_executed_worklist_map = None

    def reset(self):
        BaseTool.reset(self)
        self.__single_stock_rack_map = {}
        self.__prep_plate_map = {}
        self.__empty_stock_rack_positions_map = {}
        self.__stock_transfer_executed_worklist_map = None

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
            # We need to keep the stock transfer jobs separate for reporting
            # purposes.
            stock_transfer_job_map = {}
            self.__build_stock_transfer_jobs(stock_transfer_job_map)
            transfer_job_map.update(stock_transfer_job_map)
            self.__stock_transfer_executed_worklist_map = \
                            dict.fromkeys(stock_transfer_job_map.keys())
        if not self.has_errors():
            self.__build_aliquot_transfer_jobs(transfer_job_map)
        if not self.has_errors():
            executed_jobs_map = \
                self.__execute_transfer_jobs(transfer_job_map)
        if not self.has_errors():
            self.return_value = executed_jobs_map
            self.add_info('Library creation executor finished.')

    def get_working_layout(self):
        """
        Returns the working layout of the library (for reporting purposes).
        """
        cnv = LibraryLayoutConverter(self.iso.rack_layout,
                                     parent=self)
        return cnv.get_result()

    def get_executed_stock_worklists(self):
        """
        Returns the executed worklist map for all stock transfer jobs.
        """
        return self.__stock_transfer_executed_worklist_map()

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

    def __build_stock_transfer_jobs(self, transfer_job_map):
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
                # Build the job(s) for the transfer(s) from the single
                # design stock rack(s) to the pool stock racks.
                for sdsr in self.__single_stock_rack_map[sec_idx]:
                    sdsr_wl = sdsr.worklist_series.get_worklist_for_index(0)
                    job_idx = len(transfer_job_map)
                    sdsr_trf_job = RackSampleTransferJob(
                                        job_idx,
                                        sdsr_wl.planned_liquid_transfers[0],
                                        psr.rack,
                                        sdsr.rack)
                transfer_job_map[job_idx] = (sdsr_trf_job, sdsr_wl)
            # Build the job for the transfer from the preparation plate source
            # rack to the preparation plate.
            sr_wl = psr.worklist_series.get_worklist_for_index(0)
            job_idx = len(transfer_job_map)
            sr_trf_job = \
                RackSampleTransferJob(job_idx,
                                      sr_wl.planned_liquid_transfers[0],
                                      self.__prep_plate_map[sec_idx].rack,
                                      psr.rack)
            transfer_job_map[job_idx] = (sr_trf_job, sr_wl)

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
        # FIXME: This is terrible - we have to manually keep track of which
        #        worklist belongs to which transfer job and create
        #        ExecutedWorklist instances *only* for rack sample transfer
        #        jobs - plus we have to store the executed worklists for
        #        stock transfer jobs separately for reporting purposes.
        exc_wl_map = {}
        for trf_job_idx, trf_job_data in transfer_job_map.iteritems():
            trf_job, planned_wl = trf_job_data
            if isinstance(trf_job, RackSampleTransferJob):
                exc_rack_trf = exc_jobs_map[trf_job_idx]
                ew = exc_wl_map.get(planned_wl)
                if ew is None:
                    ew = ExecutedWorklist(planned_worklist=planned_wl)
                    exc_wl_map[planned_wl] = ew
                ew.executed_liquid_transfers.append(exc_rack_trf)
            if trf_job_idx in self.__stock_transfer_executed_worklist_map:
                self.__stock_transfer_executed_worklist_map[trf_job_idx] = ew
        return exc_jobs_map
