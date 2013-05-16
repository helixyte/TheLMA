"""
Stock sample mapper.
"""
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from thelma.models.moleculedesign import MoleculeDesignPool
from thelma.models.moleculetype import MoleculeType
from thelma.models.organization import Organization
from thelma.models.sample import SAMPLE_TYPES
from thelma.models.sample import SampleRegistration
from thelma.models.sample import StockSample

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(sample_mapper, stock_sample_tbl):
    "Mapper factory."
    m = mapper(StockSample, stock_sample_tbl, inherits=sample_mapper,
        properties=dict(
            molecule_design_pool=relationship(MoleculeDesignPool,
                                              uselist=False,
                                              back_populates='stock_samples',
                                              lazy='joined'),
            supplier=relationship(Organization),
            molecule_type=relationship(MoleculeType, lazy='joined'),
            registration=
                    relationship(SampleRegistration,
                                 back_populates='sample',
                                 uselist=False),
            ),
        polymorphic_identity=SAMPLE_TYPES.STOCK
        )
    return m
