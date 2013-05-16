"""
:Date: 05 Aug 2011
:Author: AAB, berger at cenix-bioscience dot com

This module creates or updates an experiment metadata. It applies several
parsers and tools.
"""
from thelma.automation.handlers.experimentdesign \
    import ExperimentDesignParserHandler
from thelma.automation.handlers.experimentpoolset \
    import ExperimentPoolSetParserHandler
from thelma.automation.handlers.isorequest import IsoRequestParserHandler
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.tools.iso.prep_utils import PrepIsoParameters
from thelma.automation.tools.metadata.isolayoutfinder \
    import TransfectionLayoutFinder
from thelma.automation.tools.metadata.transfection_utils \
    import TransfectionAssociationData
from thelma.automation.tools.metadata.transfection_utils \
    import TransfectionLayout
from thelma.automation.tools.metadata.transfection_utils \
    import TransfectionLayoutConverter
from thelma.automation.tools.metadata.transfection_utils \
    import TransfectionParameters
from thelma.automation.tools.metadata.worklist \
    import ExperimentWorklistGenerator
from thelma.automation.tools.semiconstants \
    import get_reservoir_specs_standard_384
from thelma.automation.tools.semiconstants \
    import get_reservoir_specs_standard_96
from thelma.automation.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.tools.semiconstants import RESERVOIR_SPECS_NAMES
from thelma.automation.tools.semiconstants import get_experiment_metadata_type
from thelma.automation.tools.semiconstants import get_experiment_type_manual_optimisation
from thelma.automation.tools.semiconstants import get_reservoir_specs_deep_96
from thelma.automation.tools.stock.base import STOCK_CONCENTRATIONS
from thelma.automation.tools.stock.base import get_default_stock_concentration
from thelma.automation.tools.utils.base import add_list_map_element
from thelma.automation.tools.utils.base import get_trimmed_string
from thelma.automation.tools.utils.base import is_valid_number
from thelma.automation.tools.utils.base import round_up
from thelma.automation.tools.utils.racksector import QuadrantIterator
from thelma.automation.tools.worklists.base \
    import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.tools.worklists.base import MIN_BIOMEK_TRANSFER_VOLUME
from thelma.automation.tools.worklists.base import MIN_CYBIO_TRANSFER_VOLUME
from thelma.automation.tools.worklists.base import VOLUME_CONVERSION_FACTOR
from thelma.models.experiment import ExperimentDesign
from thelma.models.experiment import ExperimentMetadata
from thelma.models.iso import ISO_STATUS
from thelma.models.iso import IsoRequest
from thelma.models.library import MoleculeDesignLibrary
from thelma.models.moleculetype import MOLECULE_TYPE_IDS
from thelma.models.user import User
import logging

__docformat__ = 'reStructuredText en'

__all__ = ['ExperimentMetadataGenerator',
           'ExperimentMetadataGeneratorOpti',
           'ExperimentMetadataGeneratorScreen',
           'ExperimentMetadataGeneratorManual',
           'ExperimentMetadataGeneratorIsoless',
           '_GENERATOR_CLASSES',
           'RobotSupportDeterminator',
           'RobotSupportDeterminatorOpti',
           'RobotSupportDeterminatorScreen',
           'WellAssociator',
           'WellAssociatorManual',
           'WellAssociatorOptimisation'
           ]


