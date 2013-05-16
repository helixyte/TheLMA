"""
Molecule design set mapper.
"""
from everest.repositories.rdb.utils import mapper
from thelma.models.moleculedesign import MOLECULE_DESIGN_SET_TYPES
from thelma.models.moleculedesign import MoleculeDesignSet

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(molecule_design_set_mapper):
    "Mapper factory."
    m = mapper(MoleculeDesignSet,
               inherits=molecule_design_set_mapper,
               polymorphic_identity=MOLECULE_DESIGN_SET_TYPES.STANDARD)
    return m
