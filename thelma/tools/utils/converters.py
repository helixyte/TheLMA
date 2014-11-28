"""
:Date: 03 Aug 2011
:Author: AAB, berger at cenix-bioscience dot com

This module converts a normal layout into an IsoLayout (or an
IsoPosition map).
"""

from everest.entities.utils import get_root_aggregate
from thelma.tools.semiconstants import get_positions_for_shape
from thelma.tools.base import BaseTool
from thelma.tools.utils.base import add_list_map_element
from thelma.tools.utils.layouts import EMPTY_POSITION_TYPE
from thelma.tools.utils.layouts import LIBRARY_POSITION_TYPE
from thelma.tools.utils.layouts import LibraryBaseLayout
from thelma.tools.utils.layouts import LibraryBaseLayoutParameters
from thelma.tools.utils.layouts import LibraryBaseLayoutPosition
from thelma.tools.utils.layouts import MOCK_POSITION_TYPE
from thelma.tools.utils.layouts import MoleculeDesignPoolLayout
from thelma.tools.utils.layouts import MoleculeDesignPoolParameters
from thelma.tools.utils.layouts import MoleculeDesignPoolPosition
from thelma.tools.utils.layouts import ParameterSet
from thelma.tools.utils.layouts import TransferLayout
from thelma.tools.utils.layouts import TransferParameters
from thelma.tools.utils.layouts import TransferPosition
from thelma.tools.utils.layouts import WorkingLayout
from thelma.tools.utils.layouts import WorkingPosition
from thelma.tools.utils.layouts import is_valid_number
from thelma.interfaces import IMoleculeDesignPool
from thelma.entities.racklayout import RackLayout

__docformat__ = 'reStructuredText en'

__author__ = 'Anna-Antonia Berger'

__all__ = ['BaseLayoutConverter',
           'TransferLayoutConverter',
           'MoleculeDesignPoolLayoutConverter',
           'LibraryBaseLayoutConverter']