class ExperimentMetadataGenerator(BaseAutomationTool):
    """
    Parses and experiment metadata file, generates worklists and performs
    checks. There are different generators depending on the scenario.
    The passed experiment metadata is updated accordingly.

    If there already ISOs for the ISO request of an experiment metadata,
    the upload must not alter the ISO request anymore. If there are already
    experiments running, the experiment design is blocked as well.

    **Return Value:** experiment metadata
        (:class:`thelma.models.experiment.ExperimentMetadata`)
    """
    NAME = 'Experiment Metadata Generator'

    #: The experiment metadata scenario supported by this generator.
    SUPPORTED_EXPERIMENT_TYPE = None

    def __init__(self, stream, experiment_metadata, requester,
                 logging_level=logging.WARNING, add_default_handlers=False):
        """
        Constructor:

        :param stream: The content of the experiment metadata file.

        :param experiment_metadata: The experiment metadata to update.
        :type experiment_metadata:
            :class:`thelma.models.experiment.ExperimentMetadata`

        :param requester: The user uploading the file.
        :type requester: :class:`thelma.models.user.User`

        :param logging_level: the desired minimum log leve l
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *False*
        """
        BaseAutomationTool.__init__(self, None, logging_level,
                                    add_default_handlers, depending=False)

        #: the open excelerator file
        self.stream = stream
        #: The experiment metadata whose values to update.
        self.experiment_metadata = experiment_metadata
        #: The user uploading the file.
        self.requester = requester

        #: The display name of the supported scenario (for messages).
        self._scenario_display_name = get_experiment_metadata_type(
                                    self.SUPPORTED_EXPERIMENT_TYPE).display_name

        #: The experiment design parsed from the file.
        self._experiment_design = None
        #: The ISO request parsed from the file.
        self._iso_request = None
        #: The molecule design pool set parsed from the file.
        self._pool_set = None

        #: The number of the ISO request ticket.
        self._ticket_number = None
        #: The completed source (ISO/transfection) layout.
        self._source_layout = None
        #: The tags rack positions sets for the tags that are not part of the
        #: transfection layout mapped onto their rack position set hash values.
        self._additional_trps = None

        #: The final concentration for each well in each design rack
        #: required for report generation).
        self._final_concentrations = None

        #: The transfer data for each design rack (as copied source transfection
        #: layout with cell plate wells completed).
        self._design_rack_associations = None

        #: The presence of ISOs lead to additional checks, because if there
        #: are already ISOs for the ISO request of the existing metadata
        #: (before file parsing), the ISO request must not be changed anymore.
        self.__has_isos = None
        #: The presence of experiments leads to additional checks, because
        #: if there experiment jobs in the experiment design of the
        #: existing metadata (before file parsing) the experiment design
        #: must not be changed anymore.
        self.__has_experiment_jobs = None

        #: States whether it is possible to use the BioMek for the mastermix
        #: preparation.
        self.supports_mastermix = None
        #: Use deep well plates. Specifies whether one needs to use
        #: deep well plates for the ISO plate.
        self.use_deep_well = None

    def reset(self):
        BaseAutomationTool.reset(self)
        self._experiment_design = None
        self._iso_request = None
        self._pool_set = None
        self._source_layout = None
        self._additional_trps = None
        self._final_concentrations = None
        self._design_rack_associations = None
        self.__has_isos = None
        self.__has_experiment_jobs = None
        self.supports_mastermix = None
        self.use_deep_well = None

    @classmethod
    def create(cls, stream, experiment_metadata, requester,
               logging_level=logging.WARNING, add_default_handlers=False):
        """
        Factory method initialising a generator for the given experiment type.

        :raises KeyError: If an unsupported experiment type is requested.
        :raise ValueError: If the experiment metadata is 8None*
        """
        kw = dict(stream=stream, experiment_metadata=experiment_metadata,
                  requester=requester, logging_level=logging_level,
                  add_default_handlers=add_default_handlers)

        if experiment_metadata is None:
            msg = 'The experiment metadata must not be None!'
            raise ValueError(msg)
        em_type = experiment_metadata.experiment_metadata_type
        if not _GENERATOR_CLASSES.has_key(em_type.id):
            msg = 'Unexpected experiment type "%s"' % (em_type.display_name)
            raise KeyError(msg)

        cls = _GENERATOR_CLASSES[em_type.id]
        return cls(**kw)

    def get_source_layout(self):
        """
        Returns the source layout for the ISO plate (for reports).
        """
        if self.return_value is None: return None
        return self._source_layout

    def get_association_layouts(self):
        """
        Returns the association layouts (for reports).
        """
        if self.return_value is None: return None
        return self._design_rack_associations

    def get_final_concentrations(self):
        """
        Returns the final concentration maps (for reports).
        """
        if self.return_value is None: return None
        return self._final_concentrations

    def run(self):
        self.reset()
        self.add_info('Start metadata generation ...')

        self.__check_input()
        if not self.has_errors(): self.__check_experiment_type()
        if not self.has_errors(): self.__search_for_isos_and_experiments()
        if not self.has_errors(): self.__obtain_experiment_design()
        if not self.has_errors(): self._obtain_iso_request()

        if self._iso_request is not None:
            if not self.has_errors(): self._obtain_pool_set()
            if not self.has_errors(): self._set_optimem_dilution_factors()
            if not self.has_errors(): self._associate_iso_layout_and_design()
            if not self.has_errors(): self._determine_mastermix_support()
            if not self.has_errors(): self._check_iso_concentrations()
            if not self.has_errors(): self.__generate_worklists()
            if not self.has_errors(): self._determine_plate_number()

        if not self.has_errors(): self.__check_blocked_entities()

        if not self.has_errors():
            if not self._iso_request is None: self.__look_for_compounds()
            self.__update_metadata()
            self.return_value = self.experiment_metadata
            self.add_info('Metadata generation completed.')

    def __check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input ...')

        if self._check_input_class('experiment metadata',
                                self.experiment_metadata, ExperimentMetadata):
            self._ticket_number = self.experiment_metadata.ticket_number
            if self._ticket_number is None:
                msg = 'Unable to find ticket number!'
                self.add_error(msg)

        self._check_input_class('requester', self.requester, User)

    def __check_experiment_type(self):
        """
        Checks whether the experiment type of the passed metadata complies
        with the one supported by the tool.
        """
        em_type = self.experiment_metadata.experiment_metadata_type
        if not em_type.id == self.SUPPORTED_EXPERIMENT_TYPE:
            msg = 'Unsupported experiment type "%s".' % (em_type.display_name)
            self.add_error(msg)

    def __search_for_isos_and_experiments(self):
        """
        If there are ISOs in the ISO request of the existing metadata, the
        ISO request must not be changed anymore. If there experiments,
        also the experiment design is blocked.
        """
        self.add_debug('Search for ISOs and experiments ...')

        self.__has_isos = False
        iso_request = self.experiment_metadata.iso_request
        if not iso_request is None:
            for iso in iso_request.isos:
                if not iso.status == ISO_STATUS.CANCELLED:
                    self.__has_isos = True
                    msg = 'The ISO generation for this experiment metadata ' \
                          'has already started!'
                    self.add_warning(msg)
                    break

        num_experiment_jobs = self.experiment_metadata.experiment_design.\
                              experiment_jobs
        self.__has_experiment_jobs = len(num_experiment_jobs) > 0
        if self.__has_experiment_jobs:
            msg = 'There are already experiment jobs for this metadata! ' \
                  'Delete all experiment jobs or talk to the IT department, ' \
                  'please.'
            self.add_warning(msg)

    def __obtain_experiment_design(self):
        """
        Generates the experiment design.
        """
        self.add_debug('Obtain experiment design ...')

        handler = ExperimentDesignParserHandler(stream=self.stream,
                            requester=self.requester,
                            scenario=get_experiment_metadata_type(
                                                self.SUPPORTED_EXPERIMENT_TYPE),
                            log=self.log)
        self._experiment_design = handler.get_result()

        if self._experiment_design is None:
            msg = 'Error when trying to generate experiment design.'
            self.add_error(msg)

    def _obtain_iso_request(self):
        """
        Generates the ISO request.
        """
        self.add_error('Abstract method: _obtain_iso_request()')

    def _create_iso_request_handler(self):
        """
        Convenience function creating the ISO request parser handler.
        """
        handler = IsoRequestParserHandler.create(
                        experiment_type_id=self.SUPPORTED_EXPERIMENT_TYPE,
                        stream=self.stream, requester=self.requester,
                        log=self.log)
        return handler

    def _obtain_pool_set(self):
        """
        Generates the molecule design pool set (only some experiment types).
        """
        has_floatings = self._source_layout.has_floatings()
        handler = ExperimentPoolSetParserHandler(self.stream, self.log)
        pool_set = handler.get_result()

        if pool_set is None:
            if has_floatings:
                msg = 'Error when trying to determine molecule design pool ' \
                      'set for floating positions.'
                abort_message = handler.parser.abort_message
                if not abort_message is None:
                    msg = msg[:-1] + ': ' + abort_message
                self.add_error(msg)

        else:
            if not has_floatings:
                msg = 'There are molecule design pools for floating ' \
                      'positions specified although there are no floating ' \
                      'positions!'
                self.add_error(msg)
            else:
                self._pool_set = pool_set
                self._source_layout.set_floating_molecule_type(
                                                 self._pool_set.molecule_type)
                self._source_layout.set_floating_stock_concentration(
                                            handler.get_stock_concentration())
                self._check_set_designs()

    def _check_set_designs(self):
        """
        Commits scenario-specific molecule design pool set checks.
        """
        pass

    def _set_optimem_dilution_factors(self):
        """
        Sets the molecule types for floating and mock positions (required for
        ISO volume and concentration determinations and stock concentration
        checks).
        """
        pass

    def _associate_iso_layout_and_design(self):
        """
        Associates the ISO layout with the layouts of the design racks
        (required for the generation of transfer worklists).
        Also determines the capability for mastermix support.
        """
        self.add_error('Abstract method: _associate_iso_layout_and_design()')

    def _associate_one_to_one(self):
        """
        Some experiment types do only support a one-to-one association.
        In this case, we need to add the transfection data tags to experiment
        design rack layouts. The final concentration need not be stored because
        they are not required in reports for oe-to-one cases.
        """
        self.add_info('Association ISO layout and design racks one to one ...')

        source_shape = self._source_layout.shape.name
        design_shape = self._experiment_design.rack_shape.name
        if not source_shape == design_shape:
            msg = 'The plate format for experiment design and ISO do not ' \
                  'match (ISO plate layout: %s, experiment design: %s).' \
                  % (source_shape, design_shape)
            self.add_error(msg)

        if not self.has_errors():
            self._source_layout.close()
            for design_rack in self._experiment_design.design_racks:
                new_rack_layout = self._source_layout.\
                    complete_rack_layout_with_screening_tags(design_rack.layout,
                                  self._iso_request.iso_layout, self.requester)
                design_rack.layout = new_rack_layout

    def _check_iso_concentrations(self):
        """
        Checks whether the ordered ISO concentrations are small enough.
        """
        self.add_debug('Check ISO concentrations ...')

        above_stock = []
        above_crit = []

        for rack_pos, tf_pos in self._source_layout.iterpositions():
            if tf_pos.is_mock or tf_pos.is_untreated: continue
            if tf_pos.is_floating:
                stock_conc = self._source_layout.floating_stock_concentration
            else:
                stock_conc = tf_pos.stock_concentration

            iso_concentration = tf_pos.iso_concentration
            crit_iso_conc = TransfectionParameters.\
                            get_critical_iso_concentration(stock_conc)

            if iso_concentration == stock_conc:
                continue
            elif iso_concentration > crit_iso_conc:
                crit_fconc = TransfectionParameters.\
                        get_critical_final_concentration(stock_conc,
                                                    tf_pos.optimem_dil_factor)
                info = '%s (ordered: %.1f nM, critical ISO: %.1f nM, ' \
                       'critical final: %.1f nM)' % (rack_pos,
                        iso_concentration, crit_iso_conc, crit_fconc)
                above_crit.append(info)
            else:
                continue

            if iso_concentration > stock_conc:
                info = '%s (ordered: %.1f nM, stock: %.1f nM)' \
                       % (rack_pos.label, iso_concentration, stock_conc)
                above_stock.append(info)

        if len(above_stock) > 0:
            above_stock.sort()
            msg = 'You have tried to order ISO concentrations that are larger ' \
                  'than the maximum concentration. Reduce the concentration ' \
                  'or (if you are trying to use auto-calculations) add valid ' \
                  'ISO concentrations and volumes to the ISO sheet of ' \
                  'your file, please. Details: %s.' % (above_stock)
            self.add_error(msg)
        elif len(above_crit) > 0:
            above_crit.sort()
            msg = 'Some ISO concentration are larger than the critical ISO ' \
                  'concentration for the referring molecule type. Using ' \
                  'that large concentrations will increase the waste volume ' \
                  'generated during ISO processing. Furthermore, it might ' \
                  'cause concentration inaccuracies when using the BioMek. ' \
                  'The inaccuracies are within a range of 1 percent. ' \
                  'Affected positions: %s.' % (above_crit)
            self.add_warning(msg)

    def _determine_mastermix_support(self):
        """
        Mastermix support requires certain minimum volumes and certain
        relationships between ISO and final concentrations.
        Some experiment types do not support mastermix preparation at all.
        """
        pass

    def __generate_worklists(self):
        """
        Generates the worklists for the mastermix and cell plate preparation
        and attaches them to the experiment design or the design racks.
        """
        generator = ExperimentWorklistGenerator(
                        experiment_design=self._experiment_design,
                        label=self.experiment_metadata.label,
                        source_layout=self._source_layout,
                        scenario=get_experiment_metadata_type(
                                                self.SUPPORTED_EXPERIMENT_TYPE),
                        supports_mastermix=self.supports_mastermix,
                        log=self.log,
                        design_rack_associations=self._design_rack_associations)
        self._experiment_design = generator.get_result()

        if self._experiment_design is None:
            msg = 'Error when trying to generate experiment worklists.'
            self.add_error(msg)

    def _determine_plate_number(self):
        """
        Determines the number of (ISO) plates that must be generated for to
        cover all molecule design pools in the set (floating positions). If the
        set is empty, the number of plates is automatically set to one.
        """
        self.add_debug('Determine number of plates ...')

        if self._pool_set is None:
            self._iso_request.number_plates = 1
        else:
            queued_pools = len(self._pool_set)
            floating_positions = self._source_layout.get_floating_positions()
            number_floatings = len(floating_positions)
            plate_number = round_up(float(queued_pools) / number_floatings, 0)
            self._iso_request.number_plates = int(plate_number)

    def __check_blocked_entities(self):
        """
        Checks whether ISO request and experiment design remain consistent
        (if required).
        """
        if self.__has_isos: self.__check_blocked_iso_request()
        if not self.has_errors() and self.__has_experiment_jobs:
            self.__check_blocked_experiment_design()

    def __check_blocked_iso_request(self):
        """
        If there are already ISOs in the ISO request, the ISO request of
        the existing experiment metadata must not be altered.
        """
        self.add_debug('Check blocked ISO request ...')

        old_iso_request = self.experiment_metadata.iso_request

        changed_attributes = []
        if old_iso_request.number_aliquots != \
                                        self._iso_request.number_aliquots:
            changed_attributes.append('number of aliquots')
        if old_iso_request.plate_set_label != \
                                        self._iso_request.plate_set_label:
            changed_attributes.append('plate set label')

        converter = TransfectionLayoutConverter(log=self.log,
                                    rack_layout=old_iso_request.iso_layout,
                                    check_well_uniqueness=False)
        layout = converter.get_result()
        if layout is None:
            msg = 'Error when trying to convert ISO layout of the existing ' \
                  'ISO request.'
            self.add_error(msg)
        elif not TransfectionLayout.compare_ignoring_untreated(layout,
                                                        self._source_layout):
            changed_attributes.append('ISO layout')

        if len(changed_attributes) > 0:
            msg = 'The current file upload would change some properties of ' \
                  'the ISO request which must not be altered anymore, ' \
                  'because there are already ISOs for this experiment ' \
                  'metadata. Differences: %s. Ask the stock management to ' \
                  'cancel all ISOs or adjust your file, please.' \
                  % (changed_attributes)
            self.add_error(msg)
        else:
            self._iso_request.comment = old_iso_request.comment
            self._iso_request.id = old_iso_request.id

    def __check_blocked_experiment_design(self):
        """
        If there are already experiments in the experiment design, the
        experiment design of the existing metadata must not be altered.
        """
        self.add_debug('Check blocked experiment design ...')


        differences = []
        current_design_racks = self.experiment_metadata.experiment_design.\
                                                                    design_racks
        new_design_racks = self._experiment_design.design_racks
        if not len(current_design_racks) == len(new_design_racks):
            differences.append('different number of design racks')

        trp_map = dict()
        for design_rack in current_design_racks:
            trp_sets = design_rack.layout.tagged_rack_position_sets
            trp_map[design_rack.label] = trp_sets
        for design_rack in new_design_racks:
            if not trp_map.has_key(design_rack.label):
                differences.append('different design rack labels')
                break
            current_sets = trp_map[design_rack.label]
            new_sets = design_rack.layout.tagged_rack_position_sets
            if not len(current_sets) == len(new_sets):
                differences.append('different number of tag sets in ' \
                                   'design rack "%s"' % (design_rack.label))
                continue
            set_map = dict()
            for trp_set in current_sets:
                set_map[trp_set.rack_position_set.hash_value] = trp_set.tags
            for trp_set in new_sets:
                hash_value = trp_set.rack_position_set.hash_value
                if not set_map.has_key(hash_value):
                    differences.append('different rack position sets in ' \
                                       'design rack "%s"' % (design_rack.label))
                    break
                current_tags = set_map[hash_value]
                if not current_tags == trp_set.tags:
                    differences.append('different tags in design rack "%s"' \
                                       % design_rack.label)

        if len(differences) > 0:
            msg = 'The current file upload would change some properties of ' \
                  'the experiment design. The experiment design must not be ' \
                  'altered anymore, because there are already experiments ' \
                  'scheduled. Differences: %s. Adjust your file, please.' \
                  % (differences)
            self.add_error(msg)

    def __look_for_compounds(self):
        """
        Compounds designs have different stock concentrations, thus it might
        be we produce incorrect ISO concentrations.
        """
        compound_stock_concentrations = []
        found_compounds = set()
        default_stock_conc = STOCK_CONCENTRATIONS.COMPOUND_STOCK_CONCENTRATION

        for tf_pos in self._source_layout.working_positions():
            if not tf_pos.is_fixed: continue
            if tf_pos.molecule_design_pool.molecule_type.id \
                                            == MOLECULE_TYPE_IDS.COMPOUND:
                pool_id = tf_pos.molecule_design_pool_id
                if pool_id in found_compounds: continue
                stock_conc = round(tf_pos.stock_concentration, 1)
                info = '%s (%s nM)' % (pool_id, '{0:,}'.format(stock_conc))
                compound_stock_concentrations.append(info)
                found_compounds.add(pool_id)

        if self._pool_set is not None and \
                self._pool_set.molecule_type.id == MOLECULE_TYPE_IDS.COMPOUND:
            for pool in self._pool_set:
                if pool.id in found_compounds: continue
                stock_conc = round(pool.default_stock_concentration \
                                   * CONCENTRATION_CONVERSION_FACTOR, 1)
                info = '%s (%s nM)' % (pool.id, '{0:,}'.format(stock_conc))
                compound_stock_concentrations.append(info)
                found_compounds.add(pool.id)

        if len(compound_stock_concentrations) > 0:
            msg = 'Attention! There are compounds among your molecule design ' \
                  'pools. For compounds, we assume a stock concentration of ' \
                  '%s nM. We have found the following stock concentrations: ' \
                  '%s. Please make sure, that this is the correct stock ' \
                  'concentration for every compound in your experiment since ' \
                  'otherwise you might receive a deviating concentration. ' \
                  'Talk to Michael or Anna, please.' \
                   % ('{0:,}'.format(default_stock_conc),
                      ', '.join(sorted(compound_stock_concentrations)))
            self.add_warning(msg)

    def __update_metadata(self):
        """
        Generates the metadata entity.
        """
        self.add_debug('Generate metadata entity ...')

        if self._iso_request is not None:
            self._iso_request.iso_layout = self._source_layout.\
                            create_merged_rack_layout(self._additional_trps,
                                                      self.requester)
        new_em = ExperimentMetadata(
                    label=self.experiment_metadata.label,
                    ticket_number=self._ticket_number,
                    subproject=self.experiment_metadata.subproject,
                    experiment_design=self._experiment_design,
                    iso_request=self._iso_request,
                    number_replicates=
                            self.experiment_metadata.number_replicates,
                    molecule_design_pool_set=self._pool_set,
                    experiment_metadata_type=\
                            self.experiment_metadata.experiment_metadata_type)
        self.experiment_metadata = new_em


