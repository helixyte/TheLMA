"""
:Date: 2011 November
:Author: AAB, berger at cenix-bioscience dot com

This module fills the containers of experiment racks (intended
as executor for manual worklists).
"""
from thelma.automation.tools.experiment.base import ExperimentTool
from thelma.automation.tools.metadata.transfection_utils \
    import TransfectionLayoutConverter
from thelma.automation.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.semiconstants import get_item_status_managed
from thelma.automation.tools.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.utils.base import add_list_map_element
from thelma.models.liquidtransfer import ExecutedContainerTransfer
from thelma.models.liquidtransfer import ExecutedRackTransfer
from thelma.models.liquidtransfer import ExecutedWorklist
from thelma.models.sample import Sample
from thelma.models.user import User
from thelma.utils import get_utc_time
import logging


__docformat__ = 'reStructuredText en'

__all__ = ['ExperimentRackFiller',
           'ExperimentRackFillerOptimisation',
           'ExperimentRackFillerManual',
           'ExperimentRackFillerScreen',
           'ExperimentRackFillerIsoLess',
           'SampleInfoItem']


class ExperimentRackFiller(ExperimentTool):
    """
    This class fills the containers of experiment design racks that have
    been created without making use of the BioMek (manual pipetting).
    In addition to the sample generation, the tool will create executed
    worklists for all worklists (incl. execution time).

    **Return Value:** updated experiment
    """
    NAME = 'Experiment Rack Filler'

    SUPPORTED_EXPERIMENT_SCENARIOS = [EXPERIMENT_SCENARIOS.OPTIMISATION,
                                      EXPERIMENT_SCENARIOS.SCREENING,
                                      EXPERIMENT_SCENARIOS.MANUAL]

    MOCKS_MAY_BE_EMPTY = True

    #: Some experiment type allow for mastermix support. Do we need to
    #: check whether mastermix support would be possible? (default: *False*)
    CHECK_FOR_MASTERMIX_SUPORT = False

    def __init__(self, experiment, user, logging_level=logging.WARNING,
                 add_default_handlers=False, log=None):
        """
        Constructor:

        :param experiment: The experiment for which to generate the BioMek
                worklists.
        :type experiment: :class:`thelma.models.experiment.Experiment`

        :param user: The user who has committed the update.
        :type user: :class:`thelma.models.user.User`

        :param logging_level: the desired minimum log level
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *True*

        :param log: The ThelmaLog to write into (if used as part of a batch).
        :type log: :class:`thelma.ThelmaLog`
        """
        ExperimentTool.__init__(self, experiment=experiment,
                                logging_level=logging_level,
                                add_default_handlers=add_default_handlers,
                                log=log)

        #: The user who has committed the update.
        self.user = user
        #: The timestamp for the execution.
        self.now = get_utc_time()

        #: Maps design rack transfection layouts onto design racks (for
        #: optimisation cases).
        self._design_layouts_map = None

        #: Maps molecules of the ISO rack onto positions.
        self._iso_molecule_map = None
        #: Maps containers of the ISO rack onto rack positions.
        self.__iso_container_map = None

        #: The transfer list for screening scenarios (it is the same for
        #: all design racks).
        self.__transfer_worklist = None

    def reset(self):
        """
        Resets all attributes except for the input values.
        """
        ExperimentTool.reset(self)
        self._design_layouts_map = dict()
        self._iso_molecule_map = dict()
        self.__iso_container_map = dict()
        self.__transfer_worklist = None

    @classmethod
    def create(cls, experiment, user, logging_level=logging.WARNING,
               add_default_handlers=False, log=None):
        """
        Factory method initialising a rack filler for the given experiment type.

        :raises KeyError: If an unsupported experiment type is requested.
        :raise ValueError: If experiment or user is *None*
        """
        kw = dict(experiment=experiment, user=user,
                  logging_level=logging_level, log=log,
                  add_default_handlers=add_default_handlers)

        if experiment is None:
            raise ValueError('The experiment must not be None!')
        if user is None:
            raise ValueError('The user must not be None!')

        em_type = experiment.experiment_design.experiment_metadata_type
        if not _RACK_FILLER_CLASSES.has_key(em_type.id):
            msg = 'Unsupported experiment type "%s"' % (em_type.display_name)
            raise KeyError(msg)

        cls = _RACK_FILLER_CLASSES[em_type.id]
        return cls(**kw)

    def _check_input(self):
        """
        Checks whether all initialisation values are valid.
        """
        ExperimentTool._check_input(self)
        self._check_input_class('user', self.user, User)

    def _execute_task(self):
        """
        Runs the tool-specific tasks.
        """
        self.add_info('Start experiment rack sample generation ...')

        if not self.has_errors():
            if self.CHECK_FOR_MASTERMIX_SUPORT:
                self.__check_mastermix_support()
            self._fetch_design_layouts()

        if not self.has_errors(): self._generate_iso_maps()
        if not self.has_errors(): self._execute_transfers()
        if not self.has_errors(): self._update_rack_status()
        if not self.has_errors():
            self.return_value = self.experiment
            self.add_info('Experiment sample generation completed.')

    def __check_mastermix_support(self):
        """
        Checks whether the worklist series supports mastermix preparation.
        """
        is_compatible = False
        if not self._design_series is None:
            if self._scenario.id == EXPERIMENT_SCENARIOS.OPTIMISATION:
                is_compatible = True
            elif len(self._design_series) > 2:
                is_compatible = True

        if is_compatible:
            msg = 'This experiment is robot-compatible. Would you still ' \
                  'like to use the manual update?'
            self.add_warning(msg)

    def _fetch_design_layouts(self):
        """
        Fetches the transfection layouts for each design rack.
        """
        for design_rack in self.experiment.experiment_design.design_racks:
            converter = TransfectionLayoutConverter(
                                    rack_layout=design_rack.layout,
                                    is_iso_layout=False,
                                    log=self.log)
            tf_layout = converter.get_result()
            if tf_layout is None:
                msg = 'Could not get design layout for design rack "%s"!' \
                      % (design_rack.label)
                self.add_error(msg)
            else:
                self._design_layouts_map[design_rack.label] = tf_layout

    def _generate_iso_maps(self):
        """
        Generates the container map for the ISO rack.
        """
        no_sample = []
        no_sample_molecules = []

        for container in self._iso_plate.containers:
            rack_pos = container.location.position

            tf_pos = self._iso_tf_layout.get_working_position(rack_pos)
            if tf_pos is None: continue
            if rack_pos in self._ignored_positions and not tf_pos.is_mock:
                continue

            sample = container.sample
            if sample is None:
                if tf_pos.is_mock:
                    self._iso_molecule_map[rack_pos] = None
                    self.__iso_container_map[rack_pos] = container
                else:
                    no_sample.append(rack_pos.label)
                continue
            sample_molecules = sample.sample_molecules
            if len(sample_molecules) < 1:
                if tf_pos.is_mock:
                    self._iso_molecule_map[rack_pos] = None
                    self.__iso_container_map[rack_pos] = container
                else:
                    no_sample_molecules.append(rack_pos.label)
                continue

            self.__iso_container_map[rack_pos] = container
            molecules = []
            for sm in sample_molecules: molecules.append(sm.molecule)
            self._iso_molecule_map[rack_pos] = molecules

        if len(no_sample) > 0:
            msg = 'Could not find samples for the following positions in the ' \
                  'ISO rack: %s.' % (', '.join(sorted(no_sample)))
            self.add_error(msg)

        if len(no_sample_molecules) > 0:
            msg = 'The following rack positions in the ISO rack do not have ' \
                  'sample molecules: %s.' % (no_sample_molecules)
            self.add_warning(msg)

    def _create_rack_samples(self, rack, sample_info_list):
        """
        Creates the samples for an particular rack and generates the executed
        transfers for the rack.
        """

        sample_map = dict()
        for sample_info in sample_info_list:
            add_list_map_element(sample_map, sample_info.rack_position,
                                 sample_info)

        rack_container_map = dict()
        for container in rack.containers:
            rack_pos = container.location.position

            if not sample_map.has_key(rack_pos): continue
            rack_container_map[rack_pos] = container

            sample_infos = sample_map[rack_pos]
            sample = container.sample
            if sample is None:
                sample = Sample(0, container)
            elif sample.volume is None:
                sample.volume = 0
            corr_volume = sample.volume * VOLUME_CONVERSION_FACTOR
            new_volume = corr_volume + self.DEFAULT_SAMPLE_VOLUME
            sample.volume = (new_volume / VOLUME_CONVERSION_FACTOR)

            for sample_info in sample_infos:
                if sample_info.concentration is None: continue
                concentration = sample_info.concentration / \
                                CONCENTRATION_CONVERSION_FACTOR
                sample.make_sample_molecule(sample_info.molecule, concentration)

        return rack_container_map

    def _execute_transfers(self):
        """
        Creates the samples for the experiment racks (design rack wise)
        and generates the executed transfers using container transfer worklists.
        By default, we use well assignment (that is, we must have
        figured out which source and target wells belong together in
        :func:`_fetch_design_layouts`).
        """
        for drack_label, exp_rack_list in self._experiment_racks.iteritems():

            worklist_series = self._design_rack_series_map[drack_label]
            transfer_worklist = self._get_transfer_worklist(worklist_series)
            if transfer_worklist is None:
                msg = 'Could not find transfer worklist for design rack "%s".' \
                       % (drack_label)
                self.add_error(msg)
                continue

            sample_info_list = self.__determine_sample_data_for_assignments(
                                                drack_label, transfer_worklist)
            if sample_info_list is None: break
            for exp_rack in exp_rack_list:
                rack = exp_rack.rack
                rack_container_map = self._create_rack_samples(rack,
                                                               sample_info_list)
                self.__create_executed_worklist_for_assignments(
                                                        transfer_worklist,
                                                        rack_container_map)

    def __determine_sample_data_for_assignments(self, drack_label,
                                                transfer_worklist):
        """
        Collects the data needed to generate the samples using stored
        container transfer worklists.
        """
        sample_info_list = []
        no_molecules = []
        no_trg_tf_pos = []

        trg_tf_layout = self._design_layouts_map[drack_label]

        for pct in transfer_worklist.planned_transfers:
            source_pos = pct.source_position
            if source_pos in self._ignored_positions: continue
            if not self._iso_molecule_map.has_key(source_pos):
                no_molecules.append(source_pos.label)
                continue
            molecules = self._iso_molecule_map[source_pos]

            target_pos = pct.target_position
            trg_tf_pos = trg_tf_layout.get_working_position(target_pos)
            if trg_tf_pos is None:
                no_trg_tf_pos.append(target_pos.label)
                continue

            if molecules is None: # mock position
                sample_info_item = SampleInfoItem(rack_position=target_pos,
                                         molecule=None, concentration=None)
                sample_info_list.append(sample_info_item)
            else:
                final_concentration = trg_tf_pos.final_concentration \
                                      / len(molecules)
                for molecule in molecules:
                    sample_info_item = SampleInfoItem(rack_position=target_pos,
                          molecule=molecule, concentration=final_concentration)
                    sample_info_list.append(sample_info_item)

        if len(no_molecules) > 0:
            msg = 'Could not find molecules for the following ' \
                  'ISO positions: %s.' % (no_molecules)
            self.add_error(msg)
        if len(no_trg_tf_pos) > 0:
            msg = 'Could not find transfection data for the following rack ' \
                  'position in design rack "%s": %s!' \
                  % (drack_label, no_trg_tf_pos)
            self.add_error(msg)

        if self.has_errors(): return None
        return sample_info_list

    def __create_executed_worklist_for_assignments(self, transfer_worklist,
                                                   rack_container_map):
        """
        Creates the executed worklist for a rack.
        """
        executed_worklist = ExecutedWorklist(planned_worklist=transfer_worklist)
        for pct in transfer_worklist.planned_transfers:
            source_pos = pct.source_position
            if source_pos in self._ignored_positions: continue
            iso_container = self.__iso_container_map[source_pos]
            target_pos = pct.target_position
            rack_container = rack_container_map[target_pos]
            et = ExecutedContainerTransfer(source_container=iso_container,
                                           target_container=rack_container,
                                           planned_container_transfer=pct,
                                           user=self.user,
                                           timestamp=self.now)
            executed_worklist.executed_transfers.append(et)

    def _update_rack_status(self):
        """
        Sets the status of the experiment racks to managed.
        """
        managed_status = get_item_status_managed()
        for exp_racks in self._experiment_racks.values():
            for exp_rack in exp_racks:
                plate = exp_rack.rack
                plate.status = managed_status
                for well in plate.containers: well.status = managed_status


