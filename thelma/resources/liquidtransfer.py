"""
Liquid transfer resources.

AAB
"""

from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from thelma.resources.base import RELATION_BASE_URL
from thelma.interfaces import IRackShape
from thelma.interfaces import IRackPosition

__docformat__ = 'reStructuredText en'


__all__ = ['ReservoirSpecsCollection',
           'ReservoirSpecsMember',
           'PipettingSpecsMember']


class ReservoirSpecsMember(Member):
    relation = '%s/reservoirspecs' % RELATION_BASE_URL
    name = terminal_attribute(str, 'name')
    rack_shape = member_attribute(IRackShape, 'rack_shape')
    max_volume = terminal_attribute(float, 'max_volume')
    dead_volume = terminal_attribute(float, 'dead_volume')

class ReservoirSpecsCollection(Collection):
    title = 'Reservoir Specs'
    root_name = 'reservoir-specs'
    description = 'Manage Reservoir Specs'


class PipettingSpecsMember(Member):
    relation = '%s/pipettingspecs' % RELATION_BASE_URL
    name = terminal_attribute(str, 'name')
    min_transfer_volume = terminal_attribute(float, 'min_transfer_volume')
    max_transfer_volume = terminal_attribute(float, 'max_transfer_volume')
    max_dilution_factor = terminal_attribute(int, 'max_dilution_factor')
    has_dynamic_dead_volume = terminal_attribute(bool,
                                                 'has_dynamic_dead_volume')
    is_sector_bound = terminal_attribute(bool, 'is_sector_bound')


class PlannedLiquidTransferMember(Member):
    relation = '%s/planned_liquid_transfer' % RELATION_BASE_URL
    volume = terminal_attribute(float, 'volume')
    transfer_type = terminal_attribute(str, 'transfer_type')
    hash_value = terminal_attribute(str, 'hash_value')


class PlannedSampleDilutionMember(PlannedLiquidTransferMember):
    relation = '%s/planned_sample_dilution' % RELATION_BASE_URL
    diluent_info = terminal_attribute(str, 'diluent_info')
    target_position = member_attribute(IRackPosition, 'target_position')


class PlannedSampleTransferMember(PlannedLiquidTransferMember):
    relation = '%s/planned_sample_transfer' % RELATION_BASE_URL
    source_position = member_attribute(IRackPosition, 'source_position')
    target_position = member_attribute(IRackPosition, 'target_position')


class PlannedRackSampleTransferMember(PlannedLiquidTransferMember):
    relation = '%s/planned_rack_sample_transfer' % RELATION_BASE_URL
    number_sectors = terminal_attribute(int, 'number_sectors')
    source_sector_index = terminal_attribute(int, 'source_sector_index')
    target_sector_index = terminal_attribute(int, 'target_sector_index')
