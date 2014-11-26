"""
Unit tests for sampleregistration.
"""
from csv import DictReader
from everest.entities.utils import get_root_aggregate
from everest.mime import JsonMime
from everest.representers.utils import as_representer
from everest.resources.utils import get_collection_class
from pkg_resources import resource_filename # pylint: disable=E0611,F0401
from thelma.automation.tools.stock.sampleregistration import \
                                    ISupplierSampleRegistrationItem
from thelma.automation.tools.stock.sampleregistration import \
                                    SupplierSampleRegistrar
from thelma.interfaces import IContainerSpecs
from thelma.interfaces import IItemStatus
from thelma.interfaces import ITube
from thelma.entities.container import Tube
from thelma.entities.rack import Rack
from thelma.entities.rack import RackPosition
from thelma.entities.status import ITEM_STATUSES
from thelma.testing import ThelmaResourceTestCase
import glob
import logging
import os
import shutil
import tempfile
#from thelma.automation.tools.stock.sampleregistration import SampleRegistrar
#from thelma.automation.tools.stock.sampleregistration import \
#                                    ISampleRegistrationItem


class _SampleRegistrationTestCase(ThelmaResourceTestCase):
    delivery_file = None
    def set_up(self):
        ThelmaResourceTestCase.set_up(self)
        self._directory = tempfile.mkdtemp()
        fn = resource_filename(*self.delivery_file.split(':'))
        coll_cls = get_collection_class(ISupplierSampleRegistrationItem)
        rpr = as_representer(object.__new__(coll_cls), JsonMime)
        self.delivery_items = \
            [rc.get_entity() for rc in rpr.from_stream(open(fn, 'rU'))]

    def tear_down(self):
        shutil.rmtree(self._directory)

    def _make_registrar(self):
        return SupplierSampleRegistrar(self.delivery_items,
                                       report_directory=self._directory)

    def _run_registration(self):
        dlv_reg = self._make_registrar()
        dlv_reg.run()
        self.assert_false(dlv_reg.has_errors())
        reg_data = dlv_reg.return_value
        self._check_registration_data(reg_data)
        dlv_reg.write_report()
        return reg_data

    def _check_registration_data(self, reg_data):
        self.assert_equal(len(reg_data['molecule_designs']), 1)
        self.assert_equal(len(reg_data['chemical_structures']), 2)
        self.assert_equal(len(reg_data['molecule_design_pools']), 1)
        self.assert_equal(len(reg_data['stock_samples']), 2)
        self.assert_equal(len(reg_data['supplier_molecule_designs']), 1)
        self.assert_equal(len(reg_data['tubes']), 2)


class SiRnaSampleRegistrationTestCase(_SampleRegistrationTestCase):
    delivery_file = 'thelma:oldtests/tools/stock/registration/' \
                    'ambion_delivery_samples.json'

    def test_delivery(self):
        reg_data = self._run_registration()
        self.assert_equal(len(reg_data['racks']), 0)


class NewSiRnaSampleRegistrationTestCase(SiRnaSampleRegistrationTestCase):
    delivery_file = 'thelma:oldtests/tools/stock/registration/' \
                    'ambion_delivery_samples_new_only.json'

    def _check_registration_data(self, reg_data):
        self.assert_equal(len(reg_data['stock_samples']), 1)
        self.assert_equal(len(reg_data['tubes']), 1)


class PrimerSampleRegistrationTestCase(_SampleRegistrationTestCase):
    delivery_file = 'thelma:oldtests/tools/stock/registration/' \
                    'metabion_delivery_samples.json'

    def test_delivery(self):
        reg_data = self._run_registration()
        self.assert_equal(len(reg_data['racks']), 1)

    def _check_registration_data(self, reg_data):
        self.assert_equal(len(reg_data['molecule_designs']), 2)
        self.assert_equal(len(reg_data['chemical_structures']), 2)
        self.assert_equal(len(reg_data['molecule_design_pools']), 1)
        self.assert_equal(len(reg_data['stock_samples']), 2)
        self.assert_equal(len(reg_data['supplier_molecule_designs']), 1)
        self.assert_equal(len(reg_data['tubes']), 2)


class DuplicateSampleRegistrationTestCase(_SampleRegistrationTestCase):
    delivery_file = 'thelma:oldtests/tools/stock/registration/' \
                    'ambion_delivery_samples_duplicates.json'

    def test_delivery(self):
        dlv_reg = self._make_registrar()
        dlv_reg.run()
        self.assert_false(dlv_reg.has_errors())
        reg_data = dlv_reg.return_value
        self.assert_equal(len(reg_data['molecule_designs']), 0)
        self.assert_equal(len(reg_data['tubes']), 2)


class SampleRegistrationWithLocationsTestCase(_SampleRegistrationTestCase):
    delivery_file = 'thelma:oldtests/tools/stock/registration/' \
                    'ambion_delivery_samples_with_locations.json'

    def test_delivery(self):
        reg_data = self._run_registration()
        self.assert_equal(len(reg_data['racks']), 1)


