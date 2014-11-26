"""
Molecule type mapper.
"""
from everest.repositories.rdb.utils import as_slug_expression
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.entities.chemicalstructure import ChemicalStructure
from thelma.entities.moleculetype import MoleculeType

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(molecule_type_tbl, molecule_type_modification_vw,
                  chemical_structure_tbl):
    "Mapper factory."
    mt = molecule_type_tbl
    mtmv = molecule_type_modification_vw
    cs = chemical_structure_tbl
    m = mapper(MoleculeType, mt,
               id_attribute='molecule_type_id',
               slug_expression=lambda cls: as_slug_expression(cls.name),
               properties=dict(
                   modifications=relationship(
                            ChemicalStructure,
                            secondary=mtmv,
                            primaryjoin=mtmv.c.molecule_type_id ==
                                                mt.c.molecule_type_id,
                            secondaryjoin=cs.c.chemical_structure_id ==
                                                mtmv.c.chemical_structure_id,
                            viewonly=True),
                   ),
               )
    return m
