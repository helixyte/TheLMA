"""
These tools deal with the processing of lab ISOs. This comprises both
the transfers from stock and the actual series processing.

AAB
"""
from thelma.automation.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.semiconstants import RESERVOIR_SPECS_NAMES
from thelma.automation.semiconstants import get_reservoir_spec
from thelma.automation.tools.iso.base import IsoRackContainer
from thelma.automation.tools.iso.base import StockRackVerifier
from thelma.automation.tools.iso.base import StockTransferWriterExecutor
from thelma.automation.tools.iso.lab.base import FinalLabIsoLayoutConverter
from thelma.automation.tools.iso.lab.base import FinalLabIsoPosition
from thelma.automation.tools.iso.lab.base import LABELS
from thelma.automation.tools.iso.lab.base import LAB_ISO_ORDERS
from thelma.automation.tools.iso.lab.base import LabIsoLayout
from thelma.automation.tools.iso.lab.base import LabIsoPrepLayoutConverter
from thelma.automation.tools.iso.lab.base import create_instructions_writer
from thelma.automation.tools.worklists.series import RackSampleTransferJob
from thelma.automation.tools.worklists.series import SampleDilutionJob
from thelma.automation.tools.worklists.series import SampleTransferJob
from thelma.automation.tools.writers import merge_csv_streams
from thelma.automation.utils.base import add_list_map_element
from thelma.automation.utils.layouts import BaseRackVerifier
from thelma.models.iso import ISO_STATUS
from thelma.models.iso import IsoAliquotPlate
from thelma.models.iso import IsoJobPreparationPlate
from thelma.models.iso import IsoPlate
from thelma.models.iso import IsoPreparationPlate
from thelma.models.iso import LabIso
from thelma.models.job import IsoJob
from thelma.models.library import LibraryPlate
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.rack import Plate
from thelma.models.status import ITEM_STATUSES


__docformat__ = 'reStructuredText en'

__all__ = ['_LabIsoWriterExecutorTool',
           'WriterExecutorIsoJob',
           'WriterExecutorLabIso',
           'LabIsoPlateVerifier']