class SampleRegistrationWithInvalidLocationTestCase(
                                                _SampleRegistrationTestCase):
    delivery_file = 'thelma:oldtests/tools/stock/registration/' \
                    'ambion_delivery_samples_with_locations.json'

    def test_delivery(self):
        status = self._get_entity(IItemStatus, ITEM_STATUSES.MANAGED.lower())
        specs = self._get_entity(IContainerSpecs, 'matrix0500')
        rack = self._create_tube_rack()
        pos = RackPosition.from_label('B1')
        tube = Tube.create_from_rack_and_position(specs, status, '9999999998',
                                                  rack, pos)
        agg = get_root_aggregate(ITube)
        agg.add(tube)
        dlv_reg = self._make_registrar()
        dlv_reg.run()
        self.assert_true(dlv_reg.has_errors())
        err_msg = os.linesep.join(
                        dlv_reg.get_messages(logging_level=logging.ERROR))
        msg = '@A1) differs from actual location'
        self.assert_not_equal(err_msg.find(msg), -1)


class _SampleRegistrationWithScanfileTestCase(
                                    SampleRegistrationWithLocationsTestCase):
    scan_file = None

    def set_up(self):
        SampleRegistrationWithLocationsTestCase.set_up(self)
        vld_f_path = resource_filename(*self.scan_file.split(':'))
        self.__validation_file = os.path.join(self._directory,
                                              os.path.split(vld_f_path)[1])
        shutil.copy(vld_f_path, self._directory)

    def _make_registrar(self):
        return SupplierSampleRegistrar(
                    self.delivery_items,
                    report_directory=self._directory,
                    validation_files=self.__validation_file)


class SampleRegistrationWithValidScanfileTestCase(
                                _SampleRegistrationWithScanfileTestCase):

    scan_file = 'thelma:oldtests/tools/stock/registration/' \
                'valid_delivery_scan_file.txt'

    def test_delivery(self):
        reg_data = self._run_registration()
        self.assert_equal(len(reg_data['racks']), 1)
        # Rack barcode report file.
        bc_filename = \
            glob.glob(os.path.join(self._directory, 'rack_barcodes*.csv'))[0]
        self.assert_true(os.path.exists(bc_filename))
        with open(bc_filename, 'rU') as csv:
            reader = DictReader(csv)
            bc_lines = list(reader)
        self.assert_equal(len(bc_lines), 1)
        bc_row_data = bc_lines[0]
        self.assert_true(Rack.is_valid_barcode(bc_row_data['cenix_barcode']))
        self.assert_equal(bc_row_data['supplier_barcode'], 'AMB0123')
        # Stock samples report file.
        ss_filename = \
            glob.glob(os.path.join(self._directory, 'stock_samples*.csv'))[0]
        self.assert_true(os.path.exists(ss_filename))
        with open(ss_filename, 'rU') as csv:
            reader = DictReader(csv)
            ss_lines = list(reader)
        self.assert_equal(len(ss_lines), 2)
        ss_row_data = ss_lines[0]
        self.assert_equal(ss_row_data['tube_barcode'], '9999999998')
        self.assert_equal(float(ss_row_data['volume']), 2e-4)


class SampleRegistrationWithInvalidScanfileTestCase(
                                _SampleRegistrationWithScanfileTestCase):

    scan_file = 'thelma:oldtests/tools/stock/registration/' \
                'invalid_delivery_scan_file.txt'

    def test_delivery(self):
        dlv_reg = self._make_registrar()
        dlv_reg.run()
        self.assert_true(dlv_reg.has_errors())
        err_msg = os.linesep.join(
                        dlv_reg.get_messages(logging_level=logging.ERROR))
        self.assert_not_equal(
                err_msg.find('expected 9999999998, found 9999999999'), -1)


#class SampleRegistrarTestCase(ThelmaResourceTestCase):
#    def set_up(self):
#        ThelmaResourceTestCase.set_up(self)
#        fn = resource_filename(*'thelma:oldtests/tools/stock/registration/'
#                               'pool_registration.json'.split(':'))
#        coll_cls = get_collection_class(ISampleRegistrationItem)
#        rpr = as_representer(object.__new__(coll_cls), JsonMime)
#        self.delivery_items = \
#            [rc.get_entity() for rc in rpr.from_stream(open(fn, 'rU'))]
#
#    def test_registration(self):
#        spl_reg = SampleRegistrar(self.delivery_items)
#        spl_reg.run()
#        self.assert_false(spl_reg.has_errors())
#        reg_data = spl_reg.return_value
#        self.assert_equal(len(reg_data['stock_samples']), 2)
#        self.assert_equal(set([spl.molecule_design_pool.id
#                               for spl in reg_data['stock_samples']]),
#                          set([1066194, 1066195]))


