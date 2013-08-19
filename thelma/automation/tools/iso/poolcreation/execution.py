"""
Tools involved the execution of pool stock sample creation worklists.

AAB
"""
from everest.entities.utils import get_root_aggregate
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.tools.iso.poolcreation.base \
    import StockSampleCreationLayout
from thelma.automation.tools.iso.poolcreation.base \
    import StockSampleCreationLayoutConverter
from thelma.automation.tools.iso.poolcreation.generation \
    import StockSampleCreationWorklistGenerator
from thelma.automation.tools.iso.poolcreation.writer \
    import StockSampleCreationWorklistWriter
from thelma.automation.tools.semiconstants import PIPETTING_SPECS_NAMES
from thelma.automation.tools.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.tools.semiconstants import RESERVOIR_SPECS_NAMES
from thelma.automation.tools.semiconstants import get_96_rack_shape
from thelma.automation.tools.semiconstants import get_positions_for_shape
from thelma.automation.tools.semiconstants import get_reservoir_spec
from thelma.automation.tools.worklists.series import ContainerDilutionJob
from thelma.automation.tools.worklists.series import ContainerTransferJob
from thelma.automation.tools.worklists.series import SeriesExecutor
from thelma.interfaces import ITubeRack
from thelma.models.iso import ISO_STATUS
from thelma.models.iso import StockSampleCreationIso
from thelma.models.liquidtransfer import ExecutedWorklist
from thelma.models.rack import TubeRack
from thelma.models.user import User

__docformat__ = 'reStructuredText en'

__all__ = ['StockSampleCreationExecutor',
           'StockSampleCreationStockRackVerifier',
           ]


