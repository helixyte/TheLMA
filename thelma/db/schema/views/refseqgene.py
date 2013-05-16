"""
refseq_gene_view view.

FOG Jan 20, 2011
"""

from sqlalchemy.sql.expression import and_
from sqlalchemy.sql.expression import select
from thelma.db.view import view_factory

__docformat__ = "reStructuredText en"

__author__ = 'F Oliver Gathmann'
__date__ = '$Date: 2011-10-11 09:30:21 +0200 (Tue, 11 Oct 2011) $'
__revision__ = '$Rev: 12180 $'
__source__ = '$URL:                                                         #$'

__all__ = ['create_view']


VIEW_NAME = 'refseq_gene_view'

def create_view(metadata, gene_tbl, release_gene_transcript_tbl,
                current_db_release_tbl, db_source_tbl):
    """
    Refseq gene view factory function.
    """
    g = gene_tbl
    rgt = release_gene_transcript_tbl
    cdr = current_db_release_tbl
    ds = db_source_tbl
    # Build select.
    rsg = select([g.c.gene_id, g.c.accession, g.c.locus_name, g.c.species_id],
                 and_(rgt.c.gene_id==g.c.gene_id,
                      cdr.c.db_release_id==rgt.c.db_release_id,
                      ds.c.db_source_id==cdr.c.db_source_id,
                      ds.c.db_name=='RefSeq')
                 )
    return view_factory(VIEW_NAME, metadata, rsg)