class _LabIsoWriterExecutorTool(StockTransferWriterExecutor):
    """
    A base class for tool dealing with the lab ISO Job and lab ISO processing
    (DB execution or generation of robot worklist files).

    **Return Value:** a zip stream for for printing mode or the entity
        for execution mode
    """

    #: The entity class supported by this tool.
    ENTITY_CLS = None

    #: The barcode for the (temporary) annealing buffer plate or reservoir.
    BUFFER_PLATE_BARCODE = 'buffer'
    #: The name of the :class:`ReservoirSpecs` for the buffer dilutions.
    DILUTION_RESERVOIR_SPECS = RESERVOIR_SPECS_NAMES.QUARTER_MODULAR

    #: The file name for the instructions contains the entity label.
    FILE_NAME_INSTRUCTIONS = '%s_instructions.txt'
    #: The file name for the CyBio steps file contains the entity label.
    FILE_NAME_CYBIO = '%s_cybio_steps.txt'
    #: The file name for the buffer dilution contains the entity label.
    FILE_NAME_DILUTIONS = '%s_buffer.csv'
    #: The file name for the transfers contains the entity label and the
    #: worklist label without ticket number.
    FILE_NAME_TRANSFER = '%s_%s.csv'

    def __init__(self, entity, mode, user=None, **kw):
        """
        Constructor:

        :param entity: The ISO job or ISO to process.
        :type entity: :class:`thelma.models.job.IsoJob` or
            :class:`thelma.models.iso.LabIso`.

        :param mode: :attr:`MODE_EXECUTE` or :attr:`MODE_PRINT_WORKLISTS`
        :type mode: str

        :param user: The user who conducts the DB update (required for
            execution mode).
        :type user: :class:`thelma.models.user.User`
        :default user: *None*
        """
        StockTransferWriterExecutor.__init__(self, entity=entity, mode=mode,
                                             user=user, **kw)

        #: The lab ISO requests the entity belongs to.
        self._iso_request = None
        #: The final layout for each ISO in this entity mapped onto ISOs.
        self.__final_layouts = None
        #: see :class:`LAB_ISO_ORDERS`.
        self._processing_order = None
        #: The expected :class:`ISO_STATUS.
        self._expected_iso_status = None

        #: The involved racks (as list of :class:`IsoRackContainer`
        #: objects) mapped onto rack markers. Final plates are mapped onto the
        #: :attr:`LABELS.ROLE_FINAL` marker.
        self.__rack_containers = None
        #: The final plates (as list of :class:`IsoRackContainer` objects)
        #: mapped onto ISOs.
        self.__final_plates = None
        #: The layout for each plate mapped onto plate label.
        self.__plate_layouts = None
        #: The ignored positions for each plate.
        self.__ignored_positions = None
        #: The stock rack for this entity mapped onto labels.
        self._stock_racks = None
        #: The stock rack layouts mapped onto stock rack barcodes
        #: (for reporting).
        self.__stock_rack_layouts = None

        #: The job indices for the buffer dilutions.
        self.__buffer_dilution_indices = None
        #: The merged stream for the buffer dilutions (printer mode only).
        self.__buffer_stream = None

        #: The source :class:`ReservoirSpecs` for the dilution jobs.
        self.__dilution_rs = get_reservoir_spec(self.DILUTION_RESERVOIR_SPECS)

    def reset(self):
        StockTransferWriterExecutor.reset(self)
        self._iso_request = None
        self.__final_layouts = dict()
        self._processing_order = None
        self._expected_iso_status = None
        self.__rack_containers = dict()
        self.__final_plates = dict()
        self.__plate_layouts = dict()
        self.__ignored_positions = dict()
        self._stock_racks = dict()
        self.__stock_rack_layouts = dict()
        self.__buffer_dilution_indices = set()
        self.__buffer_stream = None

    def get_stock_rack_data(self):
        """
        Returns the stock rack layouts mapped onto rack barcodes.
        """
        return self._get_additional_value(self.__stock_rack_layouts)

    def _create_transfer_jobs(self):
        if not self.has_errors(): self.__fetch_final_layouts()
        if not self.has_errors(): self.__check_iso_status()
        if not self.has_errors():
            self._get_plates()
            self._get_stock_racks()
            self._verify_stock_racks()
        if not self.has_errors(): self.__generate_jobs()
        if not self.has_errors() and self.mode == self.MODE_EXECUTE:
            self._update_iso_status()

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        StockTransferWriterExecutor._check_input(self)
        if not self.has_errors():
            self._iso_request = self.entity.iso_request

    def __fetch_final_layouts(self):
        """
        Gets the final ISO plate layout for each ISO.s
        """
        self.add_debug('Get final ISO layouts ...')

        isos = self._get_isos()
        for iso in isos:
            converter = FinalLabIsoLayoutConverter(log=self.log,
                                                   rack_layout=iso.rack_layout)
            layout = converter.get_result()
            if layout is None:
                msg = 'Error when trying to convert final layout for ISO ' \
                      '"%s".' % (iso.label)
                self.add_error(msg)
            else:
                self.__final_layouts[iso] = layout

    def _get_isos(self):
        """
        Returns a list of ISOs belonging to this entity. If the entity ISO
        itself, the list will contain only one element.
        """
        raise NotImplementedError('Abstract method.')

    def __check_iso_status(self):
        """
        Checks the status of the involved ISOs.
        The rack status are checked later.
        """
        self.add_debug('Check ISO status ...')

        self._processing_order = LAB_ISO_ORDERS.get_order(self.entity)
        self._get_expected_iso_status()
        if not self._expected_iso_status is None:
            invalid_status = []
            for iso in self.__final_layouts.keys():
                if not iso.status == self._expected_iso_status:
                    info = '%s (expected: %s, found: %s)' % (iso.label,
                            self._expected_iso_status.replace('_', ' '),
                            iso.status.replace('_', ' '))
                    invalid_status.append(info)

            if len(invalid_status) > 0:
                msg = 'Unexpected ISO status: %s!' \
                      % (', '.join(sorted(invalid_status)))
                self.add_error(msg)


    def _get_expected_iso_status(self):
        """
        The expected status the :attr:`_isos` depends on the type of ISO
        (Is there a job to be processed? Do we have to process it first?)
        """
        raise NotImplementedError('Abstract method.')

    def _get_plates(self):
        """
        Verifies and stores the plates for all ISOs.
        The plates will be mapped onto rack markers (except for final plates
        which will be are mapped onto the :attr:`LABELS.ROLE_FINAL` marker).
        Most plates are shared by ISO and ISO job.
        """
        self.add_debug('Get plates ...')

        for iso, final_layout in self.__final_layouts.iteritems():
            for ipp in iso.iso_preparation_plates:
                self._store_and_verify_plate(ipp)
            for fp in iso.final_plates:
                self._store_and_verify_plate(fp, final_layout)
                self.__plate_layouts[fp.rack.label] = final_layout

    def _store_and_verify_plate(self, iso_plate, layout=None, verify=True):
        """
        Convenience method verifying and storing the plate as rack container
        in the :attr:`_rack_containers` map (mapped onto the rack marker).
        If the expected ISO status is queued all plates must be empty,
        otherwise we need a :class:`LabIsoPlateVerifier`.
        """
        plate = iso_plate.rack
        rack_name = '%s (%s)' % (plate.barcode, plate.label)

        if self._expected_iso_status == ISO_STATUS.QUEUED and verify:
            sample_positions = []
            for well in plate.containers:
                if well.sample is not None:
                    sample_positions.append(well.location.position.label)
            if len(sample_positions) > 0:
                msg = 'Plate %s should be empty but there are samples in ' \
                      'the following positions: %s.' \
                       % (plate.label, self._get_joined_str(sample_positions))
                self.add_error(msg)
                return None
            if not isinstance(iso_plate, (IsoAliquotPlate, LibraryPlate)):
                converter = LabIsoPrepLayoutConverter(log=self.log,
                                  rack_layout=iso_plate.rack_layout)
                layout = converter.get_result()
                if layout is None:
                    msg = 'Error when trying to convert layout of plate "%s"!' \
                          % (plate.label)
                    self.add_error(msg)
                    return None
                else:
                    self.__plate_layouts[plate.label] = layout

        elif verify:
            verifier = LabIsoPlateVerifier(log=self.log, lab_iso_layout=layout,
                                           lab_iso_plate=iso_plate,
                                           for_job=(self.ENTITY_CLS == IsoJob))
            compatible = verifier.get_result()
            if compatible is None:
                msg = 'Error when trying to verify plate %s!' % (rack_name)
                self.add_error(msg)
                return None
            elif not compatible:
                msg = 'Rack %s does not match the expected layout!' \
                       % (rack_name)
                self.add_error(msg)
                return None
            elif layout is None:
                self.__plate_layouts[plate.label] = \
                                                verifier.get_expected_layout()

        iso = None
        if self._processing_order == LAB_ISO_ORDERS.NO_ISO and \
                                            isinstance(iso_plate, LibraryPlate):
            rack_marker = LABELS.ROLE_FINAL
            iso = iso_plate.lab_iso
        else:
            values = LABELS.parse_rack_label(plate.label)
            rack_marker = values[LABELS.MARKER_RACK_MARKER]
        rack_container = IsoRackContainer(rack=plate, rack_marker=rack_marker)

        if rack_container.role == LABELS.ROLE_FINAL:
            rack_marker = LABELS.ROLE_FINAL
            if iso is None: iso = iso_plate.iso
            add_list_map_element(self.__final_plates, iso, rack_container)
        add_list_map_element(self.__rack_containers, rack_marker,
                             rack_container)

    def _get_stock_racks(self):
        """
        Stock racks are stored in the :attr:`_stock_racks` map. Stock racks
        are specific for the entity.
        """
        raise NotImplementedError('Abstract method.')

    def _verify_stock_racks(self):
        """
        Checks the samples in the stock racks (pools and samples).
        """
        self.add_debug('Verify stock racks ..')

        for stock_rack in self._stock_racks.values():
            verifier = StockRackVerifier(log=self.log, stock_rack=stock_rack)
            compatible = verifier.get_result()
            rack_name = '%s (%s)' % (stock_rack.rack.barcode, stock_rack.label)
            if compatible is None:
                msg = 'Error when trying to verify stock rack %s.' % (rack_name)
                self.add_error(msg)
            elif not compatible:
                msg = 'Stock rack %s does not match the expected layout.' \
                       % (rack_name)
                self.add_error(msg)
            else:
                layout = verifier.get_expected_layout()
                barcode = stock_rack.rack.barcode
                self.__stock_rack_layouts[barcode] = layout

        if not self.has_errors():
            self._check_for_previous_execution()

    def __generate_jobs(self):
        """
        The worklists for the stock transfers are generated first (in order
        of stock racks), then the transfer worklist for the processing series
        (stored at the ISO request) are generated (if there is one).
        All worklists of a series are handled in the series order.
        """
        self.add_debug('Generate transfer jobs ...')

        #: Stock transfer worklists.
        for sr_label in sorted(self._stock_racks.keys()):
            stock_rack = self._stock_racks[sr_label]
            self.__create_stock_transfer_jobs(stock_rack)

        #: Processing series worklists.
        worklists = self._get_sorted_processing_worklists()
        if len(worklists) > 0:
            self.__find_ignored_positions()
            for worklist in worklists:
                markers = self.__get_worklist_rack_markers(worklist)
                if markers is None: continue
                self.__create_processing_worklist_jobs(worklist, *markers)

    def __create_stock_transfer_jobs(self, stock_rack):
        """
        Convenience method creating a :class:`SampleTransferJob` for a transfer
        from stock rack to a plate.
        """
        stock_worklists = stock_rack.worklist_series.get_sorted_worklists()
        for worklist in stock_worklists:
            values = LABELS.parse_worklist_label(worklist.label)
            src_marker = values[LABELS.MARKER_WORKLIST_SOURCE]
            if not src_marker in stock_rack.label:
                msg = 'Inconsistent stock rack for worklist "%s" '  \
                      '(stock rack: %s).' % (worklist.label, stock_rack.label)
                self.add_error(msg)
            trg_marker = values[LABELS.MARKER_WORKLIST_TARGET]
            for rack_container in self.__rack_containers[trg_marker]:
                self.__create_and_store_transfer_job(worklist=worklist,
                                        target_plate=rack_container.rack,
                                        source_rack=stock_rack.rack)

    def _get_sorted_processing_worklists(self):
        """
        The worklists are sorted by index. They are fetched from the entity.
        Buffer worklists for final and ISO preparation plates are always
        processed by the first entity, however.
        """
        raise NotImplementedError('Abstract method.')

    def __find_ignored_positions(self):
        """
        The ignored positions are missing floating positions in the layouts.
        """
        for plate_label, layout in self.__plate_layouts.iteritems():
            ignored_positions = []
            for plate_pos in layout.working_positions():
                if plate_pos.is_missing_floating:
                    ignored_positions.append(plate_pos.rack_position)
            self.__ignored_positions[plate_label] = ignored_positions

    def __get_worklist_rack_markers(self, worklist):
        """
        Parses the worklist label (see :func:`LABELS.parse_worklist_label`).
        Returns *None* if the worklist is not accepted.

        This can be the case for worklists with unknown rack markers (in this
        case there are preparation plates involved that do not belong to the
        entity) or if the worklist might be part of both entity processings.
        The second is the case for some final plate worklists.
        """
        values = LABELS.parse_worklist_label(worklist.label)
        trg_marker = values[LABELS.MARKER_WORKLIST_TARGET]
        if not self.__rack_containers.has_key(trg_marker): return None
        src_marker = None
        if values.has_key(LABELS.MARKER_WORKLIST_SOURCE):
            src_marker = values[LABELS.MARKER_WORKLIST_SOURCE]
            if not self.__rack_containers.has_key(src_marker): return None

        if worklist.transfer_type == TRANSFER_TYPES.SAMPLE_DILUTION:
            if trg_marker == LABELS.ROLE_FINAL and \
                            self._expected_iso_status == ISO_STATUS.IN_PROGRESS:
                for rack_container in self.__rack_containers[trg_marker]:
                    if rack_container.rack.status.name == ITEM_STATUSES.MANAGED:
                        return None

        return trg_marker, src_marker

    def __create_processing_worklist_jobs(self, worklist, trg_marker,
                                          src_marker):
        """
        Convenience method creating a liquid transfer job for the ISO request
        worklist series - worklists with unknown rack markers (e.g. job plates
        for ISO processing) are omitted.
        """
        target_plates = self.__rack_containers[trg_marker]
        if worklist.transfer_type == TRANSFER_TYPES.SAMPLE_DILUTION:
            for rack_container in target_plates:
                self.__create_and_store_transfer_job(worklist=worklist,
                                             target_plate=rack_container.rack)

        else:
            if src_marker == trg_marker:
                for rack_container in target_plates:
                    target_plate = rack_container.rack
                    self.__create_transfer_worklist_jobs(target_plate,
                                                         target_plate, worklist)
            elif not len(self.__rack_containers[src_marker]) == 1:
                msg = 'There is more than 1 plates for preparation marker ' \
                      '"%s": %s!' % (src_marker, self._get_joined_str(
                       self.__rack_containers[src_marker], is_strs=False))
                self.add_error(msg)
            else:
                src_plate = self.__rack_containers[src_marker][0].rack
                for rack_container in target_plates:
                    self.__create_transfer_worklist_jobs(src_plate,
                                                 rack_container.rack, worklist)

    def __create_transfer_worklist_jobs(self, source_rack, target_plate,
                                        worklist):
        """
        Helper function creating the transfer job for a transfer worklist
        (type RACK_SAMPLE_TRANSFER or SAMPLE_TRANSFER).
        """
        if worklist.transfer_type == TRANSFER_TYPES.RACK_SAMPLE_TRANSFER:
            for prst in worklist:
                self.__create_and_store_transfer_job(worklist=worklist,
                        target_plate=target_plate, source_rack=source_rack,
                        planned_rack_sample_transfer=prst)
        else:
            self.__create_and_store_transfer_job(worklist, target_plate,
                                                 source_rack)

    def __create_and_store_transfer_job(self, worklist, target_plate,
                         source_rack=None, planned_rack_sample_transfer=None):
        """
        Helper function creating a new transfer job. The class is derived
        from the worklist. The job index is the length of the current
        transfer job map.
        """
        job_index = len(self._transfer_jobs)
        if worklist.transfer_type == TRANSFER_TYPES.SAMPLE_DILUTION:
            ign_positions = self.__ignored_positions[target_plate.label]
            transfer_job = SampleDilutionJob(index=job_index,
                            planned_worklist=worklist,
                            target_rack=target_plate,
                            reservoir_specs=self.__dilution_rs,
                            source_rack_barcode=self.BUFFER_PLATE_BARCODE,
                            ignored_positions=ign_positions)
            self.__buffer_dilution_indices.add(job_index)
        elif worklist.transfer_type == TRANSFER_TYPES.SAMPLE_TRANSFER:
            ign_positions = None
            if self.__ignored_positions.has_key(source_rack.label):
                ign_positions = self.__ignored_positions[source_rack.label]
            transfer_job = SampleTransferJob(index=job_index,
                            planned_worklist=worklist,
                            target_rack=target_plate,
                            source_rack=source_rack,
                            ignored_positions=ign_positions)
        else:
            transfer_job = RackSampleTransferJob(index=job_index,
                    planned_rack_sample_transfer=planned_rack_sample_transfer,
                    target_rack=target_plate, source_rack=source_rack)
            self._rack_transfer_worklists[job_index] = worklist
        self._transfer_jobs[job_index] = transfer_job

    def _check_for_previous_execution(self):
        """
        There must not be executed worklist for any planned worklists belonging
        to a stock rack.
        """
        worklists = set()
        for stock_rack in self._stock_racks.values():
            worklist_series = stock_rack.worklist_series
            for worklist in worklist_series:
                if len(worklist.executed_worklists) > 0:
                    worklists.add(worklist.label)

        if len(worklists) > 0:
            msg = 'The following stock transfers have already been executed ' \
                  'before: %s!' % (self._get_joined_str(worklists))
            self.add_error(msg)

    def _extract_executed_stock_worklists(self, executed_worklists):
        """
        Stock transfer worklists can be recognised by label (they contain
        the :attr:`LABELS.ROLE_STOCK` marker.
        """
        for ew in executed_worklists:
            pw = ew.planned_worklist
            if LABELS.ROLE_STOCK in pw.label:
                self._executed_stock_worklists.append(ew)

    def _update_iso_status(self):
        """
        Assigns a new status to the ISOs. Only called in execution mode.
        """
        self.add_debug('Update ISO status ...')

        new_status = self._get_new_iso_status()
        for iso in self.__final_layouts.keys():
            iso.status = new_status

        if new_status == ISO_STATUS.DONE:
            experiment_metadata = self._iso_request.experiment_metadata
            if not experiment_metadata.label == self._iso_request.label:
                self.__rename_final_plates(experiment_metadata)

    def _get_new_iso_status(self):
        """
        Only called in execution mode. Returns the new status of the
        involved ISOs.
        """
        raise NotImplementedError('Abstract method.')

    def __rename_final_plates(self, experiment_metadata):
        """
        Replaces the labels of the final plates by a new label derived from
        the plate set labels specified by the scientist. For ISO request
        that cannot contain more than one final plate (not regarding copies)
        the final plate label is equal to the ISO request label. Otherwise
        ISO number and aliquot number (in case of several plates per ISO),
        are added.
        Assumes the ISOs to be completed and the label of experiment metadata
        and ISO request to be different.
        """
        if len(self.__final_plates) == 1 and \
                              experiment_metadata.experiment_metadata_type_id \
                              in EXPERIMENT_SCENARIOS.ONE_PLATE_TYPES:
            for final_plates in self.__final_plates.values():
                final_plates[0].rack.label = self._iso_request.label

        else:
            for iso, final_plates in self.__final_plates.iteritems():
                if len(final_plates) == 1:
                    new_label = LABELS.create_final_plate_label(iso)
                    final_plates[0].rack.label = new_label
                else:
                    for container in final_plates:
                        values = LABELS.parse_rack_marker(container.rack_marker)
                        plate_num = None
                        if values.has_key(LABELS.MARKER_RACK_NUM):
                            plate_num = values[LABELS.MARKER_RACK_NUM]
                        new_label = LABELS.create_final_plate_label(iso,
                                                                    plate_num)
                        container.rack.label = new_label

    def _merge_streams(self, stream_map):
        """
        All buffer streams are merged too.
        """
        dilution_streams = dict()
        for job_index in self.__buffer_dilution_indices:
            dilution_streams[job_index] = stream_map[job_index]
            del stream_map[job_index]

        if len(dilution_streams) > 0:
            self.__buffer_stream = merge_csv_streams(dilution_streams)
        return StockTransferWriterExecutor._merge_streams(self, stream_map)

    def _get_file_map(self, merged_stream_map, rack_transfer_stream):
        """
        The buffer worklists and not part of the merged stream map. The
        instructions file is added, too.
        """
        instructions_stream = self.__create_instructions_file()
        if instructions_stream is None: return None

        file_map = dict()
        instructions_fn = self.FILE_NAME_INSTRUCTIONS % (self.entity.label)
        file_map[instructions_fn] = instructions_stream

        if rack_transfer_stream is not None:
            rst_fn = self.FILE_NAME_CYBIO % (self.entity.label)
            file_map[rst_fn] = rack_transfer_stream

        if self.__buffer_stream is not None:
            buffer_fn = self.FILE_NAME_DILUTIONS % (self.entity.label)
            file_map[buffer_fn] = self.__buffer_stream

        for worklist_label, merged_stream in merged_stream_map.iteritems():
            label_tokens = worklist_label.split(LABELS.SEPARATING_CHAR)
            adj_label = LABELS.SEPARATING_CHAR.join(label_tokens[1:])
            fn = self.FILE_NAME_TRANSFER % (self.entity.label, adj_label)
            file_map[fn] = merged_stream

        return file_map

    def __create_instructions_file(self):
        """
        Creates the instruction file for the :attr:`entity` (printer
        :attr:`mode` only).
        """
        rack_containers = []
        for containers in self.__rack_containers.values():
            rack_containers.extend(containers)
        for sr_label, stock_rack in self._stock_racks.iteritems():
            values = LABELS.parse_rack_label(sr_label)
            rack_marker = values[LABELS.MARKER_RACK_MARKER]
            container = IsoRackContainer(rack=stock_rack.rack,
                        rack_marker=rack_marker, label=sr_label,
                        role=LABELS.ROLE_STOCK)
            rack_containers.append(container)

        kw = dict(log=self.log, entity=self.entity,
                  iso_request=self._iso_request,
                  rack_containers=rack_containers)
        writer = create_instructions_writer(**kw)
        instructions_stream = writer.get_result()

        if instructions_stream is None:
            msg = 'Error when trying to generate instructions file.'
            self.add_error(msg)
            return None
        return instructions_stream


