'''
Created on May 26, 2011

@author: berger
'''

from everest.repositories.rdb.testing import RdbContextManager
from everest.repositories.rdb.testing import check_attributes
from thelma.interfaces import IItemStatus
from thelma.models.device import Device
from thelma.models.location import BarcodedLocation
from thelma.models.location import BarcodedLocationType
from thelma.testing import ThelmaModelTestCase


class BarcodedLocationModelTest(ThelmaModelTestCase):

    model_class = BarcodedLocation

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.name = 'Drawer1_4'
        self.label = '#4'
        self.barcode = '2368377'
        self.bl_type = BarcodedLocationType('drawer')
        self.index = 4
        self.device = self._create_device()
        self.device.id = 1

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.name
        del self.label
        del self.bl_type
        del self.index
        del self.device

    def test_barcoded_location_init(self):
        bl = BarcodedLocation(self.name, self.label, self.bl_type,
                              self.barcode, self.device, self.index)
        self.assert_not_equal(bl, None)
        attributes = dict(name=self.name,
                          label=self.label,
                          barcode=self.barcode,
                          type=self.bl_type,
                          device=self.device,
                          index=self.index)
        for attr_name, wanted_value in attributes.iteritems():
            self.assert_equal(getattr(bl, attr_name), wanted_value)
        self.assert_false(bl.slug is None)
        self.assert_true(bl.id is None)
        self.assert_true(bl.rack is None)

    def test_barcoded_location_slug(self):
        name = 'L1 4'
        name_slug = 'l1-4'
        bl = BarcodedLocation(name, self.label, self.bl_type, self.barcode)
        self.assert_not_equal(bl.slug, name)
        self.assert_equal(bl.slug, name_slug)

    def test_barcoded_location_equality(self):
        id1 = 1
        id2 = 2
        bl1 = BarcodedLocation(self.name, self.label,
                               self.bl_type, self.barcode)
        bl1.id = id1
        bl2 = BarcodedLocation(self.name, self.label,
                               self.bl_type, self.barcode)
        bl2.id = id2
        bl3 = BarcodedLocation(self.name, self.label,
                               self.bl_type, self.barcode)
        bl3.id = id1
        bl4 = BarcodedLocation(self.name, 'another_label',
                               self.bl_type, self.barcode)
        bl4.id = id1
        other_type = BarcodedLocationType('freezer')
        bl5 = BarcodedLocation(self.name, self.label,
                               other_type, self.barcode)
        bl5.id = id1
        self.assert_not_equal(bl1, bl2)
        self.assert_equal(bl1, bl3)
        self.assert_equal(bl1, bl4)
        self.assert_equal(bl1, bl5)
        self.assert_not_equal(bl1, id1)

    def test_load_10_barcoded_locations(self):
        with RdbContextManager() as session:
            query = session.query(self.model_class)
            bls = query.limit(10).all()
            self.assert_equal(len(bls), 10)

    def test_barcoded_location_values(self):
        with RdbContextManager() as session:
            bl = session.query(self.model_class).filter_by(id=78).one()
            blt = session.query(BarcodedLocationType) \
                                              .filter_by(name='robot').one()
            d = session.query(Device).filter_by(id=2).one()
            attributes = dict(id=78,
                              name='GENESIS1_C6',
                              slug='genesis1-c6',
                              label='C6',
                              barcode='02373383',
                              device=d,
                              index=6,
                              )
            check_attributes(bl, attributes)
            #FIXME: Fix barcoded location type mapper.
            self.assert_equal(d.locations[0].type, blt.name)

    def test_checkin_checkout_rack(self):
        mg_status = self._get_entity(IItemStatus, 'managed')
        rack = self._create_tube_rack(status=mg_status)
        tube = self._create_tube(status=mg_status)
        spl = tube.make_sample(100e-6)
        spl_mol = spl.make_sample_molecule(self._create_molecule(), 5e-5)
        rack.containers.append(tube)
        self.assert_is_none(spl_mol.checkout_date)


class BarcodedLocationTypeModelTest(ThelmaModelTestCase):

    model_class = BarcodedLocationType

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.name = 'drawer'

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.name

    def test_barcoded_location_type_init(self):
        blt = BarcodedLocationType(self.name)
        self.assert_not_equal(blt, None)
        self.assert_equal(blt.name, self.name)
        self.assert_not_equal(blt.name, None)

    def test_barcoded_location_type_slug(self):
        name = 'Freezing Drawer'
        name_slug = 'freezing-drawer'
        blt = BarcodedLocationType(name)
        self.assert_not_equal(blt.slug, name)
        self.assert_equal(blt.slug, name_slug)

    def test_barcoded_location_type_equality(self):
        blt1 = BarcodedLocationType(self.name)
        blt2 = BarcodedLocationType(self.name)
        blt3 = BarcodedLocationType('freezer')
        self.assert_equal(blt1, blt2)
        self.assert_not_equal(blt1, blt3)
        self.assert_not_equal(blt1, self.name)

    def test_load_4_barcoded_location_types(self):
        with RdbContextManager() as session:
            query = session.query(self.model_class)
            blt = query.limit(4).all()
            self.assert_equal(len(blt), 4)

    def test_barcoded_location_type_values(self):
        with RdbContextManager() as session:
            blt = \
              session.query(self.model_class).filter_by(name='f_drawer').one()
            attributes = dict(name='f_drawer',
                              slug='f-drawer')
            check_attributes(blt, attributes)
