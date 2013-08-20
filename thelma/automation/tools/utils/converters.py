"""
:Date: 03 Aug 2011
:Author: AAB, berger at cenix-bioscience dot com

This module converts a normal layout into an IsoLayout (or an
IsoPosition map).
"""

from everest.entities.utils import get_root_aggregate
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.tools.semiconstants import get_positions_for_shape
from thelma.automation.tools.utils.base import FIXED_POSITION_TYPE
from thelma.automation.tools.utils.base import LibraryLayout
from thelma.automation.tools.utils.base import LibraryLayoutParameters
from thelma.automation.tools.utils.base import LibraryLayoutPosition
from thelma.automation.tools.utils.base import MoleculeDesignPoolLayout
from thelma.automation.tools.utils.base import MoleculeDesignPoolParameters
from thelma.automation.tools.utils.base import MoleculeDesignPoolPosition
from thelma.automation.tools.utils.base import TransferLayout
from thelma.automation.tools.utils.base import TransferParameters
from thelma.automation.tools.utils.base import TransferPosition
from thelma.automation.tools.utils.base import WorkingPosition
from thelma.automation.tools.utils.base import is_valid_number
from thelma.interfaces import IMoleculeDesignPool
from thelma.models.racklayout import RackLayout

__docformat__ = 'reStructuredText en'

__author__ = 'Anna-Antonia Berger'

__all__ = ['BaseLayoutConverter',
           'TransferLayoutConverter',
           'MoleculeDesignPoolLayoutConverter',
           'LibraryLayoutConverter']


