"""
Target mapper.
"""
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from thelma.models.gene import Target
from thelma.models.gene import Transcript
from thelma.models.moleculedesign import MoleculeDesign

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(target_tbl):
    "Mapper factory."
    m = mapper(Target, target_tbl,
               properties=
                    dict(id=synonym('target_id'),
                         transcript=relationship(Transcript),
                         molecule_design=relationship(MoleculeDesign)
                         )
               )
    return m
