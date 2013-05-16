"""
molecule_design_gene view

NP
"""

from sqlalchemy.sql import select, and_

from thelma.db.view import view_factory


__docformat__ = 'reStructuredText en'

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2010-06-09 15:09:47 +0200 (Wed, 09 Jun 2010) $'
__revision__ = '$Rev: 11526 $'
__source__ = '$URL:: http://svn/cenix/TheLMA/trunk/thelma/db/schema/views/mol#$'

__all__ = ['create_view']


VIEW_NAME = 'molecule_design_gene_view'


def create_view(metadata, molecule_design_tbl, gene_tbl,
                release_gene_transcript_tbl, versioned_transcript_tbl,
                release_versioned_transcript_tbl, current_db_release_tbl,
                molecule_design_versioned_transcript_target_tbl):
    """
    molecule_design_gene view factory
    """
    cdr = current_db_release_tbl.alias('cdr')
    rvt = release_versioned_transcript_tbl.alias('rvt')
    vt = versioned_transcript_tbl.alias('vt')
    rgt = release_gene_transcript_tbl.alias('rgt')
    g = gene_tbl.alias('g')
    mdvtt = molecule_design_versioned_transcript_target_tbl.alias('mdvtt')

    transcript = select(
        [vt.c.transcript_id, vt.c.versioned_transcript_id],
        and_(cdr.c.db_release_id == rvt.c.db_release_id,
             rvt.c.versioned_transcript_id == vt.c.versioned_transcript_id)
             ).alias('transcript')

    gene = select([g.c.gene_id, rgt.c.transcript_id],
                  and_(cdr.c.db_release_id == rgt.c.db_release_id,
                       rgt.c.gene_id == g.c.gene_id)
                  ).alias('gene')

    mdg = select(
        [mdvtt.c.molecule_design_id, gene.c.gene_id],
        and_(gene.c.transcript_id == transcript.c.transcript_id,
             transcript.c.versioned_transcript_id == mdvtt.c.versioned_transcript_id
             )
        ).distinct()

    return view_factory(VIEW_NAME, metadata, mdg)