class ExperimentMetadataGeneratorOpti(ExperimentMetadataGenerator):
    """
    An experiment metadata generator for optimisation scenarios.

    **Return Value:** experiment metadata
        (:class:`thelma.models.experiment.ExperimentMetadata`)
    """
    SUPPORTED_EXPERIMENT_TYPE = EXPERIMENT_SCENARIOS.OPTIMISATION

    def __init__(self, stream, experiment_metadata, requester,
                 logging_level=logging.WARNING, add_default_handlers=False):
        """
        Constructor:

        :param stream: The content of the experiment metadata file.

        :param experiment_metadata: The experiment metadata to update.
        :type experiment_metadata:
            :class:`thelma.models.experiment.ExperimentMetadata`

        :param requester: The user uploading the file.
        :type requester: :class:`thelma.models.user.User`

        :param logging_level: the desired minimum log leve l
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *False*
        """
        ExperimentMetadataGenerator.__init__(self, stream=stream,
                                    experiment_metadata=experiment_metadata,
                                    requester=requester,
                                    logging_level=logging_level,
                                    add_default_handlers=add_default_handlers)

        #: The converted layout of each experiment design rack.
        self.__design_rack_layouts = None

    def reset(self):
        """
        Resets all values except for initialisation values.
        """
        ExperimentMetadataGenerator.reset(self)
        self.__design_rack_layouts = None

    def _obtain_iso_request(self):
        """
        Generates the ISO request.
        """
        self.add_debug('Obtain ISO request ...')

        handler = self._create_iso_request_handler()
        self._iso_request = handler.get_result()

        if self._iso_request is None:
            if handler.has_iso_sheet():
                # If there is an ISO sheet and there was an error we quit
                msg = 'There are errors in the ISO sheet.'
                self.add_error(msg)
            else:
                # Otherwise we want to get a layout from the experiment
                # design ...
                msg = 'You did not specify an ISO layout. The system will ' \
                      'try to generate the ISO layout by itself.'
                self.add_warning(msg)

                iso_request = self.__find_iso_layout_and_create_iso_request()
                if iso_request is None:
                    msg = 'Error when trying to create ISO request.'
                    self.add_error(msg)
                self._iso_request = iso_request

        else:
            self._source_layout = handler.get_transfection_layout()
            self._additional_trps = handler.get_additional_trps()

    def __find_iso_layout_and_create_iso_request(self):
        """
        Generates an ISO layout from the experiment design and creates an
        ISO request with it.
        """
        if self._experiment_design is None:
            msg = 'Experiment metadata does not have an experiment design.'
            self.add_error(msg)
            return None

        finder = TransfectionLayoutFinder(log=self.log,
                                    experiment_design=self._experiment_design)
        self._source_layout = finder.get_result()

        if self._source_layout is None:
            msg = 'Could not obtain an ISO source layout from experiment design.'
            self.add_error(msg)
            return None
        else:
            self.__design_rack_layouts = \
                                    finder.get_experiment_transfection_layouts()
            self._additional_trps = dict()
            iso_request = IsoRequest(
                            iso_layout=self._source_layout.create_rack_layout(),
                            requester=self.requester,
                            plate_set_label='%i' % (self._ticket_number),
                            comment='autogenerated layout')
            return iso_request

    def _set_optimem_dilution_factors(self):
        """
        Sets the OptiMem dilution factor for floating and mock positions
        (required for ISO volume and concentration determinations).
        """
        self.add_debug('Set molecule types ...')


        floating_odf = None
        if self._source_layout.floating_molecule_type is not None:
            floating_odf = TransfectionParameters.get_optimem_dilution_factor(
                                    self._source_layout.floating_molecule_type)

        for tf_pos in self._source_layout.working_positions():
            if tf_pos.is_fixed:
                tf_pos.store_optimem_dilution_factor()
            elif tf_pos.is_floating and floating_odf is not None:
                tf_pos.set_optimem_dilution_factor(floating_odf)

        mock_odf = TransfectionParameters.get_layout_mock_optimem_molecule_type(
                                                            self._source_layout)
        for tf_pos in self._source_layout.working_positions():
            if tf_pos.is_mock:
                tf_pos.set_optimem_dilution_factor(mock_odf)


    def _associate_iso_layout_and_design(self):
        """
        Associates the ISO layout with the layouts of the design racks
        (required for the generation of transfer worklists).
        Also determines the capability for mastermix support.
        """
        self.add_debug('Associate ISO and design plates ...')

        associator = WellAssociatorOptimisation(
                            experiment_design=self._experiment_design,
                            design_rack_layouts=self.__design_rack_layouts,
                            source_layout=self._source_layout, log=self.log)
        self._design_rack_associations = associator.get_result()

        if self._design_rack_associations is None:
            msg = 'Error when trying to associate ISO source layout and ' \
                  'design racks.'
            self.add_error(msg)
        else:
            self._source_layout = associator.get_completed_source_layout()
            self._final_concentrations = associator.get_final_concentrations()

    def _determine_mastermix_support(self):
        """
        This is taken over by the :class:`RobotSupportDeterminatorOpti` tool.
        """
        self.add_debug('Determine ISO values ...')

        determinator = RobotSupportDeterminatorOpti(log=self.log,
            source_layout=self._source_layout,
            number_replicates=self.experiment_metadata.number_replicates,
            design_rack_associations=self._design_rack_associations.values())
        self._source_layout = determinator.get_result()

        if self._source_layout is None:
            msg = 'Error when trying to determine mastermix support.'
            self.add_error(msg)
        else:
            self.use_deep_well = determinator.use_deep_well
            self.supports_mastermix = determinator.supports_mastermix
            self.__check_for_ambigous_mastermixes()

    def __check_for_ambigous_mastermixes(self):
        """
        Checks whether all mastermix compositions (corresponds to full
        hashes) are unique.
        """
        ambiguous_positions = dict()
        found_positions = dict()
        for tf_pos in self._source_layout.working_positions():
            if tf_pos.is_empty: continue
            hash_value = tf_pos.hash_full
            if ambiguous_positions.has_key(hash_value):
                add_list_map_element(ambiguous_positions, hash_value,
                                     tf_pos.rack_position.label)
            elif found_positions.has_key(hash_value):
                add_list_map_element(ambiguous_positions, hash_value,
                                     tf_pos.rack_position.label)
                add_list_map_element(ambiguous_positions, hash_value,
                                     found_positions[hash_value])
            else:
                found_positions[hash_value] = tf_pos.rack_position.label

        if len(ambiguous_positions) > 0:
            items = []
            c = 0
            for hash_value in sorted(ambiguous_positions.keys()):
                c += 1
                info_item = 'set %i: positions: %s' % (c,
                            ', '.join(sorted(ambiguous_positions[hash_value])))
                items.append(info_item)
            msg = 'Each position in the ISO layout must have a unique ' \
                  'combination of the following factor levels: molecule ' \
                  'design pool ID, final concentration, reagent name and ' \
                  'reagent dilution factor. The following positions have ' \
                  'duplicate combinatations: %s. Regard that mock and ' \
                  'untreated positions do not have a concentration.' \
                  % (' - '.join(items))
            self.add_error(msg)


class ExperimentMetadataGeneratorScreen(ExperimentMetadataGenerator):
    """
    An experiment metadata generator for screening scenarios.

    **Return Value:** experiment metadata
        (:class:`thelma.models.experiment.ExperimentMetadata`)
    """
    SUPPORTED_EXPERIMENT_TYPE = EXPERIMENT_SCENARIOS.SCREENING

    def __init__(self, stream, experiment_metadata, requester,
                 logging_level=logging.WARNING, add_default_handlers=False):
        """
        Constructor:

        :param stream: The content of the experiment metadata file.

        :param experiment_metadata: The experiment metadata to update.
        :type experiment_metadata:
            :class:`thelma.models.experiment.ExperimentMetadata`

        :param requester: The user uploading the file.
        :type requester: :class:`thelma.models.user.User`

        :param logging_level: the desired minimum log leve l
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *False*
        """
        ExperimentMetadataGenerator.__init__(self, stream=stream,
                                    experiment_metadata=experiment_metadata,
                                    requester=requester,
                                    logging_level=logging_level,
                                    add_default_handlers=add_default_handlers)

        #: The molecule type if the ISO request.
        self.__iso_request_molecule_type = None

        #: The rack sector association data.
        self.__association_data = None
        #: The ISO volume of the handler.
        self.__handler_iso_volume = None

    def reset(self):
        """
        Resets all values except for initialisation values.
        """
        ExperimentMetadataGenerator.reset(self)
        self.__iso_request_molecule_type = None
        self.__handler_iso_volume = None

    def _obtain_iso_request(self):
        """
        Generates the ISO request.
        """
        self.add_debug('Obtain ISO request ...')

        handler = self._create_iso_request_handler()
        self._iso_request = handler.get_result()

        if self._iso_request is None and not handler.has_iso_sheet():
            msg = 'You need to provide an ISO sheet for %s scenarios!' \
                   % (self._scenario_display_name)
            self.add_error(msg)

        elif self._iso_request is None:
            msg = 'Error when trying to generate ISO request.'
            self.add_error(msg)

        else:
            self._source_layout = handler.get_transfection_layout()
            self._additional_trps = handler.get_additional_trps()
            self.__iso_request_molecule_type = handler.get_molecule_type()
            self._iso_request.molecule_type = handler.get_molecule_type()
            self.__association_data = handler.get_association_data()
            self.__handler_iso_volume = handler.get_iso_volume()

    def _check_set_designs(self):
        """
        Commits scenario-specific molecule design set checks.
        """
        floating_mt = self._source_layout.floating_molecule_type
        if not floating_mt == self.__iso_request_molecule_type:
            msg = 'There must not be more than one different molecule types ' \
                  'in a %s experiments. The molecule type of the floating ' \
                  'position samples (%s) and the molecule type of the ' \
                  'controls (%s) do not match!' \
                  % (self._scenario_display_name, floating_mt.name,
                     self.__iso_request_molecule_type.name)
            self.add_error(msg)

    def _set_optimem_dilution_factors(self):
        """
        Sets the OptiMem dilution factor for floating and mock positions
        (required for ISO volume and concentration determinations). The
        Optimem dilution factor (and molecule type) must be the same for all
        positions (compliance with fixed position is tested later).
        """
        self.add_debug('Set molecule types ...')

        optimem_df = TransfectionParameters.get_optimem_dilution_factor(
                                    self._source_layout.floating_molecule_type)
        for tf_pos in self._source_layout.working_positions():
            if tf_pos.is_fixed:
                tf_pos.store_optimem_dilution_factor()
            elif tf_pos.is_mock or tf_pos.is_floating:
                tf_pos.set_optimem_dilution_factor(optimem_df)

    def _associate_iso_layout_and_design(self):
        """
        Screening scenario do only allow for one-to-one associations.
        """
        self._associate_one_to_one()

    def _determine_mastermix_support(self):
        """
        This is taken over by the :class:`RobotSupportDeterminatorScreen` tool.
        """
        self.add_debug('Check ISO volume and concentration ...')

        determinator = RobotSupportDeterminatorScreen(log=self.log,
                source_layout=self._source_layout,
                number_replicates=self.experiment_metadata.number_replicates,
                number_design_racks=len(self._experiment_design.design_racks),
                handler_iso_volume=self.__handler_iso_volume,
                association_data=self.__association_data)
        self._source_layout = determinator.get_result()

        if self._source_layout is None:
            msg = 'Error when trying to determine mastermix support.'
            self.add_error(msg)
        else:
            self.supports_mastermix = determinator.supports_mastermix
            self.use_deep_well = determinator.use_deep_well


