"""
Classes for the execution of planned liquid transfers and worklists.

AAB
"""
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.tools.semiconstants import ITEM_STATUS_NAMES
from thelma.automation.tools.semiconstants import get_item_status_managed
from thelma.automation.tools.semiconstants import get_pipetting_specs_cybio
from thelma.automation.tools.semiconstants import get_positions_for_shape
from thelma.automation.tools.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.utils.base import are_equal_values
from thelma.automation.tools.utils.base import get_trimmed_string
from thelma.automation.tools.utils.base import is_larger_than
from thelma.automation.tools.utils.base import is_smaller_than
from thelma.automation.tools.utils.racksector import RackSectorTranslator
from thelma.automation.tools.utils.racksector import check_rack_shape_match
from thelma.automation.tools.utils.racksector import get_sector_positions
from thelma.models.liquidtransfer import ExecutedSampleDilution
from thelma.models.liquidtransfer import ExecutedSampleTransfer
from thelma.models.liquidtransfer import ExecutedRackSampleTransfer
from thelma.models.liquidtransfer import ExecutedWorklist
from thelma.models.liquidtransfer import PipettingSpecs
from thelma.models.liquidtransfer import PlannedSampleDilution
from thelma.models.liquidtransfer import PlannedSampleTransfer
from thelma.models.liquidtransfer import PlannedRackSampleTransfer
from thelma.models.liquidtransfer import PlannedWorklist
from thelma.models.liquidtransfer import ReservoirSpecs
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.rack import Plate
from thelma.models.rack import Rack
from thelma.models.rack import RackPosition
from thelma.models.user import User
from thelma.utils import get_utc_time

__docformat__ = 'reStructuredText en'

__all__ = ['LiquidTransferExecutor',
           'WorklistExecutor',
           'SampleDilutionWorklistExecutor',
           'SampleTransferWorklistExecutor',
           'RackSampleTransferExecutor',
           'SampleComponent',
           'SampleData',
           'TransferredSample',
           'SourceSample',
           'TargetSample']



