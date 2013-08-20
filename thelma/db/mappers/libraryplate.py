"""
Library plate mapper.
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.models.iso import LabIso
from thelma.models.library import LibraryPlate
from thelma.models.library import MoleculeDesignLibrary
from thelma.models.rack import Rack

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']

def create_mapper(library_plate_tbl):
    """
    Mapper factory
    """

    m = mapper(LibraryPlate, library_plate_tbl,
               id_attribute='library_plate_id',
               properties=dict(
                    molecule_design_library=relationship(MoleculeDesignLibrary,
                                use_list=False,
                                back_populates='library_plates'),
                    rack=relationship(Rack, uselist=False),
                    lab_iso=relationship(LabIso, uselist=False,
                                         back_populates='library_plates')
                    )
               )
    return m
