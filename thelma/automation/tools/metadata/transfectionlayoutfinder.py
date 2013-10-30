"""
:Date: 2011 July
:Author: AAB, berger at cenix-bioscience dot com

This module creates an transfection layout (layout for an ISO request) from
an experiment design if there was no ISO request layout specified in an
experiment metadata XLS file.

Position Types
..............

There are 6 different types of position for an ISO request Layout:

 * empty position
 * mock position (no molecule design pools but all other liquids)
 * fixed position (containing a specified molecule design pools)
 * floating position (containing a molecule design pool which is not specified)
 * untreated and untransfected (empty position that are marked differently
   for experimental reasons - they might still contain cells or treatments,
   but there is not transfection taking place)

For fixed and floating position, the following parameters must be specified:
 * molecule design pool ID (or placeholder)

Additional Transfection Parameters
..................................

In order to generate the mastermix the following information must be known:

  * transfection reagent (\'reagent name\')
  * transfection reagent concentration (\'reagent dilution factor\')
  * molecule design pool ID (or placeholder)
  * final concentration in the cell plate (experiment plate)


Transfection Layout Constraints
...............................

The return value of the tool is an rack layout (derived from a Transfection
layout). Within the transfection layout for the ISO each non-empty well must
have a unique combination of the parameters (represented by the
hash value of the transfection position).

Steps
.....

 1. get ExperimentDesignRacks of an ExperimentDesign
 2. select an ExperimentDesignRack, get layout incl. parameter tags.
 3. build transfection layout for the ISO request (Biomek optimized)
"""

from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.tools.metadata.base import TransfectionLayout
from thelma.automation.tools.metadata.base import TransfectionLayoutConverter
from thelma.automation.tools.metadata.base import TransfectionPosition
from thelma.automation.tools.worklists.optimiser import BiomekLayoutOptimizer
from thelma.automation.tools.worklists.optimiser import TransferItem
from thelma.automation.utils.base import add_list_map_element
from thelma.automation.utils.iso import IsoRequestParameters
from thelma.models.experiment import ExperimentDesign

__docformat__ = 'reStructuredText en'

__all__ = ['TransfectionLayoutFinder',
           '_TransfectionTransferItem',
           '_TransfectionLayoutOptimizer']


