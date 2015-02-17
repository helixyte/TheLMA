"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Stock sample registrar.

Created on September 06, 2012.
"""
import datetime
import glob
import logging
import os

from everest.entities.utils import get_root_aggregate
from everest.querying.specifications import cntd
from everest.querying.specifications import eq
from thelma.entities.container import Tube
from thelma.entities.moleculedesign import MoleculeDesign
from thelma.entities.moleculedesign import MoleculeDesignPool
from thelma.entities.rack import Plate
from thelma.entities.rack import TubeRack
from thelma.entities.sample import StockSample
from thelma.entities.suppliermoleculedesign import SupplierMoleculeDesign
from thelma.interfaces import IChemicalStructure
from thelma.interfaces import IContainerSpecs
from thelma.interfaces import IItemStatus
from thelma.interfaces import IMoleculeDesign
from thelma.interfaces import IMoleculeDesignPool
from thelma.interfaces import IRackSpecs
from thelma.interfaces import IStockSample
from thelma.interfaces import ISupplierMoleculeDesign
from thelma.interfaces import ITube
from thelma.interfaces import ITubeRack
from thelma.tools.base import BaseTool
from thelma.tools.handlers.rackscanning \
                                    import AnyRackScanningParserHandler
from thelma.tools.handlers.rackscanning import RackScanningLayout
from thelma.tools.semiconstants import ITEM_STATUS_NAMES


__docformat__ = 'reStructuredText en'
__all__ = []


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


class ReportingAutomationTool(BaseTool): # still abstract pylint: disable=W0223
    def __init__(self, report_directory=None, parent=None):
        BaseTool.__init__(self, parent=parent)
        if report_directory is None:
            report_directory = os.getcwd()
        self.report_directory = report_directory

    def write_report(self):
        for name, data in self.return_value.items():
            ReporterDispatcher.dispatch(name, self.report_directory, data)


class RegistrationTool(ReportingAutomationTool): # still abstract pylint: disable=W0223
    def __init__(self, registration_items, report_directory=None,
                 parent=None):
        ReportingAutomationTool.__init__(self,
                                         report_directory=report_directory,
                                         parent=parent)
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
       from the registration items to the TheLMA barcodes of the freshly
       created racks;
     * Create stock samples.

    New entities are stored in the return value of the tool as a dictionary:

      stock_samples : list of stock samples created.
      tubes : list of tubes created.
      molecule_design_pools : list of molecule design pools created.
      supplier_rack_barcodes : dictionary supplier barcode -> TheLMA barcode
    """
    NAME = 'SampleRegistrar'

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
        # True if the registration items have tubes as containers.
        self.__tube_check_needed = None
        # True if all registration items have location information (rack
        # barcode and rack position).
        self.__has_location_info = None
        # The rack specs used by the registration items.
        self.__rack_specs = None
        # The container specs used by the registration items.
        self.__container_specs = None
        # The item status used by the registration items.
        self.__status = None

    def run(self):
        self.add_info('Running sample registrar.')
        self.return_value = {}
        # Fetch one semiconstants needed for new instances.
        self.__prepare_semiconstants()
        # Assign a rack to each registration item if we have rack barcodes
        # (and create new racks, if necessary). This also ensures that we
        # have location information either for all or for none of the
        # registration items.
        self.__check_racks()
        if not self.has_errors():
            # Assign a container to each registration item (and create new
            # tubes, if necessary).
            if self.__tube_check_needed:
                self.__check_tubes()
            else:
                self.__check_wells()
        if not self.has_errors():
            # Store supplier rack barcode -> TheLMA rack barcode map.
            self.return_value['rack_barcodes'] = \
                        self.__new_rack_supplier_barcode_map.items()
        if not self.has_errors() and self.__has_location_info:
            # The registration items have location information that needs
            # to be validated.
            self.__validate_locations()
        if not self.has_errors():
            self.add_info('Creating stock samples for registration items.')
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

    def __prepare_semiconstants(self):
        self.add_debug('Preparing semiconstants.')
        container_specs_agg = get_root_aggregate(IContainerSpecs)
        self.__container_specs = container_specs_agg.get_by_slug(
                                              self.__container_specs_name)
        self.__tube_check_needed = self.__container_specs.has_barcode
        rack_specs_agg = get_root_aggregate(IRackSpecs)
        self.__rack_specs = rack_specs_agg.get_by_slug(self.__rack_specs_name)
        if self.__tube_check_needed != self.__rack_specs.has_tubes:
            raise ValueError('Inconsistency in rack and tube specs detected.')
        item_status_agg = get_root_aggregate(IItemStatus)
        self.__status = item_status_agg.get_by_slug(
                                            ITEM_STATUS_NAMES.MANAGED.lower())

    def __check_racks(self):
        rack_agg = get_root_aggregate(ITubeRack)
        self.add_debug('Checking rack position information.')
        pos_infos = [(getattr(sri, 'rack_barcode'),
                     getattr(sri, 'rack_position'))
                    for sri in self.registration_items
                    if not (getattr(sri, 'rack_barcode') is None
                            or getattr(sri, 'rack_position') is None)]
        self.__has_location_info = len(pos_infos) > 0
        if self.__has_location_info \
           and len(pos_infos) != len(self.registration_items):
            msg = 'Some sample registration items contain location ' \
                  'information (rack barcode and rack position), but ' \
                  'not all of them do.'
            self.add_error(msg)
        else:
            new_racks = []
            if self.__has_location_info:
                rack_agg.filter = cntd(barcode=[pos_info[0]
                                                for pos_info in pos_infos])
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
        bcs = [getattr(sri, 'tube_barcode')
               for sri in self.registration_items]
        self.add_debug('Checking tubes. Barcodes: %s' % bcs)
        tube_agg.filter = cntd(barcode=bcs)
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

    def __check_wells(self):
        self.add_debug('Checking wells.')
        for sri in self.registration_items:
            container = sri.rack.container_positions[sri.rack_position]
            sri.container = container

    def __make_new_rack(self, sample_registration_item):
        self.add_debug('Creating new rack for registration barcode %s.'
                       % sample_registration_item.rack_barcode)
        kw = dict(label='',
                  specs=self.__rack_specs,
                  status=self.__status)
        if self.__tube_check_needed:
            rack_fac = TubeRack
        else:
            rack_fac = Plate
        rack = rack_fac(**kw)
        rack_barcode = sample_registration_item.rack_barcode
        if not rack_fac.is_valid_barcode(rack_barcode):
            self.__new_rack_supplier_barcode_map[rack] = rack_barcode
        return rack

    def __make_new_tube(self, sample_registration_item):
        self.add_debug('Creating new tube with barcode %s'
                       % sample_registration_item.tube_barcode)
        kw = dict(specs=self.__container_specs,
                  status=self.__status)
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
        if tube.location is None:
            msg = 'Tube with barcode %s does not have a location.' \
                  % tube.barcode
            self.add_error(msg)
            valid = False
        return valid

    def __validate_locations(self):
        self.add_debug('Validating tube positions (comparing current '
                       'positions with positions in sample registration '
                       'data).')
        for sri in self.registration_items:
            if sri.rack_position != sri.container.position \
               or sri.rack.barcode != sri.container.rack.barcode:
                msg = 'Location information in the registration item ' \
                      '(%s@%s) differs from actual location information ' \
                      '(%s@%s)' % \
                      (sri.rack.barcode, sri.rack_position.label,
                       sri.container.rack.barcode,
                       sri.container.position.label)
                self.add_error(msg)
        if not self.has_errors() and not self.__validation_files is None:
            self.__validate_locations_from_scanfile()

    def __validate_locations_from_scanfile(self):
        self.add_debug('Validating tube positions (comparing physical '
                       'positions from rack scanning files with current '
                       'positions.')
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
                    # barcode for which we just created a new TheLMA barcode.
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
        self.add_debug('Reading rack scanning files.')
        rsl_map = {}
        for rack_scanning_filename in self.__validation_files:
            self.add_debug('Reading rack scanning file %s.'
                           % rack_scanning_filename)
            with open(rack_scanning_filename, 'rU') as rs_stream:
                parser_handler = AnyRackScanningParserHandler(rs_stream,
                                                              parent=self)
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
    NAME = 'SuppplierSampleRegistrar'

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
        self.__new_smd_sri_map = None

    def run(self):
        self.add_info('Running supplier sample registrar.')
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
                                 parent=self)
            sr.run()
            if sr.has_errors():
                self.add_error(sr.get_messages(logging.ERROR))
            else:
                self.return_value.update(sr.return_value)
            # Checks.
            for sri in self.registration_items:
                mdpri = sri.molecule_design_pool_registration_item
                if not sri.supplier_molecule_design \
                   in mdpri.molecule_design_pool.supplier_molecule_designs:
                    msg = 'For sample (%s, %s), the design pool is not ' \
                          'associated with the supplier molecule design.' \
                          % (sri.supplier.name, sri.product_id)
                    self.add_error(msg)
                if len(mdpri.molecule_design_registration_items) == 1:
                    mdri = mdpri.molecule_design_registration_items[0]
                    if not sri.supplier_molecule_design in \
                            mdri.molecule_design.supplier_molecule_designs:
                        msg = 'For sample (%s, %s), the design is not ' \
                              'associated with the supplier molecule ' \
                              'design.' % (sri.supplier.name, sri.product_id)
                        self.add_error(msg)

    def __check_new_supplier_molecule_designs(self):
        self.add_debug('Checking for new supplier molecule designs.')
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
        new_smd_sri_map = {}
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
                # We use a map here so that multiple sample registration items
                # with the same supplier molecule design information create
                # only a single new supplier molecule design.
                new_smd_sri_map.setdefault(key, []).append(sri)
        # Store new supplier molecule design registration items for later use.
        self.__new_smd_sri_map = new_smd_sri_map

    def __check_molecule_design_pools(self):
        self.add_debug('Checking for new molecule design pools.')
        mdpris = [sri.molecule_design_pool_registration_item
                  for sri in self.registration_items]
        mdp_registrar = \
                MoleculeDesignPoolRegistrar(mdpris,
                                            report_directory=
                                                self.report_directory,
                                            parent=self)
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
        self.add_debug('Processing %d new supplier molecule designs.'
                       % len(self.__new_smd_sri_map))
        smd_agg = get_root_aggregate(ISupplierMoleculeDesign)
        new_smds = []
        for key, sris in self.__new_smd_sri_map.iteritems():
            supplier, product_id = key
            # Create a new supplier molecule design.
            smd = SupplierMoleculeDesign(product_id, supplier, is_current=True)
            for sri in sris:
                # Associate the molecule designs for the sample registration
                # item with the new supplier molecule design.
                mdpri = sri.molecule_design_pool_registration_item
                # Associate the molecule design pool with the new supplier
                # molecule design.
                mdpri_smds = \
                    mdpri.molecule_design_pool.supplier_molecule_designs
                found_mdpri_smd = False
                for mdpri_smd in mdpri_smds:
                    if mdpri_smd == smd:
                        found_mdpri_smd = True
                    # If this is the current supplier molecule design for
                    # this molecule design pool, set it to "not current".
                    if mdpri_smd.is_current:
                        mdpri_smd.is_current = False
                if not found_mdpri_smd:
                    mdpri_smds.append(smd)
                # *Only* for the case of a pool containing a single design,
                # also update the molecule design with the new supplier
                # molecule design.
                if len(mdpri.molecule_design_registration_items) == 1:
                    mdri = mdpri.molecule_design_registration_items[0]
                    mdri_smds = mdri.molecule_design.supplier_molecule_designs
                    found_mdri_smd = False
                    for mdri_smd in mdri_smds:
                        if mdri_smd == smd:
                            found_mdri_smd = True
                        # If this is the current supplier molecule design for
                        # this molecule design, set it to "not current".
                        if mdri_smd.is_current:
                            mdri_smd.is_current = False
                    if not found_mdri_smd:
                        mdri_smds.append(smd)
                # Update sample registration item.
                sri.supplier_molecule_design = smd
            smd_agg.add(smd)
            new_smds.append(smd)
        self.return_value['supplier_molecule_designs'] = new_smds


