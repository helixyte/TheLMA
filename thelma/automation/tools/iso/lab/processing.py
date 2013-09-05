"""
These tools deal with the processing of lab ISOs. This comprises both
the transfers from stock and the actual series processing.

AAB
"""
from thelma.automation.tools.iso.base import StockRackLayoutConverter
from thelma.automation.tools.iso.lab.base import FinalLabIsoLayoutConverter
from thelma.automation.tools.iso.lab.base import FinalLabIsoPosition
from thelma.automation.tools.iso.lab.base import LABELS
from thelma.automation.tools.iso.lab.base import LabIsoLayout
from thelma.automation.tools.iso.lab.base import LabIsoPrepLayoutConverter
from thelma.automation.tools.iso.lab.base import LabIsoRackContainer
from thelma.automation.tools.iso.lab.base import create_instructions_writer
from thelma.automation.tools.semiconstants import RESERVOIR_SPECS_NAMES
from thelma.automation.tools.semiconstants import get_reservoir_spec
from thelma.automation.tools.utils.base import add_list_map_element
from thelma.automation.tools.utils.verifier import BaseRackVerifier
from thelma.automation.tools.worklists.series import RackSampleTransferJob
from thelma.automation.tools.worklists.series import SampleDilutionJob
from thelma.automation.tools.worklists.series import SampleTransferJob
from thelma.automation.tools.worklists.series import SerialWriterExecutorTool
from thelma.automation.tools.writers import merge_csv_streams
from thelma.models.iso import ISO_STATUS
from thelma.models.iso import IsoAliquotPlate
from thelma.models.iso import IsoJobPreparationPlate
from thelma.models.iso import IsoPlate
from thelma.models.iso import IsoPreparationPlate
from thelma.models.iso import StockRack
from thelma.models.job import IsoJob
from thelma.models.library import LibraryPlate
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.rack import Plate
from thelma.models.rack import TubeRack
from thelma.models.status import ITEM_STATUSES


__docformat__ = 'reStructuredText en'

__all__ = ['_LabIsoWriterExecutorTool',
           'LabIsoJobWriterExecutor',
           'LabIsoWriterExecutor',
           'LabIsoPlateVerifier',
           'StockRackVerifier']