class ExperimentMetadataGeneratorLibrary(ExperimentMetadataGenerator):
    """
    An experiment metadata generator for library screening scenarios.

    **Return Value:** experiment metadata
        (:class:`thelma.models.experiment.ExperimentMetadata`)
    """
    SUPPORTED_EXPERIMENT_TYPE = EXPERIMENT_SCENARIOS.LIBRARY

    def __init__(self, stream, experiment_metadata, requester,
                 logging_level=logging.WARNING, add_default_handlers=False):
        """
        Constructor:

        :param stream: The content of the experiment metadata file.

        :param experiment_metadata: The experiment metadata to update.
        :type experiment_metadata:
            :class:`thelma.models.experiment.ExperimentMetadata`

        :param requester: The user uploading the file.
        :type requester: :class:`thelma.models.user.User`

        :param logging_level: the desired minimum log leve l
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *False*
        """
        ExperimentMetadataGenerator.__init__(self, stream=stream,
                                    experiment_metadata=experiment_metadata,
                                    requester=requester,
                                    logging_level=logging_level,
                                    add_default_handlers=add_default_handlers)

        #: The molecule design library used
        #: (:class:`thelma.models.library.MoleculeDesignLibrary`)
        self.__library = None

        #: Since all value except for the pool ID must be the same for all
        #: parameters we pass them as dictionary with the parameter names
        #: as key. Except for the final concentration the values are only
        #: required for reporting.
        self.__parameter_values = None

    def reset(self):
        ExperimentMetadataGenerator.reset(self)
        self.__library = None
        self.__parameter_values = dict()

    def get_library(self):
        """
        Returns the screening library.
        """
        return self._get_additional_value(self.__library)

    def get_parameter_values(self):
        """
        Returns the parameter values (as dictionary with parameter names as keys;
        for reporting).
        """
        return self._get_additional_value(self.__parameter_values)

    def _obtain_iso_request(self):
        """
        Generates the ISO request.
        """
        self.add_debug('Obtain ISO request ...')

        handler = self._create_iso_request_handler()
        self._iso_request = handler.get_result()

        if self._iso_request is None and not handler.has_iso_sheet():
            msg = 'You need to provide an ISO sheet for %s scenarios!' \
                   % (self._scenario_display_name)
            self.add_error(msg)

        elif self._iso_request is None:
            msg = 'Error when trying to generate ISO request.'
            self.add_error(msg)

        else:
            self._source_layout = handler.get_transfection_layout()
            self._additional_trps = handler.get_additional_trps()
            self.__library = handler.get_library()
            self.__parameter_values[
                                TransfectionParameters.FINAL_CONCENTRATION] = \
                                            handler.get_final_concentration()
            self.__parameter_values[
                                TransfectionParameters.REAGENT_NAME] = \
                                            handler.get_reagent_name()
            self.__parameter_values[
                                TransfectionParameters.REAGENT_DIL_FACTOR] = \
                                            handler.get_reagent_dil_factor()

    def _obtain_pool_set(self):
        """
        Library screenings do not allow for floating designs (since the
        designs are already defined by the library).
        """
        handler = ExperimentPoolSetParserHandler(self.stream, self.log)
        pool_set = handler.get_result()

        if not pool_set is None:
            msg = 'There are molecule design pools for floating positions ' \
                  'specified. Floating positions are not allowed for ' \
                  '%s experiments!' % (self._scenario_display_name)
            self.add_error(msg)

    def _set_optimem_dilution_factors(self):
        """
        The OptiMem dilution factor are set by the robot support determinator.
        """
        pass

    def _associate_iso_layout_and_design(self):
        """
        Library screening scenario do only allow for one-to-one associations.
        """
        self._associate_one_to_one()

    def _determine_mastermix_support(self):
        """
        This is taken over by the :class:`RobotSupportDeterminatorLibrary` tool.
        In theory robot support is always allowed. We only need to figure out
        the optimem dilution factor.
        """
        self.add_debug('Check ISO volume and concentration ...')

        final_conc = self.__parameter_values[
                                    TransfectionParameters.FINAL_CONCENTRATION]
        determinator = RobotSupportDeterminatorLibrary(log=self.log,
                source_layout=self._source_layout,
                number_replicates=self.experiment_metadata.number_replicates,
                number_design_racks=len(self._experiment_design.design_racks),
                library=self.__library,
                handler_final_concentration=final_conc)
        self._source_layout = determinator.get_result()

        if self._source_layout is None:
            msg = 'Error when trying to determine mastermix support.'
            self.add_error(msg)
        else:
            self.supports_mastermix = determinator.supports_mastermix
            self.use_deep_well = False
            self.__parameter_values[
                        TransfectionParameters.OPTIMEM_DIL_FACTOR] = \
                                        determinator.get_optimem_dil_factor()

    def _check_iso_concentrations(self):
        """
        We do not need to check the ISO concentration since it is defined
        by the library.
        """
        pass

    def _determine_plate_number(self):
        """
        The plate number is defined by the library.
        """
        self.add_debug('Determine number of plates ...')
        return self.__library.iso_request.number_plates




class ExperimentMetadataGeneratorManual(ExperimentMetadataGenerator):
    """
    An experiment metadata generator for manual optimisation scenarios.

    **Return Value:** experiment metadata
        (:class:`thelma.models.experiment.ExperimentMetadata`)
    """
    SUPPORTED_EXPERIMENT_TYPE = EXPERIMENT_SCENARIOS.MANUAL

    def _obtain_iso_request(self):
        """
        Generates the ISO request.
        """
        self.add_debug('Obtain ISO request ...')

        handler = self._create_iso_request_handler()
        self._iso_request = handler.get_result()

        if self._iso_request is None and not handler.has_iso_sheet():
            msg = 'You need to provide an ISO sheet for %s scenarios!' \
                   % (self._scenario_display_name)
            self.add_error(msg)
        elif self._iso_request is None:
            msg = 'Error when trying to generate ISO request.'
            self.add_error(msg)
        else:
            self._source_layout = handler.get_transfection_layout()
            self._additional_trps = handler.get_additional_trps()
            self.supports_mastermix = False

    def _obtain_pool_set(self):
        """
        Manual optimisation do not allow for floating designs.
        """
        handler = ExperimentPoolSetParserHandler(self.stream, self.log)
        pool_set = handler.get_result()

        if not pool_set is None:
            msg = 'There are molecule design pools for floating positions ' \
                  'specified. Floating positions are not allowed for ' \
                  '%s experiments!' % (self._scenario_display_name)
            self.add_error(msg)

    def _associate_iso_layout_and_design(self):
        """
        Associates the ISO layout with the layouts of the design racks
        (required for the generation of transfer worklists).
        Also determines the capability for mastermix support.
        """
        self.add_debug('Associate ISO and design plates ...')

        associator = WellAssociatorManual(log=self.log,
                                    experiment_design=self._experiment_design,
                                    source_layout=self._source_layout)
        self._design_rack_associations = associator.get_result()

        if self._design_rack_associations is None:
            msg = 'Error when trying to associate ISO layout and design rack ' \
                  'layouts.'
            self.add_error(msg)
        else:
            self._final_concentrations = associator.get_final_concentrations()
            self.__check_iso_volumes()

    def __check_iso_volumes(self):
        """
        Checks whether all ISO volumes are large enough to be pipetted
        with the CyBio.
        """
        too_less_volume = []
        for rack_pos, tf_pos in self._source_layout.iterpositions():
            if tf_pos.iso_volume < MIN_CYBIO_TRANSFER_VOLUME:
                too_less_volume.append(rack_pos.label)

        if len(too_less_volume) > 0:
            too_less_volume.sort()
            msg = 'The minimum ISO volume you can order is %s ul. You have ' \
                  'ordered a smaller amount for the following rack ' \
                  'positions: %s.' \
                  % (get_trimmed_string(MIN_CYBIO_TRANSFER_VOLUME),
                     too_less_volume)
            self.add_error(msg)

    def _determine_plate_number(self):
        """
        Determines the number of (ISO preparation) plates - since there are
        no floatings the number is always 1.
        """
        self._iso_request.number_plates = 1


class ExperimentMetadataGeneratorIsoless(ExperimentMetadataGenerator):
    """
    An experiment metadata generator for ISO-less scenarios.

    **Return Value:** experiment metadata
        (:class:`thelma.models.experiment.ExperimentMetadata`)
    """
    SUPPORTED_EXPERIMENT_TYPE = EXPERIMENT_SCENARIOS.ISO_LESS

    def _obtain_iso_request(self):
        """
        There are no ISO requests for ISO-less experiment scenarios.
        """
        pass


#: Lookup storing the generator classes for each experiment type.
_GENERATOR_CLASSES = {
            EXPERIMENT_SCENARIOS.OPTIMISATION : ExperimentMetadataGeneratorOpti,
            EXPERIMENT_SCENARIOS.SCREENING : ExperimentMetadataGeneratorScreen,
            EXPERIMENT_SCENARIOS.LIBRARY : ExperimentMetadataGeneratorLibrary,
            EXPERIMENT_SCENARIOS.MANUAL : ExperimentMetadataGeneratorManual,
            EXPERIMENT_SCENARIOS.ISO_LESS : ExperimentMetadataGeneratorIsoless
                     }


