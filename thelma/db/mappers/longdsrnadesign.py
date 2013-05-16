"""
long dsRNA design mapper.
"""
from sqlalchemy.orm import mapper
from thelma.models.moleculedesign import LongDoubleStrandedRnaDesign
from thelma.models.moleculetype import MOLECULE_TYPE_IDS

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(molecule_design_mapper, molecule_design_tbl):
    "Mapper factory."
    m = mapper(LongDoubleStrandedRnaDesign, molecule_design_tbl,
               inherits=molecule_design_mapper,
               polymorphic_identity=MOLECULE_TYPE_IDS.LONG_DSRNA)
    return m
