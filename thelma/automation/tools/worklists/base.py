"""
Base constants, functions and classes for liquid transfers.

AAB
"""
from thelma.automation.tools.semiconstants import RESERVOIR_SPECS_NAMES
from thelma.automation.tools.semiconstants import get_reservoir_spec
from thelma.models.liquidtransfer import ReservoirSpecs

__docformat__ = 'reStructuredText en'

__all__ = ['VOLUME_CONVERSION_FACTOR',
           'CONCENTRATION_CONVERSION_FACTOR',
           'MIN_BIOMEK_TRANSFER_VOLUME',
           'MAX_BIOMEK_TRANSFER_VOLUME',
           'MIN_CYBIO_TRANSFER_VOLUME',
           'MAX_CYBIO_TRANSFER_VOLUME',
           'LIMIT_TARGET_WELLS',
           'DEAD_VOLUME_COEFFICIENT',
           'TRANSFER_ROLES',
           'get_biomek_dead_volume',
           ]


#: Volumes are stored in litres (in the DB), we work in ul.
VOLUME_CONVERSION_FACTOR = 1e6
#: Concentration are stored in molars (in the DB), we work with nM.
CONCENTRATION_CONVERSION_FACTOR = 1e9

#: The minimum volume that can be pipetted by a BioMek in ul.
MIN_BIOMEK_TRANSFER_VOLUME = 3
#: The maximum volume that can be pipetted by a BioMek in ul.
MAX_BIOMEK_TRANSFER_VOLUME = 200
#: The minimum volume that can be pipetted by a CyBio in ul.
MIN_CYBIO_TRANSFER_VOLUME = 1
#: The maximum volume that can be pipetted by a CyBio in ul.
MAX_CYBIO_TRANSFER_VOLUME = 200

#: This refers to the dynamic dead volume calculation for the Biomek.
#: It is the maximum number of targets well a source might have before its
#: dead is corrected.
LIMIT_TARGET_WELLS = 3
#: This refers to the dynamic dead volume calculation for the Biomek.
#: It is the volume [in ul] that is added to the source volume for each new
#: new target well (if LIMIT_TARGET_WELLS is exceeded).
DEAD_VOLUME_COEFFICIENT = 1


class TRANSFER_ROLES(object):
    """
    Roles of racks or reservoirs in sample transfers
    """
    #: A source provides volumes.
    SOURCE = 'source'
    #: A target takes up volume.
    TARGET = 'target'


def get_biomek_dead_volume(target_well_number,
                    reservoir_specs=RESERVOIR_SPECS_NAMES.STANDARD_96):
    """
    Calculate a dynamic dead volume for a Biomek worklist.

    :param target_well_number: The number of target wells for the given
        source well.
    :type target_well_number: :class:` int`
    :param is_96_well_plate: Is the source plate a 96 well plate?
    :param reservoir_specs: The reservoir specs you are assuming.
    :type reservoir_specs: a :class:`RESERVOIR_SPECS_NAMES` element or
        a :class:`thelma.models.liquidtransfer.ReservoirSpecs` object
    :default reservoir_specs: RESERVOIR_SPECS_NAMES.STANDARD_96

    :Note: At the moment corrections are only applied to plates.

    :raises TypeError: if resrevoir_specs is not a string or ReservoirSpecs
    :return: The adjusted dead volume in ul.
    """

    if isinstance(reservoir_specs, ReservoirSpecs):
        rs = reservoir_specs
    elif isinstance(reservoir_specs, basestring):
        rs = get_reservoir_spec(reservoir_specs)
    else:
        msg = 'Unsupported type for reservoir specs: %s. Expectes string ' \
              'or ReservoirSpecs object.' % (reservoir_specs.__class__.__name__)
        raise TypeError(msg)

    # pylint: disable=E1103
    min_dead_volume_ul = rs.min_dead_volume * VOLUME_CONVERSION_FACTOR
    max_dead_volume_ul = rs.max_dead_volume * VOLUME_CONVERSION_FACTOR
    # pylint: enable=E1103

    if min_dead_volume_ul == max_dead_volume_ul:
        return min_dead_volume_ul

    if target_well_number <= LIMIT_TARGET_WELLS:
        return min_dead_volume_ul

    exceeding_well_count = target_well_number - LIMIT_TARGET_WELLS
    additional_volume = exceeding_well_count * DEAD_VOLUME_COEFFICIENT
    adjusted_dead_volume = min_dead_volume_ul + additional_volume
    if adjusted_dead_volume > max_dead_volume_ul:
        adjusted_dead_volume = max_dead_volume_ul
    return adjusted_dead_volume
