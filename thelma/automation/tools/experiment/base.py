"""
This module provides base classes for tools dealing with experiments.
The :class:`ExperimentTool` fetches experiment data such as the source rack,
the experiment racks and the worklist series.

:class:`ExperimentOptimisationTool` and :class:`ExperimentScreeningTool`
(inheriting from :class:`ExperimentTool`) provides lists of transfer jobs for
the mastermix preparation and the cell plate preparation. These lists can be
used be series tools.

AAB
"""
from thelma.automation.tools.iso.lab.base import LabIsoLayoutConverter
from thelma.automation.tools.metadata.transfection_utils \
    import TransfectionLayoutConverter
from thelma.automation.tools.metadata.transfection_utils \
    import TransfectionParameters
from thelma.automation.tools.metadata.worklist \
    import EXPERIMENT_WORKLIST_PARAMETERS
from thelma.automation.tools.metadata.worklist \
    import ExperimentWorklistGenerator
from thelma.automation.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.semiconstants import ITEM_STATUS_NAMES
from thelma.automation.tools.semiconstants import PIPETTING_SPECS_NAMES
from thelma.automation.tools.semiconstants import RESERVOIR_SPECS_NAMES
from thelma.automation.tools.semiconstants import get_reservoir_spec
from thelma.automation.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.utils.base import round_up
from thelma.automation.tools.utils.iso import IsoRequestLayout
from thelma.automation.tools.utils.iso import IsoRequestLayoutConverter
from thelma.automation.tools.utils.verifier import BaseRackVerifier
from thelma.automation.tools.worklists.biomek import BiomekWorklistWriter
from thelma.automation.tools.worklists.biomek import SampleDilutionWorklistWriter
from thelma.automation.tools.worklists.series import SampleDilutionJob
from thelma.automation.tools.worklists.series import SerialWriterExecutorTool
from thelma.automation.tools.writers import CsvColumnParameters
from thelma.automation.tools.writers import CsvWriter
from thelma.models.experiment import Experiment
from thelma.models.experiment import ExperimentMetadataType
from thelma.models.iso import LabIsoRequest
from thelma.models.rack import Plate

__docformat__ = 'reStructuredText en'

__all__ = ['PRINT_SUPPORT_SCENARIOS',
           'ExperimentTool',
           'SourceRackVerifier',
           'ReagentPreparationWriter']


PRINT_SUPPORT_SCENARIOS = [EXPERIMENT_SCENARIOS.OPTIMISATION,
                           EXPERIMENT_SCENARIOS.SCREENING,
                           EXPERIMENT_SCENARIOS.LIBRARY]