class StockSampleCreationExecutor(BaseAutomationTool):
    """
    Executes the worklist file for a pool stock sample creation ISO.
    This comprises both buffer dilution and stock transfer.

    **Return Value:** the updated ISO
    """
    NAME = 'Stock Sample Creation Executor'

    #: The barcode for the buffer source reservoir.
    BUFFER_RESERVOIR_BARCODE = 'buffer_reservoir'

    def __init__(self, iso, user,
                 logging_level=None, add_default_handlers=None):
        """
        Constructor:

        :param iso: The stock sample creation ISO for which to execute the
            worklists.
        :type iso: :class:`thelma.models.iso.StockSampleCreationIso`

        :param user: The user conducting the execution.
        :type user: :class:`thelma.models.user.User`

        :param logging_level: the desired minimum log level
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: *None*

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *None*
        """
        BaseAutomationTool.__init__(self, logging_level=logging_level,
                                    add_default_handlers=add_default_handlers,
                                    depending=False)

        #: The stock sample creation ISO for which to execute the worklists.
        self.iso = iso
        #: The user conducting the execution.
        self.user = user

        #: The stock sample creation layout for this ISO.
        self.__ssc_layout = None

        #: The ISO stock rack for the ISO (that is the rack that will
        #: contain the new pool stock samples).
        self.__iso_stock_rack = None
        #: The single design racks (the tube destination racks from the writer)
        #: should contain single design stock tubes in defined positions. Their
        #: barcodes are stored in the sample stock rack worklist.
        self.__single_design_racks = None


        #: The executed stock transfer worklists (mapped onto job indices;
        #: refers to transfer from single molecule design to pool stock rack).
        #: Required for reporting.
        self.__exec_stock_transfer_wls = None

        #: The transfer jobs for the series executor.
        self.__transfer_jobs = None
        #: The indices for the rack transfer jobs mapped onto the worklist
        #: they belong to.
        self.__rack_transfer_indices = None
        #: Positions without library positions (i.e. without transfer).
        self.__ignore_positions = None

    def reset(self):
        BaseAutomationTool.reset(self)
        self.__ssc_layout = None
        self.__iso_stock_rack = None
        self.__single_design_racks = []
        self.__exec_stock_transfer_wls = dict()
        self.__transfer_jobs = dict()
        self.__rack_transfer_indices = dict()
        self.__ignore_positions = []

    def run(self):
        """
        Executes the pool creation worklists.
        """
        self.reset()
        self.add_info('Start execution ...')

        self.__check_input()
        if not self.has_errors(): self.__get_layout()
        if not self.has_errors(): self.__get_racks()
        if not self.has_errors(): self.__verify_single_md_stock_racks()
        if not self.has_errors(): self.__create_buffer_transfer_job()
        if not self.has_errors(): self.__create_stock_transfer_jobs()
        if not self.has_errors(): self.__execute_transfer_jobs()
        if not self.has_errors(): self.__create_stock_samples()
        if not self.has_errors():
            self.iso.status = ISO_STATUS.DONE
            self.return_value = self.iso
            self.add_info('Transfer execution completed.')

    def get_executed_stock_worklists(self):
        """
        Returns the executed worklists that *deal with the stock transfer*
        (for stock transfer reporting).
        """
        return self._get_additional_value(self.__exec_stock_transfer_wls)

    def get_working_layout(self):
        """
        Returns the working layout containing the molecule design pool ID data
        (for reporting).
        """
        return self._get_additional_value(self.__ssc_layout)

    @property
    def entity(self):
        """
        Returns the ISO. Required for reporting.
        """
        return self.iso

    def __check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input values ...')

        if self._check_input_class('ISO', self.iso, StockSampleCreationIso):
            status = self.iso.status
            if not status == ISO_STATUS.QUEUED:
                msg = 'Unexpected ISO status: "%s"' % (status)
                self.add_error(msg)

        self._check_input_class('user', self.user, User)

    def __get_layout(self):
        """
        Fetches the stock sample layout and sorts its positions into quadrants.
        """
        self.add_debug('Fetch stock sample layout ...')

        converter = StockSampleCreationLayoutConverter(log=self.log,
                                               rack_layout=self.iso.rack_layout)
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

        writer_cls = StockSampleCreationWorklistWriter
        tube_rack_agg = get_root_aggregate(ITubeRack)
        not_found = []

        # There should only be one ISO stock rack
        isrs = self.iso.iso_stock_racks
        if not len(isrs) == 1:
            msg = 'There is an unexpected number of ISO stock racks ' \
                  'attached to this ISO (%i). There should be exactly one! ' \
                  % (len(isrs))
            self.add_error(msg)
            return None
        else:
            self.__iso_stock_rack = isrs[0]

        label = self.__iso_stock_rack.planned_worklist.label
        starting_index = len(writer_cls.SAMPLE_STOCK_WORKLIST_LABEL)
        barcode_str = label[starting_index:]
        barcodes = barcode_str.split(writer_cls.\
                                         SAMPLE_STOCK_WORKLIST_DELIMITER)
        for barcode in barcodes:
            rack = tube_rack_agg.get_by_slug(barcode)
            if rack is None:
                not_found.append(barcode)
            else:
                self.__single_design_racks.append(rack)

        if len(not_found) > 0:
            msg = 'The following single molecule design source stock racks ' \
                  'have not been found in the DB: %s!' \
                  % (', '.join(sorted(not_found)))
            self.add_error(msg)

    def __verify_single_md_stock_racks(self):
        """
        Makes sure we have all the molecule designs present and in the right
        positions and no additional tubes in the single molecule design
        stock racks.
        """
        verifier = StockSampleCreationStockRackVerifier(log=self.log,
                                stock_sample_creation_layout=self.__ssc_layout,
                                stock_racks=self.__single_design_racks)
        compatible = verifier.get_result()

        if compatible is None:
            msg = 'Error in the verifier!'
            self.add_error(msg)
        elif not compatible:
            msg = 'The stock racks with the single molecule designs are not ' \
                  'compatible to the expected layout!'
            self.add_error(msg)

    def __create_buffer_transfer_job(self):
        """
        Creates the transfer job for the buffer worklist.
        """
        self.add_debug('Create buffer transfer jobs ...')

        worklist_series = self.iso.iso_request.worklist_series
        buffer_worklist = worklist_series.get_worklist_for_index(
                  StockSampleCreationWorklistGenerator.BUFFER_WORKLIST_INDEX)

        rs_quarter = get_reservoir_spec(RESERVOIR_SPECS_NAMES.QUARTER_MODULAR)
        job_index = len(self.__transfer_jobs)
        cdj = ContainerDilutionJob(index=job_index,
                             planned_worklist=buffer_worklist,
                             target_rack=self.__iso_stock_rack.rack,
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

        for single_rack in self.__single_design_racks:
            job_index = len(self.__transfer_jobs)
            ctj = ContainerTransferJob(index=job_index,
                    planned_worklist=self.__iso_stock_rack.planned_worklist,
                    target_rack=self.__iso_stock_rack.rack,
                    source_rack=single_rack,
                    pipetting_specs=PIPETTING_SPECS_NAMES.BIOMEK)
            ctj.min_transfer_volume = 1
            self.__transfer_jobs[job_index] = ctj
            self.__exec_stock_transfer_wls[job_index] = None

    def __execute_transfer_jobs(self):
        """
        Executes the transfer jobs. The executed worklists for container
        dilutions and transfer are created by the tool, the executed worklists
        for rack transfers have to be created here.
        """
        self.add_debug('Execute transfer job ...')

        executor = SeriesExecutor(transfer_jobs=self.__transfer_jobs.values(),
                                  user=self.user, log=self.log)
        executed_items = executor.get_result()

        if executed_items is None:
            msg = 'Error during serial transfer execution.'
            self.add_error(msg)
        else:
            self.__create_executed_worklists_for_rack_transfers(executed_items)
            for job_index in self.__exec_stock_transfer_wls.keys():
                executed_wl = executed_items[job_index]
                self.__exec_stock_transfer_wls[job_index] = executed_wl

    def __create_executed_worklists_for_rack_transfers(self, executed_items):
        """
        Creates the executed worklists for the rack transfer jobs.
        """
        self.add_debug('Create executed rack transfer worklists ...')

        for worklist, indices in self.__rack_transfer_indices.iteritems():
            executed_worklist = ExecutedWorklist(planned_worklist=worklist)
            for i in indices:
                ert = executed_items[i]
                executed_worklist.executed_transfers.append(ert)

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

        for tube in self.__iso_stock_rack.rack.containers:
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
                                '-'.join(sorted([str(ei for ei in exp_mds)])),
                                '-'.join(sorted([str(ei for ei in found_mds)])))
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


