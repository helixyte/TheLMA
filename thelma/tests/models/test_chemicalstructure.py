"""
Chemical structure model test cases.
"""
from thelma.models.chemicalstructure import NucleicAcidChemicalStructure
from thelma.testing import ThelmaModelTestCase

__docformat__ = 'reStructuredText en'
__all__ = ['NucleicAcidChemicalStructureTestCase',
           ]

class NucleicAcidChemicalStructureTestCase(ThelmaModelTestCase):

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.valid_seq = 'CTATAUGACTAGATCGATUUT'
        self.invalid_seq = 'ATGTCTEA'

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.valid_seq
        del self.invalid_seq

    def test_sequence_init(self):
        seq = NucleicAcidChemicalStructure(self.valid_seq)
        self.assert_not_equal(seq, None)

    def test_invalid_sequence(self):
        self.assert_raises(ValueError, NucleicAcidChemicalStructure,
                           self.invalid_seq)

    def test_sequence_equality(self):
        seq1 = NucleicAcidChemicalStructure(self.valid_seq)
        seq2 = NucleicAcidChemicalStructure(self.valid_seq)
        other_seq = 'CTATAUGACTAGATCGATUU'
        seq3 = NucleicAcidChemicalStructure(other_seq)
        self.assert_equal(seq1, seq2)
        self.assert_not_equal(seq1, seq3)
        self.assert_not_equal(seq3, other_seq)
