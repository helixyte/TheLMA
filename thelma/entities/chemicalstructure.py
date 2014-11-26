"""
Chemical structure entity classes.
"""
from everest.entities.base import Entity
from everest.entities.utils import get_root_aggregate
from everest.entities.utils import slug_from_string
from everest.querying.specifications import cntd
from thelma.interfaces import IChemicalStructureType
from thelma.interfaces import IMoleculeType
from thelma.entities.cacheloaderregistry import cache_loader_registry
from thelma.entities.moleculetype import MOLECULE_TYPE_IDS
import re

__docformat__ = 'reStructuredText en'
__all__ = ['CHEMICAL_STRUCTURE_TYPE_IDS',
           'ChemicalStructure',
           'CompoundChemicalStructure',
           'NucleicAcidChemicalStructure',
           ]


class CHEMICAL_STRUCTURE_TYPE_IDS(object):
    COMPOUND = 'COMPOUND'
    NUCLEIC_ACID = 'NUCLEIC_ACID'
    MODIFICATION = 'MODIFICATION'
    UNKNOWN = 'UNKNOWN'


class ChemicalStructureType(Entity):
    name = None
    label = None
    molecule_type_ids = None
    def __init__(self, name, label, molecule_type_ids, **kw):
        Entity.__init__(self, **kw)
        self.name = name
        self.label = label
        self.molecule_type_ids = molecule_type_ids

    @property
    def slug(self):
        return slug_from_string(self.name)

    def __get_molecule_types(self):
        agg = get_root_aggregate(IMoleculeType)
        agg.filter = cntd(id=self.molecule_type_ids)
        return list(agg.iterator())

    def __set_molecule_types(self, molecule_types):
        self.molecule_type_ids = [mt.id for mt in molecule_types]

    molecule_types = property(__get_molecule_types, __set_molecule_types)

    def __eq__(self, other):
        return isinstance(other, ChemicalStructureType) \
               and self.name == other.name

    # FIXME: We need a generalized way of managing constants like these.
    @classmethod
    def make_default_instances(cls):
        return [ChemicalStructureType(
                            CHEMICAL_STRUCTURE_TYPE_IDS.COMPOUND,
                            'Compound',
                            [MOLECULE_TYPE_IDS.COMPOUND]
                            ),
                ChemicalStructureType(
                            CHEMICAL_STRUCTURE_TYPE_IDS.MODIFICATION,
                            'Modification',
                            [MOLECULE_TYPE_IDS.ANTI_MIR,
                             MOLECULE_TYPE_IDS.CLND_DSDNA,
                             MOLECULE_TYPE_IDS.MIRNA_INHI,
                             MOLECULE_TYPE_IDS.SIRNA]
                            ),
                ChemicalStructureType(
                            CHEMICAL_STRUCTURE_TYPE_IDS.NUCLEIC_ACID,
                            'Nucleic Acid',
                            [MOLECULE_TYPE_IDS.AMPLICON,
                             MOLECULE_TYPE_IDS.ANTI_MIR,
                             MOLECULE_TYPE_IDS.CLND_DSDNA,
                             MOLECULE_TYPE_IDS.ESI_RNA,
                             MOLECULE_TYPE_IDS.LONG_DSRNA,
                             MOLECULE_TYPE_IDS.SIRNA,
                             MOLECULE_TYPE_IDS.SSDNA]
                            ),
                ChemicalStructureType(
                            CHEMICAL_STRUCTURE_TYPE_IDS.UNKNOWN,
                            'Unknown',
                            [MOLECULE_TYPE_IDS.CLND_DSDNA,
                             MOLECULE_TYPE_IDS.MIRNA_INHI,
                             MOLECULE_TYPE_IDS.MIRNA_MIMI]
                            ),
                ]

# Register the default instances factory function with the cache loader
# registry for populating the caching entity store.
cache_loader_registry.register_loader(
                        ChemicalStructureType,
                        ChemicalStructureType.make_default_instances)


