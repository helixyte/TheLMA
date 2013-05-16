"""
mirna_inhibitor_modification table

NP
"""

from sqlalchemy import Table, Column, String

__docformat__ = 'reStructuredText en'

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2010-11-05 18:16:33 +0100 (Fri, 05 Nov 2010) $'
__revision__ = '$Rev: 11715 $'
__source__ = '$URL:: http://svn/cenix/TheLMA/trunk/thelma/db/schema/tables/mi#$'

__all__ = ['create_table']


def create_table(metadata):
    """
    mirna_inhibitor_modification table factory
    """
    tbl = Table('mirna_inhibitor_modification', metadata,
        Column('name', String, primary_key=True),
        Column('description', String, nullable=False, default=''),
        )
    return tbl
