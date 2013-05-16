"""
Supplier molecule design view.
"""
from thelma.db.view import view_factory
from sqlalchemy.sql.expression import select

__docformat__ = 'reStructuredText en'
__all__ = ['create_view']


VIEW_NAME = 'supplier_molecule_design_view'


def create_view(metadata, supplier_molecule_design_tbl):
    "View factory."
    smd = supplier_molecule_design_tbl
    sel = select([smd.c.supplier_molecule_design_id,
                  smd.c.supplier_id,
                  smd.c.product_id,
                  smd.c.time_stamp],
                 smd.c.is_current == True)
    return view_factory(VIEW_NAME, metadata, sel)