class _LabIsoWriterExecutorTool(SerialWriterExecutorTool):
    """
    A base class for tool dealing with the lab ISO Job and lab ISO processing
    (DB execution or generation of robot worklist files).

    **Return Value:** Depending on the subclass.
    """

    #: The entity class supported by this tool.
    _ENTITY_CLS = None

    #: The barcode for the (temporary) annealing buffer plate or reservoir.
    BUFFER_PLATE_BARCODE = 'buffer_reservoir'
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
        SerialWriterExecutorTool.__init__(self, mode=mode, user=user, **kw)

        #: The ISO job or ISO to process.
        self.entity = entity
        #: The lab ISO requests the entity belongs to.
        self._iso_request = None
        #: The final layout for each ISO in this entity.
        self._final_layouts = None
        #: The expected :class:`ISO_STATUS.
        self._expected_iso_status = None

        #: Shall warnings be recorded?
        self.__record_warnings = None

        #: The involved racks (as list of :class:`LabIsoRackContainer`
        #: objects) mapped onto rack markers. Final plates are mapped onto the
        #: :attr:`LABELS.ROLE_FINAL` marker.
        self._rack_containers = None
        #: The layout for each plate mapped onto plate label.
        self._plate_layouts = None
        #: The ignored positions for each plate.
        self._ignored_positions = None
        #: The stock rack for this entity mapped onto labels.
        self._stock_racks = None

        #: The job indices for the buffer dilutions.
        self.__buffer_dilution_indices = None
        #: The merged stream for the buffer dilutions (printer mode only).
        self.__buffer_stream = None

        #: The source :class:`ReservoirSpecs` for the dilution jobs.
        self.__dilution_rs = get_reservoir_spec(self.DILUTION_RESERVOIR_SPECS)

    def reset(self):
        SerialWriterExecutorTool.reset(self)
        self._iso_request = None
        self._final_layouts = None
        self._expected_iso_status = None
        self._rack_containers = dict()
        self._plate_layouts = dict()
        self._ignored_positions = dict()
        self._stock_racks = dict()
        self.__buffer_dilution_indices = set()
        self.__buffer_stream = None

    def _create_transfer_jobs(self):
        if not self.has_errors(): self.__fetch_final_layouts()
        if not self.has_errors(): self.__check_iso_status()
        if not self.has_errors():
            self._get_plates()
            self._get_stock_racks()
            self.__verify_stock_racks()
        if not self.has_errors(): self.__generate_jobs()

    def _check_input(self):
        """
        Checks the initialisation values ...
        """
        SerialWriterExecutorTool._check_input(self)
        if self._check_input_class('entity', self.entity, self._ENTITY_CLS):
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
                self._final_layouts[iso] = layout

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

        self._get_expected_iso_status()
        if not self._expected_iso_status is None:
            invalid_status = []
            for iso in self._final_layouts.keys():
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

        for iso, final_layout in self._final_layouts.iteritems():
            for ipp in iso.iso_preparation_plates:
                self._store_and_verify_plate(ipp.label)
            for fp in iso.final_plates:
                self._store_and_verify_plate(fp, final_layout)
                self._plate_layouts[fp.rack.label] = final_layout

    def _store_and_verify_plate(self, iso_plate, layout=None):
        """
        Convenience method verifying and storing the plate as rack container
        in the :attr:`_rack_containers` map (mapped onto the rack marker).
        If the expected ISO status is queued all plates must be empty,
        otherwise we need a :class:`LabIsoPlateVerifier`.
        """
        plate = iso_plate.rack
        rack_name = '%s (%s)' % (plate.barcode, plate.label)

        if self._expected_iso_status == ISO_STATUS.QUEUED:
            sample_positions = []
            for well in plate.containers:
                if well.sample is not None:
                    sample_positions.append(well.location.position.label)
            if len(sample_positions) > 0:
                msg = 'Plate %s should be empty but there are samples in ' \
                      'the following positions: %s.' \
                       % (', '.join(sample_positions))
                self.add_error(msg)
                compatible = False
            else:
                compatible = True

        else:
            verifier = LabIsoPlateVerifier(log=self.log, lab_iso_layout=layout,
                                           lab_iso_plate=iso_plate,
                                           for_job=(self._ENTITY_CLS == IsoJob))
            compatible = verifier.get_result()
            if compatible is None:
                msg = 'Error when trying to verify plate %s!' % (rack_name)
                self.add_error(msg)
            elif not compatible:
                msg = 'Rack %s does not match the expected layout!' \
                       % (rack_name)
                self.add_error(msg)
            elif layout is None:
                self._plate_layouts[plate.label] = \
                                                verifier.get_expected_layout()

        if compatible:
            rack_container = LabIsoRackContainer(rack=plate)
            rack_marker = rack_container.rack_marker
            if rack_container.role == LABELS.ROLE_FINAL:
                rack_marker = LABELS.ROLE_FINAL
            add_list_map_element(self._rack_containers, rack_marker,
                                 rack_container)

    def _get_stock_racks(self):
        """
        Stock racks are stored in the :attr:`_stock_racks` map. Stock racks
        are specific for the entity.
        """
        raise NotImplementedError('Abstract method.')

    def __verify_stock_racks(self):
        """
        Checks the samples in the stock racks (pools and samples).
        """
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

    def __generate_jobs(self):
        """
        The worklists for the stock transfers are generated first (in order
        of stock racks), then the transfer worklist for the processing series
        (stored at the ISO request) are generated (if there is one).
        All worklists of a series are handled in the series order.
        """
        #: Stock transfer worklists.
        for sr_label in sorted(self._stock_racks.keys()):
            stock_rack = self._stock_racks[sr_label]
            self.__create_stock_transfer_job(stock_rack)

        #: Processing series worklists.
        worklist_series = self._iso_request.worklist_series
        if worklist_series is not None:
            self.__find_ignored_positions()
            series_worklists = worklist_series.get_sorted_worklists()
            for worklist in series_worklists:
                markers = self.__get_worklist_rack_markers(worklist)
                if markers is None: continue
                self.__create_processing_worklist_jobs(worklist, *markers)

    def __create_stock_transfer_job(self, stock_rack):
        """
        Convenience method creating a :class:`SampleTransferJob` for a transfer
        from stock rack to a plate.
        """
        stock_worklists = stock_rack.worklist_series.get_sorted_worklists()
        for worklist in stock_worklists:
            values = LABELS.parse_rack_label(stock_rack.label)
            src_marker = values[LABELS.MARKER_WORKLIST_SOURCE]
            if not src_marker in stock_rack.label:
                msg = 'Inconsistent stock rack for worklist "%s" '  \
                      '(stock rack: %s).' % (worklist.label, stock_rack.label)
                self.add_error(msg)
            trg_marker = values[LABELS.MARKER_WORKLIST_TARGET]
            for rack_container in self._rack_containers[trg_marker]:
                self.__create_and_store_transfer_job(worklist=worklist,
                                        target_plate=rack_container.rack,
                                        source_rack=stock_rack.rack)

    def __find_ignored_positions(self):
        """
        The ignored positions are missing floating positions in the layouts.
        """
        for plate_label, layout in self._plate_layouts.iteritems():
            ignored_positions = []
            for plate_pos in layout.get_working_positions():
                if plate_pos.is_missing_floating:
                    ignored_positions.append(plate_pos.rack_position)
            self._ignored_positions[plate_label] = ignored_positions

    def __get_worklist_rack_markers(self, worklist):
        """
        Parses the worklist label (see :func:`LABELS.parse_worklist_label`).
        Returns *None* if the worklist is not accepted.

        This can be the case for worklists with unknown rack markers (in this
        case there are preparation plates involved that do not belong to the
        entity) or if the worklist might be part of both entity processings.
        The second is the case for some final plate worklists.
        Buffer worklists need only be registered if the final plates are not
        managed yet. Intraplate transfers in the final plate need to be done
        at the very end of the processing.
        """
        values = LABELS.parse_worklist_label(worklist.label)
        trg_marker = values[LABELS.MARKER_WORKLIST_TARGET]
        if not self._rack_containers.has_key(trg_marker): return None
        src_marker = None
        if values.has_key(LABELS.MARKER_WORKLIST_SOURCE):
            src_marker = values[LABELS.MARKER_WORKLIST_SOURCE]
            if not self._rack_containers.has_key(src_marker): return None

        if worklist.transfer_type == TRANSFER_TYPES.SAMPLE_DILUTION:
            if trg_marker == LABELS.ROLE_FINAL and \
                            self._expected_iso_status == ISO_STATUS.IN_PROGRESS:
                for rack_container in self._rack_containers[trg_marker]:
                    if rack_container.rack.status.name == ITEM_STATUSES.MANAGED:
                        return None
        elif src_marker == LABELS.ROLE_FINAL and \
                        trg_marker == LABELS.ROLE_FINAL and \
                        not self._expected_iso_status == ISO_STATUS.IN_PROGRESS:
            if not self._accept_final_intraplate_transfer(): return None

        return trg_marker, src_marker

    def _accept_final_intraplate_transfer(self):
        """
        Intraplate transfers in the final plate need to be done at the very
        end of the processing. This method assumes the
        :attr:`_expected_iso_status` to be :attr:`ISO_STATUS.QUEUED`.
        """
        raise NotImplementedError('Abstract error.')

    def __create_processing_worklist_jobs(self, worklist, trg_marker,
                                          src_marker):
        """
        Convenience method creating a liquid transfer job for the ISO request
        worklist series - worklists with unknown rack markers (job plates
        for ISO processing and vice versa) are omitted.
        """
        target_plates = self._rack_containers[trg_marker]
        if worklist.transfer_type == TRANSFER_TYPES.SAMPLE_DILUTION:
            for target_plate in target_plates:
                self.__create_and_store_transfer_job(worklist=worklist,
                                                     target_plate=target_plate)

        else:
            if src_marker == trg_marker:
                for rack_container in target_plates:
                    target_plate = rack_container.rack
                    self.__create_transfer_worklist_jobs(target_plate,
                                                         target_plate, worklist)
            elif not len(self._rack_containers[src_marker]) == 1:
                msg = 'There are more than 1 plates for preparation marker ' \
                      '"%s": %s!' % (src_marker,
                                     self._rack_containers[src_marker])
                self.add_error(msg)
            else:
                src_plate = self._rack_containers[src_marker][0].rack
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
            ign_positions = self._ignored_positions[target_plate.label]
            transfer_job = SampleDilutionJob(index=job_index,
                            planned_worklist=worklist,
                            target_rack=target_plate,
                            reservoir_specs=self.__dilution_rs,
                            pipetting_specs=worklist.pipetting_specs,
                            source_rack_barcode=self.BUFFER_PLATE_BARCODE,
                            ignored_positions=ign_positions)
            self.__buffer_dilution_indices.add(job_index)
        elif worklist.transfer_type == TRANSFER_TYPES.SAMPLE_TRANSFER:
            ign_positions = self._ignored_positions[source_rack.label]
            transfer_job = SampleTransferJob(index=job_index,
                            planned_worklist=worklist,
                            target_rack=target_plate,
                            source_rack=source_rack,
                            pipetting_specs=worklist.pipetting_specs,
                            ignored_positions=ign_positions)
        else:
            transfer_job = RackSampleTransferJob(index=job_index,
                            planned_rack_transfer=planned_rack_sample_transfer,
                            target_rack=target_plate, source_rack=source_rack)
            self._rack_transfer_worklists[job_index] = worklist
        self._transfer_jobs[job_index] = transfer_job

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
        return SerialWriterExecutorTool._merge_streams(self, stream_map)

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
        kw = dict(log=self.log, entity=self.entity,
                  iso_request=self._iso_request,
                  rack_containers=self._rack_containers.values())
        writer = create_instructions_writer(**kw)
        instructions_stream = writer.get_result()

        if instructions_stream is None:
            msg = 'Error when trying to generate instructions file.'
            self.add_error(msg)
            return None
        return instructions_stream


