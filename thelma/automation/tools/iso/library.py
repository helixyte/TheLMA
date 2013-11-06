"""
Tools for library screening ISOs.
This module is a hack. It will be replaced completely in the course of the
ISO revision.

We assume the poollib library with 4 ul ISO volume and 1270 nM
ISO concentration.

AAB
"""
from datetime import datetime
from everest.entities.utils import get_root_aggregate
from everest.querying.specifications import cntd
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.tools.iso.optimizer import IsoVolumeSpecificOptimizer
from thelma.automation.tools.iso.prep_utils import IsoControlRackLayout
from thelma.automation.tools.iso.prep_utils import IsoControlRackLayoutConverter
from thelma.automation.tools.iso.prep_utils import IsoControlRackPosition
from thelma.automation.tools.iso.prep_utils import PrepIsoLayout
from thelma.automation.tools.iso.prep_utils import PrepIsoLayoutConverter
from thelma.automation.tools.iso.prep_utils import PrepIsoPosition
from thelma.automation.tools.iso.stocktransfer import IsoControlStockRackVerifier
from thelma.automation.tools.iso.uploadreport import StockTransferReportUploader
from thelma.automation.tools.semiconstants import RACK_SPECS_NAMES
from thelma.automation.tools.semiconstants import RESERVOIR_SPECS_NAMES
from thelma.automation.tools.semiconstants import get_96_rack_shape
from thelma.automation.tools.semiconstants import get_item_status_future
from thelma.automation.tools.semiconstants import get_pipetting_specs_biomek
from thelma.automation.tools.semiconstants import get_positions_for_shape
from thelma.automation.tools.semiconstants import get_rack_position_from_label
from thelma.automation.tools.semiconstants import get_reservoir_spec
from thelma.automation.tools.semiconstants import get_reservoir_specs_standard_96
from thelma.automation.tools.utils.base import FIXED_POSITION_TYPE
from thelma.automation.tools.utils.base import TransferTarget
from thelma.automation.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.utils.base import add_list_map_element
from thelma.automation.tools.utils.base import are_equal_values
from thelma.automation.tools.utils.base import get_trimmed_string
from thelma.automation.tools.utils.iso import IsoLayoutConverter
from thelma.automation.tools.worklists.base import get_dynamic_dead_volume
from thelma.automation.tools.worklists.biomek import ContainerDilutionWorklistWriter
from thelma.automation.tools.worklists.series import ContainerDilutionJob
from thelma.automation.tools.worklists.series import ContainerTransferJob
from thelma.automation.tools.worklists.series import SeriesExecutor
from thelma.automation.tools.worklists.tubehandler import TubeTransferData
from thelma.automation.tools.worklists.tubehandler import XL20WorklistWriter
from thelma.automation.tools.writers import CsvColumnParameters
from thelma.automation.tools.writers import CsvWriter
from thelma.automation.tools.writers import TxtWriter
from thelma.automation.tools.writers import merge_csv_streams
from thelma.automation.tracbase import BaseTracTool
from thelma.interfaces import IJobType
from thelma.interfaces import IPlate
from thelma.interfaces import ITube
from thelma.interfaces import ITubeRack
from thelma.models.iso import ISO_STATUS
from thelma.models.iso import ISO_TYPES
from thelma.models.iso import Iso
from thelma.models.iso import IsoAliquotPlate
from thelma.models.iso import IsoControlStockRack
from thelma.models.iso import IsoPreparationPlate
from thelma.models.iso import IsoRequest
from thelma.models.job import IsoJob
from thelma.models.liquidtransfer import PlannedContainerDilution
from thelma.models.liquidtransfer import PlannedContainerTransfer
from thelma.models.liquidtransfer import PlannedWorklist
from thelma.models.liquidtransfer import WorklistSeries
from thelma.models.user import User
from thelma.models.utils import get_user
from tractor import AttachmentWrapper
from xmlrpclib import Fault
from xmlrpclib import ProtocolError


