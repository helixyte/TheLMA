"""
Stock sample registrar.

Created on September 06, 2012.
"""
from everest.entities.base import Entity
from everest.entities.utils import get_root_aggregate
from everest.querying.specifications import cntd
from everest.querying.specifications import eq
from everest.resources.base import Member
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from thelma.models.rack import Plate
from thelma.automation.handlers.rackscanning \
                                    import AnyRackScanningParserHandler
from thelma.automation.handlers.rackscanning import RackScanningLayout
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.tools.semiconstants import ITEM_STATUS_NAMES
from thelma.interfaces import IChemicalStructure
from thelma.interfaces import IContainerSpecs
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
from thelma.models.container import Tube
from thelma.models.container import Well
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
    molecule_type = member_attribute(IMoleculeType, 'molecule_type')
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
    molecule_type = member_attribute(IMoleculeType, 'molecule_type')
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


class Reporter(object):
    def __init__(self, directory, filename):
        self.__directory = directory
        self.__filename = filename

    def header(self):
        raise NotImplementedError('Abstract method.')

    def line(self, datum):
        raise NotImplementedError('Abstract method.')

    def run(self, data):
        lines = [self.header()]
        for datum in data:
            lines.append(self.line(datum))
        time_string = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        report_filename = os.path.join(self.__directory,
                                       "%s-%s.csv" % (self.__filename,
                                                      time_string))
        with open(report_filename, 'wb') as report_file:
            report_file.write(os.linesep.join(lines))


class BarcodeMapReporter(Reporter):
    def header(self):
        return 'cenix_barcode,supplier_barcode'

    def line(self, datum):
        rack, spl_bc = datum
        return "%s,%s" % (rack.barcode, spl_bc)


class StockSampleReporter(Reporter):
    def header(self):
        return 'tube_barcode,molecule_type,molecule_design_pool_id,' \
               'supplier,volume,concentration'

    def line(self, datum):
        return '"%s","%s",%s,"%s",%f,%f' % (datum.container.barcode,
                                            datum.molecule_type.name,
                                            datum.molecule_design_pool.id,
                                            datum.supplier.name,
                                            datum.volume,
                                            datum.concentration)


class SupplierMoleculeDesignReporter(Reporter):
    def header(self):
        return 'product_id,supplier,supplier_molecule_design_id,' \
               'molecule_design_pool_id'

    def line(self, datum):
        return '%s,%s,%s,%s' % (datum.product_id, datum.supplier.name,
                                datum.id, datum.molecule_design_pool.id)


class MoleculeDesignReporter(Reporter):
    def header(self):
        return 'molecule_design_id,structure_hash'

    def line(self, datum):
        return '%s,%s' % (datum.id, datum.structure_hash_string)


class MoleculeDesignPoolReporter(Reporter):
    def header(self):
        return 'molecule_design_pool_id,member_hash'

    def line(self, datum):
        return '%s,%s' % (datum.id, datum.member_hash_string)


class ReporterDispatcher(object):
    __reporter_map = dict(rack_barcodes=BarcodeMapReporter,
                          stock_samples=StockSampleReporter,
                          supplier_molecule_designs=
                                SupplierMoleculeDesignReporter,
                          molecule_designs=MoleculeDesignReporter,
                          molecule_design_pools=MoleculeDesignPoolReporter)
    @staticmethod
    def dispatch(name, directory, data):
        rep_cls = ReporterDispatcher.__reporter_map.get(name)
        if not rep_cls is None:
            rep = rep_cls(directory, name)
            rep.run(data)


class ReportingAutomationTool(BaseAutomationTool): # still abstract pylint: disable=W0223
    def __init__(self, report_directory=None, **kw):
        BaseAutomationTool.__init__(self, **kw)
        if report_directory is None:
            report_directory = os.getcwd()
        self.report_directory = report_directory

    def write_report(self):
        for name, data in self.return_value.items():
            ReporterDispatcher.dispatch(name, self.report_directory, data)


class RegistrationTool(ReportingAutomationTool): # still abstract pylint: disable=W0223
    def __init__(self, registration_items, report_directory=None,
                 depending=False, **kw):
        ReportingAutomationTool.__init__(self,
                                         report_directory=report_directory,
                                         depending=depending, **kw)
        self.registration_items = registration_items


