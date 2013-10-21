"""
Tools involved the execution of pool stock sample creation worklists.

AAB
"""
from thelma.automation.semiconstants import PIPETTING_SPECS_NAMES
from thelma.automation.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.semiconstants import RESERVOIR_SPECS_NAMES
from thelma.automation.semiconstants import get_positions_for_shape
from thelma.automation.semiconstants import get_reservoir_spec
from thelma.automation.tools.iso.base import IsoRackContainer
from thelma.automation.tools.iso.base import StockRackVerifier
from thelma.automation.tools.iso.base import StockTransferWriterExecutor
from thelma.automation.tools.iso.poolcreation.base \
    import PoolCreationStockRackLayoutConverter
from thelma.automation.tools.iso.poolcreation.base \
    import StockSampleCreationLayoutConverter
from thelma.automation.tools.iso.poolcreation.base import LABELS
from thelma.automation.tools.iso.poolcreation.generation \
    import StockSampleCreationWorklistGenerator
from thelma.automation.tools.worklists.series import SampleDilutionJob
from thelma.automation.tools.worklists.series import SampleTransferJob
from thelma.models.iso import ISO_STATUS
from thelma.models.iso import StockSampleCreationIso

__docformat__ = 'reStructuredText en'

__all__ = ['StockSampleCreationExecutor']