class BaseLayoutConverter(BaseAutomationTool):
    """
    A super class for tools that generated working layouts
    (:class:`thelma.automation.tools.utils.base.WorkingLayout`).
    Each converter is associated to special working layout class.
    """

    #: The parameter set for the
    #: (:class:`thelma.automation.tools.utils.base.ParameterSet`)
    PARAMETER_SET = None
    #: The class of layout to be generated (subclass of :class:`WorkingLayout`)
    WORKING_LAYOUT_CLS = None
    #: The class of the working positions to be generated (subclass of
    #: :class:`WorkingPosition`).
    WORKING_POSITION_CLS = None

    # A key for the rack position in the parameter map generated during
    # the conversion.
    _RACK_POSITION_KEY = 'rack_position'

    def __init__(self, rack_layout, log):
        """
        Constructor:

        :param rack_layout: The rack layout containing the ISO data.
        :type rack_layout: :class:`thelma.models.racklayout.RackLayout`
        :param log: The ThelmaLog you want to write in. If the
            log is None, the object will create a new log.
        :type log: :class:`thelma.ThelmaLog`
        """
        BaseAutomationTool.__init__(self, log)

        #: The rack layout containing the data for the working layout.
        self.rack_layout = rack_layout

        #: A map containing the validator objects for each parameter
        #: (:class:`thelma.automation.tools.utils.base.ParameterAliasValidator`).
        self.parameter_validators = None

        #: Maps the derived WorkingPositions onto rack positions.
        self.position_map = None

        #: A list of optional parameters which do not have to be specified
        #: in the layout at all.
        self.optional_parameters = None

        #: Lists for intermediate error storage.
        self._multiple_tags = None

    def reset(self):
        """
        Resets all attributes except for the :attr:`rack_layout`.
        """
        BaseAutomationTool.reset(self)
        self.position_map = dict()
        self.parameter_validators = None
        self.optional_parameters = []
        self._multiple_tags = []

    def run(self):
        """
        Runs the conversion.
        """
        self.reset()
        self.add_info('Start conversion ...')

        self.__check_input_values()
        if not self.has_errors():
            self._initialize_parameter_validators()
            self._initialize_other_attributes()
            self.__check_parameter_completeness()
        if not self.has_errors():
            for rack_position in get_positions_for_shape(self.rack_layout.shape):
                tag_set = self.rack_layout.get_tags_for_position(rack_position)
                parameter_map = self._get_parameter_map(tag_set, rack_position)
                working_position = self.__obtain_working_position(parameter_map)
                self.position_map[rack_position] = working_position
        self.__record_common_errors()
        self._record_additional_position_errors()

        if not self.has_errors():
            self.return_value = self.__create_layout_from_map()
            self.add_info('Layout conversion completed.')

    def __check_input_values(self):
        """
        Checks the validity of the initialisation values.
        """
        if not isinstance(self.rack_layout, RackLayout):
            msg = 'The rack layout must be a RackLayout object (obtained: ' \
                  '%s).' % (self.rack_layout.__class__.__name__)
            self.add_error(msg)

    def _initialize_parameter_validators(self):
        """
        Initialises all parameter validators for the tools
        :attr:`PARAMETER_SET`. Overwrite this method if you want to have
        other validators.

        All parameters which are not in the :attr:`REQUIRED` list are
        set as optional.
        """
        self.parameter_validators = self.PARAMETER_SET.create_all_validators()

        for parameter in self.PARAMETER_SET.ALL:
            if not parameter in self.PARAMETER_SET.REQUIRED:
                self.optional_parameters.append(parameter)

    def _initialize_other_attributes(self):
        """
        Use this method to initialise attributes that have to be set
        before position generation.
        """
        pass

    def __check_parameter_completeness(self):
        """
        Checks whether there are tags for all required parameters in the
        source rack layout.
        """

        self.add_debug('Check completeness of the required parameters ...')

        all_predicates = set()
        for tag in self.rack_layout.get_tags():
            all_predicates.add(tag.predicate)

        has_tag_map = dict()
        for parameter, validator in self.parameter_validators.iteritems():
            has_tag_map[parameter] = False
            for predicate in all_predicates:
                if validator.has_alias(predicate):
                    has_tag_map[parameter] = True

        for parameter, has_tag in has_tag_map.iteritems():
            if not has_tag and not parameter in self.optional_parameters:
                msg = 'There is no %s specification for this rack layout. ' \
                       'Valid factor names are: %s (case-insensitive).' \
                    % (parameter,
                       list(self.parameter_validators[parameter].aliases))
                self.add_error(msg)

    def _get_parameter_map(self, tag_set, rack_position):
        """
        Returns a dictionary containing the parameter values for a
        rack position.
        """

        self.add_debug('Get parameter map for rack position %s ...' \
                       % (rack_position))

        parameter_map = {self._RACK_POSITION_KEY : rack_position}
        for parameter in self.parameter_validators.keys():
            parameter_map[parameter] = None

        for tag in tag_set:
            #: Find parameter for this tag (if any).
            predicate = None
            for parameter, validator in self.parameter_validators.iteritems():
                if validator.has_alias(tag.predicate):
                    predicate = parameter
                    break
            if predicate is None: continue
            value = tag.value
            if value == WorkingPosition.NONE_REPLACER: value = None
            if not parameter_map[predicate.lower()] is None:
                info = '%s ("%s")' % (rack_position, tag.predicate)
                self._multiple_tags.append(info)
            parameter_map[predicate] = value

        return parameter_map

    def __obtain_working_position(self, parameter_map): #pylint: disable=W0613
        """
        Derives a working position from a parameter map (including validity
        checks). Invokes :func:`_get_position_keywords_and_values`.
        """
        kw = self._get_position_init_values(parameter_map)
        if kw is None: return None

        working_pos = self.WORKING_POSITION_CLS(**kw) #pylint: disable=E1102
        return working_pos

    def _get_position_init_values(self, parameter_map): #pylint: disable=W0613
        """
        Derives all values required to initialize new working position
        (including validity checks) as keyqord dictionary. If everything
        is fine the keyword dictionary will be used to create a new
        working position, otherwise there are records stored in the
        intermediate error sotrage lists and *None* is returned.
        """
        raise NotImplementedError('Abstract method')

    def __record_common_errors(self):
        """
        This method records errors that can occur in all subclasses.
        """
        if len(self._multiple_tags) > 0:
            msg = 'Some parameter have been specified multiple times for ' \
                  'the same rack position: %s.' % (self._multiple_tags)
            self.add_error(msg)

    def _record_additional_position_errors(self):
        """
        This method is meant to raise/record errors and warnings that have been
        collected during parameter map and working position generation.
        The errors could in theory also be recorded during execution.
        However, lots of similar errors that only differ in rack positions
        specification might spam the log, that's why you can store the
        referring rack position and launch the log events here.
        """
        raise NotImplementedError('Abstract method')

    def __create_layout_from_map(self):
        """
        Creates the actual working layout object.
        """
        self.add_debug('Convert position map into working layout.')

        working_layout = self._initialize_working_layout(self.rack_layout.shape)
        for rack_position in get_positions_for_shape(self.rack_layout.shape):
            working_position = self.position_map[rack_position]
            if working_position is None: continue
            try:
                working_layout.add_position(working_position)
            except TypeError:
                msg = 'You can only add %s objects to this layout. You have ' \
                      'tried to add a %s object. This is a programming error .' \
                      'Please contact the IT department.' \
                      % (self.WORKING_POSITION_CLS.__name__,
                         working_position.__class__.__name__)
                self.add_error(msg)
                break
            except ValueError, errmsg:
                self.add_error(errmsg)
                break

        if self.has_errors(): return None
        self._perform_layout_validity_checks(working_layout)
        if self.has_errors(): return None
        return working_layout

    def _initialize_working_layout(self, shape):
        """
        Initialises the working layout.
        """
        kw = dict(shape=shape)
        return self.WORKING_LAYOUT_CLS(**kw) #pylint: disable=E1102

    def _perform_layout_validity_checks(self, working_layout):
        """
        Use this method to check the validity of the generated layout.
        """
        raise NotImplementedError('Abstract method')


