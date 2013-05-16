"""
Transcript mapper.
"""
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from thelma.db.mappers.utils import as_slug_expression
from thelma.models.gene import Gene
from thelma.models.gene import Transcript
from thelma.models.species import Species

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


#FIXME: no name on DB level #pylint: disable=W0511
def create_mapper(transcript_tbl, transcript_gene_tbl, refseq_gene_vw):
    "Mapper factory."
    t = transcript_tbl
    tg = transcript_gene_tbl
    rgv = refseq_gene_vw
    m = mapper(Transcript, transcript_tbl,
               properties=
                    dict(id=synonym('transcript_id'),
                         gene=relationship(Gene,
                            primaryjoin=t.c.transcript_id == tg.c.transcript_id,
                            secondaryjoin=tg.c.gene_id == rgv.c.gene_id,
                            foreign_keys=(tg.c.transcript_id, tg.c.gene_id),
                            uselist=False,
                            secondary=transcript_gene_tbl),
                         species=relationship(Species)
                         )
               )
    if isinstance(Transcript.slug, property):
        Transcript.slug = \
            hybrid_property(Transcript.slug.fget,
                            expr=lambda cls: as_slug_expression(cls.accession))
    return m
