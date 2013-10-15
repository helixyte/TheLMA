"""
Molecule design model classes.
"""
from collections import Counter
from everest.entities.base import Entity
from everest.entities.utils import get_root_aggregate
from everest.querying.specifications import eq
from md5 import md5
from thelma.models.chemicalstructure import CHEMICAL_STRUCTURE_TYPE_IDS
from thelma.models.moleculetype import MOLECULE_TYPE_IDS

__docformat__ = 'reStructuredText en'
__all__ = ['AmpliconDesign',
           'AntiMirDesign',
           'ClonedDsDnaDesign',
           'CompoundDesign',
           'DoubleStrandedDesign',
           'EsiRnaDesign',
           'GoldDesign',
           'LongDoubleStrandedRnaDesign',
           'MOLECULE_DESIGN_SET_TYPES',
           'MiRnaInhibitorDesign',
           'MiRnaMimicDesign',
           'MoleculeDesign',
           'MoleculeDesignPool',
           'MoleculeDesignPoolSet',
           'MoleculeDesignSet',
           'SiRnaDesign',
           'SingleStrandedDesign',
           'SingleStrandedRnaDesign',
           'TitanDesign',
           ]


class MoleculeDesign(Entity):
    """
    Abstract base class for all molecule designs.

    Molecule designs are defined by a molecule tye and one or several
    chemical structures.
    """

    #: The kind (:class:`thelma.models.moleculetype.MoleculeType`)
    #: of the molecule design.
    molecule_type = None
    #: Chemical structures for this molecule design.
    chemical_structures = None
    #: Supplier molecule designs for this molecule design.
    supplier_molecule_designs = None
    #: The genes (:class:`thelma.models.gene.Gene`) this molecule design
    #: targets.
    genes = None
    #: A hash value built from the chemical structure records for this design
    #: built as md5 hash from the structure hash string as returned by the
    #: make_structure_hash_string static method.
    structure_hash = None
    # The Id (name) of the molecule type associated with this design. Used for
    # validation purposes.
    _molecule_type_id = None

    def __init__(self, molecule_type, chemical_structures,
                 supplier_molecule_designs=None, genes=None, **kw):
        Entity.__init__(self, **kw)
        if self.__class__ is MoleculeDesign:
            raise NotImplementedError('Abstract class')
        if molecule_type.name.lower() != self._molecule_type_id.lower():
            raise ValueError('Invalid molecule type %s for %s design.'
                             % (molecule_type.id, self.__class__))
        self.molecule_type = molecule_type
        self._validate_chemical_structures(chemical_structures)
        self.chemical_structures = chemical_structures
        # Set up the structure hash.
        hash_string = \
            MoleculeDesign.make_structure_hash_string(chemical_structures)
        self.structure_hash = md5(hash_string).hexdigest()
        if supplier_molecule_designs is None:
            supplier_molecule_designs = []
        self.supplier_molecule_designs = supplier_molecule_designs
        if genes is None:
            genes = []
        self.genes = genes

    @classmethod
    def create_from_data(cls, data):
        # FIXME: This should not be hardwired.
        molecule_type = data['molecule_type']
        mol_type_id = molecule_type.id
        if mol_type_id == MOLECULE_TYPE_IDS.COMPOUND:
            entity_cls = CompoundDesign
        elif mol_type_id == MOLECULE_TYPE_IDS.ANTI_MIR:
            entity_cls = AntiMirDesign
        elif mol_type_id == MOLECULE_TYPE_IDS.ESI_RNA:
            entity_cls = EsiRnaDesign
        elif mol_type_id == MOLECULE_TYPE_IDS.LONG_DSRNA:
            entity_cls = LongDoubleStrandedRnaDesign
        elif mol_type_id == MOLECULE_TYPE_IDS.SSDNA:
            entity_cls = PrimerDesign
        elif mol_type_id == MOLECULE_TYPE_IDS.AMPLICON:
            entity_cls = AmpliconDesign
        elif mol_type_id == MOLECULE_TYPE_IDS.SIRNA:
            entity_cls = SiRnaDesign
        elif mol_type_id == MOLECULE_TYPE_IDS.TITAN:
            entity_cls = TitanDesign
        elif mol_type_id == MOLECULE_TYPE_IDS.GOLD:
            entity_cls = GoldDesign
        elif mol_type_id == MOLECULE_TYPE_IDS.CLND_DSDNA:
            entity_cls = ClonedDsDnaDesign
        elif mol_type_id == MOLECULE_TYPE_IDS.MIRNA_INHI:
            entity_cls = MiRnaInhibitorDesign
        elif mol_type_id == MOLECULE_TYPE_IDS.MIRNA_MIMI:
            entity_cls = MiRnaMimicDesign
        else:
            raise ValueError('Invalid molecule type ID %s.' % mol_type_id)
        return entity_cls(**data) # ** pylint: disable=W0142

    @property
    def structure_hash_string(self):
        return self.make_structure_hash_string(self.chemical_structures)

    @staticmethod
    def make_structure_hash_string(structures):
        """
        Creates a hash string for the given chemical structures.

        The hash string conforms to the following notation:
            structure_hash := '|'<structure type>'|'<representation>'|'
            structures_hash := structure_hash ('|' structure_hash) *

        The given sequence of structures is sorted by their individual
        structure hash string values before the hash string for the sequence
        of structures is built.

        :raises ValueError: if the value passed for :param:`structures` is
            `None` or an empty sequence.
        :returns: hash string
        """
        if structures is None or len(structures) == 0:
            raise ValueError('Can not create structure hash string for '
                              'design without structure information.')
        return '||'.join([struc.hash_string for struc in sorted(structures)])

    @staticmethod
    def make_structure_hash(structures):
        """
        Uses the `make_structure_hash_string` function to obtain a hash string
        for the given chemical structures and then returns the hex digest of
        the md5 hash for that string.

        :returns: md5 hexdigest of structure hash string
        """
        md5_hash = md5(MoleculeDesign.make_structure_hash_string(structures))
        return md5_hash.hexdigest()

    def __str__(self):
        return str(self.id)

    def __repr__(self):
        return '<%s id: %s>' % (self.__class__.__name__, self.id)

    @classmethod
    def is_valid_chemical_structure(cls, chemical_structures):
        """
        Checks if the the given chemical structures are valid for this
        molecule design.

        :param chemical_structures: Sequence of
          `thelma.model.chemical_structure.ChemicalStructure` instances to
          check.
        :rtype: Boolean
        """
        try:
            cls._validate_chemical_structures(chemical_structures)
        except ValueError:
            result = False
        else:
            result = True
        return result

    @classmethod
    def _validate_chemical_structures(cls, chemical_structures):
        """
        Validates the given chemical structures for this molecule design.

        :param chemical_structures: Sequence of
          `thelma.model.chemical_structure.ChemicalStructure` instances to
          validate.
        :raises ValueError: If the given chemical structures are not valid for
          this design.
        """
        raise NotImplementedError('Abstract method.')

    def __hash__(self):
        return hash(self.structure_hash)

    def __eq__(self, other):
        return isinstance(other, MoleculeDesign) \
               and self.structure_hash == other.structure_hash


