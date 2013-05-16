"""
mirna_mimic_design table

NP
"""

from sqlalchemy import Table, Column, String, Integer, ForeignKey


__docformat__ = 'reStructuredText en'

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2010-11-05 18:16:33 +0100 (Fri, 05 Nov 2010) $'
__revision__ = '$Rev: 11715 $'
__source__ = '$URL:: http://svn/cenix/TheLMA/trunk/thelma/db/schema/tables/mi#$'

__all__ = ['create_table']


def create_table(metadata, molecule_design_tbl, mirna_tbl):
    """
    mirna_mimic_design table factory
    """
    tbl = Table('mirna_mimic_design', metadata,
        Column('molecule_design_id', Integer,
               ForeignKey(molecule_design_tbl.c.molecule_design_id,
                          onupdate='CASCADE', ondelete='CASCADE'),
               primary_key=True),
        Column('mirna_accession', String(24),
               ForeignKey(mirna_tbl.c.accession,
                          onupdate='CASCADE', ondelete='RESTRICT'),
               ),
        )
    return tbl
