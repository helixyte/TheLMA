"""
Stock info view.
"""
from sqlalchemy.sql import select
from thelma.db.view import view_factory


__docformat__ = 'reStructuredText en'
__all__ = ['create_view']


VIEW_NAME = 'molecule_design_set_gene_view'


def create_view(metadata, molecule_design_pool_tbl,
                molecule_design_set_member_tbl,
                molecule_design_gene_tbl):
    """
    molecule_design_set_gene view factory
    """
    mdp = molecule_design_pool_tbl.alias()
    mdsm = molecule_design_set_member_tbl
    mdg = molecule_design_gene_tbl
    mds_genes = select([
                    mdp.c.molecule_design_set_id, mdg.c.gene_id
                    ],
                   from_obj=[
                     mdp.join(mdsm,
                                mdsm.c.molecule_design_set_id ==
                                        mdp.c.molecule_design_set_id) \
                     .join(mdg,
                           mdg.c.molecule_design_id ==
                                        mdsm.c.molecule_design_id)
                     ])
    return view_factory(VIEW_NAME, metadata, mds_genes)