class TransfectionLayoutFinder(BaseAutomationTool):
    """
    This tool generates an transfection source layout (ISO layout plus
    transfection data) from an experiment design.

    The ISO layout is an IdQuartetLayout. Each non-empty well within the
    layout will have a unique combination of molecule design pool,
    design pool concentration, reagent name and reagent concentration.

    **Return Value:** TransfectionLayout for the ISO plate (with mastermix
        data but without ISO volumes and concentrations).
    """

    NAME = 'Transfection Layout Finder'

    def __init__(self, experiment_design, log):
        """
        Constructor:

        :param experiment_design: The experiment containing the data for the
                ISO layout.
        :type experiment_design: :class:`thelma.models.experiment.ExperimentDesign`

        :param log: The ThelmaLog you want to write in. If the
            log is None, the object will create a new log.
        :type log: :class:`thelma.ThelmaLog`
        """

        BaseAutomationTool.__init__(self, log)
        self.experiment_design = experiment_design

        #: The transfection layouts of the design racks.
        self.__experiment_layouts = None
        #: Used to sort floating positions within the layouts.
        self.__placeholder_maps = None

        #: The ISO layout created from the experiment designs layout
        #: (:class:`TransfectionLayout`).
        self.__iso_layout = None

    def reset(self):
        """
        Resets all attributes except for the :attr:`experiment_design`.
        """
        BaseAutomationTool.reset(self)
        self.__experiment_layouts = dict()
        self.__placeholder_maps = dict()
        self.__iso_layout = None

    def run(self):
        """
        Runs the conversion.
        """

        self.reset()
        self.add_info('Generate ISO layout from experiment design ...')

        self.__check_input()
        if not self.has_errors(): self.__get_experiment_layouts()
        if not self.has_errors(): self.__optimise_layout()
        if not self.has_errors():
            self.return_value = self.__iso_layout
            self.add_info('Automated ISO layout generation completed.')

    def get_experiment_transfection_layouts(self):
        """
        Returns the transfection layouts for the different design racks.

        :return: The transfections layouts as map (mapped onto design
                 rack labels).
        """
        if self.has_errors(): return None

        return self.__experiment_layouts

    def __check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input values ...')
        self._check_input_class('experiment design', self.experiment_design,
                                ExperimentDesign)

    def __get_experiment_layouts(self):
        """
        Generates the transfection layouts for the experiment design's
        design racks.
        """
        self.add_debug('Determine experiment design transfection layouts ...')

        for design_rack in self.experiment_design.experiment_design_racks:
            experiment_layout = design_rack.rack_layout
            converter = TransfectionLayoutConverter(log=self.log,
                                        rack_layout=experiment_layout,
                                        is_iso_request_layout=False,
                                        is_mastermix_template=True)
            experiment_layout = converter.get_result()

            if experiment_layout is None:
                msg = 'Error when trying to convert design rack layout for ' \
                      'design rack "%s".' % (design_rack.label)
                self.add_error(msg)
                break
            else:
                self.__experiment_layouts[design_rack.label] = experiment_layout
                self.__sort_floatings(experiment_layout, design_rack.label)

        for design_rack in self.experiment_design.experiment_design_racks:
            if self.__check_for_iso_volume_and_concentration(design_rack):
                break

    def __sort_floatings(self, experiment_layout, design_rack_label):
        """
        Sorts the floating positions within the layouts (assigned placeholders
        are stored in the :attr:`__placeholder_map`).
        Also looks whether there are controls in the layout.
        """

        has_controls = False
        for tf_pos in experiment_layout.get_sorted_working_positions():
            if tf_pos.is_fixed:
                has_controls = True
                continue
            elif not tf_pos.is_floating:
                continue
            old_placeholder = tf_pos.molecule_design_pool
            if self.__placeholder_maps.has_key(old_placeholder):
                new_placeholder = self.__placeholder_maps[old_placeholder]
            else:
                new_placeholder = '%s%03i' % (
                                        IsoRequestParameters.FLOATING_INDICATOR,
                                        len(self.__placeholder_maps) + 1)
                self.__placeholder_maps[old_placeholder] = new_placeholder
            tf_pos.molecule_design_pool = new_placeholder

        if not has_controls:
            msg = 'There are no controls in the layout for design rack "%s"!' \
                  % (design_rack_label)
            self.add_error(msg)

        return experiment_layout

    def __check_for_iso_volume_and_concentration(self, design_rack):
        """
        Checks whether there are ISO volumes and concentrations in the
        layout. If so, a warning is issued.
        """

        vol_validator = IsoRequestParameters.create_validator_from_parameter(
                                        IsoRequestParameters.ISO_VOLUME)
        conc_validator = IsoRequestParameters.create_validator_from_parameter(
                                        IsoRequestParameters.ISO_CONCENTRATION)

        has_vol = False
        has_conc = False

        for tag in design_rack.rack_layout.get_tags():
            if has_vol and has_conc: break
            if vol_validator.has_alias(tag.predicate):
                has_vol = True
                continue
            if  conc_validator.has_alias(tag.predicate):
                has_conc = True
                continue

        if has_vol or has_conc:
            if has_vol: what = 'ISO volume'
            if has_conc: what = 'ISO concentration'
            if has_vol and has_conc: what = 'ISO volume and ISO concentration'
            msg = 'The experiment design has %s specifications! ISO volumes ' \
                  'and concentrations are ignored for automated ISO layout ' \
                  'generation. Please use a separate ISO sheet, if you want ' \
                  'to provide these values by yourself!' % (what)
            self.add_warning(msg)

        return (has_vol or has_conc)

    def __optimise_layout(self):
        """
        Runs the transfection layout optimiser.
        """
        self.add_debug('Optimise ISO layout ...')

        optimiser = _TransfectionLayoutOptimizer(log=self.log,
                                design_rack_layouts=self.__experiment_layouts)
        self.__iso_layout = optimiser.get_result()

        if self.__iso_layout is None:
            msg = 'Error when trying to optimise ISO layout.'
            self.add_error(msg)


class _TransfectionTransferItem(TransferItem):
    """
    A special :class:`TransferItem` for :class:`TransfectionPosition`
    objects (using the full hash).
    """

    def _get_hash_value(self):
        return self.working_pos.hash_full



