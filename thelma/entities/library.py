"""
Entity classes related to molecule design libraries.
"""
from everest.entities.base import Entity
from everest.entities.utils import slug_from_string


__docformat__ = 'reStructuredText en'
__all__ = ['LibraryPlate',
           'MoleculeDesignLibrary',
           ]


class MoleculeDesignLibrary(Entity):
    """
    Library of molecule designs.
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
    #: The number of different layouts for this molecule design library.
    number_layouts = None
    #: The rack layout (:class:`thelma.entities.racklayout.RackLayout`, working
    #: layout type: :class:`LibraryLayout`) defines which rack position are
    #: reserved for library samples.
    rack_layout = None
    #: The library plates for this library (:class:`LibraryPlate`).
    library_plates = None
    #: The ISO request used to generate this library (optional,
    #: :class:`thelma.entities.iso.StockSampleCreationIsoRequest`).
    creation_iso_request = None

    def __init__(self, molecule_design_pool_set, label, final_volume,
                 final_concentration, number_layouts, rack_layout,
                 creation_iso_request=None, **kw):
        Entity.__init__(self, **kw)
        self.molecule_design_pool_set = molecule_design_pool_set
        self.label = label
        self.final_volume = final_volume
        self.final_concentration = final_concentration
        self.number_layouts = number_layouts
        self.rack_layout = rack_layout
        self.creation_iso_request = creation_iso_request

    @property
    def plate_specs(self):
        """
        The :class:`thelma.entities.rack.PlateSpecs` for the library plates.
        """
        if len(self.library_plates) is None: return None
        lp = self.library_plates[0]
        return lp.rack.specs

    @property
    def slug(self):
        """
        The slug for molecule design libraries is derived from the
        :attr:`label`.
        """
        return slug_from_string(self.label)

    def __eq__(self, other):
        """
        Equality is based on the label attribute.
        """
        return isinstance(other, MoleculeDesignLibrary) and \
                other.label == self.label

    def __ne__(self, other):
        return not (self.__eq__(other))

    def __str__(self):
        return self.label

    def __repr__(self):
        str_format = '<%s id: %s, label: %s, number layouts: %s, ' \
                     'molecule design set: %s>'
        params = (self.__class__.__name__, self.id, self.label,
                  self.number_layouts, self.molecule_design_pool_set)
        return str_format % params


class LibraryPlate(Entity):
    """
    Represents a ready-to-use plates being part of a screening library.
    These plates usually already contain samples but have some positions
    free for controls or other position types.
    """
    #: The library this plate belongs to (:class:`MoleculeDesignLibrary`).
    molecule_design_library = None
    #: The plate entity (:class:`thelma.entities.rack.Rack`).
    rack = None
    #: The number of the layout this plate contains (a running number
    #: within the library, starting with 1).
    layout_number = None
    #: Marks whether a plate is still available for experiments.
    has_been_used = None
    #: Library plates can be used by lab ISOs instead of aliquot plates
    #: (:class:`thelma.entities.iso.LabIso`).
    lab_iso = None

    def __init__(self, molecule_design_library, rack, layout_number,
                 has_been_used=False, lab_iso=None, **kw):
        Entity.__init__(self, **kw)
        self.molecule_design_library = molecule_design_library
        self.rack = rack
        self.layout_number = layout_number
        self.has_been_used = has_been_used
        self.lab_iso = lab_iso

    def __str__(self):
        return self.rack

    def __repr__(self):
        str_format = '<%s id: %s, rack: %s, library: %s, layout number: %s, ' \
                     'has been used: %s>'
        params = (self.__class__.__name__, self.id, self.rack,
                  self.molecule_design_library, self.layout_number,
                  self.has_been_used)
        return str_format % params
