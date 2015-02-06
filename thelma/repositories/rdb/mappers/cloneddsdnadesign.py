"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Clonded dsDNA mapper.
"""
from sqlalchemy.orm import mapper

from thelma.entities.moleculedesign import ClonedDsDnaDesign
from thelma.entities.moleculetype import MOLECULE_TYPE_IDS


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(molecule_design_mapper, molecule_design_tbl):
    "Mapper factory."
    m = mapper(ClonedDsDnaDesign, molecule_design_tbl,
               inherits=molecule_design_mapper,
               polymorphic_identity=MOLECULE_TYPE_IDS.CLND_DSDNA)
    return m
