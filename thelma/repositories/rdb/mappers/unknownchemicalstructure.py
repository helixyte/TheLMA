"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Unknown chemical structure mapper.
"""
from sqlalchemy.orm import mapper

from thelma.entities.chemicalstructure import CHEMICAL_STRUCTURE_TYPE_IDS
from thelma.entities.chemicalstructure import UnknownChemicalStructure


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(chemical_structure_mapper, chemical_structure_tbl):
    "Mapper factory."
    m = mapper(UnknownChemicalStructure, chemical_structure_tbl,
               inherits=chemical_structure_mapper,
               polymorphic_identity=CHEMICAL_STRUCTURE_TYPE_IDS.UNKNOWN
               )
    return m
