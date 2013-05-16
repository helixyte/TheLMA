"""
Molecule design set mapper.
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.models.gene import Gene
from thelma.models.moleculedesign import MOLECULE_DESIGN_SET_TYPES
from thelma.models.moleculedesign import MoleculeDesignPool
from thelma.models.moleculetype import MoleculeType
from thelma.models.suppliermoleculedesign import SupplierMoleculeDesign

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(molecule_design_set_mapper, molecule_design_pool_tbl,
                  pooled_supplier_molecule_design_tbl,
                  supplier_molecule_design_tbl, molecule_design_set_gene_tbl):
    "Mapper factory."
    mdp = molecule_design_pool_tbl
    psmd = pooled_supplier_molecule_design_tbl
    smd = supplier_molecule_design_tbl
    mdsg = molecule_design_set_gene_tbl
    m = mapper(MoleculeDesignPool,
               molecule_design_pool_tbl,
               inherits=molecule_design_set_mapper,
               properties=dict(
                    molecule_type=relationship(MoleculeType,
                                               lazy='joined'),
                    supplier_molecule_designs=
                        relationship(
                            SupplierMoleculeDesign,
                            secondary=psmd,
                            primaryjoin=psmd.c.molecule_design_set_id ==
                                                mdp.c.molecule_design_set_id,
                            secondaryjoin=smd.c.supplier_molecule_design_id ==
                                           psmd.c.supplier_molecule_design_id,
                            foreign_keys=[psmd.c.molecule_design_set_id,
                                          psmd.c.supplier_molecule_design_id],
                            back_populates='molecule_design_pool'),
                    genes=relationship(Gene,
                                       viewonly=True,
                                       secondary=mdsg),
                    ),
               polymorphic_identity=MOLECULE_DESIGN_SET_TYPES.POOL)
    return m
