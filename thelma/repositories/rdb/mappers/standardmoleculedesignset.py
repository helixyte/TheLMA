"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Molecule design set mapper.
"""
from everest.repositories.rdb.utils import mapper
from thelma.entities.moleculedesign import MOLECULE_DESIGN_SET_TYPES
from thelma.entities.moleculedesign import MoleculeDesignSet


__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(molecule_design_set_mapper):
    "Mapper factory."
    m = mapper(MoleculeDesignSet,
               inherits=molecule_design_set_mapper,
               polymorphic_identity=MOLECULE_DESIGN_SET_TYPES.STANDARD)
    return m