class LiquidTransferExecutor(BaseAutomationTool):
    """
    An abstract tool for the execution of a planned liquid transfer or
    planned transfer worklist (rack-based).

    **Return Value*:* executed worklist or transfer
    """

    #: The transfer type supported by this class
    #: (see :class:`thelma.models.liquidtransfer.TRANSFER_TYPES`).
    TRANSFER_TYPE = None

    def __init__(self, target_rack, user, pipetting_specs, log):
        """
        Constructor:

        :param target_rack: The rack into which the volumes will be dispensed.
        :type target_rack: :class:`thelma.models.rack.Rack`

        :param user: The user who has launched the execution.
        :type user: :class:`thelma.models.user.User`

        :param pipetting_specs: Pipetting specs define transfer properties and
            conditions like the transfer volume range.
        :type pipetting_specs:
            :class:`thelma.models.liquidtransfer.PipettingSpecs`

        :param log: The ThelmaLog you want to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        BaseAutomationTool.__init__(self, log=log)

        #: The rack into which the volumes will be dispensed.
        self.target_rack = target_rack
        #: The user who has launched the execution.
        self.user = user
        #: Pipetting specs define transfer properties and conditions like
        #: the transfer volume range.
        self.pipetting_specs = pipetting_specs

        self.now = get_utc_time()

        #: Maps the containers of the source rack onto rack position.
        self._source_containers = None
        #: The minimum dead volume of source rack container in ul.
        self._source_dead_volume = None
        #: Maps the containers of the target rack onto rack positions.
        self._target_containers = None
        #: The maximum volume of a target rack container in ul.
        self._target_max_volume = None

        #: The minimum transfer volume used in ul.
        self._min_transfer_volume = None
        #: The maximum transfer volume used in ul.
        self._max_transfer_volume = None

        # Intermediate storage of volumes and concentrations

        #: :class:`SourceSample` objects mapped onto rack positions.
        #: Note: Contains only data for samples that are going to be altered.
        self._source_samples = None
        #: :class:`TargetSample` objects mapped onto rack positions.
        #: Note: Contains only data for samples that are going to be altered.
        self._target_samples = None
        # :ATTENTION: It is important not to include data of sample that
        # are not altered because otherwise we will get in trouble with
        # intra-rack transfers when target sample is overwritten by source data.

        # Intermediate storage of errors
        self._transfer_volume_too_small = None
        self._transfer_volume_too_large = None
        self._source_volume_too_small = None
        self._source_container_missing = None
        self._target_volume_too_large = None
        self._target_container_missing = None

    def reset(self):
        """
        Resets all values except for input values.
        """
        BaseAutomationTool.reset(self)
        self._source_samples = dict()
        self._target_samples = dict()
        self._target_containers = dict()
        self._target_max_volume = None
        self._source_containers = dict()
        self._source_dead_volume = None
        # Intermediate storage of errors
        self._transfer_volume_too_small = []
        self._transfer_volume_too_large = []
        self._source_volume_too_small = []
        self._source_container_missing = set()
        self._target_volume_too_large = []
        self._target_container_missing = []

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Start execution ...')

        self._check_input()
        if not self.has_errors():
            self._init_target_data()
            self._init_source_data()
        if not self.has_errors(): self._register_planned_liquid_transfers()
        if not self.has_errors():
            self.__check_resulting_volumes()
            self._record_errors()
        if not self.has_errors():
            self.__execute_transfers()
            self.__update_target_rack_status()
        if not self.has_errors(): self.add_info('Execution completed.')

    def _check_input(self):
        """
        Checks the input values.
        """
        self.add_debug('Check input values ...')

        self._check_input_class('target rack', self.target_rack, Rack)
        self._check_input_class('user', self.user, User)
        self._check_input_class('pipetting specs', self.pipetting_specs,
                                PipettingSpecs)

    def _init_target_data(self):
        """
        Initialises the target rack related values and lookups.
        """
        for container in self.target_rack.containers:
            rack_pos = container.location.position
            self._target_containers[rack_pos] = container

        if isinstance(self.target_rack, Plate):
            well_specs = self.target_rack.specs.well_specs
            self._target_max_volume = well_specs.max_volume \
                                      * VOLUME_CONVERSION_FACTOR

    def _init_source_data(self):
        """
        Initialises the source rack related values and lookups.
        """
        raise NotImplementedError('Abstract method.')

    def _register_planned_liquid_transfers(self):
        """
        Registers the planned liquid transfers and checks the transfer volumes.
        """
        raise NotImplementedError('Abstract method.')

    def _get_target_sample(self, rack_pos):
        """
        Fetches the target sample object for the given rack position or
        creates a new object if there is none so far.
        """
        if self._target_samples.has_key(rack_pos):
            target_sample = self._target_samples[rack_pos]
        else:
            target_container = self._target_containers[rack_pos]
            target_sample = TargetSample.from_sample(target_container.sample)
            if target_sample is None: target_sample = TargetSample(volume=0)
            self._target_samples[rack_pos] = target_sample

        return target_sample

    def _get_source_sample(self, rack_pos):
        """
        Fetches the source sample object for the given rack position or
        creates a new object if there is none so far.
        """
        if self._source_samples.has_key(rack_pos):
            source_sample = self._source_samples[rack_pos]
        else:
            source_container = self._source_containers[rack_pos]
            source_sample = SourceSample.from_sample(source_container.sample)
            self._source_samples[rack_pos] = source_sample

        if source_sample is None:
            info = '%s (no sample)' % (rack_pos.label)
            self._source_volume_too_small.append(info)

        return source_sample

    def __check_resulting_volumes(self):
        """
        Checks the final volumes that would result from the execution.
        """
        self.add_debug('Check resulting volumes ...')

        # checking the target samples
        for trg_pos, target_sample in self._target_samples.iteritems():
            max_volume = self.__get_max_volume_for_target_container(trg_pos)
            if max_volume is None: continue
            final_volume = target_sample.final_volume
            if is_smaller_than(max_volume, final_volume):
                info = '%s (final vol: %.1f ul, max vol: %.0f ul)' \
                        % (trg_pos.label, final_volume, max_volume)
                self._target_volume_too_large.append(info)

        # checking the source samples
        for src_pos, source_sample in self._source_samples.iteritems():
            if source_sample is None: continue
            dead_volume = self.__get_dead_volume_for_source_container(src_pos)
            if dead_volume is None: continue
            total_transfer_volume = source_sample.total_transfer_volume
            if are_equal_values(total_transfer_volume, 0): continue
            required_volume = total_transfer_volume + dead_volume
            sample_volume = source_sample.volume
            if is_smaller_than(sample_volume, required_volume):
                info = '%s (required: %.1f ul, found: %.1f ul)' \
                        % (src_pos.label, required_volume, sample_volume)
                self._source_volume_too_small.append(info)

    def __get_max_volume_for_target_container(self, target_position):
        """
        Returns the maximum volume for the container at the given
        target position.
        """
        if self._target_max_volume is None:
            if not self._target_containers.has_key(target_position):
                self._target_container_missing.append(target_position.label)
                return None
            container = self._target_containers[target_position]
            return container.specs.max_volume * VOLUME_CONVERSION_FACTOR
        else:
            return self._target_max_volume

    def __get_dead_volume_for_source_container(self, source_position):
        """
        Returns the maximum volume for the container at the given
        target position.
        """
        if self._source_dead_volume is None:
            if not self._source_containers.has_key(source_position):
                self._source_container_missing.add(source_position.label)
                return None
            container = self._source_containers[source_position]
            return container.specs.dead_volume * VOLUME_CONVERSION_FACTOR
        else:
            return self._source_dead_volume

    def _is_valid_transfer_volume(self, planned_liquid_transfer):
        """
        Checks whether the volume is in valid range for Biomek transfers.
        """
        if self._min_transfer_volume is None:
            self._min_transfer_volume = self.pipetting_specs.\
                                min_transfer_volume * VOLUME_CONVERSION_FACTOR
        if self._max_transfer_volume is None:
            self._max_transfer_volume = self.pipetting_specs.\
                                max_transfer_volume * VOLUME_CONVERSION_FACTOR

        transfer_volume = planned_liquid_transfer.volume \
                          * VOLUME_CONVERSION_FACTOR
        try:
            trg_position_label = planned_liquid_transfer.target_position.label
        except AttributeError:
            info = '%.1f ul' % (transfer_volume)
        else:
            info = '%s (%.1f ul)' % (trg_position_label, transfer_volume)
        if is_larger_than(transfer_volume, self._max_transfer_volume) and \
                    not self.TRANSFER_TYPE == TRANSFER_TYPES.SAMPLE_DILUTION:
            self._transfer_volume_too_large.append(info)
            return False
        elif is_smaller_than(transfer_volume, self._min_transfer_volume):
            self._transfer_volume_too_small.append(info)
            return False

        return True

    def _record_errors(self):
        """
        Records errors that have been found during value list creation.
        """

        if len(self._source_volume_too_small) > 0:
            msg = 'Some source containers do not contain enough volume to ' \
                  'provide liquid for all target containers: %s ' \
                  '(the required volumes include dead volumes).' \
                  % (', '.join(sorted(self._source_volume_too_small)))
            self.add_error(msg)

        if len(self._source_container_missing) > 0:
            error_list = sorted(list(self._source_container_missing))
            msg = 'Could not find containers for the following source ' \
                  'positions: %s.' % (', '.join(error_list))
            self.add_error(msg)

        if len(self._target_volume_too_large) > 0:
            msg = 'Some target container cannot take up the transfer volume: ' \
                  '%s. ' % (', '.join(sorted(self._target_volume_too_large)))
            if self._target_max_volume is not None:
                msg += 'Assumed maximum volume per target well: %s ul.' \
                       % (get_trimmed_string(self._target_max_volume))
            self.add_error(msg)

        if len(self._target_container_missing) > 0:
            msg = 'Could not find containers for the following target ' \
                  'positions: %s.' \
                   % (', '.join(sorted(self._target_container_missing)))
            self.add_error(msg)

        if len(self._transfer_volume_too_small) > 0:
            msg = 'Some transfer volumes are smaller than the allowed ' \
                  'minimum transfer volume of %s ul: %s.' % (
                   get_trimmed_string(self._min_transfer_volume),
                   ', '.join(sorted(self._transfer_volume_too_small)))
            self.add_error(msg)

        if len(self._transfer_volume_too_large) > 0:
            meth = self.add_error
            if self.TRANSFER_TYPE == TRANSFER_TYPES.SAMPLE_DILUTION:
                meth = self.add_warning
            msg = 'Some transfer volumes are larger than the allowed maximum ' \
                  'transfer volume of %s ul: %s.' % (
                   get_trimmed_string(self._max_transfer_volume),
                  ', '.join(sorted(self._transfer_volume_too_large)))
            meth(msg)

    def __execute_transfers(self):
        """
        Updates the racks or containers and creates the executed liauid
        transfers. This method has to set the return value.
        """
        self.add_debug('Execute transfers ...')
        self._update_racks()
        self._create_executed_items()

    def _update_racks(self):
        """
        Updates the racks involved in the transfer.
        """
        self._update_rack(self.target_rack, self._target_samples)

    def _update_rack(self, rack, sample_data_map):
        """
        Updates the racks sample for a particular rack.
        If the rack is a target rack, the sample molecules are updated as well.
        """
        for container in rack.containers:
            rack_pos = container.location.position
            if not sample_data_map.has_key(rack_pos): continue
            sample_data = sample_data_map[rack_pos]
            updated_sample = sample_data.update_container_sample(container)
            container.sample = updated_sample

    def _create_executed_items(self):
        """
        Creates the executed liquid transfers and worklists. This method should
        also set the return value.
        """
        raise NotImplementedError('Abstract method.')

    def _create_executed_liquid_transfer(self, planned_liquid_transfer):
        """
        Creates the executed lqiuid transfer for a planned liquid transfer
        and stores it in the :attr:`_executed_worklist`.
        """
        raise NotImplementedError('Abstract method.')

    def __update_target_rack_status(self):
        """
        Sets the status of the target rack to "managed" if it has be "future"
        before.
        """
        self.add_debug('Update target rack status ...')

        if self.target_rack.status.name == ITEM_STATUS_NAMES.FUTURE:
            managed_status = get_item_status_managed()
            self.target_rack.status = managed_status

            is_plate = isinstance(self.target_rack, Plate)
            if is_plate:
                for well in self.target_rack.containers:
                    well.status = managed_status

            else:
                tubes = self._get_target_tubes()
                for tube in tubes:
                    if tube.status.name == ITEM_STATUS_NAMES.FUTURE:
                        tube.status = managed_status

    def _get_target_tubes(self):
        """
        Returns the tubes of the target container (for status updates).
        """
        raise NotImplementedError('Abstract method.')


class WorklistExecutor(LiquidTransferExecutor):
    """
    This is abstract tool for the execution of planned worklists.

    **Return Value:** An executed worklist
        (:class:`thelma.models.liquidtransfer.ExecutedWorklist`).
    """

    def __init__(self, planned_worklist, target_rack, user, pipetting_specs,
                 log, ignored_positions=None):
        """
        Constructor:

        :param planned_worklist: The worklist to execute.
        :type planned_worklist:
            :class:`thelma.models.liquidtransfer.PlannedWorklist`

        :param target_rack: The rack into which the volumes will be dispensed.
        :type target_rack: :class:`thelma.models.rack.Rack`

        :param user: The user who has launched the execution.
        :type user: :class:`thelma.models.user.User`

        :param pipetting_specs: Pipetting specs define transfer properties and
            conditions like the transfer volume range.
        :type pipetting_specs:
            :class:`thelma.models.liquidtransfer.PipettingSpecs`

        :param log: The ThelmaLog you want to write into.
        :type log: :class:`thelma.ThelmaLog`

        :param ignored_positions: A list of positions (target
            for dilutions and source for transfers) that are not included
            in the DB execution.
        :type ignored_positions: :class:`list` of :class:`RackPosition`
        """
        LiquidTransferExecutor.__init__(self, log=log, user=user,
                                        target_rack=target_rack,
                                        pipetting_specs=pipetting_specs)
        #: The planned worklist to execute.
        self.planned_worklist = planned_worklist

        if ignored_positions is None: ignored_positions = []
        #: A list of positions that will not be included in the DB execution
        #: (even if there are planned liquid transfers for them).
        self.ignored_positions = ignored_positions

        #: The executed worklist.
        self._executed_worklist = None

    def reset(self):
        """
        Resets all values except for input values.
        """
        LiquidTransferExecutor.reset(self)
        self._executed_worklist = None

    def _check_input(self):
        """
        Checks the input values.
        """
        LiquidTransferExecutor._check_input(self)
        self._check_input_class('planned worklist', self.planned_worklist,
                                PlannedWorklist)

        if self._check_input_class('ignored position list',
                                   self.ignored_positions, list):
            for rack_pos in self.ignored_positions:
                if not self._check_input_class('ignored rack position',
                                    rack_pos, RackPosition): break

    def _register_planned_liquid_transfers(self):
        """
        Registers the planned liquid transfers and checks the transfer volumes.
        """
        self.add_debug('Register transfers ...')

        for plt in self.planned_worklist.planned_liquid_transfers:
            if not self.__is_valid_transfer_type(plt): break
            if not self._is_valid_transfer_volume(plt): continue
            self._register_transfer(plt)

    def __is_valid_transfer_type(self, planned_liquid_transfer):
        """
        Checks whether the passed planned liquid transfers has the correct type.
        """
        if not planned_liquid_transfer.transfer_type == self.TRANSFER_TYPE:
            msg = 'Some transfers planned in the worklist are not supported: ' \
                  '%s. Supported type: %s.' \
                   % (planned_liquid_transfer.transfer_type, self.TRANSFER_TYPE)
            self.add_error(msg)
            return False

        return True

    def _register_transfer(self, planned_liquid_transfer):
        """
        Registers a particular planned liquid transfer.
        """
        raise NotImplementedError('Abstract method.')

    def _create_executed_items(self):
        """
        Creates the executed liquid transfers and worklists.
        """
        self._executed_worklist = ExecutedWorklist(
                                        planned_worklist=self.planned_worklist)
        for plt in self.planned_worklist.planned_liquid_transfers:
            self._create_executed_liquid_transfer(plt)

        if not self.has_errors(): self.return_value = self._executed_worklist

    def _get_target_tubes(self):
        """
        Returns the tubes of the target container (for status updates).
        """
        tubes = []
        for pt in self.planned_worklist.planned_liquid_transfers:
            tube = self._target_containers[pt.target_position]
            tubes.append(tube)

        return tubes


class SampleDilutionWorklistExecutor(WorklistExecutor):
    """
    An executor for sample dilution worklists.

    **Return Value:** An executed worklist
        (:class:`thelma.models.liquidtransfer.ExecutedWorklist`).
    """

    NAME = 'Container Dilution Worklist Executor'

    TRANSFER_TYPE = TRANSFER_TYPES.SAMPLE_DILUTION

    def __init__(self, planned_worklist, target_rack, user, reservoir_specs,
                 pipetting_specs, log, ignored_positions=None):
        """
        Constructor:

        :param planned_worklist: The worklist to execute.
        :type planned_worklist:
            :class:`thelma.models.liquidtransfer.PlannedWorklist`

        :param target_rack: The rack into which the volumes will be dispensed.
        :type target_rack: :class:`thelma.models.rack.Rack`

        :param user: The user who has launched the execution.
        :type user: :class:`thelma.models.user.User`

        :param reservoir_specs: The specs for the source rack or reservoir.
        :type reservoir_specs:
            :class:`thelma.models.liquidtransfer.ReservoirSpecs`

        :param log: The ThelmaLog you want to write into.
        :type log: :class:`thelma.ThelmaLog`

        :param pipetting_specs: Pipetting specs define transfer properties and
            conditions like the transfer volume range.
        :type pipetting_specs:
            :class:`thelma.models.liquidtransfer.PipettingSpecs`

        :param ignored_positions: A list of positions (target
            for dilutions and source for transfers) that are not included
            in the DB execution.
        :type ignored_positions: :class:`list` of :class:`RackPosition`
        """
        WorklistExecutor.__init__(self, log=log, target_rack=target_rack,
                                  planned_worklist=planned_worklist,
                                  ignored_positions=ignored_positions,
                                  pipetting_specs=pipetting_specs,
                                  user=user)

        #: The specs for the source rack or reservoir.
        self.reservoir_specs = reservoir_specs

    def _check_input(self):
        """
        Checks the input values.
        """
        WorklistExecutor._check_input(self)

        self._check_input_class('reservoir specs', self.reservoir_specs,
                                ReservoirSpecs)

    def _init_source_data(self):
        """
        We do not need source data since changes for the source rack or
        reservoir are not tracked.
        """
        pass

    def _register_transfer(self, planned_liquid_transfer):
        """
        Planned liquid transfers are planned container dilutions.
        """
        trg_pos = planned_liquid_transfer.target_position

        if trg_pos in self.ignored_positions:
            pass
        elif not self._target_containers.has_key(trg_pos):
            self._target_container_missing.append(trg_pos.label)
        else:
            target_sample = self._get_target_sample(trg_pos)
            target_sample.create_and_add_transfer(planned_liquid_transfer)

    def _create_executed_liquid_transfer(self, planned_liquid_transfer):
        """
        Creates the executed liquid transfer for a planned liquid transfer
        and stored it in the :attr:`_executed_worklist`.
        """

        target_pos = planned_liquid_transfer.target_position
        if not target_pos in self.ignored_positions:
            container = self._target_containers[target_pos]
            elt = ExecutedSampleDilution(user=self.user,
                                target_container=container,
                                reservoir_specs=self.reservoir_specs,
                                planned_sample_dilution=planned_liquid_transfer,
                                timestamp=self.now)
            self._executed_worklist.executed_liquid_transfers.append(elt)


class SampleTransferWorklistExecutor(WorklistExecutor):
    """
    An executor for sample transfer worklists.

    **Return Value:** An executed worklist
        (:class:`thelma.models.liquidtransfer.ExecutedWorklist`).
    """

    NAME = 'Container Transfer Worklist Executor'

    TRANSFER_TYPE = TRANSFER_TYPES.SAMPLE_TRANSFER

    def __init__(self, planned_worklist, user, target_rack, source_rack, log,
                 pipetting_specs, ignored_positions=None):
        """
        Constructor:

        :param planned_worklist: The worklist to execute.
        :type planned_worklist:
            :class:`thelma.models.liquidtransfer.PlannedWorklist`

        :param user: The user who has launched the execution.
        :type user: :class:`thelma.models.user.User`

        :param target_rack: The rack into which the volumes will be dispensed.
        :type target_rack: :class:`thelma.models.rack.Rack`

        :param source_rack: The source from which to take the volumes.
        :type source_rack: :class:`thelma.models.rack.Rack`

        :param log: The ThelmaLog you want to write into.
        :type log: :class:`thelma.ThelmaLog`

        :param pipetting_specs: Pipetting specs define transfer properties and
            conditions like the transfer volume range.
        :type pipetting_specs:
            :class:`thelma.models.liquidtransfer.PipettingSpecs`

        :param ignored_positions: A list of positions (target
            for dilutions and source for transfers) that are not included
            in the DB execution.
        :type ignored_positions: :class:`list` of :class:`RackPosition`
        """
        WorklistExecutor.__init__(self, log=log, target_rack=target_rack,
                                  planned_worklist=planned_worklist,
                                  ignored_positions=ignored_positions,
                                  pipetting_specs=pipetting_specs,
                                  user=user)

        #: The source from which to take the volumes.
        self.source_rack = source_rack

    def _check_input(self):
        """
        Checks the input values.
        """
        WorklistExecutor._check_input(self)

        self._check_input_class('source rack', self.source_rack, Rack)

    def _init_source_data(self):
        """
        Initialises the source rack related values and lookups.
        """
        for container in self.source_rack.containers:
            rack_pos = container.location.position
            self._source_containers[rack_pos] = container

        if isinstance(self.source_rack, Plate):
            well_specs = self.source_rack.specs.well_specs
            self._source_dead_volume = well_specs.dead_volume \
                                      * VOLUME_CONVERSION_FACTOR

    def _register_transfer(self, planned_liquid_transfer):
        """
        Planned liquid transfers are planned container transfers.
        """
        trg_pos = planned_liquid_transfer.target_position
        src_pos = planned_liquid_transfer.source_position

        if src_pos in self.ignored_positions:
            pass
        elif not self._source_containers.has_key(src_pos):
            self._source_container_missing.add(src_pos.label)
        elif not self._target_containers.has_key(trg_pos):
            self._target_container_missing.append(trg_pos.label)
        else:
            source_sample = self._get_source_sample(src_pos)
            if not source_sample is None:
                transfer_sample = source_sample.create_and_add_transfer(
                                                        planned_liquid_transfer)
                target_sample = self._get_target_sample(trg_pos)
                target_sample.add_transfer(transfer_sample)

    def _update_racks(self):
        """
        Updates the racks involved in the transfer.
        """
        WorklistExecutor._update_racks(self)
        self._update_rack(self.source_rack, self._source_samples)

    def _create_executed_liquid_transfer(self, planned_liquid_transfer):
        """
        Creates the executed liquid transfer for a planned liquid transfer
        and stored it in the :attr:`_executed_worklist`.
        """

        source_pos = planned_liquid_transfer.source_position
        if not source_pos in self.ignored_positions:
            source_container = self._source_containers[source_pos]
            target_container = self._target_containers[
                                        planned_liquid_transfer.target_position]
            elt = ExecutedSampleTransfer(user=self.user,
                            source_container=source_container,
                            target_container=target_container,
                            planned_sample_transfer=planned_liquid_transfer,
                            timestamp=self.now)
            self._executed_worklist.executed_liquid_transfers.append(elt)


class RackSampleTransferExecutor(LiquidTransferExecutor):
    """
    An executor for a (single) rack sample transfer.

    :Note: This is a special executor. Source wells without volume are
        omitted silently.

    *Return Value:* Executed Rack Sample Transfer
    """

    NAME = 'Rack Transfer Executor'

    TRANSFER_TYPE = TRANSFER_TYPES.RACK_SAMPLE_TRANSFER

    def __init__(self, planned_rack_transfer, target_rack, source_rack, user,
                 log, pipetting_specs=None):
        """
        Constructor:

        :param planned_rack_transfer: The planned rack transfer to execute.
        :type planned_rack_transfer:
            :class:`thelma.models.liquidtransfer.PlannedRackTransfer`

        :param target_rack: The rack into which the volumes will be dispensed.
        :type target_rack: :class:`thelma.models.rack.Rack`

        :param source_rack: The source from which to take the volumes.
        :type source_rack: :class:`thelma.models.rack.Rack`

        :param user: The user who has launched the execution.
        :type user: :class:`thelma.models.user.User`

        :param log: The ThelmaLog you want to write into.
        :type log: :class:`thelma.ThelmaLog`

        :param pipetting_specs: Pipetting specs define transfer properties and
            conditions like the transfer volume range.
        :type pipetting_specs:
            :class:`thelma.models.liquidtransfer.PipettingSpecs`
        :default pipetting_specs: None (CYBIO)
        """
        LiquidTransferExecutor.__init__(self, target_rack=target_rack,
                                        pipetting_specs=pipetting_specs,
                                        user=user, log=log)

        #: The planned rack transfer to execute.
        self.planned_rack_transfer = planned_rack_transfer
        #: The source from which to take the volumes.
        self.source_rack = source_rack

        if self.pipetting_specs is None:
            self.pipetting_specs = get_pipetting_specs_cybio()

        #: Translates the rack positions of one rack into another.
        self._translator = None
        #: The translation behaviour in case of sectors (see
        #: :class:`thelma.automation.tool.utils.racksector.RackSectorTranslator`)
        self.__translation_behaviour = None

        #: Is this a rack transfer within the same rack?
        self.__is_intra_rack_transfer = False

    def reset(self):
        """
        Resets all values except for input values.
        """
        LiquidTransferExecutor.reset(self)
        self._translator = None
        self.__translation_behaviour = None
        self.__is_intra_rack_transfer = False

    def _check_input(self):
        """
        Checks the input values.
        """
        LiquidTransferExecutor._check_input(self)

        self._check_input_class('planned rack sample transfer',
                        self.planned_rack_transfer, PlannedRackSampleTransfer)
        self._check_input_class('source rack', self.source_rack, Rack)

    def _init_source_data(self):
        """
        Initialises the source rack related values and lookups. Also checks
        the rack shape and translation type match and the transfer volume.
        """
        for container in self.source_rack.containers:
            rack_pos = container.location.position
            self._source_containers[rack_pos] = container

        if isinstance(self.source_rack, Plate):
            well_specs = self.source_rack.specs.well_specs
            self._source_dead_volume = well_specs.dead_volume \
                                      * VOLUME_CONVERSION_FACTOR

        if self.source_rack.barcode == self.target_rack.barcode:
            self.__is_intra_rack_transfer = True
        self.__setup_translator()
        if not self.has_errors():
            self.__check_shape_and_sector_match()
            self._is_valid_transfer_volume(self.planned_rack_transfer)

    def __setup_translator(self):
        """
        Initialises the rack position translator and sets the translation
        method.
        """
        src_shape = self.source_rack.rack_shape
        trg_shape = self.target_rack.rack_shape

        if self.__is_intra_rack_transfer:
            self.__translation_behaviour = RackSectorTranslator.MANY_TO_MANY
        else:
            self.__translation_behaviour = RackSectorTranslator.\
                        get_translation_behaviour(
                        source_shape=src_shape, target_shape=trg_shape,
                        number_sectors=self.planned_rack_transfer.sector_number)

        try:
            self._translator = RackSectorTranslator.from_planned_rack_transfer(
                        planned_rack_transfer=self.planned_rack_transfer,
                        behaviour=self.__translation_behaviour)
        except ValueError as e:
            msg = 'Error when trying to initialise rack sector translator. ' \
                  'Details: %s' % (e)
            self.add_error(msg)

    def __check_shape_and_sector_match(self):
        """
        Checks whether the both rack (sectors) have a matching rack shape.
        """
        self.add_debug('Check rack shape matching ...')

        src_shape = self.source_rack.rack_shape
        trg_shape = self.target_rack.rack_shape
        shapes_match = check_rack_shape_match(source_shape=src_shape,
                          target_shape=trg_shape,
                          row_count=self._translator.row_count,
                          col_count=self._translator.col_count,
                          translation_behaviour=self.__translation_behaviour)

        if not shapes_match:
            msg = 'The shapes of the rack sectors do not match the planned ' \
                  'rack transfer. Source rack shape: %s, target rack ' \
                  'shape: %s, number of sectors: %i, source sector: %i, ' \
                  'target sector: %i, translation type: %s.' \
                  % (src_shape, trg_shape,
                     self.planned_rack_transfer.sector_number,
                     self.planned_rack_transfer.source_sector_index,
                     self.planned_rack_transfer.target_sector_index,
                     self.__translation_behaviour)
            self.add_error(msg)

        if self.__translation_behaviour == RackSectorTranslator.ONE_TO_MANY \
                and not self.planned_rack_transfer.target_sector_index == 0:
            msg = 'The target sector index for one to many translations must ' \
                  'be 0 (obtained: %i, source rack shape: %s, ' \
                  'target rack shape: %s!)' \
                   % (self.planned_rack_transfer.target_sector_index,
                      src_shape, trg_shape)
            self.add_error(msg)
        elif self.__translation_behaviour == RackSectorTranslator.MANY_TO_ONE \
                and not self.planned_rack_transfer.source_sector_index == 0:
            msg = 'The source sector index for many to one translations must ' \
                  'be 0 (obtained: %i, source rack shape: %s, ' \
                  'target rack shape: %s!)' \
                   % (self.planned_rack_transfer.source_sector_index,
                      src_shape, trg_shape)
            self.add_error(msg)

    def _register_planned_liquid_transfers(self):
        """
        Registers the planned liquid transfers. The transfer volume is equal for
        all single transfers and has already been checked before in the
        :func:`_init_source_data` method.
        """
        self.add_debug('Check rack transfer content ...')

        for container in self.source_rack.containers:
            if container.sample is None: continue
            sample = container.sample
            if sample.volume == 0: continue
            source_pos = container.location.position

            try:
                target_pos = self._translator.translate(source_pos)
            except ValueError as e:
                if self.__is_intra_rack_transfer: continue
                msg = 'Error when trying to find target position for ' \
                      'rack position: %s. Details: %s' \
                      % (str(source_pos), e)
                self.add_error(msg)
                break

            if not self._target_containers.has_key(target_pos):
                self._target_container_missing.append(target_pos.label)
                continue

            source_sample = self._get_source_sample(source_pos)
            if not source_sample is None:
                transfer_sample = source_sample.create_and_add_transfer(
                                                    self.planned_rack_transfer)
                target_sample = self._get_target_sample(target_pos)
                target_sample.add_transfer(transfer_sample)

    def _create_executed_items(self):
        """
        Creates the executed liquid transfers and worklists. This method should
        also set the return value.
        """
        self.return_value = ExecutedRackSampleTransfer(
                        source_rack=self.source_rack,
                        target_rack=self.target_rack, user=self.user,
                        planned_rack_transfer=self.planned_rack_transfer,
                        timestamp=self.now)

    def _create_executed_liquid_transfer(self, planned_liquid_transfer):
        """
        Creating of the executed items is already handled in
        :func:`_create_executed_items`.
        """
        pass

    def _update_racks(self):
        """
        Updates the racks involved in the transfer.
        """
        LiquidTransferExecutor._update_racks(self)
        self._update_rack(self.source_rack, self._source_samples)

    def _get_target_tubes(self):
        """
        Returns the tubes of the target container (for status updates).
        """
        if self.__translation_behaviour == RackSectorTranslator.ONE_TO_MANY:
            target_positions = get_positions_for_shape(
                                                    self.target_rack.rack_shape)
        else:
            target_positions = get_sector_positions(
                    sector_index=self.planned_rack_transfer.target_sector_index,
                    rack_shape=self.target_rack.rack_shape,
                    number_sectors=self.planned_rack_transfer.sector_number)

        tubes = []
        for rack_pos in target_positions:
            if self._target_containers.has_key(rack_pos):
                tube = self._target_containers[rack_pos]
                tubes.append(tube)

        return tubes


class SampleComponent(object):
    """
    A helper class representing a component of a liquid (sample). It stores
    a concentration and molecule. The volume is left at the sample, since
    a sample might comprise several components.

    :Note: This class is similar to :class:`thelma.models.sample.SampleMolecule`
    """
    def __init__(self, molecule, concentration):
        """
        Constructor:

        :param molecule: The molecule being the component.
        :type molecule: :class:`thelma.models.sample.Molecule`

        :param concentration: The concentration of the molecule *in M*.
        :type concentration: positive number.
        """
        #: The molecule being the component.
        self.molecule = molecule
        #: The concentration of the molecule *in nM*.
        self.concentration = concentration * CONCENTRATION_CONVERSION_FACTOR

    @property
    def molecule_design(self):
        """
        The molecule design of the molecule.
        """
        return self.molecule.molecule_design

    def __str__(self):
        return '%s-%.02f' % (self.molecule_design.id, self.concentration)

    def __repr__(self):
        str_format = '<%s molecule: %s, molecule design: %s, ' \
                     'concentration: %.2f nM>'
        params = (self.__class__.__name__, self.molecule,
                  self.molecule_design, self.concentration)
        return str_format % params


class SampleData(object):
    """
    A container class storing all relevant data for the liquid involved
    in the transfer. The liquid can either be the source sample, the
    target sample or the volume that is actually transferred
    There are specialised subclasses for each case.

    The object intrisically convert database units (l and M) into working
    units (ul and nM).
    On update, the values are rounded and converted back.
    """

    def __init__(self, volume):
        """
        Constructor:

        :param volume: The volume of the liquid *in l*.
        :type volume: positive number
        """
        if self.__class__ is SampleData:
            raise TypeError('Abstract class')

        #: The volume of the liquid *in ul*.
        self.volume = volume * VOLUME_CONVERSION_FACTOR

        #: The components making up that liquid (0-n).
        self._sample_components = dict()

    @classmethod
    def from_sample(cls, sample):
        """
        Factory method creating a :class:`SampleData` from a sample entity.

        :Note: The sample is allowed to be *None*.

        :param sample: The sample data object.
        :type sample: :class:`thelma.models.sample.Sample`

        :return: :class:`SampleData` object representing that sample.
        """
        if sample is None: return None

        sample_data = cls(volume=sample.volume)

        for sm in sample.sample_molecules:
            sample_data.add_sample_component(sm)

        return sample_data

    def add_sample_component(self, sample_molecule):
        """
        Creates and registers a :class:`SampleComponent` object using the
        pass sample molecule.

        :raises ValueError: If there is already a component with this
            molecule design ID.
        """
        comp = SampleComponent(molecule=sample_molecule.molecule,
                               concentration=sample_molecule.concentration)

        md_id = sample_molecule.molecule.molecule_design.id
        if self._sample_components.has_key(md_id):
            raise ValueError('Duplicate sample component: %s' % (comp))
        self._sample_components[md_id] = comp

    def update_container_sample(self, container):
        """
        Updates the passed container reflecting its state after transfer
        execution.
        """
        raise NotImplementedError('Abstract method')

    def __str__(self):
        return '%.1f ul' % (self.volume)

    def __repr__(self):
        str_format = '<%s volume: %.1f ul, components: %s>'
        params = (self.__class__.__name__, self.volume,
                  self._sample_components.values())
        return str_format % params


class TransferredSample(SampleData):
    """
    A special :class:`SampleData` class for transferred volumes.
    Transfer sample do not get updated.
    """

    def __init__(self, volume):
        """
        Constructor:

        :param volume: The volume of the liquid *in l*.
        :type volume: positive number
        """
        SampleData.__init__(self, volume=volume)

    @property
    def sample_components(self):
        """
        The components making up that liquid.
        """
        return self._sample_components

    @classmethod
    def from_sample(cls, sample):
        """
        Transfer sample are temporary. They are not attached to sample entities.
        """
        raise NotImplementedError('Transfer samples are not attached to ' \
                                  'sample entities.')

    def add_source_sample_components(self, sample_components):
        """
        Adds the sample components of the source sample.

        :param sample_components: The sample components of the source sample.
        :type sample_components: :class:`list`
        """
        self._sample_components = sample_components

    def update_container_sample(self, container):
        """
        Transfer sample are not associated with containers.
        """
        raise NotImplementedError('Transfers are not stored in containers!')


class SourceSample(SampleData):
    """
    A special :class:`SampleData` class for source sample. They might contain
    any number of :class:`TransferredSample` object.

    The class calculate the final volume of the sample using all registered
    :class:`TransferredSample` objects. :attr:`volume` refers to the original
    source sample volume. SampleComponent objects (SampleMolecule objects) are
    not altered.
    """

    def __init__(self, volume):
        """
        Constructor:

        :param volume: The volume of the liquid *in l*.
        :type volume: positive number
        """
        SampleData.__init__(self, volume=volume)

        #: All transfers using this sample as source.
        self.__transfers = []

    @property
    def total_transfer_volume(self):
        """
        The volume required to provide liquid for all registered transfers.
        """
        total_transfer_volume = 0
        for transfer_sample in self.__transfers:
            total_transfer_volume += transfer_sample.volume

        return total_transfer_volume

    def create_and_add_transfer(self, planned_liquid_transfer):
        """
        Creates, registers and returns a :class:`TransferredSample` object using
        a planned liquid transfer as input.

        :param planned_liquid_transfer: The planned liquid transfer.
        :type: :class:`thelma.models.liquidtransfer.PlannedSampleTransfer` or
            :class:`thelma.models.liquidtransfer.PlannedRackSampleTransfer`
        :raises TypeErrors: in case of invalid planned transfer type

        :return: The generated :class:`TransferredSample` object.
        """
        valid_types = (PlannedSampleTransfer, PlannedRackSampleTransfer)
        if not isinstance(planned_liquid_transfer, valid_types):
            msg = 'Unsupported type "%s"' \
                   % (planned_liquid_transfer.__class__.__name__)
            raise TypeError(msg)

        transfer_sample = TransferredSample(volume=\
                                            planned_liquid_transfer.volume)
        transfer_sample.add_source_sample_components(self._sample_components)
        self.__transfers.append(transfer_sample)

        return transfer_sample

    def update_container_sample(self, container):
        """
        Updates the passed container reflecting its state after transfer
        execution. In case of source sample, we only need to adjust the
        volume.
        """
        if container.sample is None: return None

        final_volume = self.volume - self.total_transfer_volume
        final_volume = round(final_volume, 1)
        container.sample.volume = final_volume / VOLUME_CONVERSION_FACTOR
        return container.sample

    def __repr__(self):
        str_format = '<%s volume: %.1f ul, components: %s, number of ' \
                     'transfers: %s, total transfer volume: %s>'
        params = (self.__class__.__name__, self.volume,
                  self._sample_components.values(), len(self.__transfers),
                  self.total_transfer_volume)
        return str_format % params


class TargetSample(SampleData):
    """
    A special :class:`SampleData` class for source sample. They might contain
    up to one transfer samples.

    The class calculate the final volume of the sample using the registered
    :class:`TransferredSample` object. Also sample components are updated or
    added.
    """

    def __init__(self, volume):
        """
        Constructor:

        :param volume: The volume of the liquid *in l*.
        :type volume: positive number
        """
        SampleData.__init__(self, volume=volume)

        #: The transfer (singular!) using this sample as target.
        self.__transfer = None

    @property
    def final_volume(self):
        """
        The volume of the sample after the transfer.
        """
        if self.__transfer is None: return self.volume
        return self.volume + self.__transfer.volume

    def create_and_add_transfer(self, planned_sample_dilution):
        """
        Creates, registers and returns a :class:`TransferredSample` object using
        a planned container dilution as input.

        :Note: invokes :func:`add_transfer`

        :param planned_sample_dilution: The planned container dilution.
        :type: :class:`thelma.models.liquidtransfer.PlannedSampleDilution`
        :raises TypeErrors: in case of invalid transfer type
        :raises AttributeError: If there is already a transfer present.

        :return: The generated :class:`TransferredSample` object.
        """
        if not isinstance(planned_sample_dilution, PlannedSampleDilution):
            msg = 'Unsupported type "%s"' \
                   % (planned_sample_dilution.__class__.__name__)
            raise TypeError(msg)

        transfer_sample = TransferredSample(volume=\
                                            planned_sample_dilution.volume)
        self.add_transfer(transfer_sample)

        return transfer_sample

    def add_transfer(self, transfer_sample):
        """
        Registers pass transfer sample.

        :raises AttributeError: If there is already a transfer present.
        """
        if not self.__transfer is None:
            raise AttributeError('There is already a transfer registered!')

        self.__transfer = transfer_sample

    def update_container_sample(self, container):
        """
        Updates the passed container reflecting its state after transfer
        execution. In case of target sample, we adjust the volumes and the
        sample components.
        """
        final_volume = round(self.final_volume, 1)
        conv_final_volume = final_volume / VOLUME_CONVERSION_FACTOR
        if are_equal_values(final_volume, 0):
            return None
        elif container.sample is None:
            container.make_sample(conv_final_volume)
        else:
            container.sample.volume = conv_final_volume

        updated_mds = set()
        transfer_components = dict()
        if not self.__transfer is None:
            transfer_components = self.__transfer.sample_components

        # update existing sample molecules
        for sm in container.sample.sample_molecules:
            md_id = sm.molecule.molecule_design.id
            updated_mds.add(md_id)
            target_comp = self._sample_components[md_id]

            if transfer_components.has_key(md_id):
                transfer_conc = transfer_components[md_id].concentration
            else:
                transfer_conc = 0
            final_conc = self.__get_final_concentration(
                                    target_comp.concentration, transfer_conc)
            sm.concentration = final_conc / CONCENTRATION_CONVERSION_FACTOR

        # add new sample molecules
        for md_id, comp in transfer_components.iteritems():
            if md_id in updated_mds: continue
            final_conc = self.__get_final_concentration(0, comp.concentration)
            conv_final_conc = final_conc / CONCENTRATION_CONVERSION_FACTOR
            container.sample.make_sample_molecule(comp.molecule,
                                                  conv_final_conc)

        return container.sample

    def __get_final_concentration(self, target_conc, transfer_conc):
        """
        Calculates the final concentration of a sample component using the
        following formula:

                    (targetConc * targetVol) + (transferConc * transferVol)
        finalConc = -------------------------------------------------------
                                        finalVol
        """
        transfer_volume = 0
        if not self.__transfer is None: transfer_volume = self.__transfer.volume

        target_product = target_conc * self.volume
        transfer_product = transfer_conc * transfer_volume
        final_conc = (target_product + transfer_product) / self.final_volume

        final_conc = round(final_conc, 2)
        return final_conc

    def __repr__(self):
        str_format = '<%s volume: %.1f ul, components: %s, transfer: %s>'
        params = (self.__class__.__name__, self.volume, self._sample_components,
                  self.__transfer)
        return str_format % params

