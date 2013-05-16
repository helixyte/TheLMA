"""
Compound chemical structure mapper.
"""
from sqlalchemy.orm import mapper
from thelma.models.chemicalstructure import CHEMICAL_STRUCTURE_TYPE_IDS
from thelma.models.chemicalstructure import CompoundChemicalStructure

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(chemical_structure_mapper, chemical_structure_tbl):
    "Mapper factory."
    m = mapper(CompoundChemicalStructure, chemical_structure_tbl,
               inherits=chemical_structure_mapper,
               polymorphic_identity=CHEMICAL_STRUCTURE_TYPE_IDS.COMPOUND
               )
    return m
