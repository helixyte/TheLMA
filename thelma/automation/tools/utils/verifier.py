"""
Verification tools that compare racks against expected layouts.

AAB, Jan 2012
"""
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.tools.iso.prep_utils import PrepIsoLayoutConverter
from thelma.automation.tools.semiconstants import get_positions_for_shape
from thelma.automation.tools.utils.iso import IsoLayout
from thelma.automation.tools.utils.iso import IsoLayoutConverter
from thelma.models.iso import Iso
from thelma.models.iso import IsoRequest
from thelma.models.rack import Plate
import logging


__docformat__ = 'reStructuredText en'

__all__ = ['BaseRackVerifier',
           'IsoRackVerifier',
           'SourceRackVerifier']


class BaseRackVerifier(BaseAutomationTool):
    """
    A base tool for plate-to-layout verifiers.

    **Return Value:** boolean
    """

    #: The expected rack class (TubeRack, Plate or Rack).
    RACK_CLS = None
    #: The expected class of the reference layout.
    LAYOUT_CLS = None

    def __init__(self, rack, reference_layout=None,
                 record_success=True,
                 log=None, depending=True,
                 logging_level=logging.WARNING,
                 add_default_handlers=False):
        """
        Constructor:

        :param rack: The rack to be checked.
        :type rack: :class:`thelma.models.rack.Rack`

        :param reference_layout: The layout containing the molecule design
            data. Can be set here or derived during the run.
        :type reference_layout:
            :class:`thelma.automation.tools.base.WorkingLayout`
        :default reference_layout: *None*

        :param record_success: If *True* the tool will release a warning
            message in case of compatibility.
        :type record_sucess: :class:`bool`
        :default record_success: *True*

        :param log: The log the write in.
        :type log: :class:`thelma.ThelmaLog`

        :param logging_level: the desired minimum log level
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *False*

        :param depending: Defines whether a tool can be initialised directly
            (*False*) of if it is always called by other tools (*True*).
            Depending tools must obtain a log and are not capable to
            reset a log.
        :type depending: :class:`bool`
        :default depending: *True*
        """
        depending = not (log is None)
        BaseAutomationTool.__init__(self, logging_level=logging_level,
                                    add_default_handlers=add_default_handlers,
                                    depending=depending, log=log)

        #: The rack to be checked.
        self.rack = rack
        #: The layout containing the molecule design data. Can be set here or
        #: derived during the run.
        self.reference_layout = reference_layout
        #: If *True* the tool will release a warning message in case of
        #: compatibility.
        self.record_success = record_success

        #: Indicates whether the rack-layout combination is a valid one
        #: (required to distinguish run time errors from verification errors).
        self._is_valid = None

        #: The expected layout as working layout.
        self._expected_layout = None
        #: Maps the molecule designs of the tubes in the rack onto positions.
        self._rack_md_map = None

        #: Stores positions that are empty in the stock rack but not in the
        #: layout.
        self._missing_positions = None
        #: Stores positions which have a tube although they should be empty
        #: in the preparation plate.
        self._additional_positions = None
        #: Stores positions whose molecule designs are not matching.
        self._mismatching_positions = None

    def reset(self):
        """
        Resets all values except for initialisation values.
        """
        BaseAutomationTool.reset(self)
        self._is_valid = True
        self._expected_layout = None
        self._rack_md_map = dict()
        self._missing_positions = []
        self._additional_positions = []
        self._mismatching_positions = []

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Start verification ...')

        self._check_input()
        if not self.has_errors():
            if self.reference_layout is None:
                self._fetch_expected_layout()
            else:
                self._expected_layout = self.reference_layout
        if not self.has_errors(): self.__compare_rack_shapes()
        if not self.has_errors(): self.__create_rack_md_map()
        if not self.has_errors():
            self.__compare_positions()
            self.__record_results()

        if not self.has_errors() or not self._is_valid:
            self.return_value = self._is_valid
            if self._is_valid and self.record_success:
                msg = 'The passed rack (%s) complies with the expected ' \
                      'layout.' % (self.rack.barcode)
                self.add_warning(msg)
            self.add_info('Verification completed.')

    def get_expected_layout(self):
        """
        Returns the :attr:`_expected_layout` (or None if there are errors).
        """
        if self.return_value is None or self.return_value is False:
            return None
        else:
            return self._expected_layout

    def _check_input(self):
        """
        Checks the input values.
        """
        self.add_debug('Check input values ...')

        self._check_input_class('rack', self.rack, self.RACK_CLS)
        self._check_input_class('record success flag', self.record_success,
                                bool)
        if not self.reference_layout is None:
            self._check_input_class('reference layout', self.reference_layout,
                                    self.LAYOUT_CLS)

    def _fetch_expected_layout(self):
        """
        Fetches the expected layout.
        """
        self.add_error('Abstract method: _fetch_expected_layout()')

    def __compare_rack_shapes(self):
        """
        Compares the rack shape of rack and layout.
        """
        self.add_debug('Compare layout ...')

        rl_shape = self._expected_layout.shape
        rack_shape = self.rack.specs.shape

        if not rl_shape == rack_shape:
            msg = 'The rack shapes of the expected layout ' \
                  '(%s) and the rack (%s) do not match!' \
                  % (rl_shape, rack_shape)
            self.add_error(msg)
            self._is_valid = False

    def __create_rack_md_map(self):
        """
        Creates the :attr:`__rack_md_map` that maps rack molecule design IDs
        onto positions.
        """
        self.add_debug('Create rack map ...')

        for rack_pos in get_positions_for_shape(self.rack.specs.shape):
            pos_label = rack_pos.label
            self._rack_md_map[pos_label] = None

        for container in self.rack.containers:
            pos_label = container.location.position.label
            sample = container.sample
            if sample is None:
                self._rack_md_map[pos_label] = None
                continue
            for sm in sample.sample_molecules:
                # do NOT use add_list_map_element here since the is initialised
                # with non-values!
                md_id = sm.molecule.molecule_design.id
                if self._rack_md_map[pos_label] is None:
                    self._rack_md_map[pos_label] = [md_id]
                else:
                    self._rack_md_map[pos_label].append(md_id)

    def __compare_positions(self):
        """
        Compares the molecule design IDs of the positions.
        """
        self.add_debug('Compare positions ...')

        for rack_pos in get_positions_for_shape(self.rack.specs.shape):
            pos_label = rack_pos.label
            exp_pos = self._expected_layout.get_working_position(rack_pos)
            rack_mds = self._rack_md_map[pos_label]
            exp_mds = self._get_exp_pos_molecule_design_ids(exp_pos)
            # in case of match check volumes
            if self._are_matching_molecule_designs(rack_mds, exp_mds): continue
            # in case of mismatch
            if rack_mds is None:
                info = '%s (expected mds: %s)' % (pos_label, '-'.join(
                                    [str(md_id) for md_id in sorted(exp_mds)]))
                self._missing_positions.append(info)
            elif exp_mds is None:
                self._additional_positions.append(pos_label)
            else:
                info = '%s (expected: %s, rack: %s)' \
                        % (pos_label,
                           '-'.join([str(md_id) for md_id in sorted(rack_mds)]),
                           '-'.join([str(md_id) for md_id in sorted(exp_mds)]))
                self._mismatching_positions.append(info)

    def _get_exp_pos_molecule_design_ids(self, exp_pos): #pylint: disable=W0613
        """
        Gets the molecule design ID expected for a working layout
        position.
        """
        self.add_error('Abstract method: ' \
                       '_get_expected_position_molecule_design_id() ')

    def _get_ids_for_pool(self, md_pool):
        """
        Returns a list containing the IDs of the molecule designs in a pool.
        """
        ids = []
        for md in md_pool:
            ids.append(md.id)
        return ids

    def _are_matching_molecule_designs(self, rack_mds, exp_mds):
        """
        Checks whether the position molecule designs are compatible with
        the ones found in the rack.
        """
        if rack_mds is None and exp_mds is None: return True
        if rack_mds is None or exp_mds is None: return False
        return (sorted(exp_mds) == sorted(rack_mds))

    def __record_results(self):
        """
        Records the results of the positions checks.
        """
        self.add_debug('Record results ...')

        if len(self._missing_positions) > 0:
            msg = 'Some expected molecule designs are missing in the rack: ' \
                  '%s.' % (self._missing_positions)
            self.add_error(msg)
            self._is_valid = False

        if len(self._additional_positions) > 0:
            msg = 'Some positions in the rack contain molecule designs ' \
                  'although they should be empty: %s!' \
                   % (self._additional_positions)
            self.add_error(msg)
            self._is_valid = False

        if len(self._mismatching_positions) > 0:
            msg = 'The molecule designs of the following positions do not ' \
                  'match: %s.' % (self._mismatching_positions)
            self.add_error(msg)
            self._is_valid = False


