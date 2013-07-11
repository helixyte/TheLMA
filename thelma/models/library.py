"""
Model classes related to molecule design libraries
"""
from everest.entities.base import Entity
from everest.entities.utils import slug_from_string

__docformat__ = 'reStructuredText en'

__all__ = ['MoleculeDesignLibrary']


class MoleculeDesignLibrary(Entity):
    """
    Library of molecule designs.

    **Equality Condition:** equal :attr:`label`
    """
    #: The pool set contains the stock sample molecule design set for this
    #: library.
    molecule_design_pool_set = None
    #: A label to address the library.
    label = None
    #: The final volume in a ready-to-use plate in l.
    final_volume = None
    #: The final concentration in a ready-to-use plate in M.
    final_concentration = None
    #: The ISO request used to generate this library
    #: (:class:`thelma.models.iso.IsoRequest`).
    iso_request = None

    def __init__(self, molecule_design_pool_set, label,
                 final_volume, final_concentration, iso_request=None, **kw):
        Entity.__init__(self, **kw)
        self.molecule_design_pool_set = molecule_design_pool_set
        self.label = label
        self.final_volume = final_volume
        self.final_concentration = final_concentration
        self.iso_request = iso_request

    @property
    def slug(self):
        """
        The slug for molecule design libraries is derived from the
        :attr:`label`.
        """
        return slug_from_string(self.label)

    def __eq__(self, other):
        return isinstance(other, MoleculeDesignLibrary) and \
                other.label == self.label

    def __ne__(self, other):
        return not (self.__eq__(other))

    def __str__(self):
        return self.label

    def __repr__(self):
        str_format = '<%s id: %s, label: %s, molecule design set: %s>'
        params = (self.__class__.__name__, self.id, self.label,
                  self.molecule_design_pool_set)
        return str_format % params
