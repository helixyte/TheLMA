"""
Stock sample registrar.

Created on September 06, 2012.
"""
from everest.entities.base import Entity
from everest.entities.utils import get_root_aggregate
from everest.mime import JsonMime
from everest.querying.specifications import cntd
from everest.querying.specifications import eq
from everest.representers.utils import as_representer
from everest.resources.base import Member
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from everest.resources.utils import get_collection_class
from thelma.automation.handlers.rackscanning \
                                    import AnyRackScanningParserHandler
from thelma.automation.handlers.rackscanning import RackScanningLayout
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.tools.semiconstants import ITEM_STATUS_NAMES
from thelma.interfaces import IChemicalStructure
from thelma.interfaces import IItemStatus
from thelma.interfaces import IMoleculeDesign
from thelma.interfaces import IMoleculeDesignPool
from thelma.interfaces import IMoleculeType
from thelma.interfaces import IOrganization
from thelma.interfaces import IRack
from thelma.interfaces import IRackPosition
from thelma.interfaces import IRackSpecs
from thelma.interfaces import IStockSample
from thelma.interfaces import ISupplierMoleculeDesign
from thelma.interfaces import ITube
from thelma.interfaces import ITubeSpecs
from thelma.models.container import Tube
from thelma.models.moleculedesign import MoleculeDesign
from thelma.models.moleculedesign import MoleculeDesignPool
from thelma.models.rack import TubeRack
from thelma.models.sample import StockSample
from thelma.models.suppliermoleculedesign import SupplierMoleculeDesign
from thelma.resources.base import RELATION_BASE_URL
from zope.interface import Interface # pylint: disable=E0611,F0401
import datetime
import glob
import logging
import os

__docformat__ = 'reStructuredText en'
__all__ = []


#class Delivery(Entity):
#    receiver_user = None
#    receipt_time_stamp = None
#    registrar_user = None
#    registration_time_stamp = None
#    sample_registration_items = None


class IMoleculeDesignPoolRegistrationItem(Interface): # pylint: disable=W0232
    pass


class IMoleculeDesignRegistrationItem(Interface): # pylint: disable=W0232
    pass


class ISampleRegistrationItem(Interface): # pylint: disable=W0232
    pass


class ISupplierSampleRegistrationItem(Interface): # pylint: disable=W0232
    pass


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


class MoleculeDesignRegistrationItemMember(Member):
    relation = "%s/molecule-design-registration-item" % RELATION_BASE_URL
    chemical_structures = collection_attribute(IChemicalStructure,
                                               'chemical_structures')


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


class MoleculeDesignPoolRegistrationItemMember(Member):
    relation = "%s/molecule-design-pool-registration-item" % RELATION_BASE_URL
    molecule_design_registration_items = \
                collection_attribute(IMoleculeDesignRegistrationItem,
                                     'molecule_design_registration_items')


class SampleData(Entity):
    #: Supplier for the sample to register.
    supplier = None
    #: Concentration for the sample to register.
    concentration = None
    #: Volume for the sample to register.
    volume = None
    #: Barcode of the tube containing the sample to register.
    tube_barcode = None
    #: Molecule type of the sample to register.
    molecule_type = None
    #: The molecule design pool associated with the sample to register.
    molecule_design_pool = None
    #: The barcode of the rack this sample is located in (optional;
    #: requires `rack_position` to be given as well). If the rack does
    #: not exist, it is created.
    rack_barcode = None
    #: The rack position in the rack this sample is located in (optional;
    #: requires `rack` to be given as well).
    rack_position = None

    def __init__(self, supplier, concentration, volume, tube_barcode,
                 molecule_type, molecule_design_pool, rack_barcode=None,
                 rack_position=None, **kw):
        Entity.__init__(self, **kw)
        self.supplier = supplier
        self.concentration = concentration
        self.volume = volume
        self.tube_barcode = tube_barcode
        self.molecule_type = molecule_type
        self.molecule_design_pool = molecule_design_pool
        if (not rack_barcode is None and rack_position is None) \
           or (not rack_position is None and rack_barcode is None):
            raise ValueError('If a value for the `rack` parameter is given, '
                             '`rack_position` needs to be given as well, and '
                             'vice versa.')
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

    def __init__(self, supplier, concentration, volume,
                 tube_barcode, molecule_design_pool, **kw):
        # For an internal sample registration, the pool is always known in
        # advance, so we can extract the molecule type from the pool.
        SampleData.__init__(self, supplier, concentration, volume,
                            tube_barcode, molecule_design_pool.molecule_type,
                            molecule_design_pool, **kw)