class BaseLayoutConverter(BaseTool):
    """
    A super class for tools that generated working layouts
    (:class:`thelma.tools.utils.layouts.WorkingLayout`) from
    rack layouts (:class:`thelma.entities.racklayout.RackLayout`).
    Each converter is associated to special working layout class.

    **Return Value:** :class:`thelma.tools.utils.layouts.WorkingLayout`
    """

    #: The parameter set for the
    #: (:class:`thelma.tools.utils.layouts.ParameterSet`)
    PARAMETER_SET = ParameterSet
    #: The class of layout to be generated (subclass of :class:`WorkingLayout`)
    LAYOUT_CLS = WorkingLayout
    #: The class of the working positions to be generated (subclass of
    #: :class:`WorkingPosition`).
    POSITION_CLS = WorkingPosition

    # A key for the rack position in the parameter map generated during
    # the conversion.
    _RACK_POSITION_KEY = 'rack_position'

    def __init__(self, rack_layout, parent=None):
        """
        Constructor.

        :param rack_layout: The rack layout containing the ISO data.
        :type rack_layout: :class:`thelma.entities.racklayout.RackLayout`
        """
        BaseTool.__init__(self, parent=parent)
        #: The rack layout containing the data for the working layout.
        self.rack_layout = rack_layout
        #: A map containing the validator objects for each parameter
        #: (:class:`thelma.tools.utils.base.ParameterAliasValidator`).
        self._parameter_validators = None
        #: Maps the derived WorkingPositions onto rack positions.
        self.__position_map = None
        #: Parameters which do not have to be specified in the layout at all.
        self._optional_parameters = None
        #: Lists for intermediate error storage.
        self._multiple_tags = None

    def reset(self):
        """
        Resets all attributes except for the :attr:`rack_layout`.
        """
        BaseTool.reset(self)
        self.__position_map = dict()
        self._parameter_validators = None
        self._optional_parameters = set()
        self._multiple_tags = []

    def run(self):
        """
        Runs the conversion.
        """
        self.reset()
        self.add_info('Start conversion ...')

        self._check_input()
        if not self.has_errors():
            self._initialize_parameter_validators()
            self._initialize_other_attributes()
            self.__check_parameter_completeness()
        if not self.has_errors():
            for rack_position in get_positions_for_shape(self.rack_layout.shape):
                tag_set = self.rack_layout.get_tags_for_position(rack_position)
                parameter_map = self._get_parameter_map(tag_set, rack_position)
                working_position = self.__obtain_working_position(parameter_map)
                self.__position_map[rack_position] = working_position
        self._record_errors()

        if not self.has_errors():
            self.return_value = self.__create_layout_from_map()
            self.add_info('Layout conversion completed.')

    def _check_input(self):
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
        self._parameter_validators = self.PARAMETER_SET.create_all_validators()

        for parameter in self.PARAMETER_SET.ALL:
            if not parameter in self.PARAMETER_SET.REQUIRED:
                self._optional_parameters.add(parameter)

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

        all_predicates = \
            set([tag.predicate for tag in self.rack_layout.get_tags()])
        has_tag_map = dict()
        for parameter, validator in self._parameter_validators.iteritems():
            has_tag_map[parameter] = \
                any((validator.has_alias(pred) for pred in all_predicates))
        for parameter, has_tag in has_tag_map.iteritems():
            if not has_tag and not parameter in self._optional_parameters:
                msg = 'There is no %s specification for this rack layout. ' \
                       'Valid factor names are: %s (case-insensitive).' \
                    % (parameter, self._get_joined_str(
                       self._parameter_validators[parameter].aliases))
                self.add_error(msg)

    def _get_parameter_map(self, tag_set, rack_position):
        """
        Returns a dictionary containing the parameter values for a
        rack position.
        """
        parameter_map = {self._RACK_POSITION_KEY : rack_position}
        for parameter in self._parameter_validators.keys():
            parameter_map[parameter] = None
        for tag in tag_set:
            #: Find parameter for this tag (if any).
            predicate = None
            for parameter, validator in self._parameter_validators.iteritems():
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

    def __obtain_working_position(self, parameter_map):
        """
        Derives a working position from a parameter map (including validity
        checks). Invokes :func:`_get_position_keywords_and_values`.
        """
        rack_pos = parameter_map[self._RACK_POSITION_KEY]
        kw = self._get_position_init_values(parameter_map, rack_pos)
        result = None
        if not kw is None:
            if not kw.has_key('rack_position'):
                kw['rack_position'] = rack_pos
            result = self.POSITION_CLS(**kw) #pylint: disable=E1102
        return result

    def _get_position_init_values(self, parameter_map, rack_pos):
        """
        Derives all values required to initialise new working position
        (including validity checks) as keyword dictionary. If everything
        is fine the keyword dictionary will be used to create a new
        working position, otherwise there are records stored in the
        intermediate error storage lists and *None* is returned.

        The rack position does not have to be included.
        """
        raise NotImplementedError('Abstract method')

    def _get_boolean_value(self, bool_str, pos_label, error_list):
        """
        Helper function converting a boolean string into boolean. If the
        conversion fails an error is recorded and None is returned.
        """
        if not self.POSITION_CLS.RECORD_FALSE_VALUES and bool_str is None:
            return False

        try:
            bool_value = self.POSITION_CLS.parse_boolean_tag_value(bool_str)
        except ValueError:
            info = '%s (%s)' % (pos_label, bool_str)
            error_list.append(info)
            return None

        return bool_value

    def _record_errors(self):
        """
        Records errors for events that might occur position for several
        positions (errors that have been collected during parameter map
        and working positions generation).
        """
        if len(self._multiple_tags) > 0:
            msg = 'Some parameter have been specified multiple times for ' \
                  'the same rack position: %s.' % (self._multiple_tags)
            self.add_error(msg)

    def _record_invalid_boolean_error(self, flag_name, error_list):
        """
        Helper method recording the error messsage for invalid booleans
        (see :func:`_record_errors`).
        """
        if len(error_list) > 0:
            msg = 'The "%s" flag must be a boolean. The values for ' \
                  'some positions are invalid. Details: %s.' \
                   % (flag_name, ', '.join(sorted(error_list)))
            self.add_error(msg)

    def __create_layout_from_map(self):
        """
        Creates the actual working layout object.
        """
        self.add_debug('Convert position map into working layout.')

        working_layout = self._initialize_working_layout(self.rack_layout.shape)
        for rack_position in get_positions_for_shape(self.rack_layout.shape):
            working_position = self.__position_map[rack_position]
            if working_position is None: continue
            self._run_and_record_error(working_layout.add_position,
                    base_msg='Error when trying to add position to layout: ',
                    error_types=set([ValueError, AttributeError, KeyError,
                                     TypeError]),
                    **dict(working_position=working_position))
            if self.has_errors(): break

        if self.has_errors(): return None
        self._perform_layout_validity_checks(working_layout)
        if self.has_errors(): return None
        return working_layout

    def _initialize_working_layout(self, shape):
        """
        Initialises the working layout.
        """
        kw = dict(shape=shape)
        return self.LAYOUT_CLS(**kw) #pylint: disable=E1102

    def _perform_layout_validity_checks(self, working_layout):
        """
        Use this method to check the validity of the generated layout.
        """
        raise NotImplementedError('Abstract method')