class ExperimentRackFillerOptimisation(ExperimentRackFiller):
    """
    A special experiment rack filler for automated optimisation experiments.

    Mastermix support is possible and needs to be checked.
    Target wells are update by assignment.

    **Return Value:** updated experiment
    """
    SUPPORTED_EXPERIMENT_SCENARIOS = [EXPERIMENT_SCENARIOS.OPTIMISATION]
    CHECK_FOR_MASTERMIX_SUPORT = True


class ExperimentRackFillerManual(ExperimentRackFiller):
    """
    A special experiment rack filler for manual experiments.

    There are no special constraints here. Mastermix support is not possible
    and target wells are update by assignment.

    **Return Value:** updated experiment
    """
    SUPPORTED_EXPERIMENT_SCENARIOS = [EXPERIMENT_SCENARIOS.MANUAL]


class ExperimentRackFillerScreen(ExperimentRackFiller):
    """
    A special experiment rack filler for screening type experiments.

    Mastermix support is possible and needs to be checked. Besides,
    there is no well assignment but only a one-to-one transfer from
    source plate to target plate (conserving the rack position).

    **Return Value:** updated experiment
    """

    SUPPORTED_EXPERIMENT_SCENARIOS = [EXPERIMENT_SCENARIOS.SCREENING]
    CHECK_FOR_MASTERMIX_SUPORT = True

    def _fetch_design_layouts(self):
        """
        We do not need to fetch design layouts because there is always
        a one-to-one association between source and target
        (conserving the rack position).
        """
        pass

    def _execute_transfers(self):
        """
        In screening scenarios we do not need to use well assignments.
        """
        sample_info_list = self.__determine_sample_data_for_screen()
        transfer_worklist = self._get_transfer_worklist(self._design_series)

        for exp_rack_list in self._experiment_racks.values():
            if self.has_errors(): break

            for exp_rack in exp_rack_list:
                plate = exp_rack.rack
                self._create_rack_samples(plate, sample_info_list)

                erts = []
                for prt in transfer_worklist.planned_transfers:
                    ert = ExecutedRackTransfer(source_rack=self._iso_plate,
                                target_rack=plate, planned_rack_transfer=prt,
                                user=self.user, timestamp=self.now)
                    erts.append(ert)
                ExecutedWorklist(planned_worklist=transfer_worklist,
                                 executed_transfers=erts)

    def __determine_sample_data_for_screen(self):
        """
        Collects the data needed to generate the samples.
        """
        sample_info_list = []
        no_molecules = []

        for rack_pos, tf_pos in self._iso_tf_layout.iterpositions():
            if rack_pos in self._ignored_positions: continue
            if tf_pos.is_empty: continue

            if not self._iso_molecule_map.has_key(rack_pos):
                no_molecules.append(rack_pos.label)
                continue
            molecules = self._iso_molecule_map[rack_pos]

            if molecules is None: # mock position
                sample_info_item = SampleInfoItem(rack_position=rack_pos,
                                        molecule=None, concentration=None)
                sample_info_list.append(sample_info_item)
            else:
                final_concentration = tf_pos.final_concentration \
                                      / len(molecules)
                for molecule in molecules:
                    sample_info_item = SampleInfoItem(rack_position=rack_pos,
                          molecule=molecule, concentration=final_concentration)
                    sample_info_list.append(sample_info_item)

        if len(no_molecules) > 0:
            msg = 'Could not find molecules for the following ' \
                  'ISO positions: %s.' % (sorted(no_molecules))
            self.add_error(msg)

        if self.has_errors(): return None
        return sample_info_list


