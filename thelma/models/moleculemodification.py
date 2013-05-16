"""
Molecule modification model classes.

NP, AAB
"""

from everest.entities.base import Entity

__docformat__ = 'reStructuredText en'

__all__ = ['MoleculeModification']


UNMODIFIED = 'unmodified'


class MoleculeModification(Entity):
    """
    This class is meant for the representation of modifications of the
    molecule design.

    **Equality condition**: equal :attr:`name` and :attr:`molecule_type`
    """

    #: The Name of the modification.
    name = None
    #: The molecule type (:class:`thelma.models.moleculetype.MoleculeType`)
    #: this modification can be attached to.
    molecule_type = None

    def __init__(self, name, molecule_type, **kw):
        Entity.__init__(self, **kw)
        self.name = name
        self.molecule_type = molecule_type

    def __eq__(self, other):
        """Equality operator

        Equality is based on name and molecule type
        """
        return (isinstance(other, MoleculeModification) and
                self.name == other.name and
                self.molecule_type == other.molecule_type)

    def __str__(self):
        return self.name

    def __repr__(self):
        str_format = '<%s name: %s, molecule_type: %s>'
        params = (self.__class__.__name__, self.name, self.molecule_type)
        return str_format % params
