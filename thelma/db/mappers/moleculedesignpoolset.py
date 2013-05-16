"""
Molecule design set mapper.
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.models.moleculedesign import MoleculeDesignPool
from thelma.models.moleculedesign import MoleculeDesignPoolSet
from thelma.models.moleculetype import MoleculeType

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(molecule_design_pool_set_tbl,
                  molecule_design_pool_set_member_tbl):
    "Mapper factory."
    m = mapper(
          MoleculeDesignPoolSet, molecule_design_pool_set_tbl,
          id_attribute='molecule_design_pool_set_id',
          properties=
            dict(molecule_design_pools=
                   relationship(MoleculeDesignPool,
                                collection_class=set,
                                secondary=molecule_design_pool_set_member_tbl),
                 molecule_type=relationship(MoleculeType, uselist=False)
                 ),
           )
    return m
