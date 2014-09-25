import pytest

from everest.repositories.rdb.testing import check_attributes
from thelma.models.container import Container
from thelma.models.container import ContainerLocation
from thelma.models.container import ContainerSpecs
from thelma.models.container import Tube
from thelma.models.container import TubeSpecs
from thelma.models.container import Well
from thelma.models.container import WellSpecs
from thelma.tests.entity.conftest import TestEntityBase


class Fixtures(object):
    rack_position11 = lambda rack_position_fac: \
                            rack_position_fac(row_index=1, column_index=1)
    tube_rack = lambda tube_rack_fac: tube_rack_fac()
    plate = lambda plate_fac: plate_fac()
    tube_specs = lambda tube_specs_fac: tube_specs_fac()
    well_specs = lambda well_specs_fac: well_specs_fac()
    manufacturer = lambda organization_fac: organization_fac()


class TestContainerEntity(TestEntityBase):

    def test_init_abstract(self, item_status_destroyed, tube_specs):
        kw = dict(status=item_status_destroyed,
                  specs=tube_specs,
                  location=None)
        with pytest.raises(NotImplementedError):
            Container(**kw)


class TestTubeEntity(TestEntityBase):

    def test_init_floating(self, tube_fac):
        tube = tube_fac()
        check_attributes(tube, tube_fac.init_kw)
        assert not tube.slug is None

    def test_init_from_rack_and_position(self, tube_fac,
                                         tube_rack, rack_position11):
        kw = tube_fac.init_kw
        kw['rack'] = tube_rack
        kw['position'] = rack_position11
        tube = Tube.create_from_rack_and_position(**kw)
        check_attributes(tube, kw)
        assert not tube.slug is None
        assert tube.position == kw['position']

    def test_init_from_rack_and_invalid_position(self, tube_fac,
                                                 tube_rack,
                                                 rack_position_fac):
        kw = tube_fac.init_kw
        kw['rack'] = tube_rack
        kw['position'] = rack_position_fac(row_index=0, column_index=12)
        with pytest.raises(ValueError):
            Tube.create_from_rack_and_position(**kw)
        kw['position'] = rack_position_fac(row_index=8, column_index=0)
        with pytest.raises(ValueError):
            Tube.create_from_rack_and_position(**kw)

    @pytest.mark.parametrize('kw1,kw2,result',
                             [(dict(id=-1), dict(id=-1, barcode='0'), True),
                              (dict(id=-1), dict(id=-2), False)])
    def test_equality(self, tube_fac, kw1, kw2, result):
        tube1 = tube_fac(**kw1)
        tube2 = tube_fac(**kw2)
        assert (tube1 == tube2) is result


class TestWellEntity(TestEntityBase):

    def test_init(self, well_fac):
        kw = well_fac.init_kw
        well = Well.create_from_rack_and_position(**kw)
        assert well.location.rack.barcode == kw['rack'].barcode
        assert well.location.position == kw['position']
        check_attributes(well, kw)
        assert well.slug == well.location.position.label

    def test_equality(self, well_fac, rack_position_fac):
        kw = well_fac.init_kw
        c1 = rack_position_fac(row_index=2, column_index=0)
        kw['id'] = 1
        kw['position'] = c1
        well1 = Well.create_from_rack_and_position(**kw)
        d1 = rack_position_fac(row_index=3, column_index=0)
        kw['id'] = 2
        kw['position'] = d1
        well2 = Well.create_from_rack_and_position(**kw)
        well3 = Well.create_from_rack_and_position(**kw)
        well3.id = well2.id
        assert well1 != well2
        assert well2 == well3


class TestContainerSpecsEntity(TestEntityBase):

    def test_init_abstract(self):
        kw = dict(label='test container specs',
                  max_volume=1e-4,
                  dead_volume=5e-6)
        with pytest.raises(NotImplementedError):
            ContainerSpecs(**kw)


class TestTubeSpecsEntity(TestEntityBase):

    def test_init(self, tube_specs_fac):
        kw = tube_specs_fac.init_kw
        tube_specs = TubeSpecs(**kw)
        check_attributes(tube_specs, kw)

    def test_equality(self, tube_specs_fac):
        tube_specs1 = tube_specs_fac(id=-1, label='ts1')
        tube_specs2 = tube_specs_fac(id=-2, label='ts2')
        tube_specs3 = tube_specs_fac(id=-2)
        assert tube_specs1 != tube_specs2
        assert tube_specs2 == tube_specs3

    def test_tube_specs_tube_factory(self, tube_specs, item_status_managed):
        # Need status *and* barcode.
        with pytest.raises(TypeError):
            tube_specs.create_tube(item_status_managed)
        barcode = '1111111111'
        tube = tube_specs.create_tube(item_status_managed, barcode)
        attributes = dict(specs=tube_specs,
                          status=item_status_managed,
                          barcode=barcode)
        check_attributes(tube, attributes)


class TestWellSpecsEntity(TestEntityBase):

    def test_init(self, well_specs_fac):
        kw = well_specs_fac.init_kw
        well_specs = WellSpecs(**kw)
        check_attributes(well_specs, kw)

    def test_equality(self, well_specs_fac):
        well_specs1 = well_specs_fac(id=-1)
        well_specs2 = well_specs_fac(id=-2)
        well_specs3 = well_specs_fac()
        well_specs3.id = well_specs2.id
        assert well_specs1 != well_specs2
        assert well_specs2 == well_specs3


class TestContainerLocationEntity(TestEntityBase):

    def test_init(self, container_location_fac):
        kw = container_location_fac.init_kw
        cl = ContainerLocation(**kw)
        check_attributes(cl, kw)

    def test_equality(self, container_location_fac, tube_rack,
                      rack_position11):
        cl1 = container_location_fac(rack=tube_rack, position=rack_position11)
        cl2 = container_location_fac(rack=tube_rack, position=rack_position11)
        cl3 = container_location_fac()
        assert cl1 == cl2
        assert cl2 != cl3

    def test_move_tube(self, tube_rack, item_status_managed,
                       tube_specs_matrix, rack_position11, rack_position_fac,
                       tube_rack_fac):
        tube = Tube.create_from_rack_and_position(
                    specs=tube_specs_matrix,
                    status=item_status_managed,
                    barcode='0111111111',
                    rack=tube_rack,
                    position=rack_position11)
        assert tube.location.position is rack_position11
        assert tube.location.rack is tube_rack
        assert tube.location.container is tube
        assert tube_rack.container_locations[rack_position11].container \
               is tube
        #
        empty_position = rack_position_fac(row_index=0, column_index=0)
        new_position = rack_position_fac(row_index=0, column_index=3)
        # Move within same rack.
        tube_rack.move_tube(rack_position11, new_position)
        assert tube.location.position is new_position
        # Move to other rack.
        new_rack = tube_rack_fac(label='TestDestTubeRack')
        tube_rack.remove_tube(tube)
        # Removing again raises error.
        with pytest.raises(ValueError):
            tube_rack.remove_tube(tube)
        new_rack.add_tube(tube, new_position)
        # Adding again raises error.
        with pytest.raises(ValueError):
            tube_rack.add_tube(tube, empty_position)
        assert tube.location.rack is new_rack
        # Moving from empty position raises ValueError.
        with pytest.raises(ValueError):
            new_rack.move_tube(empty_position, new_position)
        # Moving to occupied position raises ValueError.
        with pytest.raises(ValueError):
            new_rack.move_tube(new_position, new_position)