class LabIsoJobWriterExecutor(_LabIsoWriterExecutorTool):
    """
    A base class for tool dealing with the lab ISO Job processing
    (DB execution or generation of robot worklist files).

    **Return Value:** Depending on the subclass.
    """

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
        if self._iso_request.molecule_design_library is not None:
            self._expected_iso_status = ISO_STATUS.QUEUED
        elif self.entity.number_stock_racks == 0:
            msg = 'There are no samples added via the ISO job, thus there ' \
                  'is not job processing required!'
            self.add_error(msg)
        elif self._iso_request.process_job_first:
            self._expected_iso_status = ISO_STATUS.QUEUED
        else:
            self._expected_iso_status = ISO_STATUS.IN_PROGRESS

    def _get_plates(self):
        """
        For jobs we have to add the job plates, too.
        """
        _LabIsoWriterExecutorTool._get_plates(self)
        for jpp in self.entity.iso_job_preparation_plates:
            self._store_and_verify_plate(jpp)

    def _get_stock_racks(self):
        for stock_rack in self.entity.iso_job_stock_racks:
            self._stock_racks[stock_rack.label] = stock_rack

    def _accept_final_intraplate_transfer(self):
        if self._iso_request.molecule_design_library is not None:
            return True
        return not (self._iso_request.process_job_first)


