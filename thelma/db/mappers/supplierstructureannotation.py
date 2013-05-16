"""
Chemical structure mapper.
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.models.suppliermoleculedesign import SupplierMoleculeDesign
from thelma.models.suppliermoleculedesign import SupplierStructureAnnotation
from thelma.models.chemicalstructure import ChemicalStructure


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(supplier_structure_annotation_tbl):
    "Mapper factory."
    m = mapper(SupplierStructureAnnotation, supplier_structure_annotation_tbl,
               properties=dict(
                    supplier_molecule_design=
                        relationship(SupplierMoleculeDesign,
                                     uselist=False,
                                     back_populates=
                                        'supplier_structure_annotations'),
                    chemical_structure=
                        relationship(ChemicalStructure,
                                     uselist=False),
                    ),
               )
    return m
