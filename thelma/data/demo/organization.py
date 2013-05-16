"""
Organization demo data

NP
"""

__docformat__ = 'reStructuredText en'

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2010-04-16 15:32:28 +0200 (Fri, 16 Apr 2010) $'
__revision__ = '$Rev: 11452 $'
__source__ = '$URL: http://svn/cenix/TheLMA/trunk/thelma/data/demo/organization.py $'

__all__ = ['create_demo']


ORGANIZATIONS = [
    'AbGene',
    'Ambion',
    'Cenix',
    'Hewlett Packard',
    'Siena Biotech',
    'Microsource Discovery Systems',
    'Sigma-Genesis',
    ]

def create_demo():
    from thelma.models.organization import Organization
    return dict([(name, Organization(name)) for name in ORGANIZATIONS])
