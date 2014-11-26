"""
Known molecule types

NP
"""

__docformat__ = 'reStructuredText en'

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2011-06-10 17:47:20 +0200 (Fri, 10 Jun 2011) $'
__revision__ = '$Rev: 11965 $'
__source__ = '$URL: http://svn/cenix/TheLMA/trunk/thelma/data/moleculetype.py $'

__all__ = ['create_data']

MOLECULE_TYPES = (
    ('AMPLICON', 'Amplicon', 'PCR reaction product', 0),
    ('ANTI_MIR', 'Anti-miR',
     'Anti-miRs are chemically engineered oligonucleotides that specifically '
     'silence endogenous miRNAs', 0),
    ('COMPOUND', 'Compound',
     'substance consisting of different elements chemically bonded together '
     'in fixed proportions', 0),
    ('ESI_RNA', 'esiRNA',
     'esiRNAs are enzymatically cleaved long dsRNAs, similar to a pool of '
     'siRNAs', 0),
    ('LONG_DSRNA', 'Long dsRNA', '', 0),
    ('SIRNA', 'siRNA',
     'short double-stranded RNA (typically 21 bps), can have overhang DNA bps '
     '(typically symmetrical 2 bps), used for gene knockdown experiments', 0),
    ('SSDNA', 'ssDNA', 'single-stranded DNA (e.g. PCR primer)', 0),
    )

def create_data():
    from thelma.entities.moleculetype import MoleculeType # pylint: disable=W0404
    return dict([(args[0], MoleculeType(*args)) # pylint: disable=W0142
                 for args in MOLECULE_TYPES])