class MoleculeDesignPoolLayoutConverter(BaseLayoutConverter):
    """
    Abstract class converting a :class:`thelma.entities.racklayout.RackLayout`
    into an molecule design pool layout
    (:class:`thelma.tools.utils.layouts.MoleculeDesignPoolLayout`).

    :Note: Untreated and untransfected positions are converted to empty
    positions because these position type only serve documentational purposes.

    **Return Value:**
        :class:`thelma.tools.utils.layouts.MoleculeDesignPoolLayout`
    """

    PARAMETER_SET = MoleculeDesignPoolParameters
    LAYOUT_CLS = MoleculeDesignPoolLayout
    POSITION_CLS = MoleculeDesignPoolPosition

    def __init__(self, rack_layout, parent=None):
        BaseLayoutConverter.__init__(self, rack_layout, parent=parent)
        if self.__class__ is MoleculeDesignPoolLayoutConverter:
            msg = 'This is an abstract class!'
            self.add_error(msg)
        #: The molecule design pool aggregate
        #: (see :class:`thelma.entities.aggregates.Aggregate`)
        #: used to obtain check the validity of molecule design pool IDs.
        self.__pool_aggregate = get_root_aggregate(IMoleculeDesignPool)
        #: Stores the molecule design pools for molecule design pool IDs.
        self.__pool_map = None
        # intermediate storage of invalid rack positions
        self.__unknown_pools = None
        self.__invalid_pos_type = None
        self.__missing_pool = None
        self.__type_mismatch = None

    def reset(self):
        BaseLayoutConverter.reset(self)
        self.__pool_map = dict()
        self.__unknown_pools = []
        self.__invalid_pos_type = set()
        self.__missing_pool = set()
        self.__type_mismatch = set()

    def _get_position_init_values(self, parameter_map, rack_pos):
        """
        Make sure position type and pool comply with each other.
        """
        pool_id = parameter_map[self.PARAMETER_SET.MOLECULE_DESIGN_POOL]
        pos_type = None
        if parameter_map.has_key(self.PARAMETER_SET.POS_TYPE):
            pos_type = parameter_map[self.PARAMETER_SET.POS_TYPE]

        if pool_id is None:
            if pos_type is None or self._is_empty_type(pos_type):
                return None
            self.__missing_pool.add(rack_pos.label)
            return None

        if pos_type is None:
            pos_type = self.__determine_position_type(pool_id)
            if pos_type is None: return None
        elif not self._check_type_validity(pos_type, pool_id):
            return None

        if self._is_empty_type(pos_type):
            # these position are technically empty, they are only required
            # for documentation
            return None

        if is_valid_number(pool_id, is_integer=True):
            pool = self.__get_molecule_design_pool_for_id(pool_id,
                                                          rack_pos.label)
            if pool is None: return None
        else:
            pool = pool_id

        kw = dict(molecule_design_pool=pool)
        if self.POSITION_CLS.EXPOSE_POSITION_TYPE:
            kw['position_type'] = pos_type
        return kw

    def _is_empty_type(self, pos_type):
        """
        Returns *True* if a position type is empty, untreated or untransfected.
        """
        if pos_type == EMPTY_POSITION_TYPE:
            return True
        elif self.PARAMETER_SET.is_untreated_type(pos_type):
            return True
        else:
            return False

    def __determine_position_type(self, pool_id):
        """
        We do not use the :func:`_run_and_record_error` method because we do
        not want to record potentials errors right away but postpone that
        after the position collection phase.
        """
        try:
            pos_type = self.PARAMETER_SET.get_position_type(pool_id)
        except ValueError:
            self.__invalid_pos_type.add(pool_id)
            return None
        else:
            return pos_type

    def _check_type_validity(self, pos_type, pool_id):
        """
        Is invoked if the position type is stored in the rack layout.
        """
        exp_type = None

        if self.PARAMETER_SET.is_untreated_type(pool_id):
            if not self.PARAMETER_SET.is_valid_untreated_value(pos_type):
                exp_type = self._get_joined_str(self.PARAMETER_SET.\
                        VALID_UNTREATED_NONE_REPLACERS, is_strs=False,
                        separator='/')
        elif pool_id == MOCK_POSITION_TYPE:
            if not pos_type == MOCK_POSITION_TYPE:
                exp_type = MOCK_POSITION_TYPE
        elif pool_id == LIBRARY_POSITION_TYPE:
            if not pos_type == LIBRARY_POSITION_TYPE:
                exp_type = LIBRARY_POSITION_TYPE

        if exp_type is None: return True
        info = 'pool %s (expected: %s, found: %s)' % (pool_id, exp_type,
                                                      pos_type)
        self.__type_mismatch.add(info)
        return False

    def __get_molecule_design_pool_for_id(self, pool_id, position_label):
        """
        Returns the :class:`MoleculeDesignPool` entity for a position and
        checks whether it is a valid (=known) one.
        """
        if self.__pool_map.has_key(pool_id):
            return self.__pool_map[pool_id]

        if not is_valid_number(pool_id, is_integer=True):
            info = '%s (%s)' % (pool_id, position_label)
            self.__unknown_pools.append(info)
            return None

        entity = self.__pool_aggregate.get_by_id(pool_id)
        if entity is None:
            info = '%s (%s)' % (pool_id, position_label)
            self.__unknown_pools.append(info)
            return None

        self.__pool_map[pool_id] = entity
        return entity

    def _record_errors(self):
        BaseLayoutConverter._record_errors(self)

        if len(self.__unknown_pools) > 0:
            msg = 'Some molecule design pool IDs could not be found in the ' \
                  'DB: %s.' % (self._get_joined_str(self.__unknown_pools))
            self.add_error(msg)

        if len(self.__invalid_pos_type) > 0:
            msg = 'Unknown or unsupported position types for the following ' \
                  'pool IDs: %s. Supported position types: %s.' \
                   % (self._get_joined_str(self.__invalid_pos_type),
                      self._get_joined_str(
                            self.PARAMETER_SET.ALLOWED_POSITION_TYPES))
            self.add_error(msg)

        if len(self.__missing_pool) > 0:
            msg = 'Some position have non-empty position types although ' \
                  'there is no pool for them: %s.' \
                   % (self._get_joined_str(self.__missing_pool))
            self.add_error(msg)

        if len(self.__type_mismatch) > 0:
            msg = 'The pool IDs and position types for the following pools ' \
                  'do not match: %s.' \
                   % (self._get_joined_str(self.__type_mismatch))
            self.add_error(msg)

    def _perform_layout_validity_checks(self, working_layout):
        """
        There are no checks to be performed. However, we want to remove
        unnecessary empty positions.
        """
        working_layout.close()