class SampleRegistrar(RegistrationTool):
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
    def __init__(self, registration_items, report_directory=None,
                 rack_specs_name='matrix0500',
                 container_specs_name='matrix0500',
                 validation_files=None, **kw):
        """
        :param registration_items: delivery samples to register.
        :type registration_items: sequence of
            :class:`SampleRegistrationItem`
        :param str rack_specs_name: name of the rack specs to use for newly
            created racks.
        :param str container_specs_name: name of the tube specs to use for newly
            created tubes.
        :param str validation_files: optional comma-separated list of rack
            scanning file names to use for validation of the sample positions.
        """
        RegistrationTool.__init__(self, registration_items,
                                  report_directory=report_directory, **kw)
        self.__container_specs_name = container_specs_name
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
        self.__container_create_kw = None
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
            # Store supplier rack barcode -> Cenix rack barcode map.
            self.return_value['rack_barcodes'] = \
                        self.__new_rack_supplier_barcode_map.items()
        if not self.has_errors() and not self.__validation_files is None:
            self.__validate_locations()
        if not self.has_errors():
            new_stock_spls = []
            ss_agg = get_root_aggregate(IStockSample)
            for sri in self.registration_items:
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

    def __check_racks(self):
        rack_agg = get_root_aggregate(IRack)
        bcs = [getattr(sri, 'rack_barcode')
               for sri in self.registration_items
               if not getattr(sri, 'rack_barcode') is None]
        if len(bcs) > 0 and len(bcs) != len(self.registration_items):
            msg = 'Some sample registration items contain rack ' \
                  'barcodes, but not all of them do.'
            self.add_error(msg)
        else:
            new_racks = []
            if len(bcs) > 0:
                rack_agg.filter = cntd(barcode=bcs)
                rack_map = dict([(rack.barcode, rack)
                                 for rack in rack_agg.iterator()])
                for sri in self.registration_items:
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
                          for sri in self.registration_items])
        tube_map = dict([(tube.barcode, tube)
                         for tube in tube_agg.iterator()])
        new_tubes = []
        for sri in self.registration_items:
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
        if kw['specs'].has_tubes:
            rack_fac = TubeRack
        else:
            rack_fac = Plate
        rack = rack_fac(**kw)
        rack_barcode = sample_registration_item.rack_barcode
        if not rack_fac.is_valid_barcode(rack_barcode):
            self.__new_rack_supplier_barcode_map[rack] = rack_barcode
        return rack

    def __make_new_tube(self, sample_registration_item):
        if self.__container_create_kw is None:
            container_specs_agg = get_root_aggregate(IContainerSpecs)
            item_status_agg = get_root_aggregate(IItemStatus)
            self.__container_create_kw = \
              dict(specs=container_specs_agg.get_by_slug(
                                                self.__container_specs_name),
                   status=item_status_agg.get_by_slug(
                                            ITEM_STATUS_NAMES.MANAGED.lower())
                   )
        kw = self.__container_create_kw.copy()
        is_tube = kw['specs'].has_barcode
        if is_tube:
            container_fac = Tube
            kw['barcode'] = sample_registration_item.tube_barcode
        else:
            container_fac = Well
        pos = sample_registration_item.rack_position
        if not pos is None:
            kw['rack'] = sample_registration_item.rack
            kw['position'] = pos
            tube = container_fac.create_from_rack_and_position(**kw)
        else:
            tube = container_fac(**kw)
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
            for sri in self.registration_items:
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