class IsoRackVerifier(BaseRackVerifier):
    """
    This tool verifies whether a rack is compliant to the ISO layout of
    the passed ISO.

    **Return Value:** boolean
    """

    NAME = 'ISO Rack Verifier'

    RACK_CLS = Plate
    LAYOUT_CLS = IsoLayout

    def __init__(self, plate, iso, record_success=True, log=None,
                 depending=True, logging_level=logging.WARNING,
                 add_default_handlers=False):
        """
        Constructor:

        :param iso: The ISO the rack shall checked for.
        :type iso: :class:`thelma.models.iso.Iso`

        :param plate: The plate to be checked.
        :type plate: :class:`thelma.models.rack.Plate`

        :param record_success: If *True* the tool will release a warning
            message in case of compatibility.
        :type record_sucess: :class:`bool`
        :default record_success: *True*

        :param log: The log the write in.
        :type log: :class:`thelma.ThelmaLog`

        :param logging_level: the desired minimum log level
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *False*

        :param depending: Defines whether a tool can be initialized directly
            (*False*) of if it is always called by other tools (*True*).
            Depending tools must obtain a log and are not capable to
            reset a log.
        :type depending: :class:`bool`
        :default depending: *True*
        """
        BaseRackVerifier.__init__(self, rack=plate,
                                  log=log, depending=depending,
                                  record_success=record_success,
                                  logging_level=logging_level,
                                  add_default_handlers=add_default_handlers)

        #: The ISO the rack shall be checked for.
        self.iso = iso

        #: The molecule designs pools of the ISO preparation layout mapped
        #: onto floating placeholders.
        self._floating_map = None

    def reset(self):
        BaseRackVerifier.reset(self)
        self._floating_map = None

    def _check_input(self):
        BaseRackVerifier._check_input(self)
        self._check_input_class('ISO', self.iso, Iso)

    def _fetch_expected_layout(self):
        """
        The expected layout is the ISO layout of the ISO request.
        """
        self.add_debug('Get ISO layout ...')

        iso_rack_layout = self.iso.iso_request.iso_layout
        iso_converter = IsoLayoutConverter(rack_layout=iso_rack_layout,
                                           log=self.log)
        self._expected_layout = iso_converter.get_result()
        if self._expected_layout is None:
            msg = 'Error when trying to convert ISO layout.'
            self.add_error(msg)
        else:
            self._expected_layout.close()
            has_floatings = self._expected_layout.has_floatings()
            if has_floatings: self.__get_floating_map()

    def __get_floating_map(self):
        """
        Generates a map that associates floating placeholders with molecule
        design pools. This is done by means of the preparation layout.
        """
        self.add_debug('Generate floating map ...')

        self._floating_map = dict()

        prep_converter = PrepIsoLayoutConverter(log=self.log,
                                            rack_layout=self.iso.rack_layout)
        prep_layout = prep_converter.get_result()

        if prep_layout is None:
            msg = 'Error when trying to convert preparation plate layout.'
            self.add_error(msg)
        else:
            pools = prep_layout.get_pools()
            for iso_pos in self._expected_layout.working_positions():
                if not iso_pos.is_floating: continue
                placeholder = iso_pos.molecule_design_pool
                if self._floating_map.has_key(placeholder): continue
                prep_pos = prep_layout.get_working_position(
                                                    iso_pos.rack_position)
                pool_id = prep_pos.molecule_design_pool_id
                self._floating_map[placeholder] = pools[pool_id]

    def _get_exp_pos_molecule_design_ids(self, exp_pos):
        """
        Gets the molecule design IDs expected for a ISO position.
        """
        if exp_pos is None or exp_pos.is_mock:
            return None
        elif exp_pos.is_floating:
            md_pool = self._floating_map[exp_pos.molecule_design_pool_id]
        else:
            md_pool = exp_pos.molecule_design_pool

        return self._get_ids_for_pool(md_pool)


