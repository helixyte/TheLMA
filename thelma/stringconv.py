"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

String conversion utilities.
"""
import string # pylint: disable=W0402

__docformat__ = 'reStructuredText en'


__all__ = ['reverse_dna_sequence']


def reverse_dna_sequence(sequence):
    """
    Convert a DNA strand to its reverse complement.

    Based on http://www.wellho.net/resources/ex.php4?item=y108/seqrev.py

    :param str sequence: a DNA sequence
    :returns: reverse complement of sequence
    :rtype: str
    """
    seq = sequence.upper()
    trans_table = string.maketrans('ACGT', 'TGCA')
    base_list = list(seq.translate(trans_table, ' \n'))
    base_list.reverse()
    reverse_seq = ''.join(base_list)
    return reverse_seq
