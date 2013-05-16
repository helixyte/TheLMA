from everest.resources.base import Member
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from thelma.interfaces import IIsoRequest
from thelma.interfaces import IMoleculeDesignPoolSet
from thelma.resources.base import RELATION_BASE_URL
from thelma.resources.iso import IsoMember

__docformat__ = 'reStructuredText en'

__all__ = ['LibraryCreationIsoMember',
           'MoleculeDesignLibraryMember',
           ]


class MoleculeDesignLibraryMember(Member):

    relation = "%s/molecule-design-library" % RELATION_BASE_URL

    label = terminal_attribute(str, 'label')
    molecule_design_pool_set = member_attribute(IMoleculeDesignPoolSet,
                                                'molecule_design_pool_set')
    iso_request = member_attribute(IIsoRequest, 'iso_request')

    @property
    def title(self):
        return self.label



class LibraryCreationIsoMember(IsoMember):

    ticket_number = terminal_attribute(int, 'ticket_number')
    layout_number = terminal_attribute(int, 'layout_number')