class SampleRegistrationItemMember(Member):
    relation = "%s/sample-registration-item" % RELATION_BASE_URL
    supplier = member_attribute(IOrganization, 'supplier')
    concentration = terminal_attribute(float, 'concentration')
    volume = terminal_attribute(float, 'volume')
    tube_barcode = terminal_attribute(str, 'tube_barcode')
    rack_barcode = terminal_attribute(str, 'rack_barcode')
    rack_position = member_attribute(IRackPosition, 'rack_position')
    molecule_design_pool = member_attribute(IMoleculeDesignPool,
                                            'molecule_design_pool')


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
                 tube_barcode, molecule_type,
                 molecule_design_pool_registration_item, **kw):
        # The molecule design pool is defined by the molecule design pool
        # registration item, so we pass None here.
        SampleData.__init__(self, supplier, concentration, volume,
                            tube_barcode, molecule_type, None, **kw)
        self.supplier = supplier
        self.product_id = product_id
        self.molecule_design_pool_registration_item = \
                            molecule_design_pool_registration_item


class SupplierSampleRegistrationItemMember(SampleRegistrationItemMember):
    relation = "%s/supplier-sample-registration-item" % RELATION_BASE_URL
    supplier = member_attribute(IOrganization, 'supplier')
    product_id = terminal_attribute(str, 'product_id')
    concentration = terminal_attribute(float, 'concentration')
    volume = terminal_attribute(float, 'volume')
    tube_barcode = terminal_attribute(str, 'tube_barcode')
    rack_barcode = terminal_attribute(str, 'rack_barcode')
    rack_position = member_attribute(IRackPosition, 'rack_position')
    molecule_type = member_attribute(IMoleculeType, 'molecule_type')
    molecule_design_pool_registration_item = \
            member_attribute(IMoleculeDesignPoolRegistrationItem,
                             'molecule_design_pool_registration_item')


