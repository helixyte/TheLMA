"""
Library-related resources.
"""
from everest.resources.base import Member
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from thelma.interfaces import IIsoRequest
from thelma.interfaces import ILabIso
from thelma.interfaces import ILibraryPlate
from thelma.interfaces import IMoleculeDesignPoolSet
from thelma.interfaces import IRack
from thelma.interfaces import IRackLayout
from thelma.resources.base import RELATION_BASE_URL


__docformat__ = 'reStructuredText en'
__all__ = ['LibraryPlateMember',
           'MoleculeDesignLibraryMember',
           ]


class MoleculeDesignLibraryMember(Member):
    relation = "%s/molecule-design-library" % RELATION_BASE_URL
    molecule_design_pool_set = member_attribute(IMoleculeDesignPoolSet,
                                                'molecule_design_pool_set')
    label = terminal_attribute(str, 'label')
    final_volume = terminal_attribute(float, 'final_volume')
    final_concentration = terminal_attribute(float, 'final_concentration')
    number_layouts = terminal_attribute(int, 'number_layouts')
    rack_layout = member_attribute(IRackLayout, 'rack_layout')
    library_plates = collection_attribute(ILibraryPlate, 'library_plates')
    creation_iso_request = member_attribute(IIsoRequest,
                                            'creation_iso_request')

    @property
    def title(self):
        return self.label


class LibraryPlateMember(Member):
    relation = "%s/library-plate" % RELATION_BASE_URL
    rack = member_attribute(IRack, 'rack')
    layout_number = terminal_attribute(int, 'layout_number')
    has_been_used = terminal_attribute(bool, 'has_been_used')
    lab_iso = member_attribute(ILabIso, 'lab_iso')