class MoleculeDesignPoolLayoutConverter(BaseLayoutConverter): #pylint: disable=W0223
    """
    Abstract base class converting an rack_layout into an molecule design pool
    layout
    (:class:`thelma.automation.tools.utils.base.MoleculeDesignPoolLayout`).

    :Note: Untreated positions are converted to empty positions.
    """

    PARAMETER_SET = MoleculeDesignPoolParameters
    WORKING_LAYOUT_CLS = MoleculeDesignPoolLayout
    WORKING_POSITION_CLS = MoleculeDesignPoolPosition

    def __init__(self, rack_layout, log):
        """
        Constructor:

        :param rack_layout: The rack layout containing the ISO data.
        :type rack_layout: :class:`thelma.models.racklayout.RackLayout`

        :param log: The ThelmaLog you want to write in. If the
            log is None, the object will create a new log.
        :type log: :class:`thelma.ThelmaLog`
        """
        BaseLayoutConverter.__init__(self, rack_layout=rack_layout, log=log)

        if self.__class__ == MoleculeDesignPoolLayoutConverter:
            msg = 'This is an abstract class!'
            self.add_error(msg)

        #: The molecule design pool aggregate
        #: (see :class:`thelma.models.aggregates.Aggregate`)
        #: used to obtain check the validity of molecule design pool IDs.
        self._pool_aggregate = get_root_aggregate(IMoleculeDesignPool)
        #: Stores the molecule design pools for molecule design pool IDs.
        self._pool_map = None

        # intermediate storage of invalid rack positions
        self._unknown_pools = None
        self._invalid_pos_type = None

    def reset(self):
        BaseLayoutConverter.reset(self)
        self._pool_map = dict()
        self._unknown_pools = []
        self._invalid_pos_type = set()

    def _determine_position_type(self, pool_id):
        """
        Determines the position type for a molecule design pool.
        """
        if is_valid_number(pool_id, is_integer=True):
            return FIXED_POSITION_TYPE

        try:
            pos_type = self.PARAMETER_SET.get_position_type(pool_id)
        except ValueError:
            self._invalid_pos_type.add(pool_id)
            return None
        else:
            return pos_type

    def _get_molecule_design_pool_for_id(self, pool_id, position_label):
        """
        Checks whether the molecule design pool for a fixed position is a
        valid one.
        """
        if self._pool_map.has_key(pool_id):
            return self._pool_map[pool_id]

        if not is_valid_number(pool_id, is_integer=True):
            info = '%s (%s)' % (pool_id, position_label)
            self._unknown_pools.append(info)
            return None

        entity = self._pool_aggregate.get_by_id(pool_id)
        if entity is None:
            info = '%s (%s)' % (pool_id, position_label)
            self._unknown_pools.append(info)
            return None

        self._pool_map[pool_id] = entity
        return entity

    def _record_additional_position_errors(self):
        """
        Launches collected position errors.
        """
        if len(self._unknown_pools) > 0:
            msg = 'Some molecule design pool IDs could not be found in the ' \
                  'DB: %s.' % (', '.join(sorted(self._unknown_pools)))
            self.add_error(msg)

        if len(self._invalid_pos_type) > 0:
            msg = 'Unable to determine position types for the following ' \
                  'pool IDs: %s.' % (', '.join(sorted(
                                                list(self._invalid_pos_type))))
            self.add_error(msg)

    def _perform_layout_validity_checks(self, working_layout):
        """
        There are no checks to be performed. However, we want to remove
        unnecessary empty positions.
        """
        working_layout.close()