class SingleStrandedDesign(MoleculeDesign):
    """
    Abstract base class for all single stranded molecule designs.
    """
    def __init__(self, molecule_type, **kw):
        if self.__class__ is SingleStrandedDesign:
            raise NotImplementedError('Abstract class')
        MoleculeDesign.__init__(self, molecule_type, **kw)

    @classmethod
    def _validate_chemical_structures(cls, chemical_structures):
        if not len(chemical_structures) == 1 \
           or not chemical_structures[0].structure_type_id \
                    in [CHEMICAL_STRUCTURE_TYPE_IDS.NUCLEIC_ACID,
                        CHEMICAL_STRUCTURE_TYPE_IDS.UNKNOWN]:
            raise ValueError('%s designs require exactly one nucleic '
                             'acid structure OR one unknown structure.'
                             % cls._molecule_type_id)


class DoubleStrandedDesign(MoleculeDesign):
    """
    Abstract base class for all double stranded molecule designs.
    """
    def __init__(self, molecule_type, **kw):
        if self.__class__ is DoubleStrandedDesign:
            raise NotImplementedError('Abstract class')
        MoleculeDesign.__init__(self, molecule_type, **kw)

    @classmethod
    def _validate_chemical_structures(cls, chemical_structures):
        if not (len(chemical_structures) == 2
                and set([cs.structure_type_id for cs in chemical_structures])
                    == set([CHEMICAL_STRUCTURE_TYPE_IDS.NUCLEIC_ACID])) \
           or (len(chemical_structures) == 1
                and chemical_structures[0].structure_type_id
                        == CHEMICAL_STRUCTURE_TYPE_IDS.UNKNOWN):
            raise ValueError('%s designs require exactly two nucleic '
                             'acid structures OR one unknown structure.'
                             % cls._molecule_type_id)