class TransferLayoutConverter(MoleculeDesignPoolLayoutConverter):
    """
    Converts an rack_layout into a TransferLayout
    (:class:`thelma.tools.utils.layouts.TransferLayout`).
    """

    NAME = 'Transfer Layout Converter'

    PARAMETER_SET = TransferParameters
    LAYOUT_CLS = TransferLayout
    POSITION_CLS = TransferPosition

    def __init__(self, rack_layout, parent=None):
        MoleculeDesignPoolLayoutConverter.__init__(self, rack_layout,
                                                   parent=parent)
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

    def _initialize_parameter_validators(self):
        MoleculeDesignPoolLayoutConverter._initialize_parameter_validators(self)
        for parameter in self.PARAMETER_SET.TRANSFER_TARGET_PARAMETERS:
            if not self.PARAMETER_SET.must_have_transfer_targets(parameter):
                self._optional_parameters.add(parameter)

    def _initialize_other_attributes(self):
        """
        Initialises the target well storage.
        """
        self._transfer_targets = dict()
        for parameter in self.PARAMETER_SET.TRANSFER_TARGET_PARAMETERS:
            self._transfer_targets[parameter] = []

    def _get_position_init_values(self, parameter_map, rack_pos):
        kw = MoleculeDesignPoolLayoutConverter._get_position_init_values(self,
                                                      parameter_map, rack_pos)
        if kw is None: return None

        target_tag_value = parameter_map[self.PARAMETER_SET.TRANSFER_TARGETS]
        tts = self._parse_target_tag_value(target_tag_value, rack_pos,
                                           self.PARAMETER_SET.TRANSFER_TARGETS)
        if tts is None: return None # an error has occurred

        kw['transfer_targets'] = tts
        return kw

    def _parse_target_tag_value(self, target_tag_value, rack_position,
                                parameter_name):
        """
        Converts the value of a target tag into a TargetTransfer List.
        """
        if target_tag_value is None:
            transfer_targets = []
        else:
            try:
                transfer_targets = TransferPosition.parse_target_tag_value(
                                                        target_tag_value)
            except ValueError:
                error_msg = '"%s" (%s)' % (target_tag_value, rack_position.label)
                add_list_map_element(self.__invalid_target_string, parameter_name,
                                     error_msg)
                return None

        if not self.__are_valid_transfer_targets(transfer_targets,
                                     rack_position, parameter_name):
            return None

        return transfer_targets

    def __are_valid_transfer_targets(self, transfer_targets, rack_position,
                                     parameter_name):
        """
        Stores the transfer targets and checks their consistency.
        """
        if transfer_targets is None or len(transfer_targets) < 1:
            if self.PARAMETER_SET.must_have_transfer_targets(parameter_name):
                add_list_map_element(self.__missing_transfer_target,
                                     parameter_name, rack_position.label)
                return False
            else:
                return True

        allow_duplicates = self.LAYOUT_CLS.ALLOW_DUPLICATE_TARGET_WELLS[
                                                            parameter_name]
        for transfer_target in transfer_targets:
            if not allow_duplicates and transfer_target.hash_value \
                                in self._transfer_targets[parameter_name]:
                error_msg = '%s' % (transfer_target)
                add_list_map_element(self.__duplicate_targets, parameter_name,
                                     error_msg)
                return False
            else:
                add_list_map_element(self._transfer_targets, parameter_name,
                                     transfer_target.hash_value)

        return True

    def _record_errors(self):
        MoleculeDesignPoolLayoutConverter._record_errors(self)

        if len(self.__invalid_target_string) > 0:
            self.__correct_parameter_names(self.__invalid_target_string)
            msg = 'The following rack positions have invalid target position ' \
                  'descriptions: %s.' \
                   % (self._get_joined_map_str(self.__invalid_target_string,
                                               'parameter "%s": %s'))
            self.add_error(msg)

        if len(self.__duplicate_targets) > 0:
            self.__correct_parameter_names(self.__duplicate_targets)
            msg = 'There are duplicate target positions: %s!' \
                  % (self._get_joined_map_str(self.__duplicate_targets,
                                              'parameter "%s": %s'))
            self.add_error(msg)

        if len(self.__missing_transfer_target) > 0:
            self.__correct_parameter_names(self.__missing_transfer_target)
            msg = 'Position of this type (%s) must have certain transfer ' \
                  'targets. The transfer targets are missing for the ' \
                  'following positions: %s.' \
                  % (self.POSITION_CLS.__name__,
                     self._get_joined_map_str(self.__missing_transfer_target,
                                              'parameter "%s": %s'))
            self.add_error(msg)

    def __correct_parameter_names(self, error_dict):
        """
        Replaces underscores in parameter names with white spaces.
        """
        del_parameters = []
        new_params = dict()
        for parameter, info_list in error_dict.iteritems():
            new_param = parameter.replace('_', ' ')
            new_params[new_param] = info_list
            del_parameters.append(parameter)
        for parameter in del_parameters:
            del error_dict[parameter]
        error_dict.update(new_params)


