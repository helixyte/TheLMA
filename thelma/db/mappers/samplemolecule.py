"""
Sample molecule mapper.
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.models.sample import Molecule
from thelma.models.sample import Sample
from thelma.models.sample import SampleMolecule

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(sample_molecule_tbl):
    "Mapper factory."
    m = mapper(SampleMolecule, sample_molecule_tbl,
            id_attribute='molecule_id',
            properties=dict(
                sample=relationship(Sample, uselist=False,
                                    back_populates='sample_molecules'),
                molecule=relationship(Molecule, uselist=False,
                    back_populates='sample_molecules',
                    lazy='joined'),
                ),
        )
    return m