class SourceRackVerifier(BaseRackVerifier):
    """
    This tool verifies whether a rack is a suitable ISO rack for a the
    passed experiment metadata (ISO request).

    **Return Value:** boolean
    """

    NAME = 'Source Rack Verifier'

    RACK_CLS = Plate
    LAYOUT_CLS = IsoLayout

    def __init__(self, source_plate, iso_request, record_success=True,
                 log=None, depending=True, logging_level=logging.WARNING,
                 add_default_handlers=False):
        """
        Constructor:

        :param iso_request: The ISO request the plate must represent.
        :type iso_request: :class:`thelma.models.iso.isoRequest`

        :param source_plate: The plate to be checked.
        :type source_plate: :class:`thelma.models.rack.Plate`

        :param record_success: If *True* the tool will release a warning
            message in case of compatibility.
        :type record_sucess: :class:`bool`
        :default record_success: *True*

        :param log: The log the write in.
        :type log: :class:`thelma.ThelmaLog`

        :param logging_level: the desired minimum log level
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *False*

        :param depending: Defines whether a tool can be initialized directly
            (*False*) of if it is always called by other tools (*True*).
            Depending tools must obtain a log and are not capable to
            reset a log.
        :type depending: :class:`bool`
        :default depending: *True*
        """
        BaseRackVerifier.__init__(self, rack=source_plate,
                                  log=log, depending=depending,
                                  record_success=record_success,
                                  logging_level=logging_level,
                                  add_default_handlers=add_default_handlers)

        #: The ISO request the plate must represent.
        self.iso_request = iso_request

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
        self._check_input_class('ISO request', self.iso_request, IsoRequest)

    def _fetch_expected_layout(self):
        """
        The expected layout is the ISO layout of the ISO request.
        """
        self.add_debug('Get ISO layout ...')

        iso_rack_layout = self.iso_request.iso_layout
        iso_converter = IsoLayoutConverter(rack_layout=iso_rack_layout,
                                           log=self.log)
        self._expected_layout = iso_converter.get_result()
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
            prep_converter = PrepIsoLayoutConverter(rack_layout=iso.rack_layout,
                                                    log=self.log)
            prep_layout = prep_converter.get_result()

            if prep_layout is None:
                msg = 'Error when trying to convert preparation plate layout ' \
                      'for ISO %s.' % (iso.label)
                self.add_error(msg)
                continue

            pools = prep_layout.get_pools()
            floating_map = dict()
            for iso_pos in self._expected_layout.working_positions():
                if not iso_pos.is_floating: continue
                placeholder = iso_pos.molecule_design_pool
                if floating_map.has_key(placeholder): continue
                prep_pos = prep_layout.get_working_position(
                                                    iso_pos.rack_position)
                if prep_pos is None:
                    md_pool = None
                else:
                    pool_id = prep_pos.molecule_design_pool_id
                    md_pool = pools[pool_id]
                floating_map[placeholder] = md_pool
            self._iso_map[iso.label] = floating_map

        if len(self._iso_map) < 1:
            msg = 'There are no ISOs for this ISO request!'
            self.add_error(msg)

    def _get_exp_pos_molecule_design_ids(self, exp_pos):
        """
        Gets the molecule design IDs for expected for a ISO position
        (replacing floating placeholder with the pools of the preparation
        layout position molecule designs of all ISOs).
        """
        if exp_pos is None or exp_pos.is_empty:
            return None

        elif exp_pos.is_fixed:
            md_pool = exp_pos.molecule_design_pool

        else: # floating
            placeholder = exp_pos.molecule_design_pool

            if self._used_iso is None:
                possible_pools = dict()
                for iso_label, floating_map in self._iso_map.iteritems():
                    md_pool = floating_map[placeholder]
                    if md_pool is None:
                        ids = None
                    else:
                        ids = self._get_ids_for_pool(md_pool)
                    possible_pools[iso_label] = ids
                return possible_pools
            else:
                floating_map = self._iso_map[self._used_iso]
                md_pool = floating_map[placeholder]

        return self._get_ids_for_pool(md_pool)

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