class LibraryScreeningIsoGenerator(BaseAutomationTool):
    """
    Picks tubes for the controls and assigns library layouts plates
    as ISO aliquot plates.
    All ISOs of a job share the same preparation plate. It predilutes
    the fixed position samples.
    In addition there are only three worklists:

        1. buffer addition to job preparation plate
        2. stock transfer into job preparation plate (attached to the
           the ISO control stock rack)
        3. buffer addition library plates
        4. transfer for fixed pools from preparation plate to layout plates

    ATTENTION: Changing the number of layout for an ISO will change the
        worklist content! Stick with one number of ISOs per job!
    """
    NAME = 'Libary Screening ISO Generator'

    def __init__(self, iso_request, layout_plate_barcodes):
        """
        Constructor:

        :param iso_request: The library screening ISO request for which to
            generate the ISOs.
        :type iso_request: :class:`thelma.models.iso.IsoRequest`

        :param layout_plate_barcodes: The barcodes of the layout plates
            which shall belong to the ISO.
        :type layout_plate_barcodes: A list of layout plates to be used.
        """
        BaseAutomationTool.__init__(self, depending=False)

        self.iso_request = iso_request
        self.layout_plate_barcodes = layout_plate_barcodes

        #: The new ISOs that have been generated.
        self.__iso_job = None

        #: The plates mapped onto the provided barcocdes.
        self.__plates = None
        #: The ISO layout for the ISO request.
        self.__iso_layout = None

        #: The preparation layout.
        self.__prep_layout = None
        #: The ISO target positions for each fixed pool.
        self.__fixed_pools = None
        #: The default stock coentration fro each pool.
        self.__stock_concentrations = None
        #: The candidates returned by the optimizer.
        self.__candidates = None
        #: The chosen candidate for each pool
        self.__picked_candidates = None

    def reset(self):
        BaseAutomationTool.reset(self)
        self.__iso_job = None
        self.__plates = dict()
        self.__iso_layout = None
        self.__prep_layout = None
        self.__fixed_pools = dict()
        self.__stock_concentrations = dict()
        self.__candidates = None
        self.__picked_candidates = dict()

    def run(self):
        self.reset()
        self.add_info('Run ...')

        self.__check_input()
        if not self.has_errors():
            self.__get_racks()
            self.__get_iso_layout()
        if not self.has_errors(): self.__get_fixed_pools()
        if not self.has_errors(): self.__create_preparation_layout()
        if not self.has_errors(): self.__run_optimizer()
        if not self.has_errors(): self.__distribute_candidates()
        if not self.has_errors(): self.__create_worklist_series()
        if not self.has_errors(): self.__create_iso_job()
        if not self.has_errors():
            self.return_value = self.__iso_job
            self.add_info('ISO creation completed.')

    def __check_input(self):
        if self._check_input_class('ISO request', self.iso_request, IsoRequest):
            if not self.iso_request.iso_type == ISO_TYPES.STANDARD:
                msg = 'The ISO request must be a %s type!' \
                       % (ISO_TYPES.STANDARD)
                self.add_error(msg)
        if self._check_input_class('barcode list', self.layout_plate_barcodes,
                                   list):
            for barcode in self.layout_plate_barcodes:
                if not self._check_input_class('barcode', barcode, basestring):
                    break

    def __get_racks(self):
        plate_agg = get_root_aggregate(IPlate)
        missing_plates = []
        for barcode in self.layout_plate_barcodes:
            plate = plate_agg.get_by_slug(barcode)
            if plate is None:
                missing_plates.append(barcode)
            else:
                self.__plates[barcode] = plate

        if len(missing_plates) > 0:
            msg = 'Unable to find plates for the following barcodes: ' \
                  '%s.' % (', '.join(sorted(missing_plates)))
            self.add_error(msg)

    def __get_iso_layout(self):
        converter = IsoLayoutConverter(rack_layout=self.iso_request.iso_layout,
                                       log=self.log)
        self.__iso_layout = converter.get_result()
        if self.__iso_layout is None:
            msg = 'Error when trying to convert ISO layout!'
            self.add_error(msg)

    def __get_fixed_pools(self):
        for ir_pos in self.__iso_layout.working_positions():
            if not ir_pos.is_fixed: continue
            pool = ir_pos.molecule_design_pool
            if not self.__stock_concentrations.has_key(pool.id):
                self.__stock_concentrations[pool.id] = ir_pos.stock_concentration
            add_list_map_element(self.__fixed_pools, pool, ir_pos)

    def __create_preparation_layout(self):
        shape = get_96_rack_shape()
        rs = get_reservoir_specs_standard_96()
        self.__prep_layout = PrepIsoLayout(shape)
        positions = get_positions_for_shape(shape, vertical_sorting=True)
        for pool in sorted(self.__fixed_pools.keys()):
            rack_pos = positions.pop(0)
            iso_positions = self.__fixed_pools[pool]
            vol = get_dynamic_dead_volume(len(iso_positions), rs)
            transfer_targets = []
            for ir_pos in iso_positions:
                vol += (4 * len(self.layout_plate_barcodes)) # ISO volume = 4
                tt = TransferTarget(ir_pos.rack_position, 4)
                transfer_targets.append(tt)
            prep_pos = PrepIsoPosition(rack_position=rack_pos,
                    molecule_design_pool=pool,
                    required_volume=vol,
                    position_type=FIXED_POSITION_TYPE,
                    transfer_targets=transfer_targets,
                    prep_concentration=1270)
            self.__prep_layout.add_position(prep_pos)

    def __run_optimizer(self):
        pool_ids = set([pool.id for pool in self.__fixed_pools.keys()])
        optimizer = IsoVolumeSpecificOptimizer(
                    molecule_design_pools=pool_ids,
                    preparation_layout=self.__prep_layout,
                    log=self.log, excluded_racks=[])
        self.__candidates = optimizer.get_result()
        if self.__candidates is None:
            msg = 'Error when trying to find ISO candidates.'
            self.add_error(msg)

    def __distribute_candidates(self):
        for candidate in self.__candidates:
            pool_id = candidate.pool_id
            exp_conc = self.__stock_concentrations[pool_id]
            if not are_equal_values(exp_conc, candidate.concentration): continue
            if not self.__picked_candidates.has_key(pool_id):
                self.__picked_candidates[pool_id] = candidate

        if not len(self.__picked_candidates) == len(self.__fixed_pools):
            missing_pools = []
            for pool in sorted(self.__fixed_pools.keys()):
                if not self.__picked_candidates.has_key(pool.id):
                    missing_pools.append('%i' % (pool.id))
            msg = 'Unable to find candidates for the following pools: %s.' \
                   % (', '.join(missing_pools))
            self.add_error(msg)
        else:
            for prep_pos in self.__prep_layout.working_positions():
                pool = prep_pos.molecule_design_pool
                candidate = self.__picked_candidates[pool.id]
                prep_pos.stock_tube_barcode = candidate.container_barcode
                prep_pos.stock_rack_barcode = candidate.rack_barcode

    def __create_worklist_series(self):
        label = self.iso_request.experiment_metadata.label
        generator = _WorklistSeriesCreator(label=label,
                    iso_layout=self.__iso_layout,
                    prep_layout=self.__prep_layout, log=self.log)
        worklist_series = generator.get_result()
        if worklist_series is None:
            msg = 'Error when trying to generate worklist series.'
            self.add_error(msg)
        else:
            self.iso_request.worklist_series = worklist_series

    def __create_iso_job(self):
        ps = RACK_SPECS_NAMES.from_name(RACK_SPECS_NAMES.STANDARD_96)
        job_num = len(self.iso_request.iso_jobs) + 1
        job_label = 'ISO_job_%02i' % (job_num)
        prep_plate = ps.create_rack(label='plate_%s' % (job_label),
                                    status=get_item_status_future())

        isos = []
        for plate in self.__plates.values():
            layout_num = int(plate.label.split('-')[1])
            iso_label = 'ISO_%i' % (layout_num)
            iso = Iso(label=iso_label, iso_request=self.iso_request,
                iso_type=ISO_TYPES.STANDARD,
                rack_layout=self.__prep_layout.create_rack_layout())
            isos.append(iso)
            IsoAliquotPlate(iso=iso, plate=plate)
            IsoPreparationPlate(iso=iso, plate=prep_plate)

        agg = get_root_aggregate(IJobType)
        job_type = agg.get_by_id(15)
        if job_type is None:
            msg = 'Job type is None!'
            self.add_error(msg)
        else:
            self.__iso_job = IsoJob(label=job_label, job_type=job_type,
                                    isos=isos, user=get_user('it'))