class SampleRegistrar(BaseAutomationTool):
    """
    Registrar for samples with existing design information.

    Every registration item passed to this registrar must have valid
    molecule design pool and supplier information.

    Algorithm:
     * If location information was provided in the registration items, find
       the racks containing the samples or create new racks, if the samples
       are contained in a new supplier rack;
     * Find or create tubes that contain the samples;
     * If location information was provided in the registration items,
       validate the tube locations against the validation files (rack
       scanning files). Write a CSV file mapping the supplier rack barcodes
       from the registration items to the Cenix barcodes of the freshly
       created racks;
     * Create stock samples.

    New entities are stored in the return value of the tool as a dictionary:

      stock_samples : list of stock samples created.
      tubes : list of tubes created.
      molecule_design_pools : list of molecule design pools created.
      supplier_rack_barcodes : dictionary supplier barcode -> Cenix barcode
    """
    def __init__(self, sample_registration_items, report_directory=None,
                 rack_specs_name='matrix0500', tube_specs_name='matrix0500',
                 validation_files=None, depending=False, **kw):
        """
        :param sample_registration_items: delivery samples to register.
        :type sample_registration_items: sequence of
            :class:`SampleRegistrationItem`
        :param str rack_specs_name: name of the rack specs to use for newly
            created racks.
        :param str tube_specs_name: name of the tube specs to use for newly
            created tubes.
        :param str validation_files: optional comma-separated list of rack
            scanning file names to use for validation of the sample positions.
        """
        BaseAutomationTool.__init__(self, depending=depending, **kw)
        self.sample_registration_items = sample_registration_items
        if report_directory is None:
            report_directory = os.getcwd()
        self.__report_directory = report_directory
        self.__tube_specs_name = tube_specs_name
        self.__rack_specs_name = rack_specs_name
        if not validation_files is None:
            # Validation files are given in a directory or as a
            # comma-separated string.
            if os.path.isdir(validation_files):
                validation_files = \
                    glob.glob(os.path.join(validation_files, '*.txt'))
            else:
                validation_files = validation_files.split(',')
        self.__validation_files = validation_files
        self.__tube_create_kw = None
        self.__rack_create_kw = None
        self.__new_rack_supplier_barcode_map = {}

    def run(self):
        self.return_value = {}
        # Create new racks, if necessary.
        self.__check_racks()
        if not self.has_errors():
            # Create new tubes, if necessary.
            self.__check_tubes()
        if not self.has_errors():
            # Build a mapping supplier rack barcode -> Cenix rack barcode.
            spl_rack_map = {}
            for rack, spl_bc in \
                        self.__new_rack_supplier_barcode_map.iteritems():
                spl_rack_map[spl_bc] = rack.barcode
            self.return_value['supplier_rack_barcodes'] = spl_rack_map
        #
        time_string = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        if not self.has_errors() and not self.__validation_files is None:
            self.__validate_locations()
            if not self.has_errors():
                # Generate rack barcode report file content.
                lines = ['cenix_barcode,supplier_barcode']
                for rack, spl_bc in \
                        self.__new_rack_supplier_barcode_map.items():
                    lines.append("%s,%s" % (rack.barcode, spl_bc))
                # Write out rack barcode report file.

                rack_barcode_report_filename = \
                                    os.path.join(self.__report_directory,
                                                 'rack_barcodes_%s.csv'
                                                 % time_string)
                with open(rack_barcode_report_filename, 'wb') as bc_file:
                    bc_file.write(os.linesep.join(lines))
        if not self.has_errors():
            new_stock_spls = []
            ss_agg = get_root_aggregate(IStockSample)
            for sri in self.sample_registration_items:
                # Create new stock sample.
                stock_spl = StockSample(
                                    sri.volume,
                                    sri.container,
                                    sri.molecule_design_pool,
                                    sri.supplier,
                                    sri.molecule_design_pool.molecule_type,
                                    sri.concentration)
                # Record the registration.
                stock_spl.register()
                ss_agg.add(stock_spl)
                new_stock_spls.append(stock_spl)
                # Update the sample registration item.
                sri.stock_sample = stock_spl
            self.return_value['stock_samples'] = new_stock_spls
            # Generate stock sample report file content.
            lines = ['tube_barcode,molecule_type,molecule_design_pool_id,'
                     'supplier,volume,concentration']
            for ss in new_stock_spls:
                lines.append('"%s","%s",%d,"%s",%f,%f' %
                             (ss.container.barcode,
                              ss.molecule_type.name,
                              ss.molecule_design_pool.id,
                              ss.supplier.name,
                              ss.volume,
                              ss.concentration))
            # Write out stock sample report file.
            stock_sample_repor_filename = \
                        os.path.join(self.__report_directory,
                                     'stock_samples_%s.csv'
                                     % time_string)
            with open(stock_sample_repor_filename, 'wb') as ss_file:
                ss_file.write(os.linesep.join(lines))

    def __check_racks(self):
        rack_agg = get_root_aggregate(IRack)
        bcs = [getattr(sri, 'rack_barcode')
               for sri in self.sample_registration_items
               if not getattr(sri, 'rack_barcode') is None]
        if len(bcs) > 0 and len(bcs) != len(self.sample_registration_items):
            msg = 'Some sample registration items contain rack ' \
                  'barcodes, but not all of them do.'
            self.add_error(msg)
        else:
            new_racks = []
            if len(bcs) > 0:
                rack_agg.filter = cntd(barcode=bcs)
                rack_map = dict([(rack.barcode, rack)
                                 for rack in rack_agg.iterator()])
                for sri in self.sample_registration_items:
                    rack_bc = sri.rack_barcode
                    if not rack_bc in rack_map:
                        # Create new item and add.
                        rack = self.__make_new_rack(sri)
                        rack_agg.add(rack)
                        new_racks.append(rack)
                        rack_map[rack_bc] = rack
                    else:
                        rack = rack_map[rack_bc]
                        if not self.__validate_rack(rack):
                            continue
                    # Update sample registration item.
                    sri.rack = rack
            self.return_value['racks'] = new_racks

    def __check_tubes(self):
        tube_agg = get_root_aggregate(ITube)
        tube_agg.filter = \
            cntd(barcode=[getattr(sri, 'tube_barcode')
                          for sri in self.sample_registration_items])
        tube_map = dict([(tube.barcode, tube)
                         for tube in tube_agg.iterator()])
        new_tubes = []
        for sri in self.sample_registration_items:
            tube_bc = sri.tube_barcode
            if not tube_bc in tube_map:
                tube = self.__make_new_tube(sri)
                tube_agg.add(tube)
                new_tubes.append(tube)
            else:
                # FIXME: Do we need to apply location information here?
                tube = tube_map[tube_bc]
                if not self.__validate_tube(tube):
                    continue
            sri.container = tube
        self.return_value['tubes'] = new_tubes

    def __make_new_rack(self, sample_registration_item):
        if self.__rack_create_kw is None:
            rack_specs_agg = get_root_aggregate(IRackSpecs)
            item_status_agg = get_root_aggregate(IItemStatus)
            self.__rack_create_kw = \
                dict(label='',
                     specs=rack_specs_agg.get_by_slug(self.__rack_specs_name),
                     status=item_status_agg.get_by_slug(
                                            ITEM_STATUS_NAMES.MANAGED.lower())
                     )
        kw = self.__rack_create_kw.copy()
        rack = TubeRack(**kw)
        rack_barcode = sample_registration_item.rack_barcode
        if not TubeRack.is_valid_barcode(rack_barcode):
            self.__new_rack_supplier_barcode_map[rack] = rack_barcode
        return rack

    def __make_new_tube(self, sample_registration_item):
        if self.__tube_create_kw is None:
            tube_specs_agg = get_root_aggregate(ITubeSpecs)
            item_status_agg = get_root_aggregate(IItemStatus)
            self.__tube_create_kw = \
              dict(specs=tube_specs_agg.get_by_slug(self.__tube_specs_name),
                   status=item_status_agg.get_by_slug(
                                            ITEM_STATUS_NAMES.MANAGED.lower())
                   )
        kw = self.__tube_create_kw.copy()
        kw['barcode'] = sample_registration_item.tube_barcode
        pos = sample_registration_item.rack_position
        if not pos is None:
            kw['rack'] = sample_registration_item.rack
            kw['position'] = pos
            tube = Tube.create_from_rack_and_position(**kw)
        else:
            tube = Tube(**kw)
        return tube

    def __validate_rack(self, rack):
        valid = True
        if rack.specs.slug != self.__rack_specs_name:
            msg = 'Invalid rack specs "%s" for rack with barcode "%s".' \
                  % (rack.specs.label, rack.barcode)
            self.add_error(msg)
            valid = False
        return valid

    def __validate_tube(self, tube):
        valid = True
        if not tube.sample is None:
            msg = 'Can not register a tube that already contains ' \
                  'a sample (tube barcode: %s)' % tube.barcode
            self.add_error(msg)
            valid = False
        return valid

    def __validate_locations(self):
        # Note: rack scanning files for racks which are not referenced in
        # the delivery are ignored.
        rsl_map = self.__read_rack_scanning_files()
        if not self.has_errors():
            processed_racks = set()
            for sri in self.sample_registration_items:
                if sri.rack is None:
                    msg = 'No rack was found or created for registration ' \
                          'item with tube barcode %s.' % sri.tube_barcode
                    self.add_error(msg)
                elif not sri.rack in processed_racks:
                    processed_racks.add(sri.rack)
                    reg_rsl = RackScanningLayout.from_rack(sri.rack)
                    # The barcode of the scanned rack could be a supplier
                    # barcode for which we just created a new Cenix barcode.
                    rack_bc = self.__new_rack_supplier_barcode_map.get(
                                                    sri.rack,
                                                    reg_rsl.rack_barcode)
                    try:
                        file_rsl = rsl_map[rack_bc]
                    except KeyError:
                        msg = 'No rack scanning file was provided for ' \
                              'sample rack with barcode %s.' % rack_bc
                        self.add_error(msg)
                    else:
                        mismatches = reg_rsl.diff(file_rsl)
                        if len(mismatches) > 0:
                            msgs = ['Mismatches found for sample rack with ' \
                                    'barcode %s:' % rack_bc]
                            for pos, exp, found in mismatches:
                                msgs.append(
                                    '\t%s@%s: expected %s, found %s' \
                                    % (rack_bc, pos.label,
                                       'no tube' if exp is None else exp,
                                       'no tube' if found is None else found))
                            msg = os.linesep.join(msgs)
                            self.add_error(msg)

    def __read_rack_scanning_files(self):
        rsl_map = {}
        for rack_scanning_filename in self.__validation_files:
            with open(rack_scanning_filename, 'rU') as rs_stream:
                parser_handler = \
                        AnyRackScanningParserHandler(log=self.log,
                                                     stream=rs_stream)
                file_rsl = parser_handler.get_result()
            if file_rsl is None:
                msg = 'Error parsing rack scanning file "%s".' \
                      % rack_scanning_filename
                self.add_error(msg)
            else:
                rsl_map[file_rsl.rack_barcode] = file_rsl
        return rsl_map


