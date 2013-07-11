#"""
#Base classes and constants involved in pool stock samples creation tasks.
#
#AAB
#"""
#from thelma.automation.tools.semiconstants import get_pipetting_specs_cybio
#from thelma.automation.tools.stock.base import get_default_stock_concentration
#from thelma.automation.tools.utils.base import CONCENTRATION_CONVERSION_FACTOR
#from thelma.automation.tools.utils.base import VOLUME_CONVERSION_FACTOR
#from thelma.automation.tools.utils.base import get_trimmed_string
#from thelma.automation.tools.utils.base import round_up
#
#__docformat__ = 'reStructuredText en'
#
#__all__ = ['calculate_single_design_stock_transfer_volume',
#           'calculate_single_design_stock_transfer_volume_for_library']
#
#
#def calculate_single_design_stock_transfer_volume(target_volume,
#                  target_concentration, number_designs, stock_concentration):
#    """
#    Calculates the volume that has to be transferred from a single design
#    stock tube to a future pool stock tube (for the given volume, concentration,
#    and number of designs).
#
#    :param target_volume: The requested volume for the new pool stock sample
#        in ul.
#    :type target_volume: positive number
#
#    :param concentration: The requested pool concentration for the new pool
#        stock sample in nM.
#    :type target_volume: positive number
#
#    :param number_designs: The number of designs per pool must be the same
#        for all pools to be created.
#    :type number_designs: positive integer
#
#    :param stock_concentration: The stock concentration for single designs in
#        nM.
#    :type stock_concentration: positive number
#
#    :raises ValueErrors: if something the values are not compatible
#    """
#    target_single_conc = float(target_concentration) / number_designs
#    if target_single_conc > stock_concentration:
#        msg = 'The requested target concentration (%i nM) cannot be ' \
#              'achieved since it would require a concentration of %s nM for ' \
#              'each single design in the pool. However, the stock ' \
#              'concentration for this design type is only %s nM.' \
#              % (target_concentration, get_trimmed_string(target_single_conc),
#                 get_trimmed_string(stock_concentration))
#        raise ValueError(msg)
#
#    dil_factor = stock_concentration / target_single_conc
#    cybio_specs = get_pipetting_specs_cybio()
#    min_transfer_volume = cybio_specs.min_transfer_volume \
#                          * VOLUME_CONVERSION_FACTOR
#    min_target_volume = round_up(dil_factor * min_transfer_volume)
#    if (min_target_volume > target_volume):
#        msg = 'The target volume you have requested (%i ul) is too low ' \
#              'for the required dilution (1:%s) since the CyBio cannot ' \
#              'pipet less than %.1f ul per transfer. The volume that has ' \
#              'to be taken from the stock for each single molecule ' \
#              'design would be lower that that. Increase the target ' \
#              'volume to %.1f ul or increase the target concentration.' \
#              % (target_volume, get_trimmed_string(dil_factor),
#                 min_transfer_volume, round_up(min_target_volume, 0))
#        raise ValueError(msg)
#
#    stock_transfer_volume = round_up(target_volume / dil_factor)
#    # must be at least 1 ul according to the last check
#    total_transfer_volume = stock_transfer_volume * number_designs
#    if total_transfer_volume > target_volume:
#        msg = 'The target volume you have requested (%i ul) is too low ' \
#              'for the concentration you have ordered (%i uM) since it ' \
#              'would require already %s ul per molecule design (%s ul in ' \
#              'total) to achieve the requested concentration. Increase ' \
#              'the volume or lower the concentration, please.' \
#              % (target_volume, target_concentration,
#                 get_trimmed_string(stock_transfer_volume),
#                 get_trimmed_string(total_transfer_volume))
#        raise ValueError(msg)
#
#    return stock_transfer_volume
#
#def calculate_single_design_stock_transfer_volume_for_library(
#              pool_creation_library, single_design_stock_concentration=None):
#    """
#    Convenience method calculating the volume that has to be transferred
#    from a single design stock tube to a future pool stock tube (for the
#    given entity). If there is no single design stock concentration provided
#    the method will use the default value for handled molecule type (derived
#    from the library pool set) and a number of designs of 1.
#
#    The number of designs and the molecule type are assumed to be the same
#    for all pools in the pool set.
#
#    Invokes :func:`calculate_single_design_stock_transfer_volume`
#
#    :param pool_creation_library: Contains all required numbers.
#    :type pool_creation_library:
#        :class:`thelma.models.library.MoleculeDesignLibrary`
#
#    :param single_design_stock_concentration: The stock concentration for
#        the single design stock samples used to create the pools in nM.
#    :type single_design_stock_concentration: positive number
#    :default single_design_stock_concentration: *None* (default concentration
#        for the molecule type of the pool set)
#
#    :raises ValueErrors: if something the values are not compatible
#    """
#    pool_set = pool_creation_library.molecule_design_pool_set
#    number_designs = None
#    for pool in pool_set:
#        number_designs = pool.number_designs
#        break
#
#    if single_design_stock_concentration is None:
#        single_design_stock_concentration = get_default_stock_concentration(
#                                        molecule_type=pool_set.molecule_type)
#
#    return calculate_single_design_stock_transfer_volume(
#            target_volume=\
#                pool_creation_library.final_volume * VOLUME_CONVERSION_FACTOR,
#            target_concentration=\
#                pool_creation_library.final_concentration \
#                * CONCENTRATION_CONVERSION_FACTOR,
#            number_designs=number_designs,
#            stock_concentration=single_design_stock_concentration)