class _WorklistSeriesCreator(BaseAutomationTool):

    NAME = 'Library Worklist Series Creator'

    BUFFER_DIL_INFO = 'buffer'

    def __init__(self, label, iso_layout, prep_layout, log):
        BaseAutomationTool.__init__(self, log=log)
        self.label = label
        self.iso_layout = iso_layout
        self.prep_layout = prep_layout

        self.__worklist_series = None

    def reset(self):
        BaseAutomationTool.reset(self)
        self.__worklist_series = None

    def run(self):
        self.reset()
        self.__worklist_series = WorklistSeries()
        self.__create_buffer_worklist_job_plate()
        if not self.has_errors(): self.__create_buffer_worklist_layout_plate()
        if not self.has_errors(): self.__create_transfer_worklist()
        if not self.has_errors():
            self.return_value = self.__worklist_series
            self.add_info('Worklist series generation completed.')

    def __create_buffer_worklist_job_plate(self):
        label = '%s_job_plate_buffer' % (self.label)
        planned_transfers = []
        for prep_pos in self.prep_layout.working_positions():
            take_out_vol = prep_pos.get_stock_takeout_volume()
            buffer_vol = prep_pos.required_volume - take_out_vol
            if buffer_vol < 1:
                msg = 'The buffer volume for position %s in the prep layout' \
                      'is smaller than one!' % (prep_pos.rack_position.label)
                self.add_error(msg)
                break
            volume = buffer_vol / VOLUME_CONVERSION_FACTOR
            pcd = PlannedContainerDilution(volume=volume,
                            target_position=prep_pos.rack_position,
                            diluent_info=self.BUFFER_DIL_INFO)
            planned_transfers.append(pcd)
        worklist = PlannedWorklist(label=label,
                                   planned_transfers=planned_transfers)
        self.__worklist_series.add_worklist(0, worklist)

    def __create_buffer_worklist_layout_plate(self):
        label = '%s_layout_plate_buffer' % (self.label)
        planned_transfers = []
        volume = 4 / VOLUME_CONVERSION_FACTOR
        for ir_pos in self.iso_layout.working_positions():
            if not ir_pos.is_mock: continue
            pcd = PlannedContainerDilution(volume=volume,
                        target_position=ir_pos.rack_position,
                        diluent_info=self.BUFFER_DIL_INFO)
            planned_transfers.append(pcd)
        worklist = PlannedWorklist(label=label,
                                   planned_transfers=planned_transfers)
        self.__worklist_series.add_worklist(1, worklist)

    def __create_transfer_worklist(self):
        label = '%s_fixed_transfer' % (self.label)
        planned_transfers = []
        for prep_pos in self.prep_layout.working_positions():
            for tt in prep_pos.transfer_targets:
                volume = tt.transfer_volume / VOLUME_CONVERSION_FACTOR
                target_pos = get_rack_position_from_label(tt.position_label)
                pct = PlannedContainerTransfer(volume=volume,
                        source_position=prep_pos.rack_position,
                        target_position=target_pos)
                planned_transfers.append(pct)
        worklist = PlannedWorklist(label=label,
                                   planned_transfers=planned_transfers)
        self.__worklist_series.add_worklist(2, worklist)


