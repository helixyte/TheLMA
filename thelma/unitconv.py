# -*- coding: utf-8 -*-
"""
Conversion between display and storage units

Based on celma.conversions module.

NP
"""

__docformat__ = 'reStructuredText en'


__all__ = ['VOLUME_DISPLAY_UNIT',
           'CONCENTRATION_DISPLAY_UNIT',
           'QUANTITY_DISPLAY_UNIT',
           'stored_volume_to_displayed',
           'displayed_volume_to_stored',
           'stored_concentration_to_displayed',
           'displayed_concentration_to_stored',
           'stored_quantity_to_displayed',
           'displayed_quantity_to_stored',
           ]


VOLUME_DISPLAY_UNIT = 'μl'
_VOLUME_FACTOR = 1e6

CONCENTRATION_DISPLAY_UNIT = 'μM'
_CONCENTRATION_FACTOR = 1e6

QUANTITY_DISPLAY_UNIT = 'nmol'
_QUANTITY_FACTOR = 1e9


def stored_volume_to_displayed(volume):
    """
    Converts the stored volume to the unit used for displaying the volume.

    :param volume: the volume
    :type volume: float
    :returns: volume in μl
    :rtype: float
    """
    return volume * _VOLUME_FACTOR


def displayed_volume_to_stored(volume):
    """
    Converts the displayed volume to the unit used for storing the volume.

    :param volume: the volume
    :type volume: float
    :returns: volume in l
    :rtype: L{float}
    """
    return volume / _VOLUME_FACTOR


def stored_concentration_to_displayed(concentration):
    """
    Converts the stored concentration to the unit used for displaying the
    concentration.

    :param concentration: the concentration
    :type concentration: float
    :returns: concentration in μM
    :rtype: float
    """
    return concentration * _CONCENTRATION_FACTOR


def displayed_concentration_to_stored(concentration):
    """
    Converts the displayed concentration to the unit used for storing the
    concentration

    :param concentration: the concentration
    :type concentration: float
    :returns: concentration
    :rtype: float
    """
    return concentration / _CONCENTRATION_FACTOR


def stored_quantity_to_displayed(quantity):
    """
    Converts the stored quantity to the unit used for displaying the quantity.

    :param quantity: the quantity
    :type quantity: float
    :returns: quantity in nmol
    :rtype: float
    """
    return quantity * _QUANTITY_FACTOR


def displayed_quantity_to_stored(quantity):
    """
    Converts the displayed quantity to the unit used for storing the
    quantity

    :param quantity: the quantity
    :type quantity: float
    :returns: quantity
    :rtype: float
    """
    return quantity / _QUANTITY_FACTOR
