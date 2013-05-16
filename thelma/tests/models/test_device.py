"""
Created on May 25, 2011

@author: berger
"""

from everest.testing import check_attributes
from thelma.testing import ThelmaModelTestCase

class DeviceModelTest(ThelmaModelTestCase):

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.init_data = dict(name="MYDEVICE",
                              label='My Device',
                              model='SuperModel',
                              type=self._create_device_type(),
                              manufacturer=self._create_organization())

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.init_data

    def test_init(self):
        device = self._create_device(**self.init_data)
        self.assert_false(device is None)
        check_attributes(device, self.init_data)
        self.assert_false(device.slug is None)
        self.assert_true(len(device.locations) == 0)

    def test_equality(self):
        device1 = self._create_device(id=1)
        device2 = self._create_device(id=2)
        device3 = self._create_device(**self.init_data)
        device3.id = device2.id
        self.assert_not_equal(device1, device2)
        self.assert_equal(device2, device3)


class DeviceTypeModelTest(ThelmaModelTestCase):

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.init_data = dict(name="MYDEVICETYPE",
                              label='My Device Type')

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.init_data

    def test_init(self):
        dev_type = self._create_device_type(**self.init_data)
        self.assert_false(dev_type is None)
        check_attributes(dev_type, self.init_data)
        self.assert_false(dev_type.slug is None)
        self.assert_equal(len(dev_type.devices), 0)

    def test_equality(self):
        dev_type1 = self._create_device_type(id=1)
        dev_type2 = self._create_device_type(id=2)
        dev_type3 = self._create_device_type(**self.init_data)
        dev_type3.id = dev_type2.id
        self.assert_not_equal(dev_type1, dev_type2)
        self.assert_equal(dev_type2, dev_type3)