class ExperimentRackFillerIsoLess(ExperimentRackFiller):
    """
    A special experiment rack filler for experiments without ISO.

    There are no molecule to be transferred but just sample to be generated.
    Hence, mastermix support is not possible and there are also not well
    assignments required.

    **Return Value:** updated experiment
    """
    SUPPORTED_EXPERIMENT_SCENARIOS = [EXPERIMENT_SCENARIOS.ISO_LESS]

    def _fetch_design_layouts(self):
        """
        We do not have transfection layouts here, but only unconverted
        rack layouts.
        """
        for design_rack in self.experiment.experiment_design.design_racks:
            self._design_layouts_map[design_rack.label] = design_rack.layout

    def _generate_iso_maps(self):
        """
        There are no molecules to be tracked.
        """
        pass

    def _execute_transfers(self):
        """
        There are no molecules to be transferred. We only need to generate
        samples. We also do not want to generate executed worklists
        (in theory we could add dilution worklists since we cannot even
        be sure about the volume this would probably be an overkill).
        """
        for drack_label, exp_rack_list in self._experiment_racks.iteritems():

            sample_info_list = self.__determine_sample_positions(drack_label)
            if sample_info_list is None: break
            for exp_rack in exp_rack_list:
                rack = exp_rack.rack
                self._create_rack_samples(rack, sample_info_list)

    def __determine_sample_positions(self, drack_label):
        """
        Collects positions for the samples to be generated.
        """
        sample_info_list = []

        trg_tf_layout = self._design_layouts_map[drack_label]

        for rack_pos in trg_tf_layout.get_positions():
            sample_info_item = SampleInfoItem(rack_position=rack_pos,
                                              molecule=None, concentration=None)
            sample_info_list.append(sample_info_item)

        return sample_info_list