class WriterExecutorIsoJob(_LabIsoWriterExecutorTool):
    """
    A base class for tool dealing with the lab ISO Job processing
    (DB execution or generation of robot worklist files).

    **Return Value:** a zip stream for for printing mode or the updated ISO job
        for execution mode
    """
    NAME = 'Lab ISO Writer/Executor'
    ENTITY_CLS = IsoJob

    def __init__(self, iso_job, mode, user=None, **kw):
        """
        Constructor:

        :param iso_job: The ISO job to process.
        :type iso_job: :class:`thelma.models.job.IsoJob`.

        :param mode: :attr:`MODE_EXECUTE` or :attr:`MODE_PRINT_WORKLISTS`
        :type mode: str

        :param user: The user who conducts the DB update (required for
            execution mode).
        :type user: :class:`thelma.models.user.User`
        :default user: *None*
        """
        _LabIsoWriterExecutorTool.__init__(self, entity=iso_job,
                                             user=user, mode=mode, **kw)

    def _get_isos(self):
        return self.entity.isos

    def _get_expected_iso_status(self):
        if self._processing_order == LAB_ISO_ORDERS.NO_JOB:
            msg = 'There are no samples added via the ISO job, thus there ' \
                  'is no job processing required!'
            self.add_error(msg)
        elif self._processing_order == LAB_ISO_ORDERS.ISO_FIRST:
            self._expected_iso_status = ISO_STATUS.IN_PROGRESS
        else:
            self._expected_iso_status = ISO_STATUS.QUEUED

    def _get_plates(self):
        """
        We have to add job plates.
        """
        _LabIsoWriterExecutorTool._get_plates(self)
        for jpp in self.entity.iso_job_preparation_plates:
            self._store_and_verify_plate(jpp)

    def _get_stock_racks(self):
        for stock_rack in self.entity.iso_job_stock_racks:
            self._stock_racks[stock_rack.label] = stock_rack

    def _get_sorted_processing_worklists(self):
        """
        If the job is processed first me must fetch potential buffer worklists
        from the ISO request worklists as well.
        """
        return LAB_ISO_ORDERS.get_sorted_worklists_for_job(self.entity,
                                                self._processing_order)

    def _get_new_iso_status(self):
        """
        The new status is :attr:`ISO_STATUS.IN_PROGRESS` for jobs that
        are succeeded by an ISO preparation. Library and ISO-first-preparations
        are completed after job prepraration.
        """
        if self._processing_order == LAB_ISO_ORDERS.JOB_FIRST:
            return ISO_STATUS.IN_PROGRESS
        else: # NO_ISO or ISO_FIRST
            return ISO_STATUS.DONE