class RnaDesign(object):
    """
    Mixin class for RNA molecule designs.
    """
    # FIXME: Perhaps we should have validation for RNA representations.


class DnaDesign(object):
    """
    Mixin class for DNA molecule designs.
    """
    # FIXME: Perhaps we should have validation for DNA representations.


class CompoundDesign(MoleculeDesign):
    """
    Compound molecule design.
    """
    _molecule_type_id = MOLECULE_TYPE_IDS.COMPOUND

    @classmethod
    def _validate_chemical_structures(cls, chemical_structures):
        if len(chemical_structures) != 1 \
           or chemical_structures[0].structure_type_id \
                                != CHEMICAL_STRUCTURE_TYPE_IDS.COMPOUND:
            raise ValueError('%s designs require exactly one '
                             'compound structure.' % cls._molecule_type_id)


class AntiMirDesign(SingleStrandedDesign, RnaDesign):
    """
    This is a marker class for anti-miR molecule designs.  Anti-miRs are
    chemically engineered oligonucleotides that specifically
    silence endogenous miRNAs.
    """
    _molecule_type_id = MOLECULE_TYPE_IDS.ANTI_MIR


class EsiRnaDesign(DoubleStrandedDesign, RnaDesign):
    """
    esiRNA molecule design.

    esiRNAs are enzymatically cleaved long dsRNAs, similar to a pool of
    siRNAs.
    """
    _molecule_type_id = MOLECULE_TYPE_IDS.ESI_RNA


# FIXME: This needs to be removed after the migratioin
class SingleStrandedRnaDesign(SingleStrandedDesign, RnaDesign):
    _molecule_type_id = MOLECULE_TYPE_IDS.SSRNA


class LongDoubleStrandedRnaDesign(DoubleStrandedDesign, RnaDesign):
    """
    Long double stranded RNA molecule design.

    There have a size of a few hundred base pairs and used e.g. to silence
    worm or fly genes.
    """
    _molecule_type_id = MOLECULE_TYPE_IDS.LONG_DSRNA


class PrimerDesign(SingleStrandedDesign, DnaDesign):
    """
    Primer design.

    Primers are single stranded DNA designs. They are typically designed and
    stored in pairs of complementary (but not annealed) "forward" and
    "reverse" primers.
    """
    # FIXME: The SSDNA molecule type should probably be called PRIMER
    _molecule_type_id = MOLECULE_TYPE_IDS.SSDNA


class AmpliconDesign(DoubleStrandedDesign, DnaDesign):
    """
    Amplicon design.

    Amplicons are PCR reaction products.
    """
    _molecule_type_id = MOLECULE_TYPE_IDS.AMPLICON


