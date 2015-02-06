"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

This module fills the containers of experiment racks (intended
as executor for manual worklists).

AAB
"""
from thelma.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.tools.semiconstants import get_item_status_managed
from thelma.tools.experiment.base import ExperimentTool
from thelma.tools.experiment.base import PRINT_SUPPORT_SCENARIOS
from thelma.tools.metadata.base import TransfectionLayoutConverter
from thelma.tools.metadata.base import TransfectionParameters
from thelma.tools.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.entities.racklayout import RackLayout


__docformat__ = 'reStructuredText en'

__all__ = ['ExperimentManualExecutor']


class ExperimentManualExecutor(ExperimentTool):
    """
    This class fills the containers of experiment design racks that have
    been created without mastermix support.
    The molecules are taken from the first well in the source plate having
    that pool. There are no executed worklists generated instead the
    updated experiment is returned.
    For wells without pools (mocks, ISO-less experiments) the samples have
    volumes but no molecules.

    **Return Value:** updated experiment
    """
    NAME = 'Experiment Manual Executor'

    SUPPORTED_SCENARIOS = [EXPERIMENT_SCENARIOS.OPTIMISATION,
                           EXPERIMENT_SCENARIOS.SCREENING,
                           EXPERIMENT_SCENARIOS.LIBRARY,
                           EXPERIMENT_SCENARIOS.MANUAL,
                           EXPERIMENT_SCENARIOS.ISO_LESS]

    _MODES = [ExperimentTool.MODE_EXECUTE]

    #: The default volume of a sample in an experiment plate (in ul).
    FINAL_SAMPLE_VOLUME = TransfectionParameters.TRANSFER_VOLUME * \
                            TransfectionParameters.CELL_DILUTION_FACTOR

    def __init__(self, experiment, user, parent=None):
        ExperimentTool.__init__(self, experiment, ExperimentTool.MODE_EXECUTE,
                                user=user, parent=parent)
        #: Maps molecules onto pools (or pool placeholders).
        self.__pool_molecule_map = None
        #: The final volume for the samples *in l*.
        self.__final_vol = self.FINAL_SAMPLE_VOLUME / VOLUME_CONVERSION_FACTOR

    def reset(self):
        """
        Resets all attributes except for the input values.
        """
        ExperimentTool.reset(self)
        self.__pool_molecule_map = dict()

    def _execute_worklists(self):
        if not self.has_errors(): self._generate_pool_molecule_map()
        if not self.has_errors(): self.__update_racks()
        if not self.has_errors(): self._update_iso_aliquot_plate()
        if not self.has_errors():
            self.return_value = self.experiment
            self.add_info('Experiment sample generation completed.')

    def _check_mastermix_compatibility(self):
        """
        Checks whether the worklist series supports mastermix preparation.
        """
        is_compatible = False
        if self._scenario.id in PRINT_SUPPORT_SCENARIOS and \
                                        not self._design_series is None:
            if self._scenario.id == EXPERIMENT_SCENARIOS.OPTIMISATION:
                is_compatible = True
            elif len(self._design_series) > 2:
                is_compatible = True

        if is_compatible:
            msg = 'This experiment is robot-compatible. Would you still ' \
                  'like to use the manual update?'
            self.add_warning(msg)

    def _create_all_transfer_jobs(self, add_cell_jobs):
        """
        We do not use a serial tool and do not need transfer jobs.
        """
        pass

    def _generate_pool_molecule_map(self):
        """
        Stores the molecules for each pool (using the first occurrence of
        the pool in the source plate and also
        """
        self.add_debug('Store molecules for pools ...')

        if not self._scenario.id == EXPERIMENT_SCENARIOS.ISO_LESS:
            for well in self._source_plate.containers:
                if well.sample is None: continue
                rack_pos = well.location.position
                ir_pos = self._source_layout.get_working_position(rack_pos)
                if ir_pos.is_library:
                    pool = rack_pos.label
                else:
                    pool = ir_pos.molecule_design_pool
                if self.__pool_molecule_map.has_key(pool): continue
                mols = []
                for sm in well.sample.sample_molecules:
                    mols.append(sm.molecule)
                self.__pool_molecule_map[pool] = mols

    def __update_racks(self):
        """
        The layout type for the design rack depends on the experiment metadata
        type. Creates samples for all racks and sets their status to
        :attr:`managed`.
        """
        is_one_to_one = (self._scenario.id in \
                         EXPERIMENT_SCENARIOS.ONE_TO_ONE_TYPES)
        for design_rack in self.experiment.experiment_design.\
                                                    experiment_design_racks:
            if is_one_to_one:
                layout = self._source_layout
            elif self._scenario.id == EXPERIMENT_SCENARIOS.ISO_LESS:
                # We only care if there is a well or not.
                layout = design_rack.rack_layout
            else:
                layout = self.__fetch_design_rack_layout(design_rack)
                if layout is None: continue
            self.__create_rack_samples(layout, design_rack)

    def __fetch_design_rack_layout(self, design_rack):
        """
        Fetches the transfection layouts for each design rack.
        """
        converter = TransfectionLayoutConverter(design_rack.rack_layout,
                                                is_iso_request_layout=False,
                                                parent=self)
        tf_layout = converter.get_result()
        if tf_layout is None:
            msg = 'Could not get layout for design rack "%s"!' \
                  % (design_rack.label)
            self.add_error(msg)
        return tf_layout

    def __create_rack_samples(self, layout, design_rack):
        """
        Generates the sample for each experiment plate belonging to a particular
        experiment design rack. The volume is fixed
        (:attr:`FINAL_SAMPLE_VOLUME`), the molecule are stored in the
        :attr:`_pool_molecule_map` and positions and concentrations are
        derived from the layout.
        """
        without_pool_data = isinstance(layout, RackLayout)
        design_rack_label = design_rack.label
        for exp_rack in self._experiment_racks[design_rack_label]:
            plate = exp_rack.rack
            if without_pool_data:
                positions = layout.get_positions()
                self.__add_samples_without_pools(positions, plate)
            else:
                self.__add_samples_with_pools(layout, plate, design_rack_label)
            if self.has_errors(): break
            plate.status = get_item_status_managed()

    def __add_samples_without_pools(self, positions, plate):
        """
        Helper functions adding the pools to an experiment plate if there
        are no pools in the experiment (volumes only).
        """
        for well in plate.containers:
            rack_pos = well.location.position
            if not rack_pos in positions: continue
            well.make_sample(self.__final_vol)

    def __add_samples_with_pools(self, layout, plate, design_rack_label):
        """
        Helper functions adding the pools to an experiment plate if there
        are pools in the experiment.
        """
        missing_pools = set()
        for well in plate.containers:
            rack_pos = well.location.position
            tf_pos = layout.get_working_position(rack_pos)
            if tf_pos is None: continue
            if tf_pos.is_empty: continue
            if self._scenario.id == EXPERIMENT_SCENARIOS.MANUAL \
               and not tf_pos.is_fixed:
                # For manual experiments, we allow only fixed and empty
                # positions in the ISO layout, but we should not restrict
                # the transfection layout.
                continue
            pool = tf_pos.molecule_design_pool
            if tf_pos.is_library:
                pool = rack_pos.label
            if not self.__pool_molecule_map.has_key(pool):
                if not ((tf_pos.is_library and \
                            rack_pos in self._ignored_positions) \
                        or pool in self._ignored_floatings):
                    missing_pools.add(pool)
                continue
            sample = well.make_sample(self.__final_vol)
            if tf_pos.is_mock: continue
            mols = self.__pool_molecule_map[pool]
            conc = (tf_pos.final_concentration / len(mols)) \
                    / CONCENTRATION_CONVERSION_FACTOR
            for mol in mols:
                sample.make_sample_molecule(molecule=mol, concentration=conc)

        if len(missing_pools) > 0:
            msg = 'The following pools from design rack %s could not be ' \
                  'found on the source plate: %s.' % (design_rack_label,
                   self._get_joined_str(missing_pools, is_strs=False))
            self.add_error(msg)
