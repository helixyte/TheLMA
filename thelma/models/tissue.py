"""
Species model classes.

NP, AAB
"""

from everest.entities.base import Entity
from everest.entities.utils import slug_from_string

__docformat__ = 'reStructuredText en'

__all__ = ['Tissue']

class Tissue(Entity):
    """
    Represents a tissue.
    """

    #: The label associated with the tissue
    label = None
    #: A list of cell lines (:class:`thelma.models.gene.CellLine`)
    #: stored in the database that are derived from this tissue.
    cell_lines = []

    def __init__(self, label, cell_lines=None, **kw):
        Entity.__init__(self, **kw)
        self.label = label
        if cell_lines is None:
            cell_lines = []
        self.cell_lines = cell_lines

    @property
    def slug(self):
        #: For instances of this class, the slug is derived from the
        #: :attr:`label`.
        return slug_from_string(self.label)

    def __eq__(self, other):
        return (isinstance(other, Tissue) \
                and self.label == other.label)

    def __str__(self):
        return self.label

    def __repr__(self):
        str_format = '<%s id: %s, label: %s, cell_lines: %s>'
        params = (self.__class__.__name__, self.id, self.label,
                  self.cell_lines)
        return str_format % params
