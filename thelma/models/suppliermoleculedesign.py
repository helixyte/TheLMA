"""
Supplier molecule design model classes.
"""
from everest.entities.base import Entity
from thelma.utils import get_utc_time

__docformat__ = 'reStructuredText en'
__all__ = ['SupplierMoleculeDesign',
           'SupplierStructureAnnotation',
           ]


class SupplierMoleculeDesign(Entity):
    #: Product ID issued by the supplier for this supplier molecule design.
    product_id = None
    #: Supplier for this supplier molecule design.
    supplier = None
    #: Time stamp when this supplier molecule design was registered.
    time_stamp = None
    #: Flag indicating if this is the most recent supplier molecule design
    #: from the supplier for the associated molecule design.
    is_current = None
    #: Flag indicating if this supplier molecule design was discontinued by
    #: the supplier
    is_deleted = None
    #: Molecule design associated with this supplier design.
    molecule_design = None
    #: Molecule design pool associated with this supplier design.
    molecule_design_pool = None
    #: Annotations to structures in this design.
    supplier_structure_annotations = None

    def __init__(self, product_id, supplier,
                 time_stamp=None, is_current=False, is_deleted=False, **kw):
        Entity.__init__(self, **kw)
        self.product_id = product_id
        self.supplier = supplier
        if time_stamp is None:
            time_stamp = get_utc_time()
        self.time_stamp = time_stamp
        self.is_current = is_current
        self.is_deleted = is_deleted


class SupplierStructureAnnotation(Entity):
    #: Supplier molecule design containing this annotation.
    supplier_molecule_design = None
    #: Chemical structure that this annotation annotates.
    chemical_structure = None
    #: Annotation string.
    annotation = None

    def __init__(self, supplier_molecule_design, chemical_structure,
                 annotation, **kw):
        Entity.__init__(self, **kw)
        self.supplier_molecule_design = supplier_molecule_design
        self.chemical_structure = chemical_structure
        self.annotation = annotation
