"""
Sample molecule mapper.
"""
from sqlalchemy import String
from sqlalchemy.orm import column_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.sql import cast
from sqlalchemy.sql import literal
from thelma.models.sample import Molecule
from thelma.models.sample import Sample
from thelma.models.sample import SampleMolecule

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(sample_molecule_tbl):
    "Mapper factory."
    m = mapper(SampleMolecule, sample_molecule_tbl,
        properties=dict(
            id=column_property(
                    cast(sample_molecule_tbl.c.sample_id, String) +
                    literal('_') +
                    cast(sample_molecule_tbl.c.molecule_id, String)),
            sample=relationship(Sample, uselist=False,
                                back_populates='sample_molecules'),
            molecule=relationship(Molecule, uselist=False,
                back_populates='sample_molecules',
                lazy='joined'),
            ),
        )
    return m
