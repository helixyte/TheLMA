"""
Lab ISO mapper
"""

from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.models.iso import ISO_TYPES
from thelma.models.iso import LabIso
from thelma.models.library import LibraryPlate

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(iso_mapper, iso_tbl, iso_library_plate_tbl):
    "Mapper factory."
    m = mapper(LabIso, iso_tbl,
               inherits=iso_mapper,
               polymorphic_identity=ISO_TYPES.LAB,
               properties=dict(
                        library_plates=relationship(LibraryPlate,
                                        secondary=iso_library_plate_tbl,
                                        back_populates='lab_iso',
                                        cascade='all')
                               )
               )
    return m
