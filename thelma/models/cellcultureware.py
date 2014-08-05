"""
Cell culture ware model classes.
"""

from everest.entities.base import Entity
from everest.entities.utils import slug_from_string

__docformat__ = 'reStructuredText en'

__all__ = ['CellCultureWare']

class CellCultureWare(Entity):
    """
    Represents a cell culture ware.
    """

    #: The label associated with the cell culture ware
    label = None
    #: A list of cell lines (:class:`thelma.models.cellline.CellLine`)
    #: stored in the database that can use this culture ware.
    cell_lines = []
    #: The supplier that provide this culture ware
    supplier = None
    #: The recommended size of the wells of this culture ware
    size = None
    #: The recommended coating applied to this culture ware
    coating = None

    def __init__(self, label, cell_lines, size, coating, **kw):
        Entity.__init__(self, **kw)
        self.label = label
        self.cell_lines = cell_lines
        self.size = size
        self.coating = coating

    @property
    def slug(self):
        #: For instances of this class, the slug is derived from the
        #: :attr:`label`.
        return slug_from_string(self.label)

    def __eq__(self, other):
        return (isinstance(other, CellCultureWare) \
                and self.label == other.label)

    def __str__(self):
        return self.label

    def __repr__(self):
        str_format = '<%s id: %s, label: %s, cell_lines: %s, size: %s, coating: %s>'
        params = (self.__class__.__name__, self.id, self.label,
                  self.cell_lines, self.size, self.coating)
        return str_format % params
