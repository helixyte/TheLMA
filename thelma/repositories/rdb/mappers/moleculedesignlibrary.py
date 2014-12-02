"""
Molecule design library mapper.
"""
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import as_slug_expression
from everest.repositories.rdb.utils import mapper
from thelma.entities.iso import StockSampleCreationIsoRequest
from thelma.entities.library import LibraryPlate
from thelma.entities.library import MoleculeDesignLibrary
from thelma.entities.moleculedesign import MoleculeDesignPoolSet
from thelma.entities.racklayout import RackLayout


__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(molecule_design_library_tbl,
                  stock_sample_creation_iso_request_tbl,
                  molecule_design_library_creation_iso_request_tbl):
    "Mapper factory."
    mdl = molecule_design_library_tbl
    sscir = stock_sample_creation_iso_request_tbl
    mdlcir = molecule_design_library_creation_iso_request_tbl
    m = mapper(MoleculeDesignLibrary, molecule_design_library_tbl,
               id_attribute='molecule_design_library_id',
               slug_expression=lambda cls: as_slug_expression(cls.label),
               properties=dict(
                    molecule_design_pool_set=
                        relationship(MoleculeDesignPoolSet,
                                     uselist=False,
                                     cascade='all,delete-orphan',
                                     single_parent=True),
                    rack_layout=relationship(RackLayout, uselist=False,
                                cascade='all,delete,delete-orphan',
                                single_parent=True),
                    creation_iso_request=relationship(
                            StockSampleCreationIsoRequest,
                            uselist=False,
                            back_populates='molecule_design_library',
                            primaryjoin=(mdl.c.molecule_design_library_id == \
                                         mdlcir.c.molecule_design_library_id),
                            secondaryjoin=(mdlcir.c.iso_request_id == \
                                           sscir.c.iso_request_id),
                            secondary=mdlcir,
                            cascade='all,delete-orphan',
                            single_parent=True),
                    library_plates=relationship(LibraryPlate,
                                    back_populates='molecule_design_library',
                                    cascade='all,delete-orphan')
                               )
               )
    return m