class SupplierSampleRegistrar(BaseAutomationTool):
    """
    Registrar for samples shipped by a supplier.

     * Use (supplier, product ID) to check if we have a (current) supplier
       molecule design for the registration items;
     * Use the structure hash to check if we have a molecule design for the
       registration items. Run the :class:`MoleculeDesignRegistrar` for all
       new designs;
     * Use the member hash to check if we have a molecule design pool for the
       registration items and create new molecule design pools where needed;
     * Now run the supplier molecule design registrar for all new supplier
       molecule designs;
     * Now that designs are available for all registration items, run the
       :class:`SampleRegistrar` to register samples.
     * Check that all molecule designs have a supplier molecule design.
    """
    def __init__(self, sample_registration_items, report_directory=None,
                 validation_files=None, depending=False, **kw):
        BaseAutomationTool.__init__(self, depending=depending, **kw)
        self.sample_registration_items = sample_registration_items
        self.__report_directory = report_directory
        self.__validation_files = validation_files
        self.__new_smd_sris = None

    def run(self):
        self.return_value = {}
        # Collect unknown supplier molecule designs and check known against
        # the design information in the current registration.
        self.__check_new_supplier_molecule_designs()
        #
        if not self.has_errors():
            self.__check_molecule_designs()
        #
        if not self.has_errors():
            self.__check_molecule_design_pools()
        #
        if not self.has_errors():
            self.__check_supplier_molecule_designs()
        #
        if not self.has_errors():
            # Run the sample registrar.
            sr = SampleRegistrar(self.sample_registration_items,
                                 report_directory=self.__report_directory,
                                 validation_files=self.__validation_files)
            sr.run()
            if sr.has_errors():
                self.add_error(sr.get_messages(logging.ERROR))
            else:
                self.return_value.update(sr.return_value)
            # Checks.
            for sri in self.sample_registration_items:
                mdpri = sri.molecule_design_pool_registration_item
                for mdri in mdpri.molecule_design_registration_items:
                    if not sri.supplier_molecule_design in \
                            mdri.molecule_design.supplier_molecule_designs:
                        msg = 'Supplier molecule design for sample ' \
                              '(%s, %s) not found.' \
                              % (sri.supplier.name, sri.product_id)
                        self.add_error(msg)

    def __check_new_supplier_molecule_designs(self):
        smd_agg = get_root_aggregate(ISupplierMoleculeDesign)
        # FIXME: We should really build a single filtering spec here like so:
        #        spec = reduce(or_,
        #                      [eq(supplier=sri.supplier, product_id=sri.product_id)
        #                       for in in self.sample_registration_items])
        #        However, this leads to "maximum recursion depth exceeded"
        #        problems with the current everest.
        exst_smd_map = {}
        for sri in self.sample_registration_items:
            smd_spec = eq(supplier=sri.supplier,
                          product_id=sri.product_id,
                          is_current=True)
            smd_agg.filter = smd_spec
            try:
                smd = smd_agg.iterator().next()
            except StopIteration:
                continue
            else:
                exst_smd_map[(smd.supplier, smd.product_id)] = smd
        new_smd_sris = []
        for sri in self.sample_registration_items:
            mdpri = sri.molecule_design_pool_registration_item
            key = (sri.supplier, sri.product_id)
            if key in exst_smd_map:
                # Update sample registration item.
                smd = exst_smd_map[key]
                sri.supplier_molecule_design = smd
                if not smd.molecule_design_pool is None:
                    # Compare found design information against existing design
                    # information.
                    mdris = mdpri.molecule_design_registration_items
                    found_md_hashes = sorted([self.__make_hash(mdri)
                                              for mdri in mdris])
                    exist_mds = smd.molecule_design_pool.molecule_designs
                    exist_md_hashes = sorted([md.structure_hash
                                              for md in exist_mds])
                    if found_md_hashes != exist_md_hashes:
                        msg = 'For product ID "%s" and supplier "%s", a ' \
                              'supplier molecule design exists which has ' \
                              'different design information than the one ' \
                              'included in the current registration.' \
                              % (sri.product_id, sri.supplier.name)
                        self.add_error(msg)
                        continue
                else:
                    # FIXME: Should this be a warning instead?
                    msg = 'For product ID "%s" and supplier "%s", a ' \
                          'supplier molecule design was found which does ' \
                          'not have an associated molecule design pool.' \
                          % (sri.product_id, sri.supplier.name)
                    self.add_error(msg)
                    continue
            else:
                new_smd_sris.append(sri)
        # Store new supplier molecule design registration items for later use.
        self.__new_smd_sris = new_smd_sris

    def __check_molecule_designs(self):
        md_agg = get_root_aggregate(IMoleculeDesign)
        # Build a map design hash -> registration item for all molecule design
        # registration items. Note that if several registration items produce
        # the same design hash (i.e., several pools sharing one or more
        # designs submitted for registration), only the last one is included.
        mdri_map = {}
        for sri in self.sample_registration_items:
            mdpri = sri.molecule_design_pool_registration_item
            for mdri in mdpri.molecule_design_registration_items:
                struc_hash = self.__make_hash(mdri)
                mdri_map[struc_hash] = mdri
                # Set the molecule type on the molecule design registration
                # item.
                mdri.molecule_type = sri.molecule_type
        # Build "contained" specification, filter all existing designs and
        # build difference set of new designs.
        md_agg.filter = cntd(structure_hash=mdri_map.keys())
        existing_md_map = dict([(md.structure_hash, md)
                                for md in md_agg.iterator()])
        # Update registration items with existing molecule designs.
        for struc_hash, md in existing_md_map.iteritems():
            mdri = mdri_map[struc_hash]
            mdri.molecule_design = md
        # Collect molecule design registration items to submit to the
        # registrar.
        new_md_hashes = \
                set(mdri_map.keys()).difference(existing_md_map.keys())
        if len(new_md_hashes) > 0:
            # Register the new designs.
            new_mdris = [mdri_map[hash_string]
                         for hash_string in new_md_hashes]
            md_registrar = MoleculeDesignRegistrar(new_mdris, log=self.log)
            md_registrar.run()
            if not md_registrar.has_errors():
                self.return_value.update(md_registrar.return_value)
            else:
                self.add_error(md_registrar.get_messages(logging.ERROR))

    def __check_molecule_design_pools(self):
        md_pool_agg = get_root_aggregate(IMoleculeDesignPool)
        # Create design pool hashes for the samples that are being registered.
        hash_map = {}
        for sri in self.sample_registration_items:
            # New single designs are not yet flushed at this point and will
            # create an impossible member hash (using None as ID value).
            # This is not a problem as we can not have an existing design pool
            # for a new single design.
            mdpri = sri.molecule_design_pool_registration_item
            hash_func = MoleculeDesignPool.make_member_hash
            hash_val = hash_func([mdri.molecule_design
                           for mdri in
                           mdpri.molecule_design_registration_items])
            hash_map[sri] = hash_val
        md_pool_agg.filter = cntd(member_hash=hash_map.values())
        mdp_map = dict([(mdp.member_hash, mdp)
                        for mdp in md_pool_agg.iterator()])
        new_md_pools = []
        for sri, hash_string in hash_map.iteritems():
            mdpri = sri.molecule_design_pool_registration_item
            if not hash_string in mdp_map:
                # Create new molecule design pool.
                md_pool = MoleculeDesignPool(
                        set([mdri.molecule_design
                             for mdri in
                             mdpri.molecule_design_registration_items]))
                md_pool_agg.add(md_pool)
                new_md_pools.append(md_pool)
            else:
                md_pool = mdp_map[hash_string]
            # Update sample registration item.
            mdpri.molecule_design_pool = md_pool
            sri.molecule_design_pool = md_pool
        self.return_value['molecule_design_pools'] = new_md_pools

    def __check_supplier_molecule_designs(self):
        # Run the supplier molecule design registrar to create missing
        # supplier molecule designs.
        smd_reg = SupplierMoleculeDesignRegistrar(self.__new_smd_sris,
                                                  log=self.log)
        smd_reg.run()
        if not smd_reg.has_errors():
            self.return_value.update(smd_reg.return_value)
