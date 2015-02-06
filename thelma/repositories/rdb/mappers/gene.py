"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Refseq Gene mapper.
"""
from sqlalchemy.orm import column_property
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import as_slug_expression
from everest.repositories.rdb.utils import mapper
from everest.repositories.rdb.utils import synonym
from thelma.entities.gene import Gene
from thelma.entities.moleculedesign import MoleculeDesign
from thelma.entities.moleculedesign import MoleculeDesignPool
from thelma.entities.species import Species
from thelma.repositories.rdb.mappers.utils import CaseInsensitiveComparator


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(refseq_gene_tbl, molecule_design_gene_tbl,
                  molecule_design_set_gene_tbl,
                  molecule_design_tbl,
                  molecule_design_pool_tbl):
    "Mapper factory."
    rsg = refseq_gene_tbl
    mdg = molecule_design_gene_tbl
    mdsg = molecule_design_set_gene_tbl
    md = molecule_design_tbl
    mdp = molecule_design_pool_tbl
    m = mapper(Gene, rsg,
        id_attribute='gene_id',
        slug_expression=lambda cls: as_slug_expression(cls.accession),
        properties=dict(
            accession=column_property(
                rsg.c.accession,
                comparator_factory=CaseInsensitiveComparator
                ),
            locus_name=column_property(
                rsg.c.locus_name,
                comparator_factory=CaseInsensitiveComparator
                ),
            molecule_designs=
                relationship(
                    MoleculeDesign, viewonly=True,
                    secondary=mdg,
                    primaryjoin=(mdg.c.gene_id == rsg.c.gene_id),
                    secondaryjoin=(md.c.molecule_design_id ==
                                            mdg.c.molecule_design_id),
                    foreign_keys=(mdg.c.molecule_design_id,
                                  mdg.c.gene_id),
                    back_populates='genes',
                    ),
            molecule_design_pools=
                relationship(
                    MoleculeDesignPool, viewonly=True,
                    secondary=mdsg,
                    primaryjoin=(mdsg.c.gene_id == rsg.c.gene_id),
                    secondaryjoin=(mdsg.c.molecule_design_set_id ==
                                            mdp.c.molecule_design_set_id),
                    foreign_keys=(mdsg.c.molecule_design_set_id,
                                  mdsg.c.gene_id),
                    ),
            species=relationship(Species, uselist=False,
                                 back_populates='genes',
#                                 lazy='joined'
                                 ),
            ),
        )
    Gene.name = synonym('locus_name')
    return m
