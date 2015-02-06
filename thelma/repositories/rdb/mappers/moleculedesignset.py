"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Molecule design set mapper.
"""
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import mapper
from thelma.entities.moleculedesign import MOLECULE_DESIGN_SET_TYPES
from thelma.entities.moleculedesign import MoleculeDesign
from thelma.entities.moleculedesign import MoleculeDesignSetBase
from thelma.entities.sample import StockSample


__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(molecule_design_set_tbl, molecule_design_set_member_tbl):
    "Mapper factory."
    m = mapper(
          MoleculeDesignSetBase, molecule_design_set_tbl,
          id_attribute='molecule_design_set_id',
          properties=
            dict(molecule_designs=
                   relationship(MoleculeDesign, collection_class=set,
                                secondary=molecule_design_set_member_tbl,
                                lazy='joined'),
                 stock_samples=
                    relationship(StockSample,
                                 back_populates='molecule_design_pool'),
                 ),
            polymorphic_on=molecule_design_set_tbl.c.set_type,
            polymorphic_identity=MOLECULE_DESIGN_SET_TYPES.BASE,
           )
    return m