class ExperimentTool(SerialWriterExecutorTool):
    """
    An abstract base class for tools dealing with experiment (fetching
    experiment data).

    **Return Value:** a zip stream for for printing mode or executed worklists
        for execution mode
    """

    #: The experiment types supported by this tool.
    SUPPORTED_SCENARIOS = []

    #: May mock positions be empty in the ISO rack? (default: *True*)
    MOCKS_MAY_BE_EMPTY = True

    #: The index of the optimem worklist in the experiment design series.
    OPTIMEM_WORKLIST_INDEX = ExperimentWorklistGenerator.OPTIMEM_WORKLIST_INDEX
    #: The index of the optimem worklist in the experiment design series.
    REAGENT_WORKLIST_INDEX = ExperimentWorklistGenerator.REAGENT_WORKLIST_INDEX

    #: The barcode of the reservoir providing the optimem medium.
    OPTIMEM_PLATE_BARCODE = 'optimem_plate'
    #: The barcode of the reservoir providing the transfection reagent.
    REAGENT_PLATE_BARCODE = 'complexes'

    #: The suffix for the file name of the first CSV worklist (which deals with
    #: addition of OptiMem solutions into the ISO plate). The first part of the
    #: file name will be the experiment metadata label.
    FILE_SUFFIX_OPTIMEM = '_biomek_optimem.csv'
    #: The suffix for the file name of the first CSV worklist (which deals with
    #: addition of complex solutions into the ISO plate). The first part of the
    #: file name will be the experiment metadata label.
    FILE_SUFFIX_REAGENT = '_biomek_reagent.csv'
    #: The suffix for the file name of the file dealing with the the transfer
    #: of mastermix solution from ISO plate to experiment plates).
    #: The first part of the file name will be the experiment metadata label.
    FILE_SUFFIX_TRANSFER = None

    #: The suffix for the file name of the reagent solution preparation file.
    #: The first part of the file name will be the experiment metadata label.
    FILE_SUFFIX_PREPARATION = '_reagent_instructions.csv'

    #: The index of the optimem worklist in the experiment design series.
    OPTIMEM_WORKLIST_INDEX = ExperimentTool.OPTIMEM_WORKLIST_INDEX
    #: The index of the optimem worklist in the experiment design series.
    REAGENT_WORKLIST_INDEX = ExperimentTool.REAGENT_WORKLIST_INDEX

    def __init__(self, experiment, mode, user=None, log=None, **kw):
        """
        Constructor:

        :param experiment: The experiment to process.
        :type experiment: :class:`thelma.models.experiment.Experiment`

        :param mode: :attr:`MODE_EXECUTE` or :attr:`MODE_PRINT_WORKLISTS`
        :type mode: str

        :param user: The user who conducts the DB update (required for
            execution mode).
        :type user: :class:`thelma.models.user.User`
        :default user: *None*

        :param log: The ThelmaLog to write into (if used as part of a batch).
        :type log: :class:`thelma.ThelmaLog`
        :default log: *None*
        """
        depending = not log is None
        SerialWriterExecutorTool.__init__(self, log=log,
                                          mode=mode, user=user,
                                          depending=depending, **kw)

        #: The experiment for which to generate the rack.
        self.experiment = experiment

        #: The experiment metadata type
        #: (:class:`thelma.models.experiment.ExperimentMetadataType`).
        self._scenario = None
        #: The worklist series of the experiment design
        #: (:class:`thelma.models.liquidtransfer.WorklistSeries`).
        self._design_series = None
        #: The worklist series for the design racks mapped onto design
        #: racks labels (if there are any).
        #: (:class:`thelma.models.liquidtransfer.WorklistSeries`).
        self._design_rack_series_map = None
        #: The index of the transfer worklist within a valid design rack series.
        self._transfer_worklist_index = None
        #: The index of the cell worklist within a valid design rack series.
        self._cell_worklist_index = None

        #: Maps experiment racks onto the design rack they belong to.
        self._experiment_racks = None
        #: The source plate (ISO plate) for this experiment.
        self._source_plate = None

        #: The ISO layout for this experiment.
        self._source_layout = None
        #: A list of rack position to be ignore during execution or worklist
        #: generation. The rack position are floating position for which
        #: there were no molecule design pools left anymore.
        self._ignored_positions = None

        #: The final stream mapped onto file suffixes (print mode only).
        self._final_streams = None

    def reset(self):
        """
        Resets all attributes except for the initialisation values.
        """
        SerialWriterExecutorTool.reset(self)
        self._scenario = None
        self._design_series = None
        self._design_rack_series_map = dict()
        self._transfer_worklist_index = None
        self._cell_worklist_index = None
        self._experiment_racks = dict()
        self._source_plate = None
        self._source_layout = None
        self._ignored_positions = []
        self._final_streams = dict()

    def _create_transfer_jobs(self):
        if not self.has_errors(): self._check_experiment_type()
        if not self.has_errors():
            self.__fetch_experiment_data()
            self.__check_for_previous_execution()
        if not self.has_errors() and \
                    not self._scenario.id == EXPERIMENT_SCENARIOS.ISO_LESS:
            if not self.has_errors(): self.__verify_source_plate()
            if not self.has_errors() and self._source_layout.has_floatings():
                self.__find_ignored_positions()
        if not self.has_errors(): self._check_mastermix_compatibility()
        if not self.has_errors(): self._generate_transfer_jobs()

    def _check_input(self):
        """
        Checks whether all initialisation values are valid.
        """
        self.add_debug('Check input ...')
        self._check_input_class('experiment', self.experiment, Experiment)

    def _check_experiment_type(self):
        """
        Ensures that the tool is supporting the given experiment type.
        """
        self.add_debug('Check experiment type ...')

        self._scenario = self.experiment.experiment_design.\
                         experiment_metadata_type

        if not self._scenario.id in self.SUPPORTED_SCENARIOS:
            msg = 'The type of this experiment is not supported by this tool ' \
                  '(given: %s, supported: %s).' % (self._scenario.display_name,
                   ', '.join(EXPERIMENT_SCENARIOS.get_displaynames(
                                        self.SUPPORTED_SCENARIOS)))
            self.add_error(msg)
        elif not self._scenario.id in EXPERIMENT_SCENARIOS.\
                                                EXPERIMENT_MASTERMIX_TYPES:
            pass # there are no worklists
        else:
            storage_location = EXPERIMENT_WORKLIST_PARAMETERS.STORAGE_LOCATIONS[
                                                            self._scenario.id]
            self._transfer_worklist_index = EXPERIMENT_WORKLIST_PARAMETERS.\
                                    TRANSFER_WORKLIST_INDICES[storage_location]
            self._cell_worklist_index = EXPERIMENT_WORKLIST_PARAMETERS.\
                                    CELL_WORKLIST_INDICES[storage_location]

        if self.mode == self.MODE_PRINT_WORKLISTS and \
                        not self._scenario.id in PRINT_SUPPORT_SCENARIOS:
            msg = 'There is no worklist printing support for this ' \
                  'experiment type (%s).' % (self._scenario.display_name)
            self.add_error(msg)

    def __fetch_experiment_data(self):
        """
        Sets the transfer plans and experiment racks for the different
        design racks.
        """
        self.add_debug('Set transfer plans and experiment racks ...')

        experiment_design = self.experiment.experiment_design
        self._source_plate = self.experiment.source_rack
        self._design_series = experiment_design.worklist_series

        design_racks = self.experiment.experiment_design.design_racks
        for design_rack in design_racks:
            self._experiment_racks[design_rack.label] = []
            worklist_series = design_rack.worklist_series
            if worklist_series is None: continue
            self._design_rack_series_map[design_rack.label] = worklist_series

        for experiment_rack in self.experiment.experiment_racks:
            design_rack_label = experiment_rack.design_rack.label
            if not self._experiment_racks.has_key(design_rack_label):
                msg = 'Unknown design rack "%s" for experiment rack "%s"!' \
                      % (design_rack_label, experiment_rack.rack.barcode)
                self.add_error(msg)
            self._experiment_racks[design_rack_label].append(experiment_rack)

        for experiment_racks in self._experiment_racks.values():
            experiment_racks.sort(cmp=lambda er1, er2: cmp(er1.rack.barcode,
                                                           er2.rack.barcode))

    def __check_for_previous_execution(self):
        """
        Makes sure the experiment has not been executed before.
        """
        self.add_debug('Check for previous execution ...')

        has_been_executed = False

        for exp_rack_list in self._experiment_racks.values():
            for exp_rack in exp_rack_list:
                if exp_rack.rack.status.name == ITEM_STATUS_NAMES.MANAGED:
                    has_been_executed = True
                    break

        if has_been_executed:
            if self._scenario.id == EXPERIMENT_SCENARIOS.ISO_LESS:
                exp_detail = 'experiment "%s"' % (self.experiment.label)
            else:
                exp_detail = 'source plate %s' % (self._source_plate.barcode)
            msg = 'The database update for %s has already been made before!' \
                  % (exp_detail)
            self.add_error(msg)


    def __verify_source_plate(self):
        """
        Verifies the source plate (if there is one). In any case the layout
        for the source plate is retrieved and stored.
        """
        self.add_debug('Verify source plate ...')

        iso_request = self.experiment.experiment_design.experiment_metadata.\
                      lab_iso_request

        if self._source_plate is None:
            self.__fetch_iso_layout(iso_request)
        else:
            verifier = SourceRackVerifier(log=self.log,
                            source_plate=self._source_plate,
                            iso_request=iso_request,
                            experiment_type=self._scenario)
            compatible = verifier.get_result()
            if compatible is None:
                msg = 'Error when trying to verify source rack!'
                self.add_error(msg)
            elif not compatible:
                msg = 'The source rack does not match the ISO request layout!'
                self.add_error(msg)
            else:
                self._source_layout = verifier.get_expected_layout()

    def __fetch_iso_layout(self, iso_request):
        """
        Fetches the ISO request layout if there is no source rack (for
        seeding experiments).
        """
        self.add_debug('Fetch ISO request layout ...')

        converter = TransfectionLayoutConverter(log=self.log,
                                        rack_layout=iso_request.iso_layout,
                                        is_iso_layout=False)
        self._source_layout = converter.get_result()

        if self._source_layout is None:
            msg = 'Could not convert ISO transfection layout!'
            self.add_error(msg)
        else:
            layout_shape = self._source_layout.shape
            rack_shape = self._source_plate.specs.shape
            if not layout_shape == rack_shape:
                msg = 'The rack shape of ISO layout (%s) and ISO rack (%s) ' \
                      'do not match!' % (layout_shape, rack_shape)
                self.add_error(msg)

    def __find_ignored_positions(self):
        """
        Determines positions that can be ignored (caused by floating positions
        for which there was no molecule design pool left anymore).
        """
        missing_fixed_positions = []

        for container in self._source_plate.containers:
            rack_pos = container.location.position
            sample = container.sample
            if not (sample is None or sample.volume is None or \
                    sample.volume == 0):
                continue
            iso_pos = self._source_layout.get_working_position(rack_pos)
            if iso_pos is None or iso_pos.is_empty or iso_pos.is_mock: continue
            if iso_pos.is_floating:
                self._ignored_positions.append(rack_pos)
            else:
                missing_fixed_positions.append(rack_pos.label)

        if len(missing_fixed_positions) > 0:
            msg = 'Some wells of the ISO rack which should contain controls ' \
                  'are empty: %s!' % (missing_fixed_positions)
            self.add_error(msg)

    def _check_mastermix_compatibility(self):
        """
        Checks whether the worklist series allows for a complete
        execution (as opposed to a partial one) of the DB (requires the full
        set of worklist series).
        """
        raise NotImplementedError('Abstract method.')

    def _generate_transfer_jobs(self):
        """
        For printing mode, the target racks for each design rack are sorted
        by label. Cell suspension transfer jobs are only added for
        execution mode.
        """
        add_cell_jobs = True
        if self.mode == self.MODE_PRINT_WORKLISTS:
            add_cell_jobs = False
        self._create_all_transfer_jobs(add_cell_jobs)

    def _create_all_transfer_jobs(self, add_cell_jobs):
        """
        For printing mode we do not need the cell worklist.
        """
        raise NotImplementedError('Abstract method.')


    def _get_transfer_worklist(self, worklist_series):
        """
        A helper function returning the worklist for the transfer to the
        experiment plates.
        """
        return self.__get_worklist_by_index(worklist_series,
                                            self._transfer_worklist_index)

    def _get_cell_suspension_worklist(self, worklist_series):
        """
        A helper function returning the worklist for the addition of cell
        suspension to the experiment plates.
        """
        return self.__get_worklist_by_index(worklist_series,
                                            self._cell_worklist_index)

    def _create_transfer_jobs_for_mastermix_preparation(self):
        """
        Return the transfer jobs for the mastermix preparation.
        """
        self.add_debug('Create mastermix transfer jobs ...')

        optimem_worklist = self._get_optimem_worklist()
        if optimem_worklist is None:
            msg = 'Could not get worklist for Optimem dilution.'
            self.add_error(msg)

        reagent_worklist = self._get_reagent_worklist()
        if reagent_worklist is None:
            msg = 'Could not get worklist for addition of transfection ' \
                  'reagent.'
            self.add_error(msg)

        if self.has_errors(): return None

        optimem_job = self._create_optimem_job(optimem_worklist)
        reagent_job = self._create_reagent_job(reagent_worklist)

        self._transfer_jobs = {0 : optimem_job, 1 : reagent_job}

    def _get_optimem_worklist(self):
        """
        A helper function returning the worklist for the transfer to the
        experiment plates.
        """
        return self.__get_worklist_by_index(self._design_series,
                                            self.OPTIMEM_WORKLIST_INDEX)

    def _get_reagent_worklist(self):
        """
        A helper function returning the worklist for the transfer to the
        experiment plates.
        """
        return self.__get_worklist_by_index(self._design_series,
                                            self.REAGENT_WORKLIST_INDEX)

    def _create_optimem_job(self, optimem_worklist):
        """
        Helper function creating an optimem dilution job.
        """
        quarter_rs = get_reservoir_spec(RESERVOIR_SPECS_NAMES.QUARTER_MODULAR)

        optimem_job = SampleDilutionJob(index=0,
                       planned_worklist=optimem_worklist,
                       target_rack=self._source_plate,
                       reservoir_specs=quarter_rs,
                       source_rack_barcode=self.OPTIMEM_PLATE_BARCODE,
                       ignored_positions=self._ignored_positions,
                       pipetting_specs=PIPETTING_SPECS_NAMES.BIOMEK)
        return optimem_job

    def _create_reagent_job(self, reagent_worklist):
        """
        Helper function creating an transfection reagent dilution job.
        """
        tube_24_rs = get_reservoir_spec(RESERVOIR_SPECS_NAMES.TUBE_24)

        optimem_job = SampleDilutionJob(index=1,
                       planned_worklist=reagent_worklist,
                       target_rack=self._source_plate,
                       reservoir_specs=tube_24_rs,
                       source_rack_barcode=self.REAGENT_PLATE_BARCODE,
                       ignored_positions=self._ignored_positions,
                       pipetting_specs=PIPETTING_SPECS_NAMES.BIOMEK)
        return optimem_job

    def __get_worklist_by_index(self, worklist_series, worklist_index):
        """
        Helper function return worklist for a certain index within a
        worklist series.
        """
        for worklist in worklist_series:
            if worklist.index == worklist_index:
                return worklist

        return None

    def _add_cell_suspension_job(self, cell_worklist, job_index, plate,
                                 cell_ignored_positions):
        """
        Helper function registering a container dilution job for the given
        worklist, plate and job index. In addition, in increments the
        job index.
        """
        falcon_reservoir = get_reservoir_spec(
                                            RESERVOIR_SPECS_NAMES.FALCON_MANUAL)
        cell_job = SampleDilutionJob(index=job_index,
                    planned_worklist=cell_worklist,
                    target_rack=plate,
                    reservoir_specs=falcon_reservoir,
                    ignored_positions=cell_ignored_positions,
                    pipetting_specs=PIPETTING_SPECS_NAMES.MANUAL)
        self._transfer_jobs[job_index] = cell_job
        job_index += 1
        return job_index

    def _merge_streams(self, stream_map):
        """
        Optimem and reagent streams extracted.
        """
        self._extract_mastermix_streams(stream_map)
        SerialWriterExecutorTool._merge_streams(self, stream_map)

    def _extract_mastermix_streams(self, stream_map):
        """
        Extracts the optimem and reagent stream from the stream map.
        """
        self._final_streams[self.FILE_SUFFIX_OPTIMEM] = \
                                        stream_map[self.OPTIMEM_WORKLIST_INDEX]
        self._final_streams[self.FILE_SUFFIX_REAGENT] = \
                                        stream_map[self.REAGENT_WORKLIST_INDEX]
        del stream_map[self.OPTIMEM_WORKLIST_INDEX]
        del stream_map[self.REAGENT_WORKLIST_INDEX]

    def _get_file_map(self, merged_stream_map, rack_transfer_stream):
        """
        The common part of the zip map for the zip archive contains optimem,
        reagent and reagent preparation file. Transfer worklist files
        have to be added by the subclasse.
        """
        file_map = dict()
        self.__write_preparations_file()

        experiment_label = self.experiment.label
        for suffix, stream in self._final_streams.iteritems():
            fn = '%s%s' % (experiment_label, suffix)
            file_map[fn] = stream
        return file_map

    def __add_file(self, suffix, stream, file_map):
        """
        Helper function storing the given stream in the zip file map. The
        file name is comprised of the suffix and the experiment label.
        """
        fn = '%s%s' % (self.experiment.label, suffix)
        file_map[fn] = stream

    def __write_preparations_file(self):
        """
        Writes the stream for reagent solution preparation file.
        """
        reagent_stream = self._final_streams[self.FILE_SUFFIX_REAGENT]
        reagent_content = reagent_stream.read()
        reagent_stream.seek(0)
        preparation_writer = ReagentPreparationWriter(log=self.log,
                                    reagent_stream_content=reagent_content)
        prep_stream = preparation_writer.get_result()
        if prep_stream is None:
            msg = 'ExperimentWorklistWriters - Error when trying to write ' \
                  'preparation file.'
            self.add_warning(msg)
        else:
            self._final_streams[self.FILE_SUFFIX_PREPARATION] = prep_stream