class RobotSupportDeterminator(BaseAutomationTool):
    """
    Determines whether the ISO volumes and concentrations of a tool
    support mastermix preparation via robot and adds the missing values
    to the source layout.

    If there is no robot support the layout is return unaltered.

    **Return Value:** updated source layout
    """
    NAME = 'Robot Support Determinator'

    def __init__(self, log, source_layout, number_replicates):
        """
        Constructor:

        :param log: The ThelmaLog to write into.
        :type log: :class:`thelma.ThelmaLog`

        :param source_layout: The transfection layout storing the ISO plate
            data.
        :type source_layout: :class:`TransfectionLayout`

        :param number_replicates: The number of inter-plate replicates
            for the experiment metadata.
        :type number_replicates: :class:`int`
        """
        BaseAutomationTool.__init__(self, log=log)

        #: The transfection layout storing the ISO plate data.
        self.source_layout = source_layout
        #: The number of inter-plate replicates.
        self.number_replicates = number_replicates

        #: States whether it is possible to use the BioMek for the mastermix
        #: preparation.
        self.supports_mastermix = None
        #: Use deep well plates. Specifies whether one needs to use
        #: deep well plates for the ISO plate.
        self.use_deep_well = None

        #: The reservoir specs of the ISO plate.
        self._iso_reservoir_specs = None
        #: Checks whether the ISO volumes support mastermix preparation.
        self._has_compatible_volumes = None
        #: Checks whether the ISO concentration support mastermix preparation.
        self._has_compatible_concentrations = None

        #: Does the sourcce layout have ISO concentration values?
        self._layout_has_iso_concentrations = None
        #: Stores rack positions and concentrations for contration updates.
        self._new_concentration_values = None

    def reset(self):
        BaseAutomationTool.reset(self)
        self.supports_mastermix = None
        self.use_deep_well = None
        self._iso_reservoir_specs = None
        self._has_compatible_concentrations = True
        self._has_compatible_volumes = True
        self._layout_has_iso_concentrations = None
        self._new_concentration_values = dict()

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Run ISO value determinator ...')

        self._check_input()
        if not self.has_errors(): self.__init_iso_reservoir_specs()
        if not self.has_errors(): self._check_iso_concentrations()
        if not self.has_errors(): self._check_iso_volumes()
        if not self.has_errors(): self._complete_layout()
        if not self.has_errors():
            self.return_value = self.source_layout
            self.add_info('Run completed.')

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input values ...')

        self._check_input_class('source layout', self.source_layout,
                                TransfectionLayout)
        self._check_input_class('number of replicates', self.number_replicates,
                                int)

    def __init_iso_reservoir_specs(self):
        """
        Initialises the reservoir specs for the ISO plate (used for mastermix
        support).
        """
        self.add_debug('Initialise ISO reservoir specs ...')
        max_target_count = self._get_max_target_count()

        if self.source_layout.shape.name == RACK_SHAPE_NAMES.SHAPE_384:
            self._iso_reservoir_specs = get_reservoir_specs_standard_384()

        else:
            self.use_deep_well = False
            std_96 = get_reservoir_specs_standard_96()
            max_vol = std_96.max_volume * VOLUME_CONVERSION_FACTOR
            if TransfectionParameters.requires_deepwell(max_target_count,
                                                        self.number_replicates):
                self.use_deep_well = True
            for tf_pos in self.source_layout.working_positions():
                if not tf_pos.iso_volume is None:
                    if tf_pos.iso_volume > max_vol:
                        self.use_deep_well = True
                        break

            if self.use_deep_well:
                self._iso_reservoir_specs = get_reservoir_specs_deep_96()
            else:
                self._iso_reservoir_specs = std_96

    def _get_max_target_count(self):
        """
        Determines the highest number of target wells for a single source well
        (without replicates).
        """
        self.add_error('Abstract method: _get_max_target_count()')

    def _check_iso_concentrations(self):
        """
        Checks whether there are ISO concentrations and whether there are
        compatible.
        """
        self.add_debug('Check ISO concentrations ...')

        missing_iso_conc = []
        self._layout_has_iso_concentrations = \
                                self.source_layout.has_iso_concentrations()

        if self._layout_has_iso_concentrations:

            for rack_pos, tf_pos in self.source_layout.iterpositions():
                if tf_pos.is_mock or tf_pos.is_untreated: continue
                iso_conc = tf_pos.iso_concentration
                expected_iso_conc = tf_pos.final_concentration \
                                    * tf_pos.get_total_dilution_factor()
                if iso_conc is None:
                    missing_iso_conc.append(rack_pos.label)
                    continue
                elif not iso_conc == expected_iso_conc:
                    self._has_compatible_concentrations = False

        else:
            for rack_pos, tf_pos in self.source_layout.iterpositions():
                if tf_pos.is_mock or tf_pos.is_untreated: continue
                iso_conc = tf_pos.final_concentration \
                           * tf_pos.get_total_dilution_factor()
                self._new_concentration_values[rack_pos] = iso_conc

        if len(missing_iso_conc) > 0:
            msg = 'Some layout positions have a final concentration but no ' \
                  'ISO concentration. Specify either all ISO concentration ' \
                  'or none, please. Mock positions can be omitted.'
            self.add_error(msg)
        elif not self._has_compatible_concentrations:
            msg = 'The concentrations you have ordered to not allow ' \
                  'robot-supported mastermix preparation. Worklist ' \
                  'support is disabled now.'
            self.add_warning(msg)

    def _check_iso_volumes(self):
        """
        Checks whether ISO volumes are valid and sufficient.
        """
        self.add_debug('Check ISO volumes ...')

        has_iso_volumes = self.source_layout.has_iso_volumes()
        if not has_iso_volumes and not self._has_compatible_concentrations:
            msg = 'The concentrations in your metadata file do not allow for ' \
                  'robot support. In such a case, you have to provide ISO ' \
                  'volumes. Please add ISO volumes or adjust your ISO ' \
                  'concentrations and re-upload your file.'
            self.add_error(msg)
        else:
            self._compare_iso_volumes(has_iso_volumes)

    def _compare_iso_volumes(self, has_iso_volumes): #pylint: disable=W0613
        """
        Determines the required ISO volumes and compares them against the found
        one (if applicable).
        This method also has to make sure, that any ordered voluems are not
        not below the minimum volume.
        """
        self.add_error('Abstract method: _determine_iso_volumes()')

    def _complete_layout(self):
        """
        Summarises the results, updates the layouts and launches the deep
        well warning (if applicable).
        """
        self.add_debug('Summarise results ...')

        self.supports_mastermix = self._has_compatible_volumes and \
                                  self._has_compatible_concentrations
        if self.supports_mastermix:
            self._replace_concentrations()
            self._replace_volumes()
        elif not self._has_compatible_volumes and \
                                    not self._layout_has_iso_concentrations:
            msg = 'The volumes in your metadata file do not allow for ' \
                  'robot support. In such a case, you have to provide ISO ' \
                  'concentrations. Please add ISO concentration or adjust ' \
                  'your ISO volumes and re-upload your file.'
            self.add_error(msg)

        if not self.has_errors():
            std_96 = get_reservoir_specs_standard_96()
            if self.supports_mastermix and self.use_deep_well:
                msg = 'Use deep well plates for the ISO plate. The volumes ' \
                      'for the mastermix preparation will exceed %s ul.' \
                      % (get_trimmed_string(
                                std_96.max_volume * VOLUME_CONVERSION_FACTOR))
                self.add_warning(msg)
            elif self.use_deep_well:
                msg = 'Use deep well plates for the ISO plate. The ordered ' \
                      'ISO volumes exceed %s ul.' % (get_trimmed_string(
                                std_96.max_volume * VOLUME_CONVERSION_FACTOR))
                self.add_warning(msg)

    def _replace_concentrations(self):
        """
        Replaces the ISO concentration in the layout by the new values stored
        in :attr:`__new_concentration_values`.
        """
        self.add_debug('Update ISO concentrations ...')

        for rack_pos, new_conc in self._new_concentration_values.iteritems():
            tf_pos = self.source_layout.get_working_position(rack_pos)
            tf_pos.iso_concentration = new_conc

    def _replace_volumes(self):
        """
        Replaces the ISO volumes in the layout by the new one.
        """
        self.add_error('Abstract method: _replace_volumes()')


class RobotSupportDeterminatorOpti(RobotSupportDeterminator):
    """
    The determiner for optimisations requires the result of the well
    assignments (see :class:`WellAssociatorOptimisation`).
    Each source position is treated separately.

    **Return Value:** updated source layout
    """
    def __init__(self, log, source_layout, number_replicates,
                 design_rack_associations):
        """
        Constructor:

        :param log: The ThelmaLog to write into.
        :type log: :class:`thelma.ThelmaLog`

        :param source_layout: The transfection layout storing the ISO plate
            data.
        :type source_layout: :class:`TransfectionLayout`

        :param number_replicates: The number of inter-plate replicates
            for the experiment metadata.
        :type number_replicates: :class:`int`

        :param design_rack_associations: The completed source layout for
            each design rack containing well assignments.
        :type design_rack_associations: list of transfection layouts
        """
        RobotSupportDeterminator.__init__(self, log=log,
                                      source_layout=source_layout,
                                      number_replicates=number_replicates)

        #: The transfection layout storing the ISO plate data.
        self.source_layout = source_layout
        #: The number of inter-plate replicates.
        self.number_replicates = number_replicates

        #: The transfection layout for each design rack.
        self.design_rack_associations = design_rack_associations

        #: The number of target wells for each source position.
        self.__target_count_map = None
        #: Stores rack positions and volumes for volume updates.
        self.__new_volumes_values = None

    def reset(self):
        RobotSupportDeterminator.reset(self)
        self.__target_count_map = dict()
        self.__new_volumes_values = dict()

    def _check_input(self):
        RobotSupportDeterminator._check_input(self)
        if self._check_input_class('design rack association list',
                                   self.design_rack_associations, list):
            for layout in self.design_rack_associations:
                if not self._check_input_class('design rack layout', layout,
                                               TransfectionLayout): break

    def _get_max_target_count(self):
        """
        Determines the highest number of target wells for a single source well.
        The target counts themselves are stored in the
        :attr:`__target_count_map`.
        """
        for rack_pos in self.source_layout.get_positions():
            target_well_count = 0
            for tf_layout in self.design_rack_associations:
                tf_pos = tf_layout.get_working_position(rack_pos)
                target_well_count += len(tf_pos.cell_plate_positions)
            self.__target_count_map[rack_pos] = target_well_count

        return max(self.__target_count_map.values())

    def _compare_iso_volumes(self, has_iso_volumes): #pylint: disable=W0613
        """
        Determines the required ISO volumes and compares them against the found
        one (if applicable).
        This method also has to make sure, that any ordered voluems are not
        not below the minimum volume.
        """
        volume_too_small = []
        volume_not_sufficient = []

        for rack_pos, tf_pos in self.source_layout.iterpositions():

            expected_volume = TransfectionParameters.calculate_iso_volume(
                number_target_wells=self.__target_count_map[rack_pos],
                number_replicates=self.number_replicates, use_cybio=False,
                iso_reservoir_spec=self._iso_reservoir_specs,
                optimem_dil_factor=tf_pos.optimem_dil_factor)
            iso_vol = tf_pos.iso_volume
            if iso_vol is None:
                self.__new_volumes_values[rack_pos] = expected_volume
            elif iso_vol < MIN_BIOMEK_TRANSFER_VOLUME:
                volume_too_small.append(str(rack_pos.label))
            elif (iso_vol - expected_volume) < -0.01:
                info = '%s (found: %.1f ul, required: %.1f ul)' \
                        % (rack_pos.label, iso_vol, expected_volume)
                volume_not_sufficient.append(info)
                self._has_compatible_volumes = False

        if len(volume_too_small) > 0:
            volume_too_small.sort()
            msg = 'The minimum ISO volume you can order for optimisations ' \
                  'is %s ul. If you want to order less volume, switch the ' \
                  'experiment type to "%s", please. Positions with invalid ' \
                  'volume: %s.' \
                  % (get_trimmed_string(MIN_BIOMEK_TRANSFER_VOLUME),
                     get_experiment_type_manual_optimisation().display_name,
                     ', '.join(sorted(volume_too_small)))
            self.add_error(msg)

        if len(volume_not_sufficient) > 0:
            volume_not_sufficient.sort()
            msg = 'If you want to prepare a standard mastermix (incl. robot ' \
                  'support) you need to order a certain volume of molecule ' \
                  'design pool. The following volumes are not sufficient ' \
                  'to provide mastermix for all target wells in the cell ' \
                  'plate: %s. Robot support is disabled now. If you want ' \
                  'robot support for your experiment, increase the ISO ' \
                  'volume and re-upload the file, please.' \
                   % (volume_not_sufficient)
            self.add_warning(msg)

        if self._has_compatible_volumes: self.__check_deep_well_usage()

    def __check_deep_well_usage(self):
        """
        If deep well is not used so far and the ISO volumes have been adjusted,
        we need to recheck the deep well requirement.
        """
        if self._iso_reservoir_specs.name == RESERVOIR_SPECS_NAMES.STANDARD_96:
            max_vol = self._iso_reservoir_specs.max_volume \
                      * VOLUME_CONVERSION_FACTOR
            for rack_pos, tf_pos in self.source_layout.iterpositions():
                iso_vol = tf_pos.iso_volume
                if self.__new_volumes_values.has_key(rack_pos):
                    iso_vol = self.__new_volumes_values[rack_pos]
                mm_volume = TransfectionParameters.\
                                calculate_complete_volume(iso_vol,
                                        tf_pos.optimem_dil_factor)
                if mm_volume > max_vol:
                    self.use_deep_well = True
                    self._iso_reservoir_specs = \
                                            get_reservoir_specs_deep_96()
                    break

    def _replace_volumes(self):
        """
        Replaces the ISO volume in the layout by the new values stored
        in :attr:`_new_volume_values`.
        """
        self.add_debug('Update ISO volumes ...')

        for rack_pos, new_volume in self.__new_volumes_values.iteritems():
            tf_pos = self.source_layout.get_working_position(rack_pos)
            tf_pos.iso_volume = new_volume