class TransferLayoutConverter(MoleculeDesignPoolLayoutConverter): #pylint: disable=W0223
    """
    Converts an rack_layout into a TransferLayout
    (:class:`thelma.automation.tools.utils.transfer.TransferLayout`).
    """

    NAME = 'Transfer Layout Converter'

    PARAMETER_SET = TransferParameters
    WORKING_LAYOUT_CLS = TransferLayout
    WORKING_POSITION_CLS = TransferPosition

    def __init__(self, rack_layout, log):
        """
        Constructor:

        :param rack_layout: The rack layout containing the transfer data.
        :type rack_layout: :class:`thelma.models.racklayout.RackLayout`

        :param log: The ThelmaLog you want to write in. If the
            log is None, the object will create a new log.
        :type log: :class:`thelma.ThelmaLog`
        """
        MoleculeDesignPoolLayoutConverter.__init__(self, log=log,
                                                   rack_layout=rack_layout)

        #: Stores the target wells (for consistency checking).
        self._transfer_targets = None

        # intermediate storage of invalid rack positions
        self.__invalid_target_string = None
        self.__duplicate_targets = None
        self.__missing_transfer_target = None

    def reset(self):
        """
        Resets all attributes except for the :attr:`rack_layout`.
        """
        MoleculeDesignPoolLayoutConverter.reset(self)
        self.__invalid_target_string = dict()
        self.__duplicate_targets = dict()
        self.__missing_transfer_target = dict()
        self._transfer_targets = dict()

    def _initialize_other_attributes(self):
        """
        Initialises the target well storage.
        """
        self._transfer_targets = dict()
        for parameter in self.PARAMETER_SET.TRANSFER_TARGET_PARAMETERS:
            self._transfer_targets[parameter] = []

    def _get_parameter_map(self, tag_set, rack_position):
        """
        Returns a dictionary containing the parameter values for a
        rack position.
        """
        self.add_debug('Get parameter map for rack position %s ...' \
                       % (rack_position))

        parameter_map = {self._RACK_POSITION_KEY : rack_position}
        for parameter in self.parameter_validators.keys():
            parameter_map[parameter] = None

        for tag in tag_set:
            #: Find parameter for this tag (if any).
            predicate = None
            for parameter, validator in self.parameter_validators.iteritems():
                if validator.has_alias(tag.predicate):
                    predicate = parameter
                    break
            if predicate is None: continue
            value = tag.value
            if value == WorkingPosition.NONE_REPLACER: value = None
            if not parameter_map[predicate.lower()] is None:
                msg = 'Parameter "%s" for rack position %s has been ' \
                      'specified multiple times!' \
                      % (tag.predicate, rack_position)
                self.add_error(msg)

            if parameter in TransferParameters.TRANSFER_TARGET_PARAMETERS:
                value = self.__parse_target_tag_value(value, rack_position,
                                                      parameter_name=parameter)

            parameter_map[predicate] = value

        return parameter_map

    def __parse_target_tag_value(self, target_tag_value, rack_position,
                                 parameter_name):
        """
        Converts the value of a target tag into a TargetTransfer List.
        """
        if target_tag_value is None: return None
        try:
            transfer_targets = TransferPosition.parse_target_tag_value(
                                                            target_tag_value)
        except ValueError:
            error_msg = '"%s" (%s)' % (target_tag_value, rack_position.label)
            self.__invalid_target_string[parameter_name].append(error_msg)
            return None
        else:
            return transfer_targets

    def _are_valid_transfer_targets(self, transfer_targets, rack_position,
                                    parameter_name=None):
        """
        Stores the transfer targets and checks their consistency.
        """
        if transfer_targets is None:
            if self.PARAMETER_SET.must_have_transfer_targets(parameter_name):
                self.__missing_transfer_target[parameter_name].\
                        append(rack_position.label)
                return False
            else:
                return True

        for transfer_target in transfer_targets:
            if transfer_target.position_label in self._transfer_targets[
                                                            parameter_name]:
                error_msg = '%s (source: %s)' % (
                                   transfer_target.position_label,
                                   rack_position.label)
                self.__duplicate_targets[parameter_name].append(error_msg)
                return False
            else:
                self._transfer_targets[parameter_name].append(
                                                transfer_target.position_label)

        return True

    def _record_additional_position_errors(self):
        """
        Records errors that have been collected for rack positions.
        """
        MoleculeDesignPoolLayoutConverter._record_additional_position_errors(
                                                                        self)

        if len(self.__invalid_target_string) > 0:
            msg = 'The following rack positions have invalid target position ' \
                  'descriptions: %s.' \
                   % (self.__get_error_record_string(
                                                self.__invalid_target_string))
            self.add_error(msg)

        if len(self.__duplicate_targets) > 0:
            msg = 'There are duplicate target positions: %s!' \
                  % (self.__get_error_record_string(self.__duplicate_targets))
            self.add_error(msg)

        if len(self.__missing_transfer_target) > 0:
            msg = '%s must have transfer targets. The transfer targets are ' \
                  'missing for the following positions: %s.' \
                  % (self.WORKING_POSITION_CLS.__name__,
                     self.__get_error_record_string(
                                            self.__missing_transfer_target))
            self.add_error(msg)

    def __get_error_record_string(self, recorded_events):
        """
        Generates a pretty detail string for error messages.
        """
        if len(self.PARAMETER_SET.TRANSFER_TARGET_PARAMETERS) == 1:
            infos = recorded_events.keys()[0]
            return ', '.join(infos)
        else:
            records = []
            for parameter, infos in recorded_events.iteritems():
                record = '%s: %s' % (parameter.replace('_', ' '),
                                     ', '.join(infos))
                records.append(record)
            return ' -- '.join(records)

    def _perform_layout_validity_checks(self, working_layout):
        """
        Use this method to check the validity of the generated layout.
        """
        pass