#            # Iterate over registration items again and update supplier
#            # molecule designs with freshly registered molecule design pools.
#            for sri in self.sample_registration_items:
#                smd = sri.supplier_molecule_design
#                if not smd.molecule_design_pool is None:
#                    smd.molecule_design_pool = sri.molecule_design_pool
        else:
            self.add_error(smd_reg.get_messages(logging.ERROR))

    def __make_hash(self, mdri):
        return MoleculeDesign.make_structure_hash(mdri.chemical_structures)


class SupplierMoleculeDesignRegistrar(BaseAutomationTool):
    """
    Registers new supplier molecule designs for a set of sample registration
    items.

    Note that no check is performed if a supplier molecule design with the
    specified product ID and supplier already exists.
    """
    def __init__(self, sample_registration_items, **kw):
        """
        :param sample_registration_items: sequence of sample registration
          items to register supplier molecule designs for.
        :type sample_registration_items: sequence of
          :class:`SampleRegistrationItem`
        """
        BaseAutomationTool.__init__(self, **kw)
        self.sample_registration_items = sample_registration_items

    def run(self):
        smd_agg = get_root_aggregate(ISupplierMoleculeDesign)
        self.return_value = {}
        new_smds = []
        for sri in self.sample_registration_items:
            # Create a new supplier molecule design.
            smd = SupplierMoleculeDesign(sri.product_id, sri.supplier,
                                         is_current=True)
            # Associate the molecule designs for the sample registration
            # item with the new supplier molecule design.
            mdpri = sri.molecule_design_pool_registration_item
            for mdri in mdpri.molecule_design_registration_items:
                mdri.molecule_design.supplier_molecule_designs.append(smd)
            mdpri.molecule_design_pool \
                 .supplier_molecule_designs.append(smd)
            smd_agg.add(smd)
            new_smds.append(smd)
            # Update sample registration item.
            sri.supplier_molecule_design = smd
        self.return_value['supplier_molecule_designs'] = new_smds