class WriterExecutorLabIso(_LabIsoWriterExecutorTool):
    """
    A base class for tool dealing with the lab ISO processing
    (DB execution or generation of robot worklist files).

    **Return Value:** a zip stream for for printing mode or the updated ISO
        for execution mode
    """
    NAME = 'Lab ISO Job Writer/Executor'
    ENTITY_CLS = LabIso

    def __init__(self, iso, mode, user=None, **kw):
        """
        Constructor:

        :param iso: The lab ISO to process.
        :type iso: :class:`thelma.models.iso.LabIso`.

        :param mode: :attr:`MODE_EXECUTE` or :attr:`MODE_PRINT_WORKLISTS`
        :type mode: str

        :param user: The user who conducts the DB update (required for
            execution mode).
        :type user: :class:`thelma.models.user.User`
        :default user: *None*
        """
        _LabIsoWriterExecutorTool.__init__(self, entity=iso, user=user,
                                             mode=mode, **kw)

    def _get_isos(self):
        """
        There is only one ISO: the entity.
        """
        return [self.entity]

    def _get_expected_iso_status(self):
        if self._processing_order == LAB_ISO_ORDERS.NO_ISO:
            msg = 'All samples for this ISO are handled by the ISO job, ' \
                  'thus, there is no specific ISO handling required!'
            self.add_error(msg)
        elif self._processing_order == LAB_ISO_ORDERS.JOB_FIRST:
            self._expected_iso_status = ISO_STATUS.IN_PROGRESS
        else:
            self._expected_iso_status = ISO_STATUS.QUEUED

    def _get_stock_racks(self):
        stock_racks = self.entity.iso_stock_racks \
                      + self.entity.iso_sector_stock_racks
        for stock_rack in stock_racks:
            self._stock_racks[stock_rack.label] = stock_rack

    def _get_sorted_processing_worklists(self):
        """
        If the job is processed first me must remove potential buffer worklists
        from the ISO request worklists because these have already been handled
        before by the job.
        """
        return LAB_ISO_ORDERS.get_sorted_worklists_for_iso(self.entity,
                                                self._processing_order)

    def _get_new_iso_status(self):
        """
        The new status is :attr:`ISO_STATUS.IN_PROGRESS` for ISOs that
        are succeeded by a job preparation. For all other cases, the ISOs
        are completed after execution.
        """
        if self._processing_order == LAB_ISO_ORDERS.ISO_FIRST:
            return ISO_STATUS.IN_PROGRESS
        else: # NO_JOB or JOB_FIRST
            return ISO_STATUS.DONE


