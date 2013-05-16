"""
thelma.stringconv

NP
"""

import string # pylint: disable=W0402

__docformat__ = 'reStructuredText en'

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2011-10-07 12:52:11 +0200 (Fri, 07 Oct 2011) $'
__revision__ = '$Rev: 12174 $'
__source__ = '$URL:: http://svn/cenix/TheLMA/trunk/thelma/stringconv.py       $'

__all__ = ['reverse_dna_sequence']


def reverse_dna_sequence(sequence):
    """
    Convert a DNA strand to its reverse complement

    It is based on http://www.wellho.net/resources/ex.php4?item=y108/seqrev.py

    :param sequence: a DNA sequence
    :type sequence: str
    :returns: reverse complement of sequence
    :rtype: str
    """
    seq = sequence.upper()
    trans_table = string.maketrans('ACGT', 'TGCA')
    base_list = list(seq.translate(trans_table, ' \n'))
    base_list.reverse()
    reverse_seq = ''.join(base_list)
    return reverse_seq
