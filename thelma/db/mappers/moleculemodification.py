"""
Molecule modification mapper.
"""
from sqlalchemy.orm import mapper
from sqlalchemy.orm import synonym
from thelma.models.moleculemodification import MoleculeModification


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(molecule_modification_vw):
    """
    Mapper factory.
    """
    m = mapper(MoleculeModification, molecule_modification_vw,
               primary_key=[molecule_modification_vw.c.name,
                            molecule_modification_vw.c.molecule_type_id
                            ],
               order_by=[molecule_modification_vw.c.molecule_type_id,
                         molecule_modification_vw.c.name],
               properties=dict(id=synonym('molecule_type_id'),
                               )
               )
    return m