class LibraryScreeningWorklistGenerator(BaseAutomationTool):

    NAME = 'Library Screening Worklist Generator'

    def __init__(self, iso_job, stock_rack_barcode):
        BaseAutomationTool.__init__(self, depending=False)
        self.iso_job = iso_job
        self.stock_rack_barcode = stock_rack_barcode

        self.__stock_rack = None
        self.__prep_layout = None
        self.__file_map = None
        self.__tube_map = None
        self.__tube_transfers = None
        self.__source_rack_locations = None
        self.__control_stock_rack = None
        self.__control_stock_layout = None

    def reset(self):
        BaseAutomationTool.reset(self)
        self.__stock_rack = None
        self.__prep_layout = None
        self.__file_map = dict()
        self.__tube_map = dict()
        self.__tube_transfers = []
        self.__source_rack_locations = dict()
        self.__control_stock_rack = None
        self.__control_stock_layout = None

    def run(self):
        self.reset()
        self.add_info('Start worklist writer ...')

        self.__check_input()
        if not self.has_errors():
            self.__get_stock_rack()
            self.__get_prep_layout()
        if not self.has_errors(): self.__fetch_tube_locations()
        if not self.has_errors(): self.__create_control_stock_rack()
        if not self.has_errors():
            self.__write_xl20_files()
            self.__write_biomek_files()
        if not self.has_errors():
            self.return_value = self.__file_map
            self.add_info('Worklist file generation completed.')

    def __check_input(self):
        self._check_input_class('iso_job', self.iso_job, IsoJob)
        self._check_input_class('stock rack barcode', self.stock_rack_barcode,
                                basestring)

    def __get_stock_rack(self):
        agg = get_root_aggregate(ITubeRack)
        self.__stock_rack = agg.get_by_slug(self.stock_rack_barcode)
        if self.__stock_rack is None:
            msg = 'Unable to find stock rack %s.' % (self.stock_rack_barcode)
            self.add_error(msg)
        elif len(self.__stock_rack.containers) > 0:
            msg = 'There are tubes in the stock rack!'
            self.add_error(msg)

    def __get_prep_layout(self):
        iso = self.iso_job.isos[0]
        converter = PrepIsoLayoutConverter(rack_layout=iso.rack_layout,
                                           log=self.log)
        self.__prep_layout = converter.get_result()
        if self.__prep_layout is None:
            msg = 'Error when trying to convert ISO layout!'
            self.add_error(msg)

    def __fetch_tube_locations(self):
        self.__fetch_tubes_and_create_transfer_data()
        if not self.has_errors():
            source_racks = set()
            for tube in self.__tube_map.values():
                source_rack = tube.location.rack
                source_racks.add(source_rack)
            self.__get_rack_locations(source_racks)

    def __fetch_tubes_and_create_transfer_data(self):
        tube_barcodes = []
        for prep_pos in self.__prep_layout.working_positions():
            tube_barcodes.append(prep_pos.stock_tube_barcode)

        tube_agg = get_root_aggregate(ITube)
        tube_agg.filter = cntd(barcode=tube_barcodes)
        iterator = tube_agg.iterator()
        while True:
            try:
                tube = iterator.next()
            except StopIteration:
                break
            else:
                self.__tube_map[tube.barcode] = tube

        if not len(tube_barcodes) == len(self.__tube_map):
            missing_tubes = []
            for tube_barcode in tube_barcodes:
                if not self.__tube_map.has_key(tube_barcode):
                    missing_tubes.append(tube_barcode)
            msg = 'Could not find tubes for the following tube barcodes: %s.' \
                  % (', '.join(sorted(missing_tubes)))
            self.add_error(msg)
        else:
            for rack_pos, prep_pos in self.__prep_layout.iterpositions():
                tube = self.__tube_map[prep_pos.stock_tube_barcode]
                tube_rack = tube.location.rack
                ttd = TubeTransferData(tube_barcode=tube.barcode,
                            src_rack_barcode=tube_rack.barcode,
                            src_pos=tube.location.position,
                            trg_rack_barcode=self.stock_rack_barcode,
                            trg_pos=rack_pos)
                self.__tube_transfers.append(ttd)

    def __get_rack_locations(self, source_racks):
        """
        Returns a map that stores the rack location for each source rack
        (DB query).
        """
        self.add_debug('Fetch rack locations ...')

        for src_rack in source_racks:
            barcode = src_rack.barcode
            loc = src_rack.location
            if loc is None:
                self.__source_rack_locations[barcode] = 'not found'
                continue
            name = loc.name
            index = loc.index
            if index is None or \
                        (isinstance(index, basestring) and len(index) < 1):
                self.__source_rack_locations[barcode] = name
            else:
                self.__source_rack_locations[barcode] = '%s, index: %s' \
                                                         % (name, index)

    def __create_control_stock_rack(self):
        worklist = self.__create_takeout_worklist()
        layout = self.__create_control_rack_layout()

        self.__control_stock_rack = IsoControlStockRack(iso_job=self.iso_job,
                    rack=self.__stock_rack, planned_worklist=worklist,
                    rack_layout=layout.create_rack_layout())

    def __create_takeout_worklist(self):
        """
        Creates the container transfer for the stock sample worklist (this
        is in theory a 1-to-1 rack transfer, but since the sources are tubes
        that can be moved we use container transfers instead).
        """
        self.add_debug('Create stock take out worklists ...')

        label = '%s_%s_stock_transfer' % (self.stock_rack_barcode,
                                          self.iso_job.label)
        worklist = PlannedWorklist(label=label)
        for rack_pos, prep_pos in self.__prep_layout.iterpositions():
            volume = prep_pos.get_stock_takeout_volume()
            vol = volume / VOLUME_CONVERSION_FACTOR
            pct = PlannedContainerTransfer(volume=vol,
                               source_position=rack_pos,
                               target_position=rack_pos)
            worklist.planned_transfers.append(pct)

        return worklist

    def __create_control_rack_layout(self):
        self.__control_stock_layout = IsoControlRackLayout()
        for rack_pos, prep_pos in self.__prep_layout.iterpositions():
            vol = prep_pos.get_stock_takeout_volume()
            tt = TransferTarget(rack_position=rack_pos,
                                transfer_volume=vol)
            icr_pos = IsoControlRackPosition(rack_position=rack_pos,
                    molecule_design_pool=prep_pos.molecule_design_pool,
                    transfer_targets=[tt])
            self.__control_stock_layout.add_position(icr_pos)
        return self.__control_stock_layout

    def __write_xl20_files(self):
        xl20_writer = XL20WorklistWriter(log=self.log,
                                     tube_transfers=self.__tube_transfers)
        self.__write_file(xl20_writer, '%s_xl20_worklist.csv',
                          'tube handler worklist')

        overview_writer = _LibraryScreeningOverviewWriter(log=self.log,
                    tube_transfers=self.__tube_transfers, iso_job=self.iso_job,
                    source_rack_locations=self.__source_rack_locations)
        self.__write_file(overview_writer, '%s_overview.txt', 'overview')

    def __write_biomek_files(self):

        layout_plates = dict()
        prep_plate = None
        for iso in self.iso_job.isos:
            layout_plate = iso.iso_aliquot_plates[0].plate
            layout_plates[layout_plate.barcode] = layout_plate
            if prep_plate is None:
                prep_plate = iso.iso_preparation_plate.plate

        stock_writer = _LibraryScreeningStockTransferBiomekWriter(log=self.log,
                    prep_plate_barcode=prep_plate.barcode,
                    iso_control_layout=self.__control_stock_layout,
                    stock_rack_barcode=self.stock_rack_barcode)
        self.__write_file(stock_writer, '%s_stock_transfer.csv', 'stock transfer')

        transfer_writer = _LibraryScreeningFinalTransferBiomekWriter(
                    prep_layout=self.__prep_layout, log=self.log,
                    layout_plate_barcodes=layout_plates.keys(),
                    prep_plate_barcode=prep_plate.barcode)
        self.__write_file(transfer_writer, '%s_final_transfer.csv',
                          'final transfer')

        worklist_series = self.iso_job.iso_request.worklist_series
        dil1_wl = None
        dil2_wl = None
        for worklist in worklist_series:
            if worklist.index == 0:
                dil1_wl = worklist
            elif worklist.index == 1:
                dil2_wl = worklist

        rs = get_reservoir_spec(RESERVOIR_SPECS_NAMES.FALCON_MANUAL)
        ps_biomek = get_pipetting_specs_biomek()

        dil_writer_job = ContainerDilutionWorklistWriter(
                    planned_worklist=dil1_wl, target_rack=prep_plate,
                    source_rack_barcode='buffer',
                    reservoir_specs=rs, log=self.log,
                    pipetting_specs=ps_biomek)
        self.__write_file(dil_writer_job, '%s_job_preparation_buffer.csv',
                          'buffer file for the job preparation plate')

        layout_streams = dict()
        for layout_plate_barcode in sorted(layout_plates.keys()):
            plate = layout_plates[layout_plate_barcode]
            writer = ContainerDilutionWorklistWriter(
                        planned_worklist=dil2_wl,
                        target_rack=plate,
                        source_rack_barcode='buffer',
                        reservoir_specs=rs, log=self.log,
                        pipetting_specs=ps_biomek)
            stream = self.__write_file(writer, 'fn', 'buffer dilution ' \
                'worklist for layout plate "%s"' % (layout_plate_barcode),
                save_stream=False)
            num = len(layout_streams)
            layout_streams[num] = stream
        final_stream = merge_csv_streams(layout_streams)
        fn = '%s_layout_plates_buffer.csv' % (self.iso_job.label)
        self.__file_map[fn] = final_stream


    def __write_file(self, writer, name_pattern, msg_name, save_stream=True):
        stream = writer.get_result()
        if stream is None:
            msg = 'Error when trying to write %s file.' % (msg_name)
            self.add_error(msg)
        elif save_stream:
            fn = name_pattern % (self.iso_job.label)
            self.__file_map[fn] = stream
        return stream