class SiRnaDesign(DoubleStrandedDesign, RnaDesign):
    """
    siRNA molecule design.

    Short double-stranded RNA (typically 21 bps) can have overhang DNA bps
    (typically symmetrical 2 bps). They are used for gene knockdown
    experiments.
    """
    _molecule_type_id = MOLECULE_TYPE_IDS.SIRNA

    @classmethod
    def _validate_chemical_structures(cls, chemical_structures):
        cnt = Counter([cs.structure_type_id for cs in chemical_structures])
        is_invalid = \
            not cnt.get(CHEMICAL_STRUCTURE_TYPE_IDS.UNKNOWN) == 1 \
            and (cnt.get(CHEMICAL_STRUCTURE_TYPE_IDS.NUCLEIC_ACID) != 2 \
                 or (len(chemical_structures) == 3 and
                     cnt.get(CHEMICAL_STRUCTURE_TYPE_IDS.MODIFICATION) != 1))
        if is_invalid:
            raise ValueError('%s designs with known structure require '
                             'exactly two nucleic acid structures and at '
                             'most one modification structure.'
                             % cls._molecule_type_id)


class TitanDesign(DoubleStrandedDesign, RnaDesign):
    """
    Titan molecule design.

    Titan molecule designs are a variant of short double-stranded RNA with
    elaborate overhang bp requirements. They were an early knockdown reagent
    candidate before siRNA was settled upon.
    """
    _molecule_type_id = MOLECULE_TYPE_IDS.TITAN


class GoldDesign(DoubleStrandedDesign, RnaDesign):
    """
    Gold molecule design.

    Gold molecule designs are short hairpin RNA whose structure resembles an
    siRNA with a connecting loop. They are used for gene knockdown.
    """
    _molecule_type_id = MOLECULE_TYPE_IDS.GOLD


class ClonedDsDnaDesign(DoubleStrandedDesign, DnaDesign):
    """
    cloned dsDNA molecule design.

    These molecules have a DNA fragment inserted into a cloning vector
    (usually a plasmid, but it can also be, for example, a cosmid).
    This circular, double-stranded DNA molecule is also known as a construct.
    The cloning vector sequence is considered as packaging (represented in
    the database as a modification chemical structure record).
    """
    _molecule_type_id = MOLECULE_TYPE_IDS.CLND_DSDNA

    @classmethod
    def _validate_chemical_structures(cls, chemical_structures):
        cnt = Counter([cs.structure_type for cs in chemical_structures])
        is_invalid = False
        if len(cnt.keys()) == 1:
            is_invalid = cnt.get(CHEMICAL_STRUCTURE_TYPE_IDS.UNKNOWN) is None
        else:
            is_invalid = \
                not len(cnt.keys()) == 3 \
                or cnt.get(CHEMICAL_STRUCTURE_TYPE_IDS.NUCLEIC_ACID) != 2
        if is_invalid:
            raise ValueError('%s designs require exactly two nucleic acid '
                             'structures and one modification structure OR '
                             'one unknown structure.' % cls._molecule_type_id)


class MiRnaInhibitorDesign(SingleStrandedDesign, RnaDesign):
    """
    miRNA Inhibitor molecule design.
    """
    _molecule_type_id = MOLECULE_TYPE_IDS.MIRNA_INHI

    @classmethod
    def _validate_chemical_structures(cls, chemical_structures):
        cnt = Counter([cs.structure_type for cs in chemical_structures])
        is_invalid = \
            len(cnt.keys()) != 2 \
            or (cnt.get(CHEMICAL_STRUCTURE_TYPE_IDS.UNKNOWN) != 1
                or cnt.get(CHEMICAL_STRUCTURE_TYPE_IDS.MODIFICATION != 1))
        if is_invalid:
            raise ValueError('%s designs require exactly one unknown and '
                             'one modification structure.'
                             % cls._molecule_type_id)


class MiRnaMimicDesign(DoubleStrandedDesign, RnaDesign):
    """
    miRNA Mimic molecule design.
    """
    _molecule_type_id = MOLECULE_TYPE_IDS.MIRNA_MIMI


class MOLECULE_DESIGN_SET_TYPES(object):
    #: Base set - only for internal use.
    BASE = 'BASE'
    #: Standard (mutable) design set.
    STANDARD = 'STANDARD'
    #: Stock sample set (immutable).
    POOL = 'POOL'
    #: ISO set.
    ISO = 'ISO'


