"""
Model classes related to molecule design libraries
"""
from everest.entities.base import Entity
from everest.entities.utils import slug_from_string
from thelma.models.iso import ISO_TYPES
from thelma.models.iso import Iso

__docformat__ = 'reStructuredText en'

__all__ = ['MoleculeDesignLibrary',
           'LibraryCreationIso',
           'LibrarySourcePlate']


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


class LibraryCreationIso(Iso):
    """
    This special type of :class:`Iso` is used to generate plates for
    (pooled) libraries. The ISO request for this ISO is not linked to an
    experiment metadata.

    **Equality condition**: equal :attr:`iso_request` and equal
        :attr:`layout_number`
    """
    #: The number of the Trac ticket.
    ticket_number = None
    #: The number of the library layout this ISO deals with.
    layout_number = None
    #: The library source plates for this ISO.
    library_source_plates = None

    def __init__(self, ticket_number, layout_number, label,
                 library_source_plates=None, **kw):
        Iso.__init__(self, label=label, iso_type=ISO_TYPES.LIBRARY_CREATION,
                     **kw)
        self.ticket_number = ticket_number
        self.layout_number = layout_number
        if library_source_plates is None:
            library_source_plates = []
        self.library_source_plates = library_source_plates

    def __eq__(self, other):
        return isinstance(other, self.__class__) and \
            other.iso_request == self.iso_request and \
            other.layout_number == self.layout_number

    def __repr__(self):
        str_format = '<%s id: %s, label: %s, ticket number: %i, ' \
                     'layout_number: %i, status: %s>'
        params = (self.__class__.__name__, self.id, self.label,
                  self.ticket_number, self.layout_number, self.status)
        return str_format % params


class LibrarySourcePlate(Entity):
    """
    This class a plate serving as source plate (and sometimes
    backup) for an ISO aliquot plate in a library creation ISO.
    Unlike as in normal ISOs there is one plate for each quadrant
    (aliquot plates and source plates have different rack shapes).

    **Equality Condition**: equal :attr:`iso` and equal :attr:`plate`
    """

    #: The library creation ISO this preparation plate belongs to (:class:`Iso`).
    iso = None
    #: The plate being the source plate (:class:`thelma.models.rack.Plate`).
    plate = None
    #: The sector index for this plate.
    sector_index = None

    def __init__(self, iso, plate, sector_index, **kw):
        """
        Constructor
        """
        Entity.__init__(self, **kw)
        self.iso = iso
        self.plate = plate
        self.sector_index = sector_index

    def __eq__(self, other):
        return isinstance(other, LibrarySourcePlate) and \
                self.iso == other.iso and \
                self.plate == other.plate

    def __ne__(self, other):
        return not (self.__eq__(other))

    def __str__(self):
        return self.id

    def __repr__(self):
        str_format = '<%s id: %s, ISO: %s, plate: %s, sector index: %i>'
        params = (self.__class__.__name__, self.id, self.iso, self.plate,
                  self.sector_index)
        return str_format % params