class StockSampleCreationExecutor(StockTransferWriterExecutor):
    """
    Executes the worklist file for a pool stock sample creation ISO.
    This comprises both buffer dilution and stock transfer.

    **Return Value:** the updated ISO
    """
    NAME = 'Stock Sample Creation Executor'

    ENTITY_CLS = StockSampleCreationIso

    #: The barcode for the buffer source reservoir.
    BUFFER_RESERVOIR_BARCODE = 'buffer_reservoir'

    _MODES = [StockTransferWriterExecutor.MODE_EXECUTE]

    def __init__(self, iso, user, **kw):
        """
        Constructor:

        :param iso: The stock sample creation ISO for which to execute the
            worklists.
        :type iso: :class:`thelma.models.iso.StockSampleCreationIso`

        :param user: The user conducting the execution.
        :type user: :class:`thelma.models.user.User`
        """
        StockTransferWriterExecutor.__init__(self, depending=False, user=user,
                      entity=iso, mode=StockTransferWriterExecutor.MODE_EXECUTE)

        #: The stock sample creation layout for this ISO.
        self.__ssc_layout = None

        #: The :class:`IsoRackContainer` for each stock rack mapped onto
        #: rack marker.
        self.__rack_containers = None
        #: The stock rack that serves as target rack (:class:`IsoStockRack`).
        self.__pool_stock_rack = None

        #: The stock transfer worklist is the only worklist in the stock rack
        #: series.
        self.__stock_transfer_worklist = None

        #: The transfer jobs for the series executor.
        self.__transfer_jobs = None
        #: The indices for the rack transfer jobs mapped onto the worklist
        #: they belong to.
        self.__rack_transfer_indices = None
        #: Positions without library positions (i.e. without transfer).
        self.__ignore_positions = None

    def reset(self):
        StockTransferWriterExecutor.reset(self)
        self.__ssc_layout = None
        self.__rack_containers = dict()
        self.__pool_stock_rack = None
        self.__stock_transfer_worklist = None
        self.__transfer_jobs = dict()
        self.__rack_transfer_indices = dict()
        self.__ignore_positions = []

    def _create_transfer_jobs(self):
        """
        Executes the pool creation worklists.
        """
        if not self.has_errors(): self.__get_layout()
        if not self.has_errors(): self.__get_racks()
        if not self.has_errors(): self.__create_buffer_transfer_job()
        if not self.has_errors(): self.__create_stock_transfer_jobs()
        if not self.has_errors(): self._execute_worklists()
        if not self.has_errors(): self.__create_stock_samples()
        if not self.has_errors():
            self.return_value = self.entity
            self.add_info('Transfer execution completed.')

    def get_stock_sample_creation_layout(self):
        """
        Returns the working layout containing the molecule design pool ID data
        (for reporting).
        """
        return self._get_additional_value(self.__ssc_layout)

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        StockTransferWriterExecutor._check_input()
        if not self.has_errors() and \
                                not self.entity.status == ISO_STATUS.QUEUED:
            msg = 'Unexpected ISO status: "%s"' % (self.entity.status)
            self.add_error(msg)

    def __get_layout(self):
        """
        Fetches the stock sample layout and sorts its positions into quadrants.
        """
        self.add_debug('Fetch stock sample layout ...')

        converter = StockSampleCreationLayoutConverter(log=self.log,
                                           rack_layout=self.entity.rack_layout)
        self.__ssc_layout = converter.get_result()

        if self.__ssc_layout is None:
            msg = 'Error when trying to convert stock sample creation layout.'
            self.add_error(msg)
        else:
            ssc_positions = self.__ssc_layout.get_positions()
            for rack_pos in get_positions_for_shape(RACK_SHAPE_NAMES.SHAPE_96):
                if not rack_pos in ssc_positions:
                    self.__ignore_positions.append(rack_pos)

    def __get_racks(self):
        """
        Fetches the ISO stock rack and the single molecule stock racks
        (barcodes for the single design racks are found in the worklist labels).
        """
        self.add_debug('Fetch stock racks ...')

        isrs = self.entity.iso_stock_racks
        for isr in isrs:
            label = isr.label
            label_values = LABELS.parse_stock_rack_label(label)
            rack_marker = label_values[LABELS.MARKER_RACK_MARKER]
            if rack_marker == LABELS.ROLE_POOL_STOCK:
                if self.__pool_stock_rack is not None:
                    msg = 'There are several pool stock racks for this ISO!'
                    self.add_error(msg)
                    break
                self.__pool_stock_rack = rack_marker
            else:
                rack_container = IsoRackContainer(rack=isr.rack,
                                 rack_marker=rack_marker, label=label)
                self.__rack_containers[rack_marker] = rack_container

        number_designs = self.entity.iso_request.number_designs
        exp_lengths = (number_designs, 1)
        if not len(isrs) in exp_lengths:
            msg = 'There is an unexpected number of destination stock racks ' \
                  'attached to this ISO (%i). There should be %s! ' \
                  % (self._get_joined_str(exp_lengths, is_strs=False,
                                          sort_items=False, separator=' or '))
            self.add_error(msg)
            return None
        elif self.__pool_stock_rack is None and not self.has_errors():
            msg = 'There is no pool stock rack for this ISO!'
            self.add_error(msg)
        else:
            ws = self.__pool_stock_rack.worklist_series
            if len(ws) > 1:
                msg = 'The stock rack worklist series has an unexpected ' \
                      'length (%i instead of 1)!' % (len(ws))
                self.add_error(msg)
                return None
            self.__stock_transfer_worklist = ws.get_sorted_worklists()[0]

    def __create_buffer_transfer_job(self):
        """
        Creates the transfer job for the buffer worklist.
        """
        self.add_debug('Create buffer transfer jobs ...')

        worklist_series = self.entity.iso_request.worklist_series
        buffer_worklist = worklist_series.get_worklist_for_index(
                  StockSampleCreationWorklistGenerator.BUFFER_WORKLIST_INDEX)

        rs_quarter = get_reservoir_spec(RESERVOIR_SPECS_NAMES.QUARTER_MODULAR)
        job_index = len(self.__transfer_jobs)
        cdj = SampleDilutionJob(index=job_index,
                             planned_worklist=buffer_worklist,
                             target_rack=self.__pool_stock_rack.rack,
                             reservoir_specs=rs_quarter,
                             source_rack_barcode=self.BUFFER_RESERVOIR_BARCODE,
                             ignored_positions=self.__ignore_positions,
                             pipetting_specs=PIPETTING_SPECS_NAMES.BIOMEK)
        self.__transfer_jobs[job_index] = cdj

    def __create_stock_transfer_jobs(self):
        """
        Creates the transfer jobs for the pool creation. We do not need
        to regard potential empty (ignored) positions here, because the
        worklist creation is already based on the library layout.
        """
        self.add_debug('Create pool creation transfer jobs ...')

        for rack_container in self.__rack_containers.values():
            job_index = len(self.__transfer_jobs)
            stj = SampleTransferJob(index=job_index,
                    planned_worklist=self.__stock_transfer_worklist,
                    target_rack=self.__pool_stock_rack.rack,
                    source_rack=rack_container.rack,
                    pipetting_specs=PIPETTING_SPECS_NAMES.BIOMEK)
            self.__transfer_jobs[job_index] = stj

    def _verify_stock_racks(self):
        for isr in self.entity.iso_stock_racks:
            layout = None
            if isr.rack == self.__pool_stock_rack:
                converter = PoolCreationStockRackLayoutConverter(log=self.log,
                                                    rack_layout=isr.rack_layout)
                layout = converter.get_result()
                if layout is None:
                    msg = 'Error when trying to convert pool stock rack layout!'
                    self.add_error(msg)
                    break
            verifier = StockRackVerifier(log=self.log, stock_rack=isr,
                                         stock_rack_layout=layout)
            compatible = verifier.get_result()
            rack_name = '%s (%s)' % (isr.rack.barcode, isr.label)
            if compatible is None:
                msg = 'Error when trying to verify stock rack %s.' % (rack_name)
                self.add_error(msg)
            elif not compatible:
                msg = 'Stock rack %s does not match the expected layout.' \
                       % (rack_name)
                self.add_error(msg)

    def _check_for_previous_execution(self):
        if len(self.__stock_transfer_worklist.executed_worklists) > 0:
            msg = 'The stock transfer has already been executed before.'
            self.add_error(msg)

    def _extract_executed_stock_worklists(self, executed_worklists):
        """
        The worklists are recognized by label.
        """
        exp_label = self.__stock_transfer_worklist.label
        for ew in executed_worklists:
            if ew.planned_worklist.label == exp_label:
                self._executed_stock_worklists.append(ew)

    def __create_stock_samples(self):
        """
        Converts the new pool samples into :class:`StockSample` entities.

        We also compare expected and found molecule designs again. This has
        in theory already been done by the verifier. However, we have done a
        transfer in between and we want to exclude the (slight) chance that
        something went wrong during this process since afterwards it will hardly
        be possible to reconstruct the course of events and in case of the
        stock we better double-check.
        """
        self.add_debug('Generate stock samples ...')

        mismatch = []
        diff_supplier = []

        for tube in self.__pool_stock_rack.rack.containers:
            sample = tube.sample
            if sample is None: continue
            # check whether expected pool
            rack_pos = tube.location.position
            ssc_pos = self.__ssc_layout.get_working_position(rack_pos)
            pool = ssc_pos.pool
            exp_mds = set()
            for md in pool: exp_mds.add(md.id)
            found_mds = set()
            suppliers = set()
            for sm in sample.sample_molecules:
                md_id = sm.molecule.molecule_design.id
                found_mds.add(md_id)
                suppliers.add(sm.molecule.supplier)
            if not exp_mds == found_mds:
                info = '%s (pool: %s, expected designs: %s, found designs: ' \
                       '%s)' % (rack_pos, pool,
                        self._get_joined_str(exp_mds, is_strs=False,
                                             separator='-'),
                        self._get_joined_str(found_mds, is_strs=False,
                                             separator='-'))
                mismatch.append(info)
                continue
            if len(suppliers) > 1:
                info = '%s (pool: %s, found: %s)' % (rack_pos, pool,
                       ', '.join(sorted([str(s.name) for s in suppliers])))
                diff_supplier.append(info)
                continue
            else:
                sample.convert_to_stock_sample()

        if len(mismatch) > 0:
            msg = 'The molecule designs for the following stock sample do ' \
                  'not match the expected designs for this sample. This ' \
                  'should not happen. Talk to the IT department, please. ' \
                  'Details: %s.' % (','.join(sorted(mismatch)))
            self.add_error(msg)
        if len(diff_supplier) > 0:
            msg = 'The designs for some of the pools originate from ' \
                  'different suppliers: %s.' \
                   % (', '.join(sorted(diff_supplier)))
            self.add_error(msg)

    def _update_iso_status(self):
        self.entity.status = ISO_STATUS.DONE

    def _get_file_map(self, merged_stream_map, rack_transfer_stream):
        """
        We do not need to implement this method because printing mode is not
        not allowed anyway.
        """
        self.add_error('Printing mode is not allowed for this tool!')
