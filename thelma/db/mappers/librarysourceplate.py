"""
Library ISO source (preparation) plate mapper.
"""
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from thelma.models.library import LibraryCreationIso
from thelma.models.library import LibrarySourcePlate
from thelma.models.rack import Rack

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']

def create_mapper(library_source_plate_tbl):
    """
    Mapper factory.
    """
    m = mapper(LibrarySourcePlate, library_source_plate_tbl,
               properties=dict(
                    id=synonym('library_source_plate_id'),
                    plate=relationship(Rack, uselist=False),
                    iso=relationship(LibraryCreationIso, uselist=False,
                        back_populates='library_source_plates'),
                                )
               )

    return m