class _LibraryScreeningOverviewWriter(TxtWriter):

    NAME = 'Library Screening Overview Writer'

    #: The header text for the general section.
    GENERAL_HEADER = 'General Settings'
    NUMBER_ISOS_LINE = 'Number ISOs: %i'
    #: This line presents the total number of stock tubes used.
    TUBE_NO_LINE = 'Total number of tubes: %i'
    #: The header text for the destination racks section.
    DESTINATION_RACKS_HEADER = 'Destination Rack'
    #: The body for the destination racks section.
    DESTINATION_RACK_BASE_LINE = '%s'

    #: The header for the source racks section.
    SOURCE_RACKS_HEADER = 'Source Racks'
    #: The body for the source racks section.
    SOURCE_RACKS_BASE_LINE = '%s (%s)'

    def __init__(self, log, tube_transfers, source_rack_locations, iso_job):
        TxtWriter.__init__(self, log=log)
        self.tube_transfers = tube_transfers
        self.source_rack_locations = source_rack_locations
        self.iso_job = iso_job

    def _check_input(self):
        self._check_input_class('tube transfers', self.tube_transfers, list)
        self._check_input_class('ISO job', self.iso_job, IsoJob)

    def _write_stream_content(self):
        """
        Writes into the streams.
        """
        self.add_debug('Write stream ...')

        self.__write_main_headline()
        self.__write_general_section()
        self.__write_destination_racks_section()
        self.__write_source_racks_section()

    def __write_main_headline(self):
        """
        Writes the main head line.
        """
        now = datetime.now()
        date_string = now.strftime('%d.%m.%Y')
        time_string = now.strftime('%H:%M')
        main_headline = 'Library Screening Preparation Overview for ' \
                        'job %s / %s / %s' \
                         % (self.iso_job.label, date_string, time_string)
        self._write_headline(main_headline, underline_char='=',
                             preceding_blank_lines=0, trailing_blank_lines=1)

    def __write_general_section(self):
        """
        The general section contains library name, sector index, layout number
        and the number of tubes.
        """
        self._write_headline(self.GENERAL_HEADER, preceding_blank_lines=1)

        general_lines = [self.NUMBER_ISOS_LINE % (len(self.iso_job.isos)),
                         self.TUBE_NO_LINE % (len(self.tube_transfers))]
        self._write_body_lines(general_lines)

    def __write_destination_racks_section(self):
        """
        Writes the destination rack section.
        """
        barcodes = set()
        for ttd in self.tube_transfers:
            barcodes.add(ttd.trg_rack_barcode)

        self._write_headline(self.DESTINATION_RACKS_HEADER)
        lines = []
        for barcode in barcodes:
            lines.append(self.DESTINATION_RACK_BASE_LINE % (barcode))
        self._write_body_lines(lines)

    def __write_source_racks_section(self):
        """
        Writes the source rack section.
        """
        barcodes = set()
        for ttd in self.tube_transfers:
            barcodes.add(ttd.src_rack_barcode)
        sorted_barcodes = sorted(list(barcodes))

        self._write_headline(self.SOURCE_RACKS_HEADER)
        lines = []
        for barcode in sorted_barcodes:
            loc = self.source_rack_locations[barcode]
            if loc is None: loc = 'unknown location'
            lines.append(self.SOURCE_RACKS_BASE_LINE % (barcode, loc))
        self._write_body_lines(lines)