class LibraryBaseLayoutConverter(BaseLayoutConverter):
    """
    Converts a :class:`thelma.entities.racklayout.RackLayout` into a
    :class:`LibraryBaseLayout`.

    """
    NAME = 'Library Base Layout Converter'

    PARAMETER_SET = LibraryBaseLayoutParameters
    POSITION_CLS = LibraryBaseLayoutPosition
    LAYOUT_CLS = LibraryBaseLayout

    def __init__(self, rack_layout, parent=None):
        BaseLayoutConverter.__init__(self, rack_layout, parent=parent)
        # intermediate storage of invalid rack positions
        self.__invalid_flag = None

    def reset(self):
        BaseLayoutConverter.reset(self)
        self.__invalid_flag = []

    def _get_position_init_values(self, parameter_map, rack_pos):
        is_lib_pos_str = parameter_map[self.PARAMETER_SET.IS_LIBRARY_POS]
        if is_lib_pos_str is None: return None

        is_lib_pos = self._get_boolean_value(is_lib_pos_str, rack_pos.label,
                                             self.__invalid_flag)
        if is_lib_pos is None: return None
        return dict(is_library_position=is_lib_pos)

    def _record_errors(self):
        BaseLayoutConverter._record_errors(self)
        self._record_invalid_boolean_error('library position',
                                           self.__invalid_flag)

    def _perform_layout_validity_checks(self, working_layout):
        """
        We do not check anything but we close the layout.
        """
        working_layout.close()
