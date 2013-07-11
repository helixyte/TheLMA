"""
Stock sample creation ISO mapper.
"""

from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.models.iso import ISO_TYPES
from thelma.models.iso import StockSampleCreationIso
from thelma.models.iso import IsoSectorPreparationPlate

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']

def create_mapper(iso_mapper, stock_sample_creation_iso_tbl):
    """Mapper factory"""

    m = mapper(StockSampleCreationIso, stock_sample_creation_iso_tbl,
               inherits=iso_mapper,
               properties=dict(
                    iso_sector_preparation_plates=relationship(
                        IsoSectorPreparationPlate, back_populates='iso',
                        cascade='all,delete,delete-orphan')),
               polymorphic_identity=ISO_TYPES.STOCK_SAMPLE_GENERATION)

    return m
