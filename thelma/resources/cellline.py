"""
Cell culture ware resource.
"""

from datetime import datetime
from everest.querying.specifications import AscendingOrderSpecification
from everest.resources.base import Collection, Member
from everest.resources.descriptors import attribute_alias, member_attribute, \
    terminal_attribute
from thelma.interfaces import ICellCultureWare, ICellLine, ICellLineBatch, IContainer, \
    IOrganization, ISpecies, ISubproject, ITissue
from thelma.resources.base import RELATION_BASE_URL


__docformat__ = 'reStructuredText en'

__all__ = ['CellLineCollection',
           'CellLineMember',
           'CellLineBatchCollection',
           'CellLineBatchMember',
           ]


class CellLineMember(Member):
    relation = "%s/cell_line" % RELATION_BASE_URL
    title = attribute_alias('label')
    label = terminal_attribute(str, 'label')
    species = member_attribute(ISpecies, 'species_id')
    origin = terminal_attribute(str, 'origin')
    tissue = member_attribute(ITissue, 'tissue_id')
    image = terminal_attribute(str, 'image')
    is_type_immortal = terminal_attribute(bool, 'is_type_immortal')
    is_type_adherent = terminal_attribute(bool, 'is_type_adherent')
    safety_level = terminal_attribute(int, 'safety_level')
    protocol_splitting = terminal_attribute(str, 'protocol_splitting')
    protocol_media = terminal_attribute(str, 'protocol_media')
    protocol_thawing = terminal_attribute(str, 'protocol_thawing')
    cell_culture_ware = member_attribute(IOrganization, 'cell_culture_ware_id')
    maximum_passage = terminal_attribute(int, 'maximum_passage')
    culture_conditions_temperature = terminal_attribute(float, 'culture_conditions_temperature')
    culture_conditions_humidity = terminal_attribute(float, 'culture_conditions_humidity')
    culture_conditions_co2 = terminal_attribute(float, 'culture_conditions_co2')
    comments = terminal_attribute(str, 'comments')

class CellLineCollection(Collection):
    title = 'CellLines'
    root_name = 'cell_lines'
    description = 'Manage cell lines'
    default_order = AscendingOrderSpecification('label')


class CellLineBatchMember(Member):
    relation = "%s/cell_line_batch" % RELATION_BASE_URL
    container = member_attribute(IContainer, 'container_id')
    cell_line = member_attribute(ICellLine, 'cell_line_id')
    subproject = member_attribute(ISubproject, 'subproject_id')
    freezing_date = terminal_attribute(datetime, 'freezing_date')
    defrozting_date = terminal_attribute(datetime, 'defrozting_date')
    passage = terminal_attribute(int, 'passage')
    is_master_stock = terminal_attribute(bool, 'is_master_stock')
    parent_cell_line_batch = member_attribute(ICellLineBatch, 'defrozting_date')
    cell_count = terminal_attribute(long, 'cell_count')
    freezing_medium_dmso = terminal_attribute(float, 'freezing_medium_dmso')
    freezing_medium_serum = terminal_attribute(float, 'freezing_medium_serum')
    freezing_medium_medium = terminal_attribute(float, 'freezing_medium_medium')
    comments = terminal_attribute(str, 'comments')


class CellLineBatchCollection(Collection):
    title = 'CellLineBatches'
    root_name = 'cell_line_batches'
    description = 'Manage cell lines batches'
    default_order = AscendingOrderSpecification('freezing_date') \
                    & AscendingOrderSpecification('container_id')
