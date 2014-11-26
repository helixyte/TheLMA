"""
Known species

NP
"""

__docformat__ = 'reStructuredText en'

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2010-04-16 15:32:28 +0200 (Fri, 16 Apr 2010) $'
__revision__ = '$Rev: 11452 $'
__source__ = '$URL: http://svn/cenix/TheLMA/trunk/thelma/data/species.py $'

__all__ = ['create_data']

SPECIES = (
    ('Homo', 'sapiens', 'human', 'HS', 9606),
    ('Drosophila', 'melanogaster', 'fly', 'DM', 7227),
    ('Mus', 'musculus', 'mouse', 'MM', 10090),
    ('Caenorhabditis', 'elegans', 'worm', 'CE', 6239),
    ('Rattus', 'norvegicus', 'rat', 'RN', 10116),
    )

def create_data():
    from thelma.entities.species import Species
    return dict([(args[2], Species(*args)) for args in SPECIES])
