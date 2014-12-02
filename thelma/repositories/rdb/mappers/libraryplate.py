"""
Library plate mapper.
"""
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import mapper
from thelma.entities.iso import LabIso
from thelma.entities.library import LibraryPlate
from thelma.entities.library import MoleculeDesignLibrary
from thelma.entities.rack import Rack


__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(library_plate_tbl, iso_library_plate_tbl):
    """
    Mapper factory
    """
    m = mapper(LibraryPlate, library_plate_tbl,
               id_attribute='library_plate_id',
               properties=dict(
                    molecule_design_library=relationship(MoleculeDesignLibrary,
                                uselist=False,
                                back_populates='library_plates'),
                    rack=relationship(Rack, uselist=False),
                    lab_iso=relationship(LabIso, uselist=False,
                                         secondary=iso_library_plate_tbl,
                                         back_populates='library_plates')
                    )
               )
    return m