class StockSampleCreationStockRackVerifier(BaseAutomationTool):
    """
    This tools verifies whether the single molecule design stock racks of
    a pool stock sample creation ISO (after rearrangment of stock tubes)
    are compliant to the layout of the passed ISO.

    **Return Value:** boolean
    """
    NAME = 'Pool Creation Stock Rack Verifier'

    def __init__(self, stock_sample_creation_layout, stock_racks, log):
        """
        Constructor:

        :param stock_sample_creation_layout: Contains the pool, tube and
            molecule design data.
        :type stock_sample_creation_layout: :class:`StockSampleCreationLayout`

        :param stock_racks: The stock racks for the ISO after tube handling.
        :type stock_racks: :class:`list` of :class:`thelma.models.rack.TubeRack`

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        BaseAutomationTool.__init__(self, log=log)

        #: Contains the pool, tube and molecule design data.
        self.ssc_layout = stock_sample_creation_layout
        #: The stock racks after tube handling.
        self.stock_racks = stock_racks

        #: The rack shape of a stock rack (96 wells).
        self.stock_rack_shape = None

    def reset(self):
        BaseAutomationTool.reset(self)
        self.stock_rack_shape = get_96_rack_shape()

    def run(self):
        self.reset()
        self.add_info('Start ISO sample stock rack verification ...')

        self.__check_input()

        if not self.has_errors():
            self.return_value = True
            self.return_value = self.__check_racks()

        if not self.has_errors():
            self.add_info('Verification completed.')

    def __check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input values ...')

        self._check_input_class('stock sample creation layout', self.ssc_layout,
                                StockSampleCreationLayout)
        if self._check_input_class('stock rack list', self.stock_racks, list):
            for rack in self.stock_racks:
                if not self._check_input_class('stock rack', rack,
                                               TubeRack): break

    def __check_racks(self):
        """
        Compares the molecule designs in the stock rack (after tube handling -
        that is the tube destination racks from the writer) with the data
        from the stock sample creation layout.
        """
        exp_pools = self.__get_expected_pools()
        exp_mds = dict()
        for md_pool in exp_pools.values():
            for md in md_pool:
                if not exp_mds.has_key(md):
                    exp_mds[md] = 1
                else:
                    exp_mds[md] += 1

        additional_mds = []
        missing_mds = []
        mismatching_mds = []

        for rack in self.stock_racks:
            checked_positions = set()
            for tube in rack.containers:
                rack_pos = tube.location.position
                checked_positions.add(rack_pos)
                sample = tube.sample
                if sample is None or len(sample.sample_molecules) < 1:
                    if exp_pools.has_key(rack_pos):
                        exp_pool = exp_pools[rack_pos]
                        md_ids = '-'.join([str(md.id) for md in exp_pool])
                        info = '%s in %s (exp: %s)' % (rack_pos.label,
                                                       rack.barcode, md_ids)
                        missing_mds.append(info)
                        for md in exp_pool:
                            exp_mds[md] -= 1
                            if exp_mds[md] == 0:
                                del exp_mds[md]
                    continue
                mds = []
                for sm in sample.sample_molecules:
                    mds.append(sm.molecule.molecule_design)
                found_md_str = '-'.join([str(md.id) for md in mds])
                if not exp_pools.has_key(rack_pos):
                    info = '%s in %s (found: %s)' % (rack_pos.label,
                                                     rack.barcode, found_md_str)
                    additional_mds.append(info)
                    continue
                exp_pool = exp_pools[rack_pos]
                for md in mds:
                    if not md in exp_pool.molecule_designs:
                        exp_id_str = '-'.join([str(md.id) for md in exp_pool])
                        info = '%s in %s (expected: %s, found: %s)' % (
                                rack_pos.label, rack.barcode, exp_id_str,
                                found_md_str)
                        mismatching_mds.append(info)
                    else:
                        exp_mds[md] -= 1
                        if exp_mds[md] == 0:
                            del exp_mds[md]

            if not len(checked_positions) == len(exp_pools):
                for rack_pos, exp_pool in exp_pools.iteritems():
                    if rack_pos in checked_positions: continue
                    md_ids = '-'.join([str(md.id) for md in exp_pool])
                    info = '%s in %s (exp: %s)' % (rack_pos.label,
                           rack.barcode, md_ids)
                    missing_mds.append(info)

        for md in exp_mds.keys():
            info = '%i' % (md.id)
            missing_mds.append(info)

        is_valid = True
        if len(missing_mds) > 0:
            msg = 'There are some molecule designs missing in the prepared ' \
                  'single design stock racks: %s.' % (', '.join(sorted(
                                            [str(ei) for ei in missing_mds])))
            self.add_error(msg)
            is_valid = False
        if len(additional_mds) > 0:
            msg = 'The single design stock racks contain molecule designs ' \
                  'that should not be there: %s.' \
                  % (', '.join(sorted(additional_mds)))
            self.add_error(msg)
            is_valid = False
        if len(mismatching_mds) > 0:
            msg = 'Some molecule designs in the single design stock racks do ' \
                  'not match the expected ones: %s.' \
                   % (', '.join(sorted(mismatching_mds)))
            self.add_error(msg)

        return is_valid

    def __get_expected_pools(self):
        """
        Returns the expected pool for each rack position (positions for which
        there is no pool expected are not recorded).
        """
        pool_map = dict()
        for rack_pos, ssc_pos in self.ssc_layout.iterpositions():
            pool_map[rack_pos] = ssc_pos.pool
        return pool_map
