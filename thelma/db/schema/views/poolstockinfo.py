"""
Pool stock info view.
"""
from sqlalchemy import String
from sqlalchemy.sql import and_
from sqlalchemy.sql import cast
from sqlalchemy.sql import func
from sqlalchemy.sql import literal
from sqlalchemy.sql import select
from sqlalchemy.sql.functions import coalesce
from thelma.db.view import view_factory

__docformat__ = 'reStructuredText en'
__all__ = ['create_view']


VIEW_NAME = 'stock_info_view'
_STOCK_CONTAINER_ITEM_STATUS = 'MANAGED'
_STOCK_CONTAINER_SPECS = 'MATRIX0500'


def create_view(metadata, container_tbl, container_specs_tbl, sample_tbl,
                molecule_design_pool_tbl, sample_molecule_design_pool_tbl):
    """
    View factory.
    """
    c = container_tbl
    cs = container_specs_tbl
    s = sample_tbl
    mdp = molecule_design_pool_tbl
    smdp = sample_molecule_design_pool_tbl
    cspecs = select([cs.c.container_specs_id],
                    cs.c.name == _STOCK_CONTAINER_SPECS)
    ssi = select([
            mdp.c.molecule_design_pool_id,
            s.c.volume,
            s.c.sample_id
            ],
        whereclause=and_(
            c.c.item_status == _STOCK_CONTAINER_ITEM_STATUS,
            c.c.container_specs_id == cspecs.as_scalar()
            ),
        from_obj=[
            c.outerjoin(s, s.c.container_id == c.c.container_id
                   ).outerjoin(smdp, smdp.c.sample_id == s.c.sample_id)
            ]
        ).group_by(smdp.c.molecule_design_pool_id).alias('ssi')
    stock = select([
         (literal('mdp') + cast(mdp.c.molecule_design_pool_id, String) + \
          literal('c') + cast(coalesce(ssi.c.concentration * 1000000, 0),
                              String)
          ).label('pool_stock_info_id'),
         mdp.c.molecule_design_pool_id,
         func.count(ssi.c.sample_id).label('total_tubes'),
         coalesce(func.sum(ssi.c.volume), 0).label('total_volume'),
         coalesce(func.min(ssi.c.volume), 0).label('minimum_volume'),
         coalesce(func.max(ssi.c.volume), 0).label('maximum_volume')
         ],
         from_obj=[
             mdp.outerjoin(# We join md with ssi in order to include out of stock designs
                 ssi, ssi.c.molecule_design_pool_id ==
                                              mdp.c.molecule_design_pool_id)
             ]
         )
    return view_factory(VIEW_NAME, metadata, stock)