class _LibraryScreeningTransferBiomekWriter(CsvWriter):

    #: The header for the source rack column.
    SOURCE_RACK_HEADER = 'SourcePlateBarcode'
    #: The header for the source position column.
    SOURCE_POS_HEADER = 'SourcePlateWell'
    #: The header for the target rack column.
    TARGET_RACK_HEADER = 'DestinationPlateBarcode'
    #: The header for the target position column.
    TARGET_POS_HEADER = 'DestinationPlateWell'
    #: The header for the transfer volume.
    TRANSFER_VOLUME_COLUMN = 'Volume'

    #: The index for the source rack column.
    SOURCE_RACK_INDEX = 0
    #: The index for the source position column.
    SOURCE_POS_INDEX = 1
    #: The index for the target rack column.
    TARGET_RACK_INDEX = 2
    #: The index for the target position column.
    TARGET_POS_INDEX = 3
    #: The index for the transfer volume.
    TRANSFER_VOLUME_INDEX = 4

    def __init__(self, log, prep_plate_barcode):
        CsvWriter.__init__(self, log=log)
        self.prep_plate_barcode = prep_plate_barcode
        # These are the CsvColumnParameters for the worklists.
        self._source_rack_values = None
        self._source_pos_values = None
        self._target_rack_values = None
        self._target_pos_values = None
        self._volume_values = None

    def reset(self):
        """
        Resets all values escept for input values.
        """
        CsvWriter.reset(self)
        self._source_rack_values = []
        self._source_pos_values = []
        self._target_rack_values = []
        self._target_pos_values = []
        self._volume_values = []

    def _check_input(self):
        self._check_input_class('preparation plate barcode',
                                self.prep_plate_barcode, basestring)

    def _init_column_map_list(self):
        self._add_values()
        self._init_column_maps()

    def _add_values(self):
        raise NotImplementedError('Abstract method.')

    def _init_column_maps(self):
        """
        Initialises the CsvColumnParameters object for the
        :attr:`_column_map_list`.
        """
        source_rack_column = CsvColumnParameters.create_csv_parameter_map(
                    self.SOURCE_RACK_INDEX, self.SOURCE_RACK_HEADER,
                    self._source_rack_values)
        source_pos_column = CsvColumnParameters.create_csv_parameter_map(
                    self.SOURCE_POS_INDEX, self.SOURCE_POS_HEADER,
                    self._source_pos_values)
        target_rack_column = CsvColumnParameters.create_csv_parameter_map(
                    self.TARGET_RACK_INDEX, self.TARGET_RACK_HEADER,
                    self._target_rack_values)
        target_pos_column = CsvColumnParameters.create_csv_parameter_map(
                    self.TARGET_POS_INDEX, self.TARGET_POS_HEADER,
                    self._target_pos_values)
        volume_column = CsvColumnParameters.create_csv_parameter_map(
                    self.TRANSFER_VOLUME_INDEX, self.TRANSFER_VOLUME_COLUMN,
                    self._volume_values)
        self._column_map_list = [source_rack_column, source_pos_column,
                                 target_rack_column, target_pos_column,
                                 volume_column]
        self.add_info('Column generation complete.')


