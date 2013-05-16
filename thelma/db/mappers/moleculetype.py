"""
Molecule type mapper.
"""
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from thelma.db.mappers.utils import as_slug_expression
from thelma.models.chemicalstructure import ChemicalStructure
from thelma.models.moleculetype import MoleculeType

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(molecule_type_tbl, molecule_type_modification_vw,
                  chemical_structure_tbl):
    "Mapper factory."
    mt = molecule_type_tbl
    mtmv = molecule_type_modification_vw
    cs = chemical_structure_tbl
    m = mapper(MoleculeType, mt,
               properties=dict(
                   id=synonym('molecule_type_id'),
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
    if isinstance(MoleculeType.slug, property):
        MoleculeType.slug = \
            hybrid_property(MoleculeType.slug.fget,
                            expr=lambda cls: as_slug_expression(cls.name))
    return m