class SupplierSampleRegistrar(RegistrationTool):
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
    def __init__(self, registration_items, report_directory=None,
                 rack_specs_name='matrix0500',
                 container_specs_name='matrix0500',
                 validation_files=None, **kw):
        RegistrationTool.__init__(self, registration_items,
                                  report_directory=report_directory,
                                  **kw)
        self.__validation_files = validation_files
        self.__rack_specs_name = rack_specs_name
        self.__container_specs_name = container_specs_name
        self.__new_smd_sris = None

    def run(self):
        self.return_value = {}
        # Collect unknown supplier molecule designs and check known against
        # the design information in the current registration.
        self.__check_new_supplier_molecule_designs()
        #
        if not self.has_errors():
            self.__check_molecule_design_pools()
        #
        if not self.has_errors():
            self.__process_supplier_molecule_designs()
        #
        if not self.has_errors():
            # Run the sample registrar.
            sr = SampleRegistrar(self.registration_items,
                                 report_directory=self.report_directory,
                                 validation_files=self.__validation_files,
                                 rack_specs_name=self.__rack_specs_name,
                                 container_specs_name=
                                        self.__container_specs_name,
                                 depending=True,
                                 log=self.log)
            sr.run()
            if sr.has_errors():
                self.add_error(sr.get_messages(logging.ERROR))
            else:
                self.return_value.update(sr.return_value)
            # Checks.
            for sri in self.registration_items:
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
        for sri in self.registration_items:
            smd_spec = eq(supplier=sri.supplier,
                          product_id=sri.product_id,
                          is_current=True)
            smd_agg.filter = smd_spec
            try:
                smd = next(smd_agg.iterator())
            except StopIteration:
                continue
            else:
                exst_smd_map[(smd.supplier, smd.product_id)] = smd
        new_smd_sris = []
        for sri in self.registration_items:
            mdpri = sri.molecule_design_pool_registration_item
            # Set the molecule type.
            mdpri.molecule_type = sri.molecule_type
            key = (sri.supplier, sri.product_id)
            if key in exst_smd_map:
                # Update sample registration item.
                smd = exst_smd_map[key]
                sri.supplier_molecule_design = smd
                if not smd.molecule_design_pool is None:
                    # Compare found design information against existing design
                    # information.
                    mdris = mdpri.molecule_design_registration_items
                    found_md_hashes = \
                        sorted([MoleculeDesign.make_structure_hash(
                                                    mdri.chemical_structures)
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

    def __check_molecule_design_pools(self):
        mdpris = [sri.molecule_design_pool_registration_item
                  for sri in self.registration_items]
        mdp_registrar = \
                MoleculeDesignPoolRegistrar(mdpris,
                                            depending=True,
                                            log=self.log,
                                            report_directory=
                                                self.report_directory)
        mdp_registrar.run()
        if not mdp_registrar.has_errors():
            # Update sample registration items.
            for sri in self.registration_items:
                mdpri = sri.molecule_design_pool_registration_item
                sri.molecule_design_pool = mdpri.molecule_design_pool
            self.return_value.update(mdp_registrar.return_value)
        else:
            self.add_error(mdp_registrar.get_messages(logging.ERROR))


    def __process_supplier_molecule_designs(self):
        smd_agg = get_root_aggregate(ISupplierMoleculeDesign)
        new_smds = []
        for sri in self.__new_smd_sris:
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


class MoleculeDesignPoolRegistrar(RegistrationTool):
    """
    Molecule design pool registration utility.
    """
    def __init__(self, registration_items, report_directory=None, **kw):
        RegistrationTool.__init__(self, registration_items,
                                  report_directory=report_directory, **kw)

    def run(self):
        self.return_value = {}
        # Collect molecule design registration items and set their molecule
        # type.
        mdris = []
        for mdpri in self.registration_items:
            for mdri in mdpri.molecule_design_registration_items:
                mdris.append(mdri)
                mdri.molecule_type = mdpri.molecule_type
        # First, run the MoleculeDesignRegistrar to register all designs
        # that are not in the system yet.
        md_reg = MoleculeDesignRegistrar(mdris, log=self.log)
        md_reg.run()
        if md_reg.has_errors():
            self.add_error.md_reg.get_messages(logging.ERROR)
        else:
            self.return_value.update(md_reg.return_value)
            # Now that we have all designs, proceed to the pools.
            self.__process_molecule_design_pools()

    def __process_molecule_design_pools(self):
        md_pool_agg = get_root_aggregate(IMoleculeDesignPool)
        mdpri_hash_map = {}
        hash_func = MoleculeDesignPool.make_member_hash
        new_mdpris = []
        new_mds = self.return_value['molecule_designs']
        for mdpri in self.registration_items:
            # By definition, any mdpri that contains one or more new designs
            # must be new. We must treat this as a special case because
            # building member hash values with the new designs does not work
            # reliably since they may not have been flushed yet.
            if any([mdri.molecule_design in new_mds
                    for mdri in mdpri.molecule_design_registration_items]):
                new_mdpris.append(mdpri)
            else:
                # For all others, we build a list of member hashes that we
                # then query in a single DB call.
                hash_val = \
                        hash_func([mdri.molecule_design
                                   for mdri in
                                   mdpri.molecule_design_registration_items])
                mdpri_hash_map[hash_val] = mdpri
        if len(mdpri_hash_map) > 0:
            md_pool_agg.filter = cntd(member_hash=mdpri_hash_map.keys())
            existing_mdp_map = dict([(mdp.member_hash, mdp)
                                     for mdp in md_pool_agg.iterator()])
            # Update existing molecule design pool registration items.
            for hash_val, mdp in existing_mdp_map.iteritems():
                mdpri = mdpri_hash_map[hash_val]
                mdpri.molecule_design_pool = mdp
        else:
            existing_mdp_map = {}
        # Find new molecule design pool registration items.
        new_mdp_hashes = \
                set(mdpri_hash_map.keys()).difference(existing_mdp_map.keys())
        for new_mdp_hash in new_mdp_hashes:
            new_mdpris.append(mdpri_hash_map[new_mdp_hash])
        if len(new_mdpris) > 0:
            new_md_pools = []
            for mdpri in new_mdpris:
                # Create new molecule design pool.
                md_pool = MoleculeDesignPool(
                        set([mdri.molecule_design
                             for mdri in
                             mdpri.molecule_design_registration_items]))
                md_pool_agg.add(md_pool)
                new_md_pools.append(md_pool)
                mdpri.molecule_design_pool = md_pool
            self.return_value['molecule_design_pools'] = new_md_pools


class MoleculeDesignRegistrar(RegistrationTool):
    """
    Molecule design registration utility.

    Algorithm:
     * Loop through the chemical structure information for each registration
       item and either look up the corresponding record (using the
       structure_type_id and representation as key) or create a new one;
     * Create new molecule designs using the created/found structures.
    """
    def __init__(self, registration_items, report_directory=None, **kw):
        """
        :param design_registration_items: sequence of design registration
          items to process.
        :type design_registration_items: sequence of
          :class:`MoleculeDesignRegistrationItem`
        """
        RegistrationTool.__init__(self, registration_items,
                                  report_directory=report_directory, **kw)
        self.__new_mdris = None

    def run(self):
        self.__check_new_molecule_designs()
        cs_agg = get_root_aggregate(IChemicalStructure)
        md_agg = get_root_aggregate(IMoleculeDesign)
        cs_keys = set()
        new_css = set()
        new_mds = set()
        # Build keys for all new chemical structures.
        for mdris in self.__new_mdris:
            # By definition, all mdris for a given hash have the same
            # structures, so we just take the first.
            for cs in mdris[0].chemical_structures:
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
        for mdris in self.__new_mdris:
            md_structs = []
            # By definition, all mdris for a given hash have the same
            # structures, so we just take the first.
            for struct in mdris[0].chemical_structures:
                key = (struct.structure_type_id, struct.representation)
                if not key in cs_map:
                    # New chemical structure - add and use for the design.
                    cs_agg.add(struct)
                    new_css.add(struct)
                    md_structs.append(struct)
                else:
                    # Use existing structure for the design.
                    md_structs.append(cs_map[key])
            # Create the new design.
            md = MoleculeDesign.create_from_data(
                                dict(molecule_type=mdris[0].molecule_type,
                                     chemical_structures=md_structs))
            md_agg.add(md)
            new_mds.add(md)
            # Update registration items.
            for mdri in mdris:
                mdri.molecule_design = md
        self.return_value = dict(molecule_designs=new_mds,
                                 chemical_structures=new_css)

    def __check_new_molecule_designs(self):
        md_agg = get_root_aggregate(IMoleculeDesign)
        # Build a map design hash -> registration item for all molecule design
        # registration items.
        mdri_map = {}
        for mdri in self.registration_items:
            struc_hash = \
              MoleculeDesign.make_structure_hash(mdri.chemical_structures)
            mdri_map.setdefault(struc_hash, []).append(mdri)
        # Build "contained" specification, filter all existing designs and
        # build difference set of new designs.
        md_agg.filter = cntd(structure_hash=mdri_map.keys())
        existing_md_map = dict([(md.structure_hash, md)
                                for md in md_agg.iterator()])
        # Update registration items with existing molecule designs and
        # remove from hash map.
        for struc_hash, md in existing_md_map.iteritems():
            mdris = mdri_map.pop(struc_hash)
            for mdri in mdris:
                mdri.molecule_design = md
        self.__new_mdris = list(mdri_map.values())
