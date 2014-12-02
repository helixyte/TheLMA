"""
Chemical structure mapper.
"""
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import mapper
from thelma.entities.chemicalstructure import ChemicalStructure
from thelma.entities.moleculedesign import MoleculeDesign


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


STRUCTURE_TYPE = 'STRUCTURE'


def create_mapper(chemical_structure_tbl, molecule_design_structure_tbl):
    "Mapper factory."
    m = mapper(ChemicalStructure, chemical_structure_tbl,
               id_attribute='chemical_structure_id',
               properties=dict(
                    molecule_designs=
                        relationship(MoleculeDesign,
                                     secondary=molecule_design_structure_tbl,
                                     back_populates='chemical_structures'),
                    ),
               polymorphic_on=chemical_structure_tbl.c.structure_type_id,
               polymorphic_identity=STRUCTURE_TYPE
               )
    return m
