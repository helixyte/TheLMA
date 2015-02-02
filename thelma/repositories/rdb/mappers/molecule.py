"""
Molecule mapper.
"""
from sqlalchemy.orm import column_property
from sqlalchemy.orm import relationship
from sqlalchemy.sql import distinct
from sqlalchemy.sql import select
from sqlalchemy.sql.expression import and_

from everest.repositories.rdb.utils import mapper
from thelma.entities.moleculedesign import MoleculeDesign
from thelma.entities.organization import Organization
from thelma.entities.sample import Molecule
from thelma.entities.sample import SampleMolecule
from thelma.entities.suppliermoleculedesign import SupplierMoleculeDesign


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(molecule_tbl, single_supplier_molecule_design_tbl,
                  supplier_molecule_design_tbl):
    "Mapper factory."
    ssmd = single_supplier_molecule_design_tbl
    smd = supplier_molecule_design_tbl
    mcl = molecule_tbl.alias()
    prd_sel = \
        select([distinct(smd.c.product_id)],
               and_(mcl.c.molecule_design_id ==
                                        molecule_tbl.c.molecule_design_id,
                    smd.c.supplier_id == molecule_tbl.c.supplier_id,
                    smd.c.is_current
                    ),
               from_obj=[mcl.join(ssmd,
                                  ssmd.c.molecule_design_id ==
                                            mcl.c.molecule_design_id)
                            .join(smd,
                                  smd.c.supplier_molecule_design_id ==
                                         ssmd.c.supplier_molecule_design_id)]
               )
    m = mapper(Molecule, molecule_tbl,
        id_attribute='molecule_id',
        properties=dict(
            supplier=relationship(Organization),
            molecule_design=relationship(MoleculeDesign, uselist=False,
#                                         lazy='joined'
                                         ),
            # Loading the product ID like this is faster than loading it
            # through the supplier molecule design.
            product_id=column_property(prd_sel.as_scalar(), deferred=True),
            supplier_molecule_design=
                 relationship(SupplierMoleculeDesign,
                              uselist=False,
                              secondary=ssmd,
                              primaryjoin=ssmd.c.molecule_design_id ==
                                             molecule_tbl.c.molecule_design_id,
                              secondaryjoin=
                                 and_(smd.c.supplier_molecule_design_id ==
                                         ssmd.c.supplier_molecule_design_id,
                                      smd.c.supplier_id ==
                                             molecule_tbl.c.supplier_id,
                                      smd.c.is_current),
                              foreign_keys=
                                     (ssmd.c.molecule_design_id,
                                      ssmd.c.supplier_molecule_design_id),
                              viewonly=True),
            sample_molecules=relationship(SampleMolecule,
                                          back_populates='molecule'),
            ),
        )
    return m
