"""
single_stranded_modification table

NP
"""

from sqlalchemy import Table, Column, String

__docformat__ = 'reStructuredText en'

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2010-03-03 18:07:48 +0100 (Wed, 03 Mar 2010) $'
__revision__ = '$Rev: 11401 $'
__source__ = '$URL: http://svn/cenix/TheLMA/trunk/thelma/db/schema/tables/singlestrandedmodification.py $'

__all__ = ['create_table']


def create_table(metadata):
    """
    single_stranded_modification table factory
    """
    tbl = Table('single_stranded_modification', metadata,
        Column('name', String, primary_key=True),
        Column('description', String, nullable=False, default=''),
        )
    return tbl
