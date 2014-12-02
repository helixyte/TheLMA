"""
Stock info view.
"""
from sqlalchemy import String
from sqlalchemy.schema import ForeignKey
from sqlalchemy.sql import and_
from sqlalchemy.sql import cast
from sqlalchemy.sql import func
from sqlalchemy.sql import literal
from sqlalchemy.sql import select
from sqlalchemy.sql.functions import coalesce

from thelma.repositories.rdb.view import view_factory


__docformat__ = 'reStructuredText en'
__all__ = ['create_view']


VIEW_NAME = 'stock_info_view'
_STOCK_CONTAINER_ITEM_STATUS = 'MANAGED'
_STOCK_CONTAINER_SPECS = 'MATRIX0500'


def create_view(metadata, molecule_design_pool_tbl,
                stock_sample_tbl, sample_tbl, container_tbl):
    """
    stock_info_view factory.
    """
    mdp = molecule_design_pool_tbl
    ss = stock_sample_tbl
    c = container_tbl
    s = sample_tbl
    stock = select([
            (literal('mdp')
             + cast(mdp.c.molecule_design_set_id, String)
             + literal('c')
             + cast(coalesce(ss.c.concentration * 1e6, 0),
                    String)).label('stock_info_id'),
            mdp.c.molecule_design_set_id,
            # We need to set the label explicitly here because
            # mdp.c.molecule_type_id is really mdp.c.molecule_type.
            mdp.c.molecule_type_id.label('molecule_type_id'),
            # pylint: disable=E1101
            coalesce(ss.c.concentration, 0).label('concentration'),
            coalesce(func.count(c.c.container_id), 0).label('total_tubes'),
            coalesce(func.sum(s.c.volume), 0).label('total_volume'),
            coalesce(func.min(s.c.volume), 0).label('minimum_volume'),
            coalesce(func.max(s.c.volume), 0).label('maximum_volume')
            # pylint: enable=E1101
            ],
            from_obj=
                mdp.outerjoin(ss, ss.c.molecule_design_set_id ==
                                        mdp.c.molecule_design_set_id) \
                .outerjoin(s, s.c.sample_id == ss.c.sample_id) \
                .outerjoin(c,
                           and_(c.c.container_id == s.c.container_id,
                                c.c.item_status ==
                                    _STOCK_CONTAINER_ITEM_STATUS))
                 ).group_by(mdp.c.molecule_design_set_id,
                            ss.c.concentration).alias('ssi')
    fkey_mds = ForeignKey(mdp.c.molecule_design_set_id)
    fkey_mds.parent = stock.c.molecule_design_set_id
    stock.c.molecule_design_set_id.foreign_keys.add(fkey_mds)
    fkey_mt = ForeignKey(mdp.c.molecule_type_id)
    fkey_mt.parent = stock.c.molecule_type_id
    stock.c.molecule_type_id.foreign_keys.add(fkey_mt)
    return view_factory(VIEW_NAME, metadata, stock)
