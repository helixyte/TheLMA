"""
thelma.db.schema.views.doublestrandeddesign

NP
"""

from sqlalchemy import ForeignKey
from sqlalchemy.sql import select

from thelma.db.view import view_factory


__docformat__ = 'reStructuredText en'

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2011-01-20 16:53:26 +0100 (Thu, 20 Jan 2011) $'
__revision__ = '$Rev: 11776 $'
__source__ = '$URL: http://svn/cenix/TheLMA/trunk/thelma/db/schema/views/doublestrandeddesign.py $'

__all__ = ['create_view']


VIEW_NAME = 'double_stranded_design_view'


def create_view(metadata, molecule_design_tbl, double_stranded_design_tbl):
    """
    double_stranded_design view factory
    """
    md = molecule_design_tbl
    dsd = double_stranded_design_tbl

    mddsd = select([md.c.molecule_design_id,
                    md.c.molecule_type_id,
                    dsd.c.sequence_1,
                    dsd.c.sequence_2,
                    dsd.c.modification],
                    md.c.molecule_design_id == dsd.c.molecule_design_id)

    fkey = ForeignKey(md.c.molecule_design_id)
    fkey.parent = mddsd.c.molecule_design_id
    mddsd.c.molecule_design_id.foreign_keys.add(fkey)

    return view_factory(VIEW_NAME, metadata, mddsd)