class _TransfectionLayoutOptimizer(BiomekLayoutOptimizer):
    """
    Tries to sort the source positions for the cell plate transfer (= positions
    in the ISO transfection layout) in a way that allows the Biomek to work
    as fast a possible.

    **Return Value:** The optimised transfection layout.
    """

    NAME = 'Transfection Layout Optimiser'

    SOURCE_LAYOUT_CLS = TransfectionLayout
    TRANSFER_ITEM_CLASS = _TransfectionTransferItem

    def __init__(self, design_rack_layouts, log):
        """
        Constructor:

        :param design_rack_layouts: The transfection layout for each design
            rack.
        :type design_rack_layouts: :class:`dict`

        :param log: The ThelmaLog you want to write in. If the
            log is None, the object will create a new log.
        :type log: :class:`thelma.ThelmaLog`
        """
        BiomekLayoutOptimizer.__init__(self, log=log)

        #: The transfection layout for each design rack.
        self.design_rack_layouts = design_rack_layouts

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input values ...')

        if self._check_input_class('design rack layout map',
                                   self.design_rack_layouts, dict):
            for tf_layout in self.design_rack_layouts.values():
                if not self._check_input_class('design rack layout', tf_layout,
                                               TransfectionLayout): break
            if len(self.design_rack_layouts) < 1:
                msg = 'There is no design rack in the layout map!'
                self.add_error(msg)

    def _find_hash_values(self):
        """
        Initialises :attr:`_hash_values` and :attr:`_column_maps`.
        """
        self.add_debug('Sort hash values ...')

        for label, tf_layout in self.design_rack_layouts.iteritems():
            column_map = dict()
            for tf_pos in tf_layout.get_sorted_working_positions():
                self._hash_values.add(tf_pos.hash_full)
                add_list_map_element(column_map,
                                     tf_pos.rack_position.column_index, tf_pos)
            self._column_maps[label] = column_map

    def _get_target_layout_shape(self):
        """
        All design rack layouts have the same rack shape.
        """
        return self.design_rack_layouts.values()[0].shape

    def _create_one_to_one_map(self):
        """
        Creates one position map for one to one sorting (with source rack
        positions as keys and template working positions as values).
        Return *None* if one-to-one sorting is not possible.

        This is some sort of short cut for the very simple layouts.
        In one-to-one sorting mode we simply assign the rack position of the
        earliest occurrence of a design rack transfection position. If the
        position is already occupied, the process is aborted and we switch
        back to the "normal" optimisation algorithm.

        One-to-one assumes equal rack shapes and (almost) equal design racks.
        """
        hash_map = dict() # rack positions onto hashes
        tf_map = dict() # tf positions onto rack positions

        abort_sorting = False
        is_first_layout = None
        for tf_layout in self.design_rack_layouts.values():

            if is_first_layout is None:
                is_first_layout = True
            elif is_first_layout:
                is_first_layout = False

            if abort_sorting: break
            for tf_pos in tf_layout.get_sorted_working_positions():
                hash_value = tf_pos.hash_full
                rack_pos = tf_pos.rack_position

                if not hash_map.has_key(hash_value): # new hash
                    if not tf_map.has_key(rack_pos): # position available
                        tf_map[rack_pos] = tf_pos
                        add_list_map_element(hash_map, hash_value, rack_pos)
                    else: # position occupied
                        abort_sorting = True
                        break
                elif is_first_layout:
                    add_list_map_element(hash_map, hash_value, rack_pos)
                elif not rack_pos in hash_map[hash_value]:
                    abort_sorting = True
                    break

        if abort_sorting:
            return None
        else:
            return tf_map

    def _add_source_position(self, rack_pos, working_pos):
        """
        Creates a new transfection position and places it onto the given
        position of the source transfection layout.
        """
        src_tf = TransfectionPosition(rack_position=rack_pos,
                    molecule_design_pool=working_pos.molecule_design_pool,
                    reagent_name=working_pos.reagent_name,
                    reagent_dil_factor=working_pos.reagent_dil_factor,
                    final_concentration=working_pos.final_concentration)
        self._source_layout.add_position(src_tf)
