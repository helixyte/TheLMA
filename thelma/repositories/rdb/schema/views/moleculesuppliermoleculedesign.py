"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Molecule supplier molecule design view.
"""
from sqlalchemy.schema import ForeignKey
from sqlalchemy.sql import and_
from sqlalchemy.sql import select

from thelma.repositories.rdb.view import view_factory


__docformat__ = 'reStructuredText en'
__all__ = ['create_view']


VIEW_NAME = 'molecule_supplier_molecule_design_view'


def create_view(metadata, molecule_tbl, single_supplier_molecule_design_tbl,
                supplier_molecule_design_tbl):
    """
    molecule_type_modification_view factory.
    """
    m = molecule_tbl
    ssmd = single_supplier_molecule_design_tbl
    smd = supplier_molecule_design_tbl
    msmd = \
      select([m.c.molecule_id,
              smd.c.supplier_molecule_design_id],
             from_obj=m \
              .join(ssmd,
                    ssmd.c.molecule_design_id == m.c.molecule_design_id) \
              .join(smd,
                    and_(smd.c.supplier_molecule_design_id ==
                                    ssmd.c.supplier_molecule_design_id,
                         smd.c.supplier_id == m.c.supplier_id,
                         smd.c.is_current))
              )
    fkey_m = ForeignKey(m.c.molecule_id)
    fkey_m.parent = msmd.c.molecule_id
    msmd.c.molecule_id.foreign_keys.add(fkey_m)
    return view_factory(VIEW_NAME, metadata, msmd)
