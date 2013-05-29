"""
Library creation ISO mapper.
"""

from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.models.iso import ISO_TYPES
from thelma.models.library import LibraryCreationIso
from thelma.models.library import LibrarySourcePlate

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']

def create_mapper(iso_mapper, library_creation_iso_tbl):
    """Mapper factory"""

    m = mapper(LibraryCreationIso, library_creation_iso_tbl,
               inherits=iso_mapper,
               properties=dict(
                    library_source_plates=relationship(LibrarySourcePlate,
                                                       back_populates='iso'),
                               ),
               polymorphic_identity=ISO_TYPES.LIBRARY_CREATION)

    return m
