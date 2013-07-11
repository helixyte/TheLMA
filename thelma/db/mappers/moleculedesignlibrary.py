"""
Molecule design library mapper.
"""
from everest.repositories.rdb.utils import as_slug_expression
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.models.iso import StockSampleCreationIsoRequest
from thelma.models.library import MoleculeDesignLibrary
from thelma.models.moleculedesign import MoleculeDesignPoolSet

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']

def create_mapper(molecule_design_library_tbl,
                  stock_sample_creation_iso_request_tbl,
                  molecule_design_library_iso_request_tbl):
    """
    Mapper factory
    """
    mdl = molecule_design_library_tbl
    sscir = stock_sample_creation_iso_request_tbl
    mdlir = molecule_design_library_iso_request_tbl

    m = mapper(MoleculeDesignLibrary, molecule_design_library_tbl,
               id_attribute='molecule_design_library_id',
               slug_expression=lambda cls: as_slug_expression(cls.label),
               properties=dict(
                    molecule_design_pool_set=
                        relationship(MoleculeDesignPoolSet,
                                     uselist=False),
                    iso_request=relationship(StockSampleCreationIsoRequest,
                                             uselist=False,
                            back_populates='molecule_design_library',
                            primaryjoin=(mdl.c.molecule_design_library_id == \
                                         mdlir.c.molecule_design_library_id),
                            secondaryjoin=(mdlir.c.iso_request_id == \
                                           sscir.c.iso_request_id),
                            secondary=mdlir))
               )
    return m
