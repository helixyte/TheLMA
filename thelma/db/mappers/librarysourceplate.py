"""
Library ISO source (preparation) plate mapper.
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
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
               id_attribute='library_source_plate_id',
               properties=dict(
                    plate=relationship(Rack, uselist=False),
                    iso=relationship(LibraryCreationIso, uselist=False,
                        back_populates='library_source_plates'),
                                )
               )
    return m