class _LibraryScreeningStockTransferBiomekWriter(
                                        _LibraryScreeningTransferBiomekWriter):

    NAME = 'Library Screening Stock Transfer Worklist Writer'

    def __init__(self, log, prep_plate_barcode, iso_control_layout,
                 stock_rack_barcode):
        _LibraryScreeningTransferBiomekWriter.__init__(self, log,
                           prep_plate_barcode=prep_plate_barcode)
        self.iso_control_layout = iso_control_layout
        self.stock_rack_barcode = stock_rack_barcode

    def _add_values(self):
        for rack_pos, icr_pos in self.iso_control_layout.iterpositions():
            for tt in icr_pos.transfer_targets:
                self._source_rack_values.append(self.stock_rack_barcode)
                self._source_pos_values.append(rack_pos.label)
                self._target_rack_values.append(self.prep_plate_barcode)
                self._target_pos_values.append(rack_pos.label)
                self._volume_values.append(get_trimmed_string(
                                                            tt.transfer_volume))


class _LibraryScreeningFinalTransferBiomekWriter(
                                        _LibraryScreeningTransferBiomekWriter):

    NAME = 'Library Screening Final Transfer Worklist Writer'

    def __init__(self, log, prep_plate_barcode, layout_plate_barcodes,
                 prep_layout):
        _LibraryScreeningTransferBiomekWriter.__init__(self, log, prep_plate_barcode)
        self.layout_plate_barcodes = layout_plate_barcodes
        self.prep_layout = prep_layout

    def _add_values(self):
        for layout_barcode in self.layout_plate_barcodes:
            for prep_pos in self.prep_layout.get_sorted_working_positions():
                for tt in prep_pos.transfer_targets:
                    self._source_rack_values.append(self.prep_plate_barcode)
                    self._source_pos_values.append(prep_pos.rack_position.label)
                    self._target_rack_values.append(layout_barcode)
                    self._target_pos_values.append(tt.position_label)
                    self._volume_values.append(get_trimmed_string(
                                                            tt.transfer_volume))


class LibraryScreeningWorklistUploader(BaseTracTool):
    """
    Uses the worklist files the generated by the
    :class:`LibraryScreeningWorklistGenerator` and sends them to the ticket
    of the pool creation ISO.
    """

    NAME = 'Pool Creation Ticket Worklist Uploader'

    #: File name for the zip file in the Trac.
    FILE_NAME = '%s_robot_worklists.zip'
    #: The description for the attachment.
    DESCRIPTION = 'Tube handler and !BioMek worklists.'

    #: Shall existing replacements with the same name be overwritten?
    REPLACE_EXISTING_ATTACHMENTS = True

    def __init__(self, iso_job, file_map):
        """
        Constructor:

        :param file_map: The streams for the worklists files mapped onto
            file names.
        :type file_map: :class:`dict`
        """
        BaseTracTool.__init__(self, depending=False)

        self.iso_job = iso_job
        #: The streams for the worklists files mapped onto file names.
        self.file_map = file_map

    def send_request(self):
        """
        Sends the request.
        """
        self.reset()
        self.add_info('Prepare request ...')

        self.__check_input()
        if not self.has_errors(): self.__prepare_and_submit()

    def __check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input values ...')

        self._check_input_class('ISO job', self.iso_job, IsoJob)
        if self._check_input_class('file map', self.file_map, dict):
            for fn in self.file_map.keys():
                if not self._check_input_class('file name', fn,
                                               basestring): break

    def __prepare_and_submit(self):
        """
        Submits the request.
        """
        fn = self.FILE_NAME % (self.iso_job.label)
        ticket_id = self.iso_job.iso_request.experiment_metadata.ticket_number

        attachment = AttachmentWrapper(content=self.file_map,
                                       file_name=fn,
                                       description=self.DESCRIPTION)

        try:
            trac_fn = self.tractor_api.add_attachment(ticket_id=ticket_id,
                        attachment=attachment,
                        replace_existing=self.REPLACE_EXISTING_ATTACHMENTS)
        except ProtocolError, err:
            self.add_error(err.errmsg)
        except Fault, fault:
            msg = 'Fault %s: %s' % (fault.faultCode, fault.faultString)
            self.add_error(msg)
        else:
            self.return_value = trac_fn
            msg = 'Robot worklists have been uploaded successfully.'
            self.add_info(msg)
            self.was_successful = True