# TODO: are there other sets than pools?
class MoleculeDesignSetBase(Entity):
    """
    Abstract base class for molecule design sets.

    Molecule design sets have a label and a type.
    """

    #: A set of molecule designs (:class:`MoleculeDesign`).
    molecule_designs = None
    #: Type of the design set.
    set_type = None

    def __init__(self, set_type, molecule_designs=None, **kw):
        if self.__class__ is MoleculeDesignSetBase:
            raise NotImplementedError('Abstract class.')
        Entity.__init__(self, **kw)
        if molecule_designs is None:
            molecule_designs = set()
        self.set_type = set_type
        self.molecule_designs = molecule_designs

    def __str__(self):
        return '%s' % (self.id)

    def __contains__(self, molecule_design):
        """
        Checks whether the molecule design collection contains a certain
        design.

        :param molecule_design: molecule design to check
        :type molecule_design: :class:`MoleculeDesign`
        :return: :class:`boolean`
        """
        return molecule_design in self.molecule_designs

    def __iter__(self):
        return iter(self.molecule_designs)

    def __len__(self):
        return len(self.molecule_designs)

    @property
    def molecule_type(self):
        """
        The molecule type for the molecule designs within the set - or *None*
        if there is more than one molecule type.
        """
        md_types = set([md.molecule_type for md in self.molecule_designs])
        if len(md_types) == 1:
            result = md.molecule_type # md *is* defined pylint: disable=W0631
        else:
            result = None
        return result


class MoleculeDesignSet(MoleculeDesignSetBase):
    """
    Molecule design set.
    """
    def __init__(self, molecule_designs=None, **kw):
        MoleculeDesignSetBase.__init__(self,
                                       MOLECULE_DESIGN_SET_TYPES.STANDARD,
                                       molecule_designs=molecule_designs, **kw)

    def remove_molecule_design(self, molecule_design_id):
        """
        Remove a molecule design from the set. If the molecule design is not
        part of the set, nothing happens.
        """
        del_md = None
        for md in self.molecule_designs:
            if md.id == molecule_design_id:
                del_md = md
                break
        if not del_md is None:
            self.molecule_designs.discard(del_md)