class LabIsoPlateVerifier(BaseRackVerifier):
    """
    Compares lab ISO plate positions with ISO plate layouts.
    Assumes the given plate to be managed already (i.e. the ISO must be in
    progress).
    """
    NAME = 'Lab ISO Plate Verifier'

    _RACK_CLS = Plate
    _LAYOUT_CLS = LabIsoLayout

    def __init__(self, log, lab_iso_plate, for_job, lab_iso_layout=None):
        """
        Constructor:

        :param log: The log the write in.
        :type log: :class:`thelma.ThelmaLog`

        :param lab_iso_plate: The lab ISO plate to be checked.
        :type lab_iso_plate: :class:`IsoPlate` or
            :class:`IsoJobPreparationPlate`

        :param for_job: Do we check the job processing (*True*) or the ISO?
        :type for_job: :class:`bool`

        :param lab_iso_layout: The layout containing the molecule design
            data. Must not be None for :class:`IsoAliquotPlate` or
            :class:`LibraryPlate` objects.
        :type lab_iso_layout: :class:`LabIsoLayout`
        """
        BaseRackVerifier.__init__(self, log=log,
                                  reference_layout=lab_iso_layout)

        #: The lab ISO plate to be checked.
        self.lab_iso_plate = lab_iso_plate
        #: Do we check the job processing (*True*) or the ISO (*False*)?
        self.for_job = for_job

        #: In aliquot and (for controls positions) preparation plates,
        #: we can ignore positions that are derived from another position
        #: at the same plate because the intraplate transfers might be
        #: part of the processing of the second entity.
        self.__ignore_positions = None
        #: This is kind of a hack. We cannot make safe statement about ignored
        #: positions, for this reason, the comparison for ignored positions
        #: is temporarily disabled (until the next position).
        self.__disable_comparison = None

    def reset(self):
        BaseRackVerifier.reset(self)
        self.__ignore_positions = None
        self.__disable_comparison = False

    def _check_input(self):
        BaseRackVerifier._check_input(self)
        if not isinstance(self.lab_iso_plate, (IsoPlate, LibraryPlate,
                                               IsoJobPreparationPlate)):
            msg = 'The lab ISO plate must be an %s, %s or an %s ' \
                  '(obtained: %s).' % (IsoPlate.__name__, LibraryPlate.__name__,
                    IsoJobPreparationPlate.__name__,
                    self.lab_iso_plate.__class__.__name__)
            self.add_error(msg)
        self._check_input_class('"for job" flag', self.for_job, bool)

    def _set_rack(self):
        self._rack = self.lab_iso_plate.rack

    def _fetch_expected_layout(self):
        """
        The layouts for preparation plates can be derived from the plate entity.
        Final plate layouts must be delivered because they are stored at the
        ISO.
        """
        if isinstance(self.lab_iso_plate, (IsoAliquotPlate, LibraryPlate)):
            msg = 'The reference layout for a final ISO plate must not ' \
                  'be None!'
            self.add_error(msg)
        elif isinstance(self.lab_iso_plate, (IsoPreparationPlate,
                                             IsoJobPreparationPlate)):
            converter = LabIsoPrepLayoutConverter(log=self.log,
                                    rack_layout=self.lab_iso_plate.rack_layout)
            self._expected_layout = converter.get_result()
            if self._expected_layout is None:
                msg = 'Error when trying to convert preparation plate layout!'
                self.add_error(msg)
        else:
            msg = 'Unexpected ISO plate type: %s.' \
                   % (self.lab_iso_plate.__class__.__name__)
            self.add_error(msg)

    def _get_expected_pool(self, plate_pos):
        """
        If this method is entered for the first time, we look for ignored
        positions (whose expected state we do not know). If a position is
        an ignored position the comparison is disabled until we hit the next
        position.
        """
        if self.__ignore_positions is None:
            self.__find_ignored_positions()

        if plate_pos.rack_position in self.__ignore_positions:
            self.__disable_comparison = True
            return None

        if self.__accept_position(plate_pos):
            return plate_pos.molecule_design_pool
        else:
            return None

    def __accept_position(self, plate_pos):
        """
        Some positions are always ignored, no matter whether they have transfer
        targets or not.
        For final plate positions we must only regard positions for either
        jobs or ISOs (mismatching booleans are compared because this
        processing is assumed to happen first).
        """
        if isinstance(plate_pos, FinalLabIsoPosition):
            if (plate_pos.from_job == self.for_job):
                return False
        elif self.for_job and plate_pos.is_fixed:
            return False
        elif not self.for_job and plate_pos.is_floating:
            return False
        return True

    def __find_ignored_positions(self):
        """
        In aliquot and (for controls positions) preparation plates,
        we can ignore positions that are derived from another position
        at the same plate because the intraplate transfers might be
        part of the processing of the second entity.
        Remember the plate is always in an intermediate state.
        """
        self.__ignore_positions = set()
        is_final_plate = isinstance(self.lab_iso_plate, IsoAliquotPlate)
        for rack_pos, plate_pos in self._expected_layout.iterpositions():
            if not self.__accept_position(plate_pos): continue
            if not self.for_job and not is_final_plate and \
                                        not plate_pos.is_fixed:
                # we prepare in preparation plate for an ISO and
                # floatings are always part of the ISO processing
                continue
            all_tts = plate_pos.transfer_targets
            if not is_final_plate:
                all_tts.extend(plate_pos.external_targets)
            if len(all_tts) < 1:
                self.__ignore_positions.add(rack_pos)

    def _are_matching_molecule_designs(self, rack_mds, exp_mds):
        """
        If comparison is disabled (because the current position is ignored)
        we always return *True*.
        In any case, comparison is enabled again.
        """
        if self.__disable_comparison:
            self.__disable_comparison = False
            return True
        return BaseRackVerifier._are_matching_molecule_designs(self, rack_mds,
                                                               exp_mds)