class LibraryScreeningIsoExecutor(BaseAutomationTool):

    NAME = 'Library Screening ISO Executor'
        #: The barcode for the buffer source reservoir.
    BUFFER_RESERVOIR_BARCODE = 'buffer_reservoir'

    ENTITY_CLS = IsoJob

    def __init__(self, iso_job, user):
        BaseAutomationTool.__init__(self, depending=False)
        self.user = user
        self.iso_job = iso_job

        self.__control_stock_rack = None
        self.__control_layout = None
        self.__prep_plate = None
        self.__aliquot_plates = None
        self.__transfer_jobs = None
        self.__executed_stock_worklists = None

    def reset(self):
        BaseAutomationTool.reset(self)
        self.__control_stock_rack = None
        self.__control_layout = None
        self.__prep_plate = None
        self.__aliquot_plates = dict()
        self.__transfer_jobs = []
        self.__executed_stock_worklists = None

    def get_working_layout(self):
        """
        Returns the working layout (control layout) containing the molecule
        design ID data (for reporting).
        """
        if self.return_value is None: return None
        return self.__control_layout

    def run(self):
        self.reset()
        self.add_info('Start DB execution ...')

        self.__check_input()
        if not self.has_errors(): self.__verify_control_stock_rack()
        if not self.has_errors(): self.__create_transfer_jobs()
        if not self.has_errors(): self.__execute_jobs()
        if not self.has_errors(): self.__update_iso_status()
        if not self.has_errors():
            self.return_value = self.iso_job
            self.add_info('Executor run completed.')

    def __check_input(self):
        self._check_input_class('ISO job', self.iso_job, IsoJob)
        self._check_input_class('user', self.user, User)

    def __verify_control_stock_rack(self):
        layout = self.__get_control_layout()
        verifier = IsoControlStockRackVerifier(log=self.log,
                    stock_rack=self.__control_stock_rack.rack,
                    control_layout=layout)
        res = verifier.get_result()
        if res is None:
            msg = 'The verifier returned None!'
            self.add_error(msg)
        elif not res:
            msg = 'The control stock rack is not compatible!'
            self.add_error(msg)

    def __get_control_layout(self):
        self.__control_stock_rack = self.iso_job.iso_control_stock_rack
        converter = IsoControlRackLayoutConverter(log=self.log,
                            rack_layout=self.__control_stock_rack.rack_layout)
        self.__control_layout = converter.get_result()
        if self.__control_layout is None:
            msg = 'Error when trying to convert ISO control rack layout!'
            self.add_error(msg)
        return self.__control_layout

    def __create_transfer_jobs(self):
        for iso in self.iso_job:
            if self.__prep_plate is None:
                self.__prep_plate = iso.iso_preparation_plate.plate
            aliquot_plate = iso.iso_aliquot_plates[0].plate
            self.__aliquot_plates[aliquot_plate.barcode] = aliquot_plate

        stock_worklist = self.__control_stock_rack.planned_worklist
        ps_biomek = get_pipetting_specs_biomek()
        stock_job = ContainerTransferJob(index=0,
                        planned_worklist=stock_worklist,
                        target_rack=self.__prep_plate,
                        source_rack=self.__control_stock_rack.rack,
                        pipetting_specs=ps_biomek)
        self.__transfer_jobs.append(stock_job)

        worklist_series = self.iso_job.iso_request.worklist_series
        job_buffer_wl = None
        layout_buffer_wl = None
        transfer_wl = None
        for worklist in worklist_series:
            if worklist.index == 0:
                job_buffer_wl = worklist
            elif worklist.index == 1:
                layout_buffer_wl = worklist
            else:
                transfer_wl = worklist

        rs = get_reservoir_spec(RESERVOIR_SPECS_NAMES.FALCON_MANUAL)
        buffer_job_job = ContainerDilutionJob(index=1,
                            planned_worklist=job_buffer_wl,
                            target_rack=self.__prep_plate,
                            reservoir_specs=rs,
                            pipetting_specs=ps_biomek,
                            source_rack_barcode=self.BUFFER_RESERVOIR_BARCODE)
        self.__transfer_jobs.append(buffer_job_job)

        for layout_plate in self.__aliquot_plates.values():
            new_index = len(self.__transfer_jobs)
            buffer_job = ContainerDilutionJob(index=new_index,
                            planned_worklist=layout_buffer_wl,
                            target_rack=layout_plate,
                            reservoir_specs=rs,
                            pipetting_specs=ps_biomek,
                            source_rack_barcode=self.BUFFER_RESERVOIR_BARCODE)
            self.__transfer_jobs.append(buffer_job)
            new_index = len(self.__transfer_jobs)
            transfer_job = ContainerTransferJob(index=new_index,
                            planned_worklist=transfer_wl,
                            target_rack=layout_plate,
                            source_rack=self.__prep_plate,
                            pipetting_specs=ps_biomek)
            self.__transfer_jobs.append(transfer_job)

    def __execute_jobs(self):
        executor = SeriesExecutor(transfer_jobs=self.__transfer_jobs,
                                  user=self.user, log=self.log)
        executed_worklists = executor.get_result()
        if executed_worklists is None:
            msg = 'Series executor failed!'
            self.add_error(msg)
        else:
            self.__executed_stock_worklists = [executed_worklists[0]]

    def get_executed_stock_worklists(self):
        return self._get_additional_value(self.__executed_stock_worklists)

    def __update_iso_status(self):
        for iso in self.iso_job:
            iso.status = ISO_STATUS.DONE


class LibraryScreeningStockTransferReportUploader(StockTransferReportUploader):

    EXECUTOR_CLS = LibraryScreeningIsoExecutor
