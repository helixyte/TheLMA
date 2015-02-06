"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Stock info mapper.
"""
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import as_slug_expression
from everest.repositories.rdb.utils import mapper
from thelma.entities.gene import Gene
from thelma.entities.moleculedesign import MoleculeDesignPool
from thelma.entities.moleculetype import MoleculeType
from thelma.entities.stockinfo import StockInfo


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(stock_info_vw, molecule_design_set_tbl,
                  molecule_design_set_gene_tbl, refseq_gene_tbl):
    "Mapper factory."
    siv = stock_info_vw
    mds = molecule_design_set_tbl
    mdsg = molecule_design_set_gene_tbl
    rsg = refseq_gene_tbl
    m = mapper(StockInfo, stock_info_vw,
        id_attribute='stock_info_id',
        slug_expression=lambda cls: as_slug_expression(cls.stock_info_id),
        primary_key=[stock_info_vw.c.molecule_design_set_id,
                     stock_info_vw.c.concentration],
        properties=dict(
            molecule_design_pool=
                    relationship(MoleculeDesignPool,
                                 primaryjoin=(mds.c.molecule_design_set_id ==
                                                siv.c.molecule_design_set_id),
                                 foreign_keys=[siv.c.molecule_design_set_id],
                                 uselist=False,
                                 lazy='joined'
                                 ),
            molecule_type=relationship(MoleculeType,
                                       uselist=False,
                                       lazy='joined'),
            genes=relationship(Gene, viewonly=True,
                               primaryjoin=(mdsg.c.molecule_design_set_id ==
                                                siv.c.molecule_design_set_id),
                               secondaryjoin=(rsg.c.gene_id == mdsg.c.gene_id),
                               foreign_keys=(mdsg.c.molecule_design_set_id,
                                             mdsg.c.gene_id),
                               secondary=molecule_design_set_gene_tbl,
                               lazy='joined'
                               ),
            ),
        )
    return m