class MoleculeDesignPoolRegistrar(RegistrationTool):
    """
    Molecule design pool registration utility.
    """
    NAME = 'MoleculeDesignPoolRegistrar'

    def __init__(self, registration_items, report_directory=None, **kw):
        RegistrationTool.__init__(self, registration_items,
                                  report_directory=report_directory, **kw)

    def run(self):
        self.add_info('Running molecule design pool registrar.')
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
        md_reg = MoleculeDesignRegistrar(mdris, parent=self)
        md_reg.run()
        if md_reg.has_errors():
            self.add_error(md_reg.get_messages(logging.ERROR))
        else:
            self.return_value.update(md_reg.return_value)
            # Now that we have all designs, proceed to the pools.
            self.__process_molecule_design_pools()

    def __process_molecule_design_pools(self):
        self.add_debug('Processing molecule design pools.')
        md_pool_agg = get_root_aggregate(IMoleculeDesignPool)
        mdpri_hash_map = {}
        hash_func = MoleculeDesignPool.make_member_hash
        new_mdpri_map = {}
        new_mds = self.return_value['molecule_designs']
        for mdpri in self.registration_items:
            # By definition, any mdpri that contains one or more new designs
            # must be new. We must treat this as a special case because
            # building member hash values with the new designs does not work
            # reliably since they may not have been flushed yet.
            mds = [mdri.molecule_design
                   for mdri in mdpri.molecule_design_registration_items]
            if any(md in new_mds for md in mds):
                # We use the *structure* as key for the new pools map here
                # as this is always available (unlike the design IDs, which
                # may not have been generated at this point).
                key = self.__make_new_mdpri_key(mdpri)
                new_mdpri_map.setdefault(key, []).append(mdpri)
            else:
                # For pools that consist only of existing designs, we build
                # a map with member hashes as keys so we can query with a
                # single DB call.
                hash_val = \
                        hash_func([mdri.molecule_design
                                   for mdri in
                                   mdpri.molecule_design_registration_items])
                mdpri_hash_map.setdefault(hash_val, []).append(mdpri)
        if len(mdpri_hash_map) > 0:
            md_pool_agg.filter = cntd(member_hash=mdpri_hash_map.keys())
            existing_mdp_map = dict([(mdp.member_hash, mdp)
                                     for mdp in md_pool_agg.iterator()])
            # Update existing molecule design pool registration items.
            for hash_val, mdp in existing_mdp_map.iteritems():
                mdpris = mdpri_hash_map[hash_val]
                for mdpri in mdpris:
                    if not mdpri.molecule_design_pool is None \
                       and mdp.id != mdpri.molecule_design_pool.id:
                        msg = 'The molecule design pool ID (%s) specified ' \
                              'in the sample data does not match the ID ' \
                              'of the pool that retrieved for the design ' \
                              'structure information associated with it.'
                        self.add_error(msg)
                        continue
                    mdpri.molecule_design_pool = mdp
        else:
            existing_mdp_map = {}
        # Determine non-existing molecule design pool registration items and
        # build up a map (this makes sure the same design is registered at
        # most once.
        new_mdp_hashes = \
                set(mdpri_hash_map.keys()).difference(existing_mdp_map.keys())
        for new_mdp_hash in new_mdp_hashes:
            mdpris = mdpri_hash_map[new_mdp_hash]
            for mdpri in mdpris:
                if not mdpri.molecule_design_pool is None:
                    # This is a case where we supplied both design pool ID *and*
                    # structure information in the data file and the two do not
                    # match (i.e., the structures were not found).
                    msg = 'The molecule design pool ID (%s) specified in the ' \
                          'sample data does not match the design structure ' \
                          'information associated with it.'
                    self.add_error(msg)
                    continue
                key = self.__make_new_mdpri_key(mdpri)
                new_mdpri_map.setdefault(key, []).append(mdpri)
        if len(new_mdpri_map) > 0:
            new_md_pools = []
            for mdpris in new_mdpri_map.values():
                # We use the first mdp registration item to create a
                # new pool and update all with the latter.
                md_pool = MoleculeDesignPool(
                        set([mdri.molecule_design
                             for mdri in
                             mdpris[0].molecule_design_registration_items]))
                md_pool_agg.add(md_pool)
                new_md_pools.append(md_pool)
                for mdpri in mdpris:
                    mdpri.molecule_design_pool = md_pool
            self.return_value['molecule_design_pools'] = new_md_pools

    def __make_new_mdpri_key(self, mdpri):
        mds = [mdri.molecule_design
               for mdri in mdpri.molecule_design_registration_items]
        return ','.join([md.structure_hash for md in mds])


class MoleculeDesignRegistrar(RegistrationTool):
    """
    Molecule design registration utility.

    Algorithm:
     * Loop through the chemical structure information for each registration
       item and either look up the corresponding record (using the
       structure_type_id and representation as key) or create a new one;
     * Create new molecule designs using the created/found structures.
    """
    NAME = 'MoleculeDesignRegistrar'

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
        self.add_info('Running molecule design registrar.')
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
        self.add_debug('Creating %d new molecule designs.'
                       % len(self.__new_mdris))
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
                    cs_map[key] = struct
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
        self.add_debug('Checking for new molecule designs.')
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