class RobotSupportDeterminatorScreen(RobotSupportDeterminator):
    """
    For concentrations the determiner works position-based. For the ISO volume,
    there is only one value for the whole layout.

    **Return Value:** updated source layout
    """

    def __init__(self, log, source_layout, number_replicates,
                 number_design_racks, handler_iso_volume,
                 association_data):
        """
        Constructor:

        :param log: The ThelmaLog to write into.
        :type log: :class:`thelma.ThelmaLog`

        :param source_layout: The transfection layout storing the ISO plate
            data.
        :type source_layout: :class:`TransfectionLayout`

        :param number_replicates: The number of inter-plate replicates
            for the experiment metadata.
        :type number_replicates: :class:`int`

        :param number_design_racks: The number of design racks.
        :type number_design_racks: :class:`int`

        :param handler_iso_volume: The ISO volume parsed from the ISO request
            parser handler.
        :type handler_iso_volume: :class:`float` (positive number).

        :param association_data: The IsoAssociation data (only for 384-well
            layouts).
        :type association_data: :class:`IsoAssociationData`
        """
        RobotSupportDeterminator.__init__(self, log=log,
                                      source_layout=source_layout,
                                      number_replicates=number_replicates)

        #: The number of design racks.
        self.number_design_racks = number_design_racks
        #: The ISO volume from the ISO request parser handler.
        self.handler_iso_volume = handler_iso_volume
        #: The IsoAssociation data (only for 384-well layouts).
        self.association_data = association_data

        #: The final ISO volume.
        self.__iso_volume = None
        #: The ISO concentration for each rack sector (384-well layouts only).
        self.__iso_concentrations = None

        #: The OptiMem dilution factor for the layout (must be the same
        #: for all positions).
        self.__optimem_df = None

    def reset(self):
        RobotSupportDeterminator.reset(self)
        self.__iso_volume = None
        self.__iso_concentrations = dict()
        self.__optimem_df = None

    def _check_input(self):
        RobotSupportDeterminator._check_input(self)

        self._check_input_class('number of design racks',
                                self.number_design_racks, int)

        if not self.handler_iso_volume is None:
            if not is_valid_number(self.handler_iso_volume):
                msg = 'The handler must be a positive number (obtained: %s).' \
                      % (self.handler_iso_volume)
                self.add_error(msg)
            else:
                self.handler_iso_volume = float(self.handler_iso_volume)

        if not self.has_errors() and \
                 not self.source_layout.shape.name == RACK_SHAPE_NAMES.SHAPE_96:
            self._check_input_class('association data', self.association_data,
                                    TransfectionAssociationData)

    def _get_max_target_count(self):
        """
        Screening position are transferred with the CyBio, that means
        they always have only one target position per cell plate
        (relicates are not regarded).
        """
        return self.number_design_racks

    def _check_iso_concentrations(self):
        """
        For 96-well layouts the determination is position based (we can used
        the superclass function). In case of 384-well layouts, the determination
        works on rack sectors (:attr:`association_data`).
        """
        self.__optimem_df = TransfectionParameters.get_optimem_dilution_factor(
                                    self.source_layout.floating_molecule_type)

        if self.source_layout.shape.name == RACK_SHAPE_NAMES.SHAPE_96:
            RobotSupportDeterminator._check_iso_concentrations(self)
        else:
            self.__check_sector_iso_concentration()

    def __check_sector_iso_concentration(self):
        """
        Uses the value determiner (if there are values in the sheet) or
        calculates them. ISO concentrations are mapped onto sector indices.
        """
        self.add_debug('Get ISO concentration ...')

        total_df = TransfectionParameters.get_total_dilution_factor(
                                    optimem_dilution_factor=self.__optimem_df)

        self._layout_has_iso_concentrations = \
                                    self.source_layout.has_iso_concentrations()

        if self._layout_has_iso_concentrations:
            self.__iso_concentrations = self.association_data.iso_concentrations
            for sector_index, final_conc in self.association_data.\
                                            sector_concentrations.iteritems():
                if final_conc is None: continue
                expected_iso_conc = final_conc * total_df
                if not expected_iso_conc == self.__iso_concentrations[
                                                                sector_index]:
                    self._has_compatible_concentrations = False
                    msg = 'The concentrations you have ordered to not allow ' \
                          'robot-supported mastermix preparation. Worklist ' \
                          'support is disabled now.'
                    self.add_warning(msg)
                    break

        else:
            for sector_index, final_conc in self.association_data.\
                                            sector_concentrations.iteritems():
                if final_conc is None:
                    iso_conc = None
                else:
                    iso_conc = final_conc * total_df
                self.__iso_concentrations[sector_index] = iso_conc

    def _compare_iso_volumes(self, has_iso_volumes): #pylint: disable=W0613
        """
        Determines the required ISO volume and compares them against the
        provided by the handler (if applicable).
        This method also has to make sure, that any ordered voluems are not
        not below the minimum volume.
        """
        required_volume = TransfectionParameters.calculate_iso_volume(
                            number_target_wells=self.number_design_racks,
                            number_replicates=self.number_replicates,
                            iso_reservoir_spec=self._iso_reservoir_specs,
                            optimem_dil_factor=self.__optimem_df,
                            use_cybio=True)

        if self.handler_iso_volume is None:
            iso_volume = max(MIN_CYBIO_TRANSFER_VOLUME, required_volume)
        else:
            if self.handler_iso_volume < MIN_CYBIO_TRANSFER_VOLUME:
                msg = 'The minimum ISO volume you can order is %i ul. ' \
                      'You ordered %.1f ul.' \
                       % (MIN_CYBIO_TRANSFER_VOLUME, self.handler_iso_volume)
                self.add_error(msg)
            else:
                iso_volume = self.handler_iso_volume

        if not self.has_errors():
            self.__iso_volume = self.__check_aliquot_dilution_compatibility(
                                                                 iso_volume)

        if not self.has_errors() and not self.handler_iso_volume is None:
            if (self.__iso_volume - required_volume) < -0.01:
                msg = 'If you want to prepare a standard mastermix (incl. ' \
                      'robot support) you need to order at least %s ul ' \
                      '(you ordered: %s ul). Robot support is disabled now. ' \
                      'If you want robot support for your experiment, ' \
                      'increase the ISO volume and re-upload the file, please.' \
                      % (get_trimmed_string(required_volume),
                         get_trimmed_string(self.handler_iso_volume))
                self.add_warning(msg)
                self._has_compatible_volumes = False

        if not self.has_errors and self._has_compatible_volumes:
            self.__check_deep_well_usage()

    def __check_aliquot_dilution_compatibility(self, iso_volume):
        """
        In case of 96-well layout we do not need to check anything.

        For 384-well layouts we need to check whether there is a dilution
        required between preparation plate and aliquot plate and whether the
        ISO volume is sufficient large for the dilution.
        """
        if self.source_layout.shape.name == RACK_SHAPE_NAMES.SHAPE_96:
            return iso_volume

        aliquot_dil_factor = 1
        max_dil_factor = PrepIsoParameters.MAX_DILUTION_FACTOR_CYBIO
        stock_conc = get_default_stock_concentration(
                                    self.source_layout.floating_molecule_type)

        parent_concentrations = set()
        for sector_index, parent_sector in self.association_data.\
                                           parent_sectors.iteritems():
            if not parent_sector is None: continue
            iso_conc = self.__iso_concentrations[sector_index]
            parent_concentrations.add(iso_conc)

        while aliquot_dil_factor < max_dil_factor:
            increment = False
            for iso_conc in parent_concentrations:
                df = stock_conc / (iso_conc * aliquot_dil_factor)
                if df > max_dil_factor: increment = True
            if increment:
                aliquot_dil_factor += 1
                continue
            break

        if aliquot_dil_factor == 1:
            return iso_volume
        else:
            don_vol = iso_volume / aliquot_dil_factor
            buff_vol = iso_volume - don_vol
            adjusted = False

            if don_vol < MIN_CYBIO_TRANSFER_VOLUME:
                don_vol = MIN_CYBIO_TRANSFER_VOLUME
                buff_vol = MIN_CYBIO_TRANSFER_VOLUME * (aliquot_dil_factor - 1)
                adjusted = True
            # The buffer volume is always at least as big as the donation volume
            # because the dilution factor 2 at minimum.

            if adjusted:
                new_iso_volume = don_vol + buff_vol
                msg = 'The ISO volume has to be increased to %.1f ul, ' \
                      'because the requested ISO concentration is so low ' \
                      'that that it requires a larger dilution volume. ' \
                      'Assumed minimum transfer volume for the CyBio: %i ul. ' \
                       % (new_iso_volume, MIN_CYBIO_TRANSFER_VOLUME)
                self.add_warning(msg)
                return new_iso_volume
            else:
                return iso_volume

    def __check_deep_well_usage(self):
        """
        If deep well is not used so far and the ISO volumes have been adjusted,
        we need to recheck the deep well requirement.
        """
        if self.source_layout.shape.name == RACK_SHAPE_NAMES.SHAPE_96:
            std_96 = get_reservoir_specs_standard_96()
            max_volume = std_96.max_volume * VOLUME_CONVERSION_FACTOR
            complete_volume = TransfectionParameters.calculate_complete_volume(
                                        self.__iso_volume, self.__optimem_df)
            if complete_volume > max_volume:
                self.use_deep_well = True

    def _replace_concentrations(self):
        """
        For 96-well layouts the determination is position based (we can used
        the superclass function). In case of 384-well layouts, the determination
        works on rack sector.
        """
        if self.source_layout.shape.name == RACK_SHAPE_NAMES.SHAPE_96:
            RobotSupportDeterminator._replace_concentrations(self)
        else:
            quad_iter = QuadrantIterator(self.association_data.number_sectors)
            for quadrant_wps in quad_iter.get_all_quadrants(self.source_layout):
                for sector_index, tf_pos in quadrant_wps.iteritems():
                    if tf_pos is None: continue
                    if tf_pos.is_mock or tf_pos.is_untreated: continue
                    iso_conc = self.__iso_concentrations[sector_index]
                    tf_pos.iso_concentration = iso_conc

    def _replace_volumes(self):
        """
        Replaces the ISO volumes in the layout by :attr:`__iso_volume`.
        """
        for tf_pos in self.source_layout.working_positions():
            if tf_pos.is_untreated: continue
            tf_pos.iso_volume = self.__iso_volume


