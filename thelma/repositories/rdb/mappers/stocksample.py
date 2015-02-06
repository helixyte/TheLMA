"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Stock sample mapper.
"""
from sqlalchemy.orm import column_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.sql import distinct
from sqlalchemy.sql import select
from sqlalchemy.sql.expression import and_

from thelma.entities.moleculedesign import MoleculeDesignPool
from thelma.entities.moleculetype import MoleculeType
from thelma.entities.organization import Organization
from thelma.entities.sample import SAMPLE_TYPES
from thelma.entities.sample import SampleRegistration
from thelma.entities.sample import StockSample


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(sample_mapper, stock_sample_tbl,
                  pooled_supplier_molecule_design_tbl,
                  supplier_molecule_design_tbl):
    "Mapper factory."
    psmd = pooled_supplier_molecule_design_tbl
    smd = supplier_molecule_design_tbl
    sts = stock_sample_tbl.alias()
    prd_sel = \
         select([distinct(smd.c.product_id)],
                and_(
                     sts.c.molecule_design_set_id == stock_sample_tbl.c.molecule_design_set_id,
                     smd.c.supplier_id == stock_sample_tbl.c.supplier_id,
                     smd.c.is_current),
                from_obj=[sts.join(psmd,
                                   psmd.c.molecule_design_set_id ==
                                             sts.c.molecule_design_set_id)
                             .join(smd,
                                   smd.c.supplier_molecule_design_id ==
                                          psmd.c.supplier_molecule_design_id)]
                )
#        select([distinct(smd.c.product_id)],
#               and_(
#                    sts.c.molecule_design_set_id == stock_sample_tbl.c.molecule_design_set_id,
#                    smd.c.supplier_id == stock_sample_tbl.c.supplier_id,
#                    smd.c.is_current
#                    ),
#               from_obj=[sts.join(psmd,
#                                  psmd.c.molecule_design_set_id ==
#                                            sts.c.molecule_design_set_id)
#                            .join(smd,
#                                  smd.c.supplier_molecule_design_id ==
#                                         psmd.c.supplier_molecule_design_id)]
#               )
    m = mapper(StockSample, stock_sample_tbl, inherits=sample_mapper,
        properties=dict(
            molecule_design_pool=relationship(MoleculeDesignPool,
                                              uselist=False,
                                              back_populates='stock_samples',
                                              lazy='joined'),
            supplier=relationship(Organization),
            molecule_type=relationship(MoleculeType, lazy='joined'),
            registration=
                    relationship(SampleRegistration,
                                 back_populates='sample',
                                 uselist=False),
            product_id=column_property(prd_sel.as_scalar())
            ),
        polymorphic_identity=SAMPLE_TYPES.STOCK
        )
    return m
