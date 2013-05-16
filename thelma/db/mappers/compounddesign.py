"""
Compound design mapper.
"""
from sqlalchemy.orm import mapper
from thelma.models.moleculedesign import CompoundDesign
from thelma.models.moleculetype import MOLECULE_TYPE_IDS

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(design_mapper, molecule_design_tbl):
    "Mapper factory."
    m = mapper(CompoundDesign, molecule_design_tbl,
               inherits=design_mapper,
               polymorphic_identity=MOLECULE_TYPE_IDS.COMPOUND
               )
    return m