class RobotSupportDeterminatorLibrary(RobotSupportDeterminator):
    """
    There is only one ISO concentration, ISO volume and OptiMem dilution factor
    for the layout. ISO concentration and ISO volume are defined by the library.
    The OptiMem dilution factor depends on the final concentration.

    **Return Value:** updated source layout
    """

    #: The minimum OptiMem dilution factor allowed for library screenings.
    MIN_OPTIMEM_DILUTION_FACTOR = 3

    def __init__(self, log, source_layout, number_replicates,
                 number_design_racks, library, handler_final_concentration):
        """
        Constructor:

        :param log: The ThelmaLog to write into.
        :type log: :class:`thelma.ThelmaLog`

        :param source_layout: The transfection layout storing the ISO plate
            data.
        :type source_layout: :class:`TransfectionLayout`

        :param number_replicates: The number of inter-plate replicates
            for the experiment metadata.
        :type number_replicates: :class:`int`

        :param number_design_racks: The number of design racks.
        :type number_design_racks: :class:`int`

        :param library: The molecule design library to be screened.
        :type library: class:`thelma.models.library.MoleculeDesignLibrary`.

        :param handler_final_concentration: The final concentration parsed
            from the ISO request parser handler.
        :type handler_final_concentration: :class:`float` (positive number).
        """
        RobotSupportDeterminator.__init__(self, log=log,
                                      source_layout=source_layout,
                                      number_replicates=number_replicates)

        #: The number of design racks.
        self.number_design_racks = number_design_racks
        #: The final concentration from the ISO request parser handler.
        self.handler_final_conc = handler_final_concentration
        #: The molecule design library to be screened.
        self.library = library

        #: The ISO volume for the library plates.
        self.__iso_volume = None
        #: The optimem dilution factor (must be the same for all positions).
        self.__optimem_dil_factor = None

    def reset(self):
        RobotSupportDeterminator.reset(self)
        self.__optimem_dil_factor = None

    def get_optimem_dil_factor(self):
        """
        Returns the determined OptiMem dilution factor.
        """
        return self._get_additional_value(self.__optimem_dil_factor)

    def _check_input(self):
        RobotSupportDeterminator._check_input(self)

        self._check_input_class('molecule design library', self.library,
                                MoleculeDesignLibrary)
        self._check_input_class('number of design racks',
                                self.number_design_racks, int)

        if not self.handler_final_conc is None:
            if not is_valid_number(self.handler_final_conc):
                msg = 'The final concentration must be a positive number ' \
                      '(obtained: %s).' % (self.handler_final_conc)
                self.add_error(msg)
            else:
                self.handler_final_conc = float(self.handler_final_conc)

    def _get_max_target_count(self):
        """
        Screening position are transferred with the CyBio, that means
        they always have only one target position per cell plate
        (relicates are not regarded).
        """
        return self.number_design_racks

    def _check_iso_concentrations(self):
        """
        The ISO concentrations is checked by the library and does not need
        to be checked. Instead we need to calculate the OptiMem dilution
        factor.
        """
        self.add_debug('Check ISO concentrations ...')

        iso_conc = self.library.final_concentration \
                   * CONCENTRATION_CONVERSION_FACTOR
        self.__iso_volume = self.library.final_volume * VOLUME_CONVERSION_FACTOR
        non_optimem_df = TransfectionParameters.REAGENT_MM_DILUTION_FACTOR \
                         * TransfectionParameters.CELL_DILUTION_FACTOR
        max_volume = self._iso_reservoir_specs.max_volume \
                     * VOLUME_CONVERSION_FACTOR
        max_optimem_df = max_volume / (self.__iso_volume \
                            * TransfectionParameters.REAGENT_MM_DILUTION_FACTOR)
                # dilution with cell suspension takes place in another plate

        total_df = iso_conc / self.handler_final_conc
        required_df = total_df / non_optimem_df
        if required_df < self.MIN_OPTIMEM_DILUTION_FACTOR:
            msg = 'The final concentration you have ordered is too large. ' \
                  'It requires an OptiMem dilution by the factor %.2f. The ' \
                  'allowed minimum dilution factor is %i. Please increase ' \
                  'the final concentration.' \
                  % (required_df, self.MIN_OPTIMEM_DILUTION_FACTOR)
            self.add_error(msg)
        else:
            # We still need to check whether the volume would be sufficient
            # but this is done later in the check volume part.
            self.__optimem_dil_factor = round(required_df, 1)
            iso_conc = round(iso_conc, 1)
            optimem_df = round(required_df, 1)
            for tf_pos in self.source_layout.working_positions():
                if tf_pos.is_untreated: continue
                tf_pos.set_optimem_dilution_factor(optimem_df)
                if tf_pos.is_mock: continue
                tf_pos.iso_concentration = iso_conc

        if required_df > max_optimem_df:
            msg = 'The final concentration you have ordered is too small ' \
                  'for the mastermix to be prepared in the source plate (it ' \
                  'requires an OptiMem dilution by the factor %.2f - the ' \
                  'allowed maximum dilution factor for robot support is ' \
                  '%.2f). Robot support for mastermix preparation is disabled ' \
                  'now. If you want robot support, increase the final ' \
                  'concentration, please.' % (required_df, max_optimem_df)
            self.add_warning(msg)
            self._has_compatible_concentrations = False

    def _check_iso_volumes(self):
        """
        The ISO volume is defined by the library. We need to make sure
        it is sufficient to provide mastermix for all experiment racks.
        """
        self.add_debug('Check ISO volumes ...')

        # We do this step by step to regard the rounding
        optimem_vol = self.__iso_volume * (self.__optimem_dil_factor - 1)
        optimem_vol = round(optimem_vol, 1)
        combined_vol = optimem_vol + self.__iso_volume
        mastermix_vol = combined_vol \
                        * TransfectionParameters.REAGENT_MM_DILUTION_FACTOR
        dead_vol = self._iso_reservoir_specs.min_dead_volume \
                   * VOLUME_CONVERSION_FACTOR
        available_vol = mastermix_vol - dead_vol

        required_vol = self.number_design_racks * self.number_replicates \
                       * TransfectionParameters.TRANSFER_VOLUME
        if required_vol > available_vol:
            msg = 'Currently, the mastermix in the source plate would not ' \
                  'provide enough volume for all experiment cell plates ' \
                  '(required volume: %.1f ul, available (excl. dead volume): ' \
                  '%.2f ul). Reduce the number of replicates, the number of ' \
                  'design racks or the final concentration, please.' \
                  % (required_vol, available_vol)
            self.add_error(msg)
        else:
            # The ISO volume is defined by the library and needs to be added
            # in any case.
            iso_vol = int(self.__iso_volume)
            for tf_pos in self.source_layout.working_positions():
                if tf_pos.is_untreated: continue
                tf_pos.iso_volume = iso_vol

    def _complete_layout(self):
        """
        The values habe already been added before, because they need to be
        set even without robot support. We only need to define, whether
        we offer mastermix support.
        """
        self.supports_mastermix = self._has_compatible_volumes and \
                                  self._has_compatible_concentrations


class WellAssociator(BaseAutomationTool):
    """
    Finds the source well for each well in an design rack layout. The outcome
    is stored in a map.

    **Return Value:** transfection layout incl. associations for each design
        rack (as dict)
    """

    NAME = 'Well Associator'

    def __init__(self, experiment_design, source_layout, log,
                 design_rack_layouts=None):
        """
        Constructor:

        :param experiment_design: The experiment design containing the
            design racks.
        :type experiment_design:
            :class:`thelma.models.experiment.ExperimentDesign`

        :param source_layout: The transfection layout storing the ISO plate
            data.
        :type source_layout: :class:`TransfectionLayout`

        :param log: The ThelmaLog to write into.
        :type log: :class:`thelma.ThelmaLog`

        :param design_rack_layouts: The transfection layout for each design
            rack (optional, saves duplicate conversion).
        :type design_rack_layout: transfection layouts mapped onto design
            rack labels
        :default design_rack_layouts: *None*
        """
        BaseAutomationTool.__init__(self, log=log)

        #: The experiment design containing the design racks.
        self.experiment_design = experiment_design
        #: The transfection layout storing the ISO plate data.
        self.source_layout = source_layout
        #: The transfection layout for each design rack.
        self.design_rack_layouts = design_rack_layouts

        #: The source layout with the cell plate positions for each design rack.
        self._association_layouts = None
        #: Stores the source data required for association.
        self._source_data_map = None

        #: Stores the final concentration for each well in each design rack
        #: (done here because it is more convenient to use transfection layouts
        #: and the transfection layouts are not passed back to the generator).
        self.__final_concentrations = None

    def reset(self):
        """
        Resets all values except for initialisation values.
        """
        BaseAutomationTool.reset(self)
        self._association_layouts = dict()
        self._source_data_map = dict()
        self.__final_concentrations = dict()

    def get_final_concentrations(self):
        """
        Returns the final concentration map.
        """
        if self.return_value is None: return None
        return self.__final_concentrations

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Start well association ...')

        self._check_input()
        if not self.has_errors(): self._store_source_data()
        if not self.has_errors() and self.design_rack_layouts is None:
            self.__convert_design_rack_layouts()
        if not self.has_errors(): self.__store_final_concentrations()
        if not self.has_errors(): self._associate_layouts()
        if not self.has_errors():
            self.return_value = self._association_layouts
            self.add_info('Association completed.')

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input values ...')

        self._check_input_class('experiment design', self.experiment_design,
                                ExperimentDesign)
        self._check_input_class('source layout', self.source_layout,
                                TransfectionLayout)

        if not self.design_rack_layouts is None:
            if self._check_input_class('design rack layout map',
                                       self.design_rack_layouts, dict):
                for label, layout in self.design_rack_layouts.iteritems():
                    if not self._check_input_class('design rack label', label,
                                                   basestring): break
                    if not self._check_input_class('design rack layout', layout,
                                                   TransfectionLayout): break

    def _store_source_data(self):
        """
        Stores the source data required for association (mapped onto rack
        positions).
        """
        self.add_error('Abstract method: _store_source_data()')

    def __convert_design_rack_layouts(self):
        """
        Converts the rack layouts of the design racks into transfection layouts
        (if conversion has not taken place before).
        """
        self.add_debug('Convert design rack layouts ...')

        self.design_rack_layouts = dict()
        for design_rack in self.experiment_design.design_racks:
            converter = TransfectionLayoutConverter(log=self.log,
                                    rack_layout=design_rack.layout,
                                    is_iso_layout=False)
            tf_layout = converter.get_result()
            if tf_layout is None:
                msg = 'Error when trying to convert layout for design rack ' \
                      '"%s".' % (design_rack.label)
                self.add_error(msg)
            else:
                tf_layout.close()
                self.design_rack_layouts[design_rack.label] = tf_layout

    def __store_final_concentrations(self):
        """
        Stores the final concentration for each design rack.
        """
        self.add_debug('Store final concentration ...')

        for rack_label, tf_layout in self.design_rack_layouts.iteritems():
            concentrations = dict()
            for rack_pos, tf_pos in tf_layout.iterpositions():
                concentrations[rack_pos] = tf_pos.final_concentration
            self.__final_concentrations[rack_label] = concentrations

    def _associate_layouts(self):
        """
        Performs the actual association.
        """
        self.add_error('Abstract method: _associate_layouts()')