class MoleculeDesignRegistrar(BaseAutomationTool):
    """
    Molecule design registration utility.

    Note that no check is performed if a molecule design with the specified
    structures already exists.

    Algorithm:
     * Loop through the chemical structure information for each registration
       item and either look up the corresponding record (using the
       structure_type_id and representation as key) or create a new one;
     * Create new molecule designs using the created/found structures.
    """
    def __init__(self, design_registration_items, depending=False, **kw):
        """
        :param design_registration_items: sequence of design registration
          items to process.
        :type design_registration_items: sequence of
          :class:`MoleculeDesignRegistrationItem`
        """
        BaseAutomationTool.__init__(self, depending=depending, **kw)
        self.design_registration_items = design_registration_items

    def run(self):
        cs_agg = get_root_aggregate(IChemicalStructure)
        md_agg = get_root_aggregate(IMoleculeDesign)
        cs_keys = set()
        for dri in self.design_registration_items:
            for cs in dri.chemical_structures:
                cs_keys.add((cs.structure_type_id, cs.representation))
        # FIXME: Build a single filtering spec here (see FIXME above).
        cs_map = {}
        for cs_key in cs_keys:
            sti, rpr = cs_key
            spec = eq(structure_type_id=sti,
                      representation=rpr)
            cs_agg.filter = spec
            try:
                cs = cs_agg.iterator().next()
            except StopIteration:
                continue
            else:
                cs_map[cs_key] = cs
        new_css = []
        new_mds = []
        for mdri in self.design_registration_items:
            md_structs = []
            for struct in mdri.chemical_structures:
                key = (struct.structure_type_id, struct.representation)
                if not key in cs_map:
                    # New chemical structure - add and use for the design.
                    cs_agg.add(struct)
                    new_css.append(struct)
                    md_structs.append(struct)
                else:
                    # Use existing structure for the design.
                    md_structs.append(cs_map[key])
            # Create the new design.
            md = MoleculeDesign.create_from_data(
                                        dict(molecule_type=mdri.molecule_type,
                                             chemical_structures=md_structs))
            md_agg.add(md)
            new_mds.append(md)
            # Update registration item.
            mdri.molecule_design = md
        self.return_value = dict(molecule_designs=new_mds,
                                 chemical_structures=new_css)


class DeliveryRegistrar(BaseAutomationTool):
    """
    Registrar for a sample delivery from a supplier.
    """
    def __init__(self, delivery_file, report_directory=None,
                 validation_files=None, depending=False,
                 **kw):
        """
        :param str delivery_file: XML file containing the delivery data.
        """
        BaseAutomationTool.__init__(self, depending=depending, **kw)
        self.__delivery_file = delivery_file
        self.__report_directory = report_directory
        self.__validation_files = validation_files

    def run(self):
        coll_cls = get_collection_class(ISupplierSampleRegistrationItem)
        rpr = as_representer(object.__new__(coll_cls), JsonMime)
        delivery_file = open(self.__delivery_file, 'rU')
        try:
            delivery_items = [rc.get_entity()
                              for rc in rpr.from_stream(delivery_file)]
        finally:
            delivery_file.close()
        spl_reg = SupplierSampleRegistrar(
                                delivery_items,
                                report_directory=self.__report_directory,
                                validation_files=self.__validation_files)
        spl_reg.run()
        if spl_reg.has_errors():
            self.add_error(
                    os.linesep.join(spl_reg.get_messages(logging.ERROR)))