class LibraryLayoutConverter(BaseLayoutConverter):
    """
    Converts a :class:`thelma.models.racklayout.RackLayout` into a
    :class:`LibraryBaseLayout`.

    """
    NAME = 'Library Layout Converter'

    PARAMETER_SET = LibraryLayoutParameters
    WORKING_POSITION_CLS = LibraryLayoutPosition
    WORKING_LAYOUT_CLASS = LibraryLayout

    def __init__(self, rack_layout, log):
        """
        Constructor:

        :param rack_layout: The rack layout containing the ISO data.
        :type rack_layout: :class:`thelma.models.racklayout.RackLayout`

        :param log: The ThelmaLog you want to write in. If the
            log is None, the object will create a new log.
        :type log: :class:`thelma.ThelmaLog`
        """
        BaseLayoutConverter.__init__(self, rack_layout, log=log)

        # intermediate storage of invalid rack positions
        self.__invalid_flag = None

    def reset(self):
        BaseLayoutConverter.reset(self)
        self.__invalid_flag = []

    def _get_position_init_values(self, parameter_map):
        is_lib_pos_str = parameter_map[self.PARAMETER_SET.IS_LIBRARY_POS]
        rack_pos = parameter_map[self._RACK_POSITION_KEY]
        pos_label = rack_pos.label
        if is_lib_pos_str is None: return None

        try:
            is_lib_pos = self.WORKING_POSITION_CLS.parse_boolean_tag_value(
                                                                is_lib_pos_str)
        except ValueError:
            info = '%s (%s)' % (pos_label, is_lib_pos_str)
            self.__invalid_flag.append(info)
            return None

        return dict(rack_position=rack_pos, is_library_position=is_lib_pos)

    def _record_additional_position_errors(self):
        """
        Records specific errors that have been collection during position
        generation.
        """
        if len(self.__invalid_flag) > 0:
            msg = 'The "sample position" flag must be a boolean. The values ' \
                  'for some positions are invalid. Details: %s.' \
                  % (', '.join(sorted(self.__invalid_flag)))
            self.add_error(msg)

    def _perform_layout_validity_checks(self, working_layout):
        """
        We do not check anything but we close the layout.
        """
        working_layout.close()
