"""
Stock info mapper.
"""
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from thelma.db.mappers.utils import as_slug_expression
from thelma.models.gene import Gene
from thelma.models.moleculedesign import MoleculeDesignPool
from thelma.models.moleculetype import MoleculeType
from thelma.models.stockinfo import StockInfo

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(stock_info_vw, molecule_design_set_gene_tbl, refseq_gene_tbl):
    "Mapper factory."
    siv = stock_info_vw
    mdsg = molecule_design_set_gene_tbl
    rsg = refseq_gene_tbl
    m = mapper(StockInfo, stock_info_vw,
        primary_key=[stock_info_vw.c.molecule_design_set_id,
                     stock_info_vw.c.concentration],
        properties=dict(
            id=synonym('stock_info_id'),
            molecule_design_pool=relationship(MoleculeDesignPool,
                                              lazy='joined'
                                              ),
            molecule_type=relationship(MoleculeType,
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
    if isinstance(StockInfo.slug, property):
        StockInfo.slug = \
            hybrid_property(StockInfo.slug.fget,
                            expr=lambda cls:
                                as_slug_expression(cls.stock_info_id))
    return m