class MoleculeDesignPool(MoleculeDesignSetBase):
    """
    Molecule design set for stock samples.

    For stock sample registration, we need a fast way to check if for a given
    set of molecule design IDs we already have a molecule design set on
    record. This is achieved with a member_hash which is generated as
    an md5 hash of the comma-concatenated string of the sorted design IDs in
    the set.

    :note: stock sample molecule design sets must be immutable (i.e., their
      members may not change) as they might be shared by multiple supplier
      designs.
    """
    #: The molecule type for the designs contained in this stock sample
    #: molecule design set.
    molecule_type = None
    #: The samples containing molecules with the designs contained in this
    #: stock sample molecule design set.
    stock_samples = None
    #: A hash value built as md5 hash from the the member hash string as
    #: returned by the make_member_hash_string static method.
    member_hash = None
    #: The number of molecule designs in the set of desigs.
    number_designs = None
    #: The (pool) supplier molecule designs for this design pool.
    supplier_molecule_designs = None
    #: The gene targets associated with the molecule designs in this pool.
    genes = None
    #: The default stock concentration of a molecule design pool in M. If
    #: this is not explicitly specified during initialization, the default
    #: for the pool's molecule type is used.
    default_stock_concentration = None

    def __init__(self, molecule_designs, default_stock_concentration=None,
                 **kw):
        """
        This constructor is not intended to be used directly. Use the
        factory method :func:`create_from_data` instead.
        """
        MoleculeDesignSetBase.__init__(self,
                                       MOLECULE_DESIGN_SET_TYPES.POOL,
                                       molecule_designs=molecule_designs,
                                       **kw)
        mol_types = [md.molecule_type for md in molecule_designs]
        if len(set(mol_types)) != 1:
            raise ValueError('All molecule designs in a molecule design '
                             'pool have to have the same molecule type!')
        self.molecule_type = mol_types[0]
        if default_stock_concentration is None:
            default_stock_concentration = \
                        self.molecule_type.default_stock_concentration
        self.default_stock_concentration = default_stock_concentration
        self.member_hash = \
            md5(self.make_member_hash_string(molecule_designs)).hexdigest()
        self.number_designs = len(molecule_designs)

    @staticmethod
    def make_member_hash_string(molecule_designs):
        """
        Creates a hash string for the given chemical structures.

        The hash string conforms to the following notation:
            member_hash := <design ID> (';' <design ID>) *

        The given sequence of molecule designs is sorted by their individual
        molecule design IDs before the hash string for the sequence is built.

        :raises ValueError: if the value passed for :param:`molecule_designs`
            is `None` or an empty sequence.
        :returns: hash string
        """
        if molecule_designs is None or len(molecule_designs) == 0:
            raise ValueError('Can not create member hash string for '
                              'pool without design information.')
        return ';'.join([str(md.id) for md in sorted(molecule_designs,
                                                     key=lambda md: md.id)])

    @classmethod
    def make_member_hash(cls, molecule_designs):
        """
        Uses the `make_member_hash_string` function to obtain a hash string
        for the given molecule designs and then returns the hex digest of
        the md5 hash for that string.

        :returns: md5 hexdigest of member hash string
        """
        return md5(cls.make_member_hash_string(molecule_designs)).hexdigest()

    @property
    def member_hash_string(self):
        return self.make_member_hash_string(self.molecule_designs)

    @classmethod
    def create_from_data(cls, data):
        # We reuse molecule design sets that have the same members.
        agg = get_root_aggregate(cls)
        mds = data.pop('molecule_designs')
        rpr_str = MoleculeDesignPool.make_member_hash_string(mds)
        agg.filter = eq(member_hash=md5(rpr_str).hexdigest())
        md_pools = list(agg.iterator())
        if len(md_pools) == 0:
            # New molecule design pool.
            md_pool = cls(molecule_designs=mds, **data)
        else:
            md_pool, = md_pools # Must be exactly one matching pool here.
        return md_pool

    def __eq__(self, other):
        return isinstance(other, self.__class__) \
               and self.member_hash == other.member_hash

    def __repr__(self):
        str_format = '<%s id: %s, molecule type: %s, number designs: %i>'
        params = (self.__class__.__name__, self.id, self.molecule_type,
                  self.number_designs)
        return str_format % params


class MoleculeDesignPoolSet(Entity):
    """
    Similar to a molecule design set but containing molecule design pools
    instead of molecule designs. Used by libraries, ISOs and experiment
    metadata.
    """
    #: The molecule design sets (pools) in the pool set
    #: (:class:`MoleculeDesignPool`).
    molecule_design_pools = None

    #: The molecule type of the pools in the set
    #: (:class:`thelma.models.moleculetype.MoleculeType`).
    molecule_type = None

    def __init__(self, molecule_type, molecule_design_pools=None, **kw):
        Entity.__init__(self, **kw)
        self.molecule_type = molecule_type
        if molecule_design_pools is None:
            molecule_design_pools = set()
        self.molecule_design_pools = molecule_design_pools

    def remove_pool(self, pool_id):
        """
        Remove a molecule design pool from the set. If the pool is
        not part of the set, nothing happens.
        """
        del_pool = None
        for md_pool in self.molecule_design_pools:
            if md_pool.id == pool_id:
                del_pool = md_pool
                break
        if not del_pool is None:
            self.molecule_design_pools.discard(del_pool)

    def __eq__(self, other):
        return isinstance(other, MoleculeDesignPoolSet) \
               and self.id == other.id

    def __len__(self):
        return len(self.molecule_design_pools)

    def __iter__(self):
        return iter(self.molecule_design_pools)

    def __str__(self):
        return self.id

    def __repr__(self):
        str_format = '<%s id: %s, molecule type: %s>'
        params = (self.__class__.__name__, self.id, self.molecule_type)
        return str_format % params
