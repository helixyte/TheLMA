"""
Sample model classes.
"""
from everest.entities.base import Entity
from everest.entities.utils import slug_from_integer
from thelma.utils import get_utc_time

__docformat__ = 'reStructuredText en'

__all__ = ['SAMPLE_TYPES',
           'Molecule',
           'Sample',
           'StockSample',
           'SampleMolecule',
           'SampleRegistration'
           ]


class SAMPLE_TYPES(object):
    BASIC = 'BASIC'
    STOCK = 'STOCK'


class Molecule(Entity):
    """
    This class represents molecule (solutions).

    :note: Molecules sharing the same molecule design
            (:class:`thelma.models.moleculedesign.MoleculeDesign`) can be
            listed differently if they are provided by different suppliers
            (:class:`thelma.models.organization.Organization`).
    """

    #: The date at which the molecule has been inserted into the database.
    insert_date = None
    #: The molecule design
    #: (:class:`thelma.models.moleculedesign.MoleculeDesign`) for this
    #: molecule.
    molecule_design = None
    #: The supplier of this molecule
    #: (:class:`thelma.models.organization.Organization`).
    supplier = None
    #: A list of samples (:class:`Sample`) using this molecule.
    samples = None
    #: The supplier's product ID this molecule. This is dynamically
    #: selected by the mapper.
    product_id = None

    def __init__(self, molecule_design, supplier, **kw):
        Entity.__init__(self, **kw)
        self.molecule_design = molecule_design
        self.supplier = supplier
        self.insert_date = get_utc_time()
        self.samples = []

    @property
    def slug(self):
        """
        The slug of molecule objects is derived by the :attr:`id`.
        """
        return slug_from_integer(self.id)

    def __str__(self):
        return str(self.id)

    def __repr__(self):
        str_format = '<%s id: %s, molecule_design: %s, supplier: %s, ' \
                     'product ID: %s, insert_date: %s>'
        params = (self.__class__.__name__, self.id, self.molecule_design,
                  self.supplier, self.product_id, self.insert_date)
        return str_format % params


class Sample(Entity):
    """
    Sample.

    A sample is held by a container and contains one or more sample molecules
    in solution.
    """
    #: The sample volume.
    volume = None
    #: The container (:class:`thelma.models.container.Container`) holding
    #: the sample.
    container = None
    #: The molecules present in this sample
    #: (:class:`SampleMolecule`) incl.  meta data (e.g. concentration).
    sample_molecules = None
    #: All samples which are aliquots of a `StockSample` reference the ID
    #: of the stock sample's
    #: :class:`thelma.models.moleculedesign.MoleculeDesignPool`. This
    #: attribute may be `None` for samples that are created by mixing several
    #: stock samples; it will certainly be `None` if the designs of the
    #: sample molecules have not all the same molecule type.
    molecule_design_pool_id = None

    def __init__(self, volume, container, **kw):
        Entity.__init__(self, **kw)
        self.volume = volume
        self.container = container

    def __repr__(self):
        str_format = '<%s id: %s, container: %s, volume: %s>'
        params = (self.__class__.__name__, self.id, self.container,
                  self.volume)
        return str_format % params

    def make_sample_molecule(self, molecule, concentration, **kw):
        return SampleMolecule(molecule, concentration, sample=self, **kw)

    def convert_to_stock_sample(self):
        """
        Converts this instance into a stock sample by setting all the
        required attributes. The object class is ''not'' changed.
        """
        mols = [sm.molecule for sm in self.sample_molecules]
        if len(mols) == 0:
            raise ValueError('Stock samples must have at least one sample '
                             'molecule.')
        if len(set([(mol.supplier, mol.molecule_design.molecule_type,
                     self.sample_molecules[idx].concentration)
                    for (idx, mol) in enumerate(mols)])) > 1:
            raise ValueError('All molecule designs in a stock sample must '
                             'have the same supplier, the same molecule type '
                             'and the same concentration.')
        from thelma.models.moleculedesign import MoleculeDesignPool
        mdp = MoleculeDesignPool.create_from_data(
                            dict(molecule_designs=[mol.molecule_design
                                                   for mol in mols]))
        # Setting attributes outside __init__ pylint: disable=W0201
        self.molecule_design_pool = mdp
        self.supplier = mols[0].supplier
        self.molecule_type = mols[0].molecule_design.molecule_type
        self.concentration = self.sample_molecules[0].concentration
        self.sample_type = SAMPLE_TYPES.STOCK
        # pylint: enable=W0201