class SourceRackVerifier(BaseRackVerifier):
    """
    This tool verifies whether a rack is a suitable source rack for a the
    passed ISO request transfection layout.

    **Return Value:** boolean
    """

    NAME = 'Source Rack Verifier'

    _RACK_CLS = Plate
    _LAYOUT_CLS = IsoRequestLayout

    def __init__(self, log, source_plate, iso_request, experiment_type):
        """
        Constructor:

        :param log: The log the write in.
        :type log: :class:`thelma.ThelmaLog`

        :param iso_request: The ISO request the plate must represent.
        :type iso_request: :class:`thelma.models.iso.isoRequest`

        :param source_plate: The plate to be checked.
        :type source_plate: :class:`thelma.models.rack.Plate`

        :param experiment_type: The experiment type defines the source layout
            type (:class:`IsoRequestLayout` or :class:`TransfectionLayout`)
        :type experiment_type: :class:`thelma.models.experiment.ExperimentType`
        """
        BaseRackVerifier.__init__(self, log=log)

        #: The ISO request the plate must represent.
        self.iso_request = iso_request
        #: The plate to be checked.
        self.source_plate = source_plate
        #: The experiment type defines the source layout.
        self.experiment_type = experiment_type

        #: Maps floating maps (molecule design pools for placeholders) onto ISO
        #: label - is only used when there are floating positions in the ISO
        #: layout.
        self._iso_map = dict()
        #: The name of the ISO the source rack represents.
        self._used_iso = None

    def reset(self):
        BaseRackVerifier.reset(self)
        self._iso_map = None
        self._used_iso = None

    def _check_input(self):
        BaseRackVerifier._check_input(self)
        self._check_input_class('ISO request', self.iso_request, LabIsoRequest)
        self._check_input_class('experiment type', self.experiment_type,
                                ExperimentMetadataType)

    def _set_rack(self):
        self._rack = self.source_plate

    def _fetch_expected_layout(self):
        """
        The expected layout is the ISO layout of the ISO request.
        """
        self.add_debug('Get ISO layout ...')

        if self.experiment_type.id == EXPERIMENT_SCENARIOS.MANUAL:
            converter_cls = IsoRequestLayoutConverter
        else:
            converter_cls = TransfectionLayoutConverter
        kw = dict(log=self.log, rack_layout=self.iso_request.iso_layout)
        converter = converter_cls(**kw)
        self._expected_layout = converter.get_result()
        if self._expected_layout is None:
            msg = 'Error when trying to convert ISO layout.'
            self.add_error(msg)
        else:
            self._expected_layout.close()
            has_floatings = self._expected_layout.has_floatings()
            if has_floatings: self.__get_iso_map()

    def __get_iso_map(self):
        """
        Generates the floating maps for all ISOs of the experiment metadata.
        """
        self.add_debug('Generate ISO map ...')

        self._iso_map = dict()

        for iso in self.iso_request.isos:
            converter = LabIsoLayoutConverter(rack_layout=iso.rack_layout,
                                              log=self.log)
            iso_layout = converter.get_result()

            if iso_layout is None:
                msg = 'Error when trying to convert layout for ISO %s.' \
                      % (iso.label)
                self.add_error(msg)
                continue

            floating_map = dict()
            for rack_pos, ir_pos in self._expected_layout.iterpositions():
                if not ir_pos.is_floating: continue
                placeholder = ir_pos.molecule_design_pool
                if floating_map.has_key(placeholder): continue
                iso_pos = iso_layout.get_working_position(rack_pos)
                if iso_pos is None:
                    pool = None
                else:
                    pool = iso_pos.molecule_design_pool
                floating_map[placeholder] = pool
            self._iso_map[iso.label] = floating_map

        if len(self._iso_map) < 1:
            msg = 'There are no ISOs for this ISO request!'
            self.add_error(msg)

    def _get_expected_pools(self, ir_pos):
        """
        Gets the molecule design pool IDs for expected for a ISO position
        (replacing floating placeholder with the pools of the preparation
        layout position molecule designs of all ISOs).
        """
        if ir_pos.is_fixed:
            pool = ir_pos.molecule_design_pool

        else: # floating
            placeholder = ir_pos.molecule_design_pool

            if self._used_iso is None:
                possible_pools = dict()
                for iso_label, floating_map in self._iso_map.iteritems():
                    pool = floating_map[placeholder]
                    if pool is None:
                        ids = None
                    else:
                        ids = self._get_ids_for_pool(pool)
                    possible_pools[iso_label] = ids
                return possible_pools
            else:
                floating_map = self._iso_map[self._used_iso]
                pool = floating_map[placeholder]

        return self._get_ids_for_pool(pool)

    def _are_matching_molecule_designs(self, rack_mds, exp_mds):
        """
        Checks whether the molecule designs for the positions match.
        The method will also try to determine the ISO if this has not
        been happened so far.
        """
        if exp_mds is None or isinstance(exp_mds, list):
            return BaseRackVerifier._are_matching_molecule_designs(self,
                                                      rack_mds, exp_mds)

        # In case of floating position and unknown ISO ...
        for iso_label, iso_mds in exp_mds.iteritems():
            if BaseRackVerifier._are_matching_molecule_designs(self,
                                                      rack_mds, iso_mds):
                self._used_iso = iso_label
                return True

        return False


