"""
Molecule design mapper.
"""
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import mapper
from thelma.entities.chemicalstructure import ChemicalStructure
from thelma.entities.gene import Gene
from thelma.entities.moleculedesign import MoleculeDesign
from thelma.entities.moleculetype import MoleculeType
from thelma.entities.suppliermoleculedesign import SupplierMoleculeDesign


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


MOLECULE_TYPE = 'DESIGN'


def create_mapper(molecule_design_tbl, molecule_design_structure_tbl,
                  single_supplier_molecule_design_tbl,
                  molecule_design_gene_tbl, refseq_gene_tbl):
    "Mapper factory."
    md = molecule_design_tbl
    ssmd = single_supplier_molecule_design_tbl
    mdg = molecule_design_gene_tbl
    rsg = refseq_gene_tbl
    m = mapper(MoleculeDesign, molecule_design_tbl,
          id_attribute='molecule_design_id',
          properties=dict(
            molecule_type=relationship(MoleculeType), #, lazy='joined'),
            chemical_structures=relationship(
                                    ChemicalStructure,
                                    secondary=molecule_design_structure_tbl,
                                    back_populates='molecule_designs'),
            supplier_molecule_designs=
                        relationship(SupplierMoleculeDesign,
                                     secondary=ssmd,
                                     back_populates='molecule_design'),
            genes=relationship(Gene, viewonly=True, secondary=mdg,
                primaryjoin=(mdg.c.molecule_design_id ==
                                                    md.c.molecule_design_id),
                secondaryjoin=(mdg.c.gene_id == rsg.c.gene_id),
                foreign_keys=(mdg.c.molecule_design_id, mdg.c.gene_id),
                back_populates='molecule_designs',
                ),
            ),
          polymorphic_on=molecule_design_tbl.c.molecule_type_id,
          polymorphic_identity=MOLECULE_TYPE,
          )
    return m
