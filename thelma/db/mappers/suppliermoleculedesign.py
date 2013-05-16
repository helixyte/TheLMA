"""
Supplier molecule design mapper.
"""
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from thelma.models.moleculedesign import MoleculeDesign
from thelma.models.moleculedesign import MoleculeDesignPool
from thelma.models.organization import Organization
from thelma.models.suppliermoleculedesign import SupplierMoleculeDesign
from thelma.models.suppliermoleculedesign import SupplierStructureAnnotation


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(supplier_molecule_design_tbl,
                  single_supplier_molecule_design_tbl,
                  pooled_supplier_molecule_design_tbl):
    "Mapper factory."
    ssmd = single_supplier_molecule_design_tbl
    psmd = pooled_supplier_molecule_design_tbl
    m = mapper(SupplierMoleculeDesign, supplier_molecule_design_tbl,
               properties=dict(
                   supplier=
                       relationship(Organization,
                                    uselist=False),
                   supplier_structure_annotations=
                       relationship(SupplierStructureAnnotation,
                                    back_populates=
                                           'supplier_molecule_design'),
                   molecule_design=\
                     relationship(MoleculeDesign,
                                  uselist=False,
                                  secondary=ssmd,
                                  back_populates='supplier_molecule_designs'),
                   molecule_design_pool=\
                     relationship(MoleculeDesignPool,
                                  uselist=False,
                                  secondary=psmd,
                                  back_populates='supplier_molecule_designs')
                   ),
               )
    return m