class LabIsoWriterExecutor(_LabIsoWriterExecutorTool):
    """
    A base class for tool dealing with the lab ISO processing
    (DB execution or generation of robot worklist files).

    **Return Value:** Depending on the subclass.
    """

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
        if self._iso_request.molecule_design_library is not None:
            msg = 'All samples for this ISO are handled by the ISO job, ' \
                  'thus, there is no specific ISO handling required!'
            self.add_error(msg)
        elif not self._iso_request.process_job_first:
            self._expected_iso_status = ISO_STATUS.QUEUED
        elif self.entity.iso_job.number_stock_racks == 0:
            self._expected_iso_status = ISO_STATUS.QUEUED
        else:
            self._expected_iso_status = ISO_STATUS.IN_PROGRESS

    def _get_stock_racks(self):
        stock_racks = self.entity.iso_stock_racks \
                      + self.entity.iso_sector_stock_racks
        for stock_rack in stock_racks:
            self._stock_racks[stock_rack.label] = stock_rack

    def _accept_final_intraplate_transfer(self):
        if self.entity.iso_job.number_stock_racks == 0:
            return True
        return self._iso_request.process_job_first


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

    def _check_input(self):
        BaseRackVerifier._check_input(self)
        if not isinstance(self.lab_iso_plate, (IsoPlate, LibraryPlate,
                                               IsoJobPreparationPlate)):
            msg = 'The lab ISO plate must be an %s, %s or an %s (obtained: ' \
                  '%s.)' % (IsoPlate.__name__, LibraryPlate.__name__,
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
        if isinstance(self.lab_iso_plate, IsoAliquotPlate, LibraryPlate):
            msg = 'The reference layout for a final ISO plate must not ' \
                  'be None!'
            self.add_error(msg)
        elif isinstance(self.lab_iso_plate, isinstance(IsoPreparationPlate,
                                                       IsoJobPreparationPlate)):
            converter = LabIsoPrepLayoutConverter(log=self.log,
                                    rack_layout=self.lab_iso_plate.rack_layout)
            self._expected_layout = converter.get_result()
            if not self._expected_layout is None:
                msg = 'Error when trying to convert rack layout!'
                self.add_error(msg)
        else:
            msg = 'Unexpected ISO plate type: %s.' \
                   % (self.lab_iso_plate.__class__.__name__)
            self.add_error(msg)

    def _get_exp_pos_molecule_design_ids(self, plate_pos):
        """
        For final plate positions we must only regard positions for either
        jobs or ISOs (mismatching booleans are compared because this
        processing is assumed to happen first).
        """
        if isinstance(plate_pos, FinalLabIsoPosition):
            if (plate_pos.for_job == self.for_job): return None
        return self._get_ids_for_pool(plate_pos.molecule_design_pool)


class StockRackVerifier(BaseRackVerifier):
    """
    Compares stock racks for lab ISOs and ISO jobs with stock racks layouts.
    """
    NAME = 'Lab ISO Stock Rack Verifier'

    _RACK_CLS = TubeRack
    _LAYOUT_CLS = StockRackVerifier
    _CHECK_VOLUMES = True

    def __init__(self, log, stock_rack):
        """
        Constructor:

        :param log: The log the write in.
        :type log: :class:`thelma.ThelmaLog`

        :param stock_rack: The stock rack to be checked.
        :type stock_rack: :class:`thelma.models.iso.StockRack`
        """
        BaseRackVerifier.__init__(self, log=log)

        #: The stock rack to be checked.
        self.stock_rack = stock_rack

    def _check_input(self):
        BaseRackVerifier._check_input(self)
        self._check_input_class('stock rack', self.stock_rack, StockRack)

    def _set_rack(self):
        self._rack = self.stock_rack.rack

    def _fetch_expected_layout(self):
        converter = StockRackLayoutConverter(log=self.log,
                                     rack_layout=self.stock_rack.rack_layout)
        self._expected_layout = converter.get_result()
        if self._expected_layout is None:
            msg = 'Error when trying to convert stock rack layout!'
            self.add_error(msg)

    def _get_exp_pos_molecule_design_ids(self, pool_pos):
        if pool_pos is None: return None
        return self._get_exp_pos_molecule_design_ids(pool_pos.molecule_design_pool)

    def _get_minimum_volume(self, pool_pos):
        """
        Returns the sum of the transfer volumes for all target positions
        plus the stock dead volume.
        """
        return pool_pos.get_required_stock_volume()



#class LabIsoProcessingWorklistWriter(_LabIsoProcessingTool):
#    pass
#class LabIsoProcessingExecutor(_LabIsoProcessingTool):
#    RECORD_WARNINGS = False