class ChemicalStructure(Entity):
    """
    A chemical structure with a structure type and a representation.

    Equality and sorting operators are defined in terms of the 2-tuple
    (structure type, representation).
    """
    #: ID of the chemical structure type (one of the attributes of
    #: :class:`thelma.entities.chemicalstructure.CHEMICAL_STRUCTURE_TYPE_IDS`).
    structure_type_id = None
    #: Representation string for the structure.
    representation = None
    #: Molecule designs referencing this chemical structure.
    molecule_designs = None

    def __init__(self, structure_type_id, representation,
                 molecule_designs=None, **kw):
        if self.__class__ is ChemicalStructure:
            raise NotImplementedError('Abstract class.')
        Entity.__init__(self, **kw)
        self.structure_type_id = structure_type_id
        self._validate_representation(representation)
        self.representation = representation
        if molecule_designs is None:
            molecule_designs = []
        self.molecule_designs = molecule_designs

    def __get_structure_type(self):
        agg = get_root_aggregate(IChemicalStructureType)
        return agg.get_by_slug(slug_from_string(self.structure_type_id))

    def __set_structure_type(self, structure_type):
        self.structure_type_id = structure_type.name

    structure_type = property(__get_structure_type, __set_structure_type)

    def __eq__(self, other):
        return self.__class__ is other.__class__ \
               and self.hash_string == other.hash_string

    def __lt__(self, other):
        return self.hash_string < other.hash_string

    def __le__(self, other):
        return not self.__gt__(other)

    def __gt__(self, other):
        return self.hash_string > other.hash_string

    def __ge__(self, other):
        return not self.__lt__(other)

    def __hash__(self):
        return hash(self.hash_string)

    def __str__(self):
        return self.representation

    def __repr__(self):
        str_format = '<%s id: %s, representation: %s>'
        params = (self.__class__.__name__, self.id, self.representation)
        return str_format % params

    @classmethod
    def create_from_data(cls, data):
        if cls is ChemicalStructure:
            structure_type_id = data.pop('structure_type_id', None)
            if structure_type_id == CHEMICAL_STRUCTURE_TYPE_IDS.COMPOUND:
                entity_cls = CompoundChemicalStructure
            elif structure_type_id == CHEMICAL_STRUCTURE_TYPE_IDS.NUCLEIC_ACID:
                entity_cls = NucleicAcidChemicalStructure
            elif structure_type_id == CHEMICAL_STRUCTURE_TYPE_IDS.MODIFICATION:
                entity_cls = ModificationChemicalStructure
            elif structure_type_id == CHEMICAL_STRUCTURE_TYPE_IDS.UNKNOWN:
                entity_cls = UnknownChemicalStructure
            else:
                raise ValueError('Invalid structure type ID "%s".'
                                 % structure_type_id)
            entity = entity_cls(**data)
        else:
            entity = cls(**data)
        return entity

    @property
    def hash_string(self):
        return '%s|%s' % (self.structure_type_id, self.representation)

    @classmethod
    def is_valid_representation(cls, representation):
        """
        Checks if the given value is a valid representation for this
        chemical structure.

        :param representation: The representation to check.
        :type representation: :class:`str`
        :rtype: :class:`boolean`
        """
        try:
            cls._validate_representation(representation)
        except ValueError:
            result = False
        else:
            result = True
        return result

    @classmethod
    def _validate_representation(cls, representation):
        """
        Validates the given representation for this chemical structure.

        :param representation: The representation to check.
        :type representation: :class:`str`
        :raises ValueError: If the representation is invalid.
        """
        raise NotImplementedError('Abstract method.')


class CompoundChemicalStructure(ChemicalStructure):
    def __init__(self, representation, **kw):
        ChemicalStructure.__init__(self, CHEMICAL_STRUCTURE_TYPE_IDS.COMPOUND,
                                   representation, **kw)

    @classmethod
    def _validate_representation(cls, representation):
        # FIXME: Check rules for SMILES here.
        return True


class NucleicAcidChemicalStructure(ChemicalStructure):
    """
    A nucleic acid sequence.

    By default, not only the standard characters of the nucleic acid notation
    alphabet are allowed (ATUCG), but also the "ambiguity characters"
    (cf. http://en.wikipedia.org/wiki/Nucleic_acid_notation).

    All incoming lower case letters are converted to upper case before the
    sequence is stored.
    """
    #: Nucleotide characters.
    NUCLEOTIDE_CHARS = 'ATUCG'
    #: Ambiguity characters
    AMBIGUITY_CHARS = 'WSMKRYBDHVN'
    # Regular expressions for sequence validation.
    _regex_without_ambiguity_chars = \
                re.compile(r'\b[%s]+\b' % NUCLEOTIDE_CHARS)
    _regex_with_ambiguity_chars = \
            re.compile(r'\b[%s%s]+\b' % (NUCLEOTIDE_CHARS, AMBIGUITY_CHARS))

    def __init__(self, representation, allow_ambiguity_chars=True, **kw):
        if not allow_ambiguity_chars \
           and not re.match(self._regex_without_ambiguity_chars,
                            representation):
            raise ValueError('Ambiguous characters in nucleic acid '
                             'structure representation detected.')
        ChemicalStructure.__init__(self,
                                   CHEMICAL_STRUCTURE_TYPE_IDS.NUCLEIC_ACID,
                                   representation.upper(), **kw)

    @classmethod
    def _validate_representation(cls, representation):
        rgx = cls._regex_with_ambiguity_chars
        if not (isinstance(representation, basestring)
                and re.match(rgx, representation.upper())):
            raise ValueError('Invalid nucleic acid structure representation.')


class ModificationChemicalStructure(ChemicalStructure):
    def __init__(self, representation, **kw):
        ChemicalStructure.__init__(self,
                                   CHEMICAL_STRUCTURE_TYPE_IDS.MODIFICATION,
                                   representation, **kw)

    @classmethod
    def _validate_representation(cls, representation):
        return True


class UnknownChemicalStructure(ChemicalStructure):
    _regex = re.compile(r'\b\w+\-\w+\b')
    def __init__(self, representation, **kw):
        ChemicalStructure.__init__(self,
                                   CHEMICAL_STRUCTURE_TYPE_IDS.UNKNOWN,
                                   representation, **kw)

    @classmethod
    def _validate_representation(cls, representation):
        if not (isinstance(representation, basestring)
                and re.match(cls._regex, representation)):
            raise ValueError('Invalid unknown structure representation.')
