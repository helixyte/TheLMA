"""
Sample registration entity classes.

Created Nov 24, 2014.
"""
from everest.entities.base import Entity


__docformat__ = 'reStructuredText en'
__all__ = ['MoleculeDesignPoolRegistrationItem',
           'MoleculeDesignRegistrationItem',
           'SampleRegistrationItem',
           'SupplierSampleRegistrationItem',
           ]


class MoleculeDesignRegistrationItemBase(Entity):
    """
    Base class for molecule design registration items.
    """
    #: Molecule type for the molecule design to register.
    molecule_type = None

    def __init__(self, molecule_type, **kw):
        Entity.__init__(self, **kw)
        self.molecule_type = molecule_type

    @classmethod
    def create_from_data(cls, data):
        if not 'molecule_type' in data:
            # We allow the creation without a molecule type or else we would
            # have to specify it in each registration item (rather than once
            # for a whole registrar run).
            data['molecule_type'] = None
        return cls(**data)


class MoleculeDesignRegistrationItem(MoleculeDesignRegistrationItemBase):
    """
    Item in a molecule design registration.
    """
    #: Structures for the molecule design to register.
    chemical_structures = None
    #: Molecule design to register (set during the registration process).
    molecule_design = None

    def __init__(self, molecule_type, chemical_structures, **kw):
        MoleculeDesignRegistrationItemBase.__init__(self, molecule_type, **kw)
        self.chemical_structures = chemical_structures


class MoleculeDesignPoolRegistrationItem(MoleculeDesignRegistrationItemBase):
    """
    Item in a molecule design pool registration.
    """
    #: Molecule designs to register.
    molecule_design_registration_items = None
    #: Molecule design pool for the molecule design to register (set during
    #: the registration process).
    molecule_design_pool = None

    def __init__(self, molecule_type, molecule_design_registration_items,
                 **kw):
        MoleculeDesignRegistrationItemBase.__init__(self, molecule_type, **kw)
        self.molecule_design_registration_items = \
                                        molecule_design_registration_items


class SampleData(Entity):
    """
    Base class for sample registration items.
    """
    #: Supplier for the sample to register.
    supplier = None
    #: Concentration for the sample to register.
    concentration = None
    #: Volume for the sample to register.
    volume = None
    #: Molecule type of the sample to register.
    molecule_type = None
    #: The molecule design pool associated with the sample to register.
    molecule_design_pool = None
    #: Barcode of the tube containing the sample to register. This is
    #: ``None`` if the samples are kept in wells.
    tube_barcode = None
    #: The barcode of the rack this sample is located in (optional;
    #: requires `rack_position` to be given as well). If the rack does
    #: not exist, it is created.
    rack_barcode = None
    #: The rack position in the rack this sample is located in (optional;
    #: requires `rack` to be given as well).
    rack_position = None

    def __init__(self, supplier, concentration, volume, molecule_type,
                 molecule_design_pool, tube_barcode=None, rack_barcode=None,
                 rack_position=None, **kw):
        Entity.__init__(self, **kw)
        self.supplier = supplier
        self.concentration = concentration
        self.volume = volume
        self.molecule_type = molecule_type
        self.molecule_design_pool = molecule_design_pool
        if (not rack_barcode is None and rack_position is None) \
           or (not rack_position is None and rack_barcode is None):
            raise ValueError('If a value for the `rack` parameter is given, '
                             '`rack_position` needs to be given as well, and '
                             'vice versa.')
        self.tube_barcode = tube_barcode
        self.rack_barcode = rack_barcode
        self.rack_position = rack_position

    @property
    def has_rack_location(self):
        return not self.rack_barcode is None


class SampleRegistrationItem(SampleData):
    """
    Item in a sample registration.
    """
    #: The stock sample created for the sample to register (created during
    #: the registration process).
    stock_sample = None
    #: The container associated with the sample to register (set during the
    #: registration process).
    container = None

    def __init__(self, supplier, concentration, volume, molecule_design_pool,
                 **kw):
        # For an internal sample registration, the pool is always known in
        # advance, so we can extract the molecule type from the pool.
        SampleData.__init__(self, supplier, concentration, volume,
                            molecule_design_pool.molecule_type,
                            molecule_design_pool, **kw)


class SupplierSampleRegistrationItem(SampleData):
    #: Product ID (from the supplier) for the sample to register to
    #: register.
    product_id = None
    #: Molecule design pool information for the sample to register.
    molecule_design_pool_registration_item = None
    #: The supplier molecule design associated with the sample to register
    #: (set during the registration process).
    supplier_molecule_design = None

    def __init__(self, supplier, product_id, concentration, volume,
                 molecule_type, molecule_design_pool_registration_item, **kw):
        # Typically, the molecule design pool is defined by the molecule
        # design pool registration item; in some cases, we have a pool and
        # want to make sure we have matching structure information.
        molecule_design_pool = kw.pop('molecule_design_pool', None)
        SampleData.__init__(self, supplier, concentration, volume,
                            molecule_type, molecule_design_pool, **kw)
        self.supplier = supplier
        self.product_id = product_id
        self.molecule_design_pool_registration_item = \
                            molecule_design_pool_registration_item
