"""
thelma.db.schema.views.singlestrandeddesign

NP
"""

from sqlalchemy import ForeignKey
from sqlalchemy.sql import select

from thelma.db.view import view_factory


__docformat__ = 'reStructuredText en'

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2010-05-07 17:50:46 +0200 (Fri, 07 May 2010) $'
__revision__ = '$Rev: 11476 $'
__source__ = '$URL: http://svn/cenix/TheLMA/trunk/thelma/db/schema/views/singlestrandeddesign.py $'

__all__ = ['create_view']

VIEW_NAME = 'single_stranded_design_view'


def create_view(metadata, molecule_design_tbl, single_stranded_design_tbl):
    """
    single_stranded_design view factory
    """
    md = molecule_design_tbl.alias('md')
    ssd = single_stranded_design_tbl.alias('ssd')
    mdssd = select([md.c.molecule_design_id,
                    md.c.molecule_type_id,
                    ssd.c.sequence,
                    ssd.c.modification],
                    md.c.molecule_design_id == ssd.c.molecule_design_id)

    fkey = ForeignKey(md.c.molecule_design_id)
    fkey.parent = mdssd.c.molecule_design_id
    mdssd.c.molecule_design_id.foreign_keys.add(fkey)

    return view_factory(VIEW_NAME, metadata, mdssd)