class StockSample(Sample):
    """
    Stock sample.

    A stock sample is a sample that satisfies the following constraints:
     * All sample molecules have the same supplier;
     * All sample molecules have the same molecule type;
     * All sample molecules have the same concentration.

    The molecule designs of all molecules in a stock sample are kept in a
    :class:`thelma.models.moleculedesign.MoleculeDesignPool`.
    """
    #: The supplier for all sample molecules.
    supplier = None
    #: The molecule type of all sample molecules.
    molecule_type = None
    #: The concentration of all sample molecules.
    concentration = None
    #: The registration event for this stock sample.
    registration = None
    #: The molecule design pool for the sample molecules in this stock
    #: sample.
    molecule_design_pool = None

    def __init__(self, volume, container, molecule_design_pool, supplier,
                 molecule_type, concentration, **kw):
        Sample.__init__(self, volume, container, **kw)
        if molecule_design_pool.molecule_type != molecule_type:
            raise ValueError('The molecule types of molecule design pool '
                             'and stock sample differ.')
        self.molecule_design_pool = molecule_design_pool
        self.supplier = supplier
        self.molecule_type = molecule_type
        self.concentration = concentration
        # Create the sample molecules for this stock sample. By definition,
        # they all have the same supplier and same concentration.
        for molecule_design in molecule_design_pool.molecule_designs:
            mol = Molecule(molecule_design, supplier)
            self.make_sample_molecule(mol, concentration)

    def register(self):
        self.registration = SampleRegistration(self, self.volume)

    def check_in(self):
        for sm in self.sample_molecules:
            checkout_time = abs(get_utc_time() - sm.checkout_date).seconds
            if checkout_time > sm.molecule.molecule_type.thaw_time:
                sm.freeze_thaw_cycles += 1
            sm.checkout_date = None

    def check_out(self):
        for sm in self.sample_molecules:
            sm.checkout_date = get_utc_time()


class SampleMolecule(Entity):
    """
    This class represents a molecule in a particular sample. It also stores
    the meta data for it.

    **Equality condition**: equal :attr:`sample` and :attr:`molecule`
    """

    #: The samples (:class:`Sample`) containing this molecule.
    sample = None
    #: The molecule regarded by this object.
    molecule = None
    #: The concentration of the :attr:`molecule` in the :attr:`sample`
    #: in [*moles per liter*].
    concentration = None
    #: The number of freeze thaw samples for the :attr:`molecule`.
    freeze_thaw_cycles = None
    #: The date of the last check out.
    checkout_date = None

    def __init__(self, molecule, concentration, sample=None, **kw):
        Entity.__init__(self, **kw)
        self.molecule = molecule
        self.concentration = concentration
        self.sample = sample
        self.freeze_thaw_cycles = 0

    def __eq__(self, other):
        return (isinstance(other, SampleMolecule) and
                self.sample == other.sample and
                self.molecule == other.molecule)

    def __str__(self):
        return str((self.sample, self.molecule))

    def __repr__(self):
        str_format = '<%s sample: %s, molecule: %s, concentration: %s, ' \
                     'freeze_thaw_cycles: %s, checkout_date: %s>'
        params = (self.__class__.__name__, self.sample, self.molecule,
                  self.concentration, self.freeze_thaw_cycles,
                  self.checkout_date)
        return str_format % params


class SampleRegistration(Entity):
    """
    Represents a sample registration event.
    """
    #: The (stock) sample which was registered.
    sample = None
    #: The initial sample volume at registration time.
    volume = None
    #: Time stamp.
    time_stamp = None

    def __init__(self, sample, volume, time_stamp=None, **kw):
        Entity.__init__(self, **kw)
        self.sample = sample
        self.volume = volume
        if time_stamp is None:
            time_stamp = get_utc_time()
        self.time_stamp = time_stamp
