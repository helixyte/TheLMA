from everest.repositories.rdb.testing import check_attributes
from thelma.tests.entity.conftest import TestEntityBase
from everest.repositories.rdb.testing import persist


class TestDeviceEntity(TestEntityBase):

    def test_init(self, device_fac):
        device = device_fac()
        check_attributes(device, device_fac.init_kw)
        assert not device.slug is None
        assert len(device.locations) == 0

    def test_persist(self, nested_session, device_fac):
        device = device_fac()
        persist(nested_session, device, device_fac.init_kw, True)


class TestDeviceTypeEntity(TestEntityBase):

    def test_init(self, device_type_fac):
        dev_type = device_type_fac()
        check_attributes(dev_type, device_type_fac.init_kw)
        assert not dev_type.slug is None
        assert len(dev_type.devices) == 0

    def test_persist(self, nested_session, device_type_fac):
        dev_type = device_type_fac()
        persist(nested_session, dev_type, device_type_fac.init_kw, True)
