"""
Gene demo data

NP
"""

__docformat__ = 'reStructuredText en'

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2010-04-16 15:32:28 +0200 (Fri, 16 Apr 2010) $'
__revision__ = '$Rev: 11452 $'
__source__ = '$URL: http://svn/cenix/TheLMA/trunk/thelma/data/demo/gene.py $'

__all__ = ['create_demo']


GENES = [
    ('847', 'CAT', 'human'),
    ('3832', 'KIF11', 'human'),
    ('171304', 'Kif11', 'worm'),
    ('16551', 'Kif11', 'mouse'),
    ]

def create_demo(species):
    from thelma.models.gene import Gene
    demo = {}
    for accession, locus_name, species_name in GENES:
        demo[accession] = Gene(accession, locus_name, species[species_name])
    return demo
