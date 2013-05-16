"""
MoleculeType model classes.

NP, AAB
"""

from everest.entities.base import Entity
from everest.entities.utils import slug_from_string

__docformat__ = "reStructuredText en"

__all__ = ['MoleculeType',
           'MOLECULE_TYPE_IDS']


class MOLECULE_TYPE_IDS(object):
    """
    Known molecule types.
    """
    # FIXME: reconcile with `thelma.data.moleculetype` # pylint:disable=W0511
    SSRNA = 'SSRNA'
    SSDNA = 'SSDNA'
    AMPLICON = 'AMPLICON'
    SIRNA = 'SIRNA'
    GOLD = 'GOLD'
    TITAN = 'TITAN'
    COMPOUND = 'COMPOUND'
    LONG_DSRNA = 'LONG_DSRNA'
    ANTI_MIR = 'ANTI_MIR'
    ESI_RNA = 'ESI_RNA'
    MIRNA_INHI = 'MIRNA_INHI'
    CLND_DSDNA = 'CLND_DSDNA'
    MIRNA_MIMI = 'MIRNA_MIMI'

    __ALL = [nm for nm in sorted(locals().keys()) if not nm.startswith('_')]

    @classmethod
    def is_known_type(cls, molecule_type_name):
        """
        Checks whether the given molecule type name is a known one.
        """
        return molecule_type_name in cls.__ALL


class MoleculeType(Entity):
    """
    Instances of this class describe molecule types, such as \'siRna\'.
    """

    #: The name of the molecule type.
    name = None
    #: A more detailed description.
    description = None
    #: An number indicating the time it takes for molecules of this type to
    #: thaw.
    thaw_time = None
    #: A list of modification chemical structures
    #: (:class:`thelma.models.chemicalstructure.ChemicalStructure`)
    #: that are associated with this molecule type.
    modifications = None
    #: The default stock concentration for this molecule type.
    default_stock_concentration = None

    def __init__(self, name, default_stock_concentration,
                 description='', thaw_time=0, modifications=None, **kw):
        Entity.__init__(self, **kw)
        self.name = name
        self.default_stock_concentration = default_stock_concentration
        self.description = description
        self.thaw_time = thaw_time
        if modifications == None:
            self.modifications = []

    @property
    def slug(self):
        #: For instances of this class, the slug is derived from the
        #: :attr:`name`.
        return slug_from_string(self.name)

    def __eq__(self, other):
        return (isinstance(other, MoleculeType) and self.name == other.name)

    def __str__(self):
        return self.id

    def __repr__(self):
        str_format = '<%s id: %s, name: %s, thaw_time: %s>'
        params = (self.__class__.__name__, self.id, self.name, self.thaw_time)
        return str_format % params