class WellAssociatorOptimisation(WellAssociator):
    """
    A WellAssociator for optimisation cases. Association is based on
    combinations of molecule design pool ID, reagent name, reagent dilution
    factor and (optinal) final concentration.
    """

    def __init__(self, experiment_design, source_layout, log,
                 design_rack_layouts=None):
        """
        Constructor:

        :param experiment_design: The experiment design containing the
            design racks.
        :type experiment_design:
            :class:`thelma.models.experiment.ExperimentDesign`

        :param source_layout: The transfection layout storing the ISO plate
            data.
        :type source_layout: :class:`TransfectionLayout`

        :param log: The ThelmaLog to write into.
        :type log: :class:`thelma.ThelmaLog`

        :param design_rack_layouts: The transfection layout for each design
            rack (optional, saves duplicate conversion).
        :type design_rack_layout: transfection layouts mapped onto design
            rack labels
        :default design_rack_layouts: *None*
        """
        WellAssociator.__init__(self, experiment_design=experiment_design,
                                source_layout=source_layout, log=log,
                                design_rack_layouts=design_rack_layouts)

        #: Indicates whether there are final concentration in the source layout
        #: (and thus, determining the hash value to be used for making
        #: the associations).
        self.source_has_final_concentrations = None

        #: Maps partial hashes of source positions onto lists of rack positions.
        #: This map is only used when there are no final concentration in
        #: the source layout.
        self.__source_triplet_map = None

        #: The reagent name (if there is only one in the source layout).
        self.__reagent_name = None
        #: The reagent dilution factor (if there is only one in the source
        #: layout).
        self.__reagent_dilution_factor = None

    def reset(self):
        """
        Resets all values except for initialisation values.
        """
        WellAssociator.reset(self)
        self.__source_triplet_map = dict()
        self.__reagent_name = None
        self.__reagent_dilution_factor = None

    def get_completed_source_layout(self):
        """
        Returns the source layout including final concentrations.
        """
        if self.return_value is None: return None
        return self.source_layout

    def _store_source_data(self):
        """
        Stores the source data required for association (mapped onto rack
        positions).
        """
        self.add_debug('Store source data ...')

        self.source_has_final_concentrations = \
                            self.source_layout.has_final_concentrations()
        # Determines the hash that is needed (full or partial).
        # Full hash values simplify well associations.

        for rack_pos, tf_pos in self.source_layout.iterpositions():
            if tf_pos.is_untreated: continue
            if self.source_has_final_concentrations:
                # a full hash may occur only once per source layout
                self._source_data_map[tf_pos.hash_full] = rack_pos
            else:
                hash_value = tf_pos.hash_partial
                if not self.__source_triplet_map.has_key(hash_value):
                    self.__source_triplet_map[hash_value] = []
                self.__source_triplet_map[hash_value].append(rack_pos)

    def _associate_layouts(self):
        """
        Performs the actual association.
        """
        self.add_debug('Associate layouts ...')

        self.__determine_default_values()
        has_defaults = (not self.__reagent_name is None \
                        or not self.__reagent_dilution_factor is None)

        for rack_label, tf_layout in self.design_rack_layouts.iteritems():

            if has_defaults:
                tf_layout = self.__add_default_values(rack_label, tf_layout)
                if tf_layout is None: continue

            if self.source_has_final_concentrations:
                associated_positions = self.__associate_with_full_hash(
                                                        rack_label, tf_layout)
            else:
                associated_positions = self.__associate_with_partial_hash(
                                                        rack_label, tf_layout)
            if associated_positions is None: continue

            copied_src_layout = self.source_layout.copy()
            for src_pos, tgt_positions in associated_positions.iteritems():
                tf_pos = copied_src_layout.get_working_position(src_pos)
                tf_pos.cell_plate_positions = tgt_positions
            self._association_layouts[rack_label] = copied_src_layout

    def __determine_default_values(self):
        """
        If there is only reagent name or reagent dilution factor in the
        source layout, the value do not need to be specified in the
        optimisation layout and can be filled in later.
        """
        names = set()
        dfs = set()

        for tf_pos in self.source_layout.working_positions():
            names.add(tf_pos.reagent_name)
            dfs.add(tf_pos.reagent_dil_factor)

        if len(names) == 1: self.__reagent_name = list(names)[0]
        if len(dfs) == 1: self.__reagent_dilution_factor = list(dfs)[0]

    def __add_default_values(self, rack_label, tf_layout):
        """
        Adds the default reagent names and dilution factors into the
        design rack layout.
        """
        found_names = []
        found_dfs = []

        for rack_pos, tf_pos in tf_layout.iterpositions():

            name = tf_pos.reagent_name
            if self.__reagent_name is None:
                pass
            elif name is None:
                tf_pos.reagent_name = self.__reagent_name
            elif not name == self.__reagent_name:
                info = '%s (%s)' % (name, rack_pos.label)
                found_names.append(info)

            df = tf_pos.reagent_dil_factor
            if self.__reagent_dilution_factor is None:
                pass
            elif df is None:
                tf_pos.reagent_dil_factor = self.__reagent_dilution_factor
            elif not df == self.__reagent_dilution_factor:
                info = '%s (%s)' % (get_trimmed_string(df), rack_pos.label)
                found_dfs.append(info)

        valid_layout = True
        if len(found_names) > 1:
            found_names.sort()
            msg = 'The layout of design rack "%s" contains other reagent ' \
                  'reagent names than the ISO plate layout: %s!' \
                  % (rack_label, found_names)
            self.add_error(msg)
            valid_layout = False
        if len(found_dfs) > 1:
            found_dfs.sort()
            msg = 'The layout of design rack "%s" contains other reagent ' \
                  'dilution factors than the ISO plate layout: %s!' \
                  % (rack_label, found_dfs)
            self.add_error(msg)
            valid_layout = False

        if valid_layout:
            return tf_layout
        else:
            return None

    def __associate_with_full_hash(self, rack_label, tf_layout):
        """
        Creates association maps using the full hash (incl. final concentration
        data).
        """
        no_source_position = []

        associated_positions = dict()
        for trg_pos, tf_pos in tf_layout.iterpositions():
            hash_value = tf_pos.hash_full

            if not self._source_data_map.has_key(hash_value):
                info = '%s (md %s, %s (%s), %s nM)' \
                        % (trg_pos.label,
                           get_trimmed_string(tf_pos.molecule_design_pool_id),
                           tf_pos.reagent_name,
                           get_trimmed_string(tf_pos.reagent_dil_factor),
                           get_trimmed_string(tf_pos.final_concentration))
                no_source_position.append(info)
                continue

            src_pos = self._source_data_map[hash_value]
            if not associated_positions.has_key(src_pos):
                associated_positions[src_pos] = []
            associated_positions[src_pos].append(trg_pos)

        if len(no_source_position) > 0:
            no_source_position.sort()
            msg = 'Could not find source position for the following ' \
                  'positions in design rack "%s": %s.' \
                  % (rack_label, no_source_position)
            self.add_error(msg)
            return None
        else:
            return associated_positions

    def __associate_with_partial_hash(self, rack_label, tf_layout):
        """
        Creates association maps using the partial hash (without final
        concentration data).
        """
        no_source_position = []
        associated_positions = dict()

        for trg_pos, tf_pos in tf_layout.iterpositions():
            full_hash = tf_pos.hash_full

            if self._source_data_map.has_key(full_hash):
                # there is already a source position for that concentration
                src_pos = self._source_data_map[full_hash]
                if not associated_positions.has_key(src_pos):
                    associated_positions[src_pos] = []
                associated_positions[src_pos].append(trg_pos)
                continue

            partial_hash = tf_pos.hash_partial
            if not self.__source_triplet_map.has_key(partial_hash):
                info = '%s (md %s, %s (%s), %s nM)' \
                        % (trg_pos.label,
                           get_trimmed_string(tf_pos.molecule_design_pool_id),
                           tf_pos.reagent_name,
                           get_trimmed_string(tf_pos.reagent_dil_factor),
                           get_trimmed_string(tf_pos.final_concentration))
                no_source_position.append(info)
                continue

            # If we get here, it is a new combination
            src_positions = self.__source_triplet_map[partial_hash]
            src_pos = src_positions.pop()
            if len(src_positions) < 1: # no positions left
                del self.__source_triplet_map[partial_hash]

            src_tf = self.source_layout.get_working_position(src_pos)
            src_tf.final_concentration = tf_pos.final_concentration
            self._source_data_map[full_hash] = src_pos
            associated_positions[src_pos] = [trg_pos]

        if len(no_source_position) > 0:
            no_source_position.sort()
            msg = 'Could not find source position for the following ' \
                  'positions in design rack "%s": %s. It might also be ' \
                  'that there are not enough wells for the combinations of ' \
                  'remaining factors. Specify a source well for each ' \
                  'combination of the four factors (molecule design pool ID, ' \
                  'reagent name, reagent dilution factor, final ' \
                  'concentration) even you do not specify the final ' \
                  'concentration itself.' % (rack_label, no_source_position)
            self.add_error(msg)
            return None
        else:
            return associated_positions


class WellAssociatorManual(WellAssociator):
    """
    A WellAssociator for manual optimisation type experiments. The association
    is based on molecule design pools.
    """

    def _store_source_data(self):
        """
        There might be several position for one molecule design pool, but
        since they all originate from the same stock tube and we do not
        track their processing, we only store the first occurrence of each
        pool.
        """
        self.add_debug('Store source data ...')

        for tf_pos in self.source_layout.get_sorted_working_positions():
            pool_id = tf_pos.molecule_design_pool_id
            if not self._source_data_map.has_key(pool_id):
                self._source_data_map[pool_id] = tf_pos.rack_position

    def _associate_layouts(self):
        """
        Performs the actual association.
        """
        self.add_debug('Associate layouts ...')

        for rack_label, tf_layout in self.design_rack_layouts.iteritems():

            no_source_pos = []
            associated_positions = dict()
            for trg_pos, tf_pos in tf_layout.iterpositions():
                if tf_pos.is_mock: continue
                md_id = tf_pos.molecule_design_pool_id

                if not self._source_data_map.has_key(md_id):
                    info = '%s (md %s)' % (trg_pos.label, md_id)
                    no_source_pos.append(info)
                    continue

                src_pos = self._source_data_map[md_id]
                if not associated_positions.has_key(src_pos):
                    associated_positions[src_pos] = []
                associated_positions[src_pos].append(trg_pos)

            if len(no_source_pos) > 0:
                no_source_pos.sort()
                msg = 'Could not find source positions for the following ' \
                      'positions in design rack "%s": %s.' \
                      % (rack_label, no_source_pos)
                self.add_error(msg)
            else:
                copied_src_layout = self.source_layout.copy()
                for src_pos, tgt_positions in associated_positions.iteritems():
                    tf_pos = copied_src_layout.get_working_position(src_pos)
                    tf_pos.cell_plate_positions = tgt_positions
                self._association_layouts[rack_label] = copied_src_layout