class SampleInfoItem(object):
    """
    A helper class storing the data need to generate a sample molecule in an
    experiment rack.
    """

    def __init__(self, rack_position, molecule, concentration):
        """
        Constructor:

        :param rack_position: The rack position in the experiment rack.
        :type rack_position: :class:`thelma.models.rack.RackPosition`

        :param molecule: The molecule for the sample.
        :type molecule: :class:`thelma.models.sample.Molecule`

        :param concentration: The final concentration of the molecule.
        :type concentration: Positive number.
        """
        #: The rack position in the experiment rack.
        self.rack_position = rack_position
        #: The molecule for the sample.
        self.molecule = molecule
        #: The final concentration of the molecule.
        self.concentration = concentration

    def __str__(self):
        return "%s-%s-%s" % (self.rack_position.label, self.molecule,
                             self.concentration)

    def __repr__(self):
        str_format = '<SampleInfoItem %s molecule: %s, concentration: %s>'
        params = (self.rack_position, self.molecule, self.concentration)
        return str_format % params

    def __eq__(self, other):
        return isinstance(other, SampleInfoItem) and \
                self.rack_position == other.rack_position and \
                self.molecule == other.molecule and \
                self.concentration == other.concentration

    def __ne__(self, other):
        return not (self.__eq__(other))


#: Lookup storing the rack filler class for each experiment type.
_RACK_FILLER_CLASSES = {
        EXPERIMENT_SCENARIOS.OPTIMISATION : ExperimentRackFillerOptimisation,
        EXPERIMENT_SCENARIOS.SCREENING : ExperimentRackFillerScreen,
        EXPERIMENT_SCENARIOS.MANUAL : ExperimentRackFillerManual,
        EXPERIMENT_SCENARIOS.ISO_LESS : ExperimentRackFillerIsoLess,
                        }