class ReagentPreparationWriter(CsvWriter):
    """
    This writer generates a CSV file providing a instructions about how
    to prepare the RNAi dilutions used for the second worklist (dilution
    with RNAi reagent).

    **Return Value:** file stream (CSV)
    """

    NAME = 'Reagent Preparation Writer'

    #: The header for the position column.
    POSITION_HEADER = 'Rack Position'
    #: The header for the reagent name column.
    REAGENT_NAME_HEADER = 'Reagent Name'
    #: The header for the final dilution factor column.
    FINAL_DIL_FACTOR_HEADER = 'Final Dilution Factor'
    #: The header for the initial dilution factor column.
    PREPAR_DIL_FACTOR_HEADER = 'Preparation Dilution Factor'
    #: The header for the total volume column.
    TOTAL_VOLUME_HEADER = 'Total Volume'
    #: The header for the reagent volume column.
    REAGENT_VOL_HEADER = 'Reagent Volume'
    #: The header for the diluent volume column.
    DILUENT_VOL_HEADER = 'Diluent Volume'

    #: The index for the position column.
    POSITION_INDEX = 0
    #: The index for the reagent name column.
    REAGENT_NAME_INDEX = 1
    #: The index for the final dilution factor column.
    FINAL_DIL_FACTOR_INDEX = 2
    #: The header for the initial dilution factor column.
    PREPAR_DIL_FACTOR_INDEX = 3
    #: The index for the total volume column.
    TOTAL_VOLUME_INDEX = 4
    #: The index for the reagent volume column.
    REAGENT_VOL_INDEX = 5
    #: The index for the diluent volume column.
    DILUENT_VOL_INDEX = 6

    def __init__(self, reagent_stream_content, log):
        """
        Constructor:

        :param reagent_stream_content: The content of the reagent dilution
            worklist stream.
        :type reagent_stream_content: :class:`str`

        :param log: The ThelmaLog you want to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        CsvWriter.__init__(self, log=log)

        #: The content of the reagent dilution worklist stream.
        self.reagent_stream_content = reagent_stream_content

        #: The relevant data of the worklist (key: line index, values:
        #: tuple (source pos, dilution volume, diluent info) .
        self.__worklist_data = None

        #: The estimated dead volume in ul.
        self.__dead_volume = get_reservoir_spec(RESERVOIR_SPECS_NAMES.TUBE_24).\
                             max_dead_volume * VOLUME_CONVERSION_FACTOR

        #: Intermediate storage for the column values.
        self.__position_values = None
        self.__name_values = None
        self.__final_dil_factor_values = None
        self.__ini_dil_factor_values = None
        self.__total_volume_values = None
        self.__reagent_volume_values = None
        self.__diluent_volume_values = None

    def reset(self):
        """
        Resets all values except for initialisation values.
        """
        CsvWriter.reset(self)
        self.__worklist_data = dict()
        self.__position_values = []
        self.__name_values = []
        self.__final_dil_factor_values = []
        self.__ini_dil_factor_values = []
        self.__total_volume_values = []
        self.__reagent_volume_values = []
        self.__diluent_volume_values = []

    def _init_column_map_list(self):
        """
        Creates the :attr:`_column_map_list`
        """
        self.__check_input()
        if not self.has_errors(): self.__get_worklist_lines()
        if not self.has_errors(): self.__generate_column_values()
        if not self.has_errors(): self.__generate_columns()

    def __check_input(self):
        """
        Checks if the tools has obtained correct input values.
        """
        self.add_debug('Check input values ...')
        self._check_input_class('reagent dilution worklist stream',
                                self.reagent_stream_content, str)

    def __get_worklist_lines(self):
        """
        Fetches the dilution layout from the rack layout of the plan.
        """
        self.add_debug('Get worklist lines ...')

        line_counter = 0
        for wl_line in self.reagent_stream_content.split('\n'):
            line_counter += 1
            if line_counter == 1: continue # header
            wl_line.strip()
            if len(wl_line) < 1: continue
            tokens = []
            if ',' in wl_line: tokens = wl_line.split(',')
            if ';' in wl_line: tokens = wl_line.split(';')

            position = self.__extract_data_from_line_tokens(tokens,
                        BiomekWorklistWriter.SOURCE_POS_INDEX)
            volume = self.__extract_data_from_line_tokens(tokens,
                        BiomekWorklistWriter.TRANSFER_VOLUME_INDEX)
            volume = float(volume)
            dil_info = self.__extract_data_from_line_tokens(tokens,
                        SampleDilutionWorklistWriter.DILUENT_INFO_INDEX)
            data_tuple = (position, volume, dil_info)
            self.__worklist_data[line_counter] = data_tuple

    def __extract_data_from_line_tokens(self, tokens, data_index):
        """
        Extracts a certain information from a line token.
        """
        token = tokens[data_index]
        if token.startswith('"'): token = token[1:]
        if token.endswith('"'): token = token[:-1]
        return token

    def __generate_column_values(self):
        """
        Generates the values for the CSV columns.
        """
        self.add_debug('Generate column value lists ...')

        dil_data_map = self.__get_distinct_reagent_infos()
        line_numbers = self.__worklist_data.keys()
        line_numbers.sort()
        used_dil_infos = []
        for line_number in line_numbers:
            data_tuple = self.__worklist_data[line_number]
            dil_info = data_tuple[2]
            if dil_info in used_dil_infos: continue
            used_dil_infos.append(dil_info)
            pos_label = data_tuple[0]
            total_vol = dil_data_map[dil_info]
            self.__store_line_value(dil_info, total_vol, pos_label)

    def __get_distinct_reagent_infos(self):
        """
        Gets the dilution positions for each distinct reagent name and dilution
        factor combination.
        """

        dil_data_map = dict()
        for data_tuple in self.__worklist_data.values():
            dil_info = data_tuple[2]
            volume = data_tuple[1]
            if not dil_data_map.has_key(dil_info):
                dil_data_map[dil_info] = self.__dead_volume
            dil_data_map[dil_info] += volume
        return dil_data_map

    def __store_line_value(self, dil_info, total_vol, pos_label):
        """
        Stores the values for one line.
        """

        dil_info = dil_info.strip()
        info_tokens = dil_info.split('(')
        final_dil_factor = float(info_tokens[1][:-1])
        initial_dil_factor = TransfectionParameters.\
                            calculate_initial_reagent_dilution(final_dil_factor)

        reagent_vol = round_up((total_vol / initial_dil_factor))
        total_vol = reagent_vol * initial_dil_factor
        total_vol = round(total_vol, 1)
        diluent_vol = total_vol - reagent_vol
        initial_dil_factor = round(initial_dil_factor, 1)

        self.__position_values.append(pos_label)
        self.__name_values.append(info_tokens[0])
        self.__final_dil_factor_values.append(final_dil_factor)
        self.__ini_dil_factor_values.append(initial_dil_factor)
        self.__total_volume_values.append(total_vol)
        self.__reagent_volume_values.append(reagent_vol)
        self.__diluent_volume_values.append(diluent_vol)

    def __generate_columns(self):
        """
        Generates the columns for the report.
        """
        position_column = CsvColumnParameters.create_csv_parameter_map(
                          self.POSITION_INDEX, self.POSITION_HEADER,
                          self.__position_values)
        name_column = CsvColumnParameters.create_csv_parameter_map(
                          self.REAGENT_NAME_INDEX, self.REAGENT_NAME_HEADER,
                          self.__name_values)
        final_df_column = CsvColumnParameters.create_csv_parameter_map(
                          self.FINAL_DIL_FACTOR_INDEX,
                          self.FINAL_DIL_FACTOR_HEADER,
                          self.__final_dil_factor_values)
        ini_df_column = CsvColumnParameters.create_csv_parameter_map(
                          self.PREPAR_DIL_FACTOR_INDEX,
                          self.PREPAR_DIL_FACTOR_HEADER,
                          self.__ini_dil_factor_values)
        total_vol_column = CsvColumnParameters.create_csv_parameter_map(
                          self.TOTAL_VOLUME_INDEX, self.TOTAL_VOLUME_HEADER,
                          self.__total_volume_values)
        reagent_vol_column = CsvColumnParameters.create_csv_parameter_map(
                          self.REAGENT_VOL_INDEX, self.REAGENT_VOL_HEADER,
                          self.__reagent_volume_values)
        diluent_vol_column = CsvColumnParameters.create_csv_parameter_map(
                          self.DILUENT_VOL_INDEX, self.DILUENT_VOL_HEADER,
                          self.__diluent_volume_values)
        self._column_map_list = [position_column, name_column, final_df_column,
                                 ini_df_column, total_vol_column,
                                 reagent_vol_column, diluent_vol_column]
