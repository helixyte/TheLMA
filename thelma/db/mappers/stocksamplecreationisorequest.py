"""
Lab ISO request mapper.
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.models.iso import ISO_TYPES
from thelma.models.iso import StockSampleCreationIsoRequest
from thelma.models.library import MoleculeDesignLibrary

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']

def create_mapper(iso_request_mapper,
                  stock_sample_creation_iso_request_tbl,
                  molecule_design_library_iso_request_tbl,
                  molecule_design_library_tbl):
    "Mapper factory."


    sscir = stock_sample_creation_iso_request_tbl
    mdlir = molecule_design_library_iso_request_tbl
    mdl = molecule_design_library_tbl

    m = mapper(StockSampleCreationIsoRequest,
               stock_sample_creation_iso_request_tbl,
               inherits=iso_request_mapper,
               properties=dict(
                    molecule_design_library=relationship(MoleculeDesignLibrary,
                        back_populates='iso_request', uselist=False,
                        primaryjoin=(sscir.c.iso_request_id == \
                                     mdlir.c.iso_request_id),
                        secondaryjoin=(mdlir.c.molecule_design_library_id == \
                                       mdl.c.molecule_design_library_id),
                        secondary=mdlir)
                        ),
               polymorphic_identity=ISO_TYPES.STOCK_SAMPLE_GENERATION,
               )

    return m
