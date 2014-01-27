"""
Created on May 26, 2011

@author: berger
"""
from everest.repositories.rdb.testing import RdbContextManager
from everest.repositories.rdb.testing import check_attributes
from thelma.interfaces import IContainerSpecs
from thelma.interfaces import IItemStatus
from thelma.interfaces import IOrganization
from thelma.interfaces import IRackPosition
from thelma.interfaces import ITubeSpecs
from thelma.models.container import Container
from thelma.models.container import ContainerSpecs
from thelma.models.container import Tube
from thelma.models.container import TubeSpecs
from thelma.models.container import Well
from thelma.models.container import WellSpecs
from thelma.models.rack import RackPosition
from thelma.models.status import ITEM_STATUSES
from thelma.testing import ThelmaModelTestCase


class ContainerThelmaModelTestCase(ThelmaModelTestCase):

    def test_init_fails(self):
        status = self._get_entity(IItemStatus, ITEM_STATUSES.DESTROYED)
        position = RackPosition.from_indices(1, 1)
        specs = self._get_entity(IContainerSpecs)
        location = self._create_container_location(position=position)
        kw = dict(status=status, location=location, specs=specs)
        self.assert_raises(NotImplementedError, Container, **kw)


class TubeThelmaModelTestCase(ThelmaModelTestCase):

    model_cls = Tube

    def __get_data(self):
        status = self._get_entity(IItemStatus, ITEM_STATUSES.DESTROYED)
        position = RackPosition.from_indices(1, 1)
        specs = self._create_tube_specs()
        location = self._create_container_location(position=position)
        barcode = '1019999999'
        return dict(status=status, location=location, specs=specs,
                    barcode=barcode)

    def __create_entity(self, attrs=None):
        if attrs == None:
            attrs = self.__get_data()
        return self.model_cls(**attrs)

    def test_init_floating(self):
        attrs = self.__get_data()
        attrs['location'] = None
        tube = self.__create_entity(attrs)
        self.assert_is_not_none(tube)
        check_attributes(tube, attrs)
        self.assert_is_not_none(tube.slug)

    def test_init_from_rack_and_position(self):
        attrs = self.__get_data()
        attrs['rack'] = self._create_tube_rack()
        attrs['position'] = RackPosition.from_label('A3')
        del attrs['location']
        tube = Tube.create_from_rack_and_position(**attrs)
        del attrs['rack']
        self.assert_is_not_none(attrs)
        check_attributes(tube, attrs)
        self.assert_is_not_none(tube.slug)
        self.assert_equal(tube.position, attrs['position'])

    def test_init_from_rack_and_invalid_position(self):
        attrs = self.__get_data()
        attrs['rack'] = self._create_tube_rack()
        del attrs['location']
        attrs['position'] = RackPosition.from_label('I1')
        self.assert_raises(ValueError, Tube.create_from_rack_and_position,
                           **attrs)
        attrs['position'] = RackPosition.from_label('A13')
        self.assert_raises(ValueError, Tube.create_from_rack_and_position,
                           **attrs)

    def test_equality(self):
        tube1 = self._create_tube(id=1)
        tube2 = self._create_tube(id=2)
        tube3 = self._create_tube()
        tube3.id = tube2.id
        tube3.barcode = 'other'
        self.assert_not_equal(tube1, tube2)
        self.assert_equal(tube2, tube3)


class WellThelmaModelTestCase(ThelmaModelTestCase):

    def __get_data(self):
        status = self._get_entity(IItemStatus, ITEM_STATUSES.DESTROYED)
        specs = self._create_well_specs()
        rack = self._create_plate()
        position = RackPosition.from_label('A1')
        return dict(status=status, specs=specs, rack=rack, position=position)

    def test_init(self):
        attrs = self.__get_data()
        well = Well.create_from_rack_and_position(**attrs)
        self.assert_is_not_none(well)
        self.assert_equal(well.location.rack.barcode, attrs['rack'].barcode)
        del attrs['rack']
        self.assert_equal(well.location.position, attrs['position'])
        del attrs['position']
        check_attributes(well, attrs)
        self.assert_equal(well.slug, well.location.position.label)

    def test_equality(self):
        c1 = RackPosition.from_label('C1')
        d1 = RackPosition.from_label('D1')
        rack = self._create_plate()
        well1 = self._create_well(id=-1, position=c1, rack=rack)
        well2 = self._create_well(id=-2, position=d1, rack=rack)
        well3 = self._create_well()
        well3.id = well2.id
        self.assert_not_equal(well1, well2)
        self.assert_equal(well2, well3)


class ContainerSpecsThelmaModelTestCase(ThelmaModelTestCase):

    def test_init_fails(self):
        attrs = dict(max_volume=0.00075, dead_volume=1e-05,
                     manufacturer=self._get_entity(IOrganization),
                     description='more info', label='test_specs')
        self.assert_raises(NotImplementedError, ContainerSpecs, **attrs)


class TubeSpecsThelmaModelTestCase(ThelmaModelTestCase):

    model_cls = TubeSpecs

    def __get_data(self):
        return dict(max_volume=0.00075, dead_volume=1e-05,
                     manufacturer=self._get_entity(IOrganization),
                     description='more info', label='my tube specs',
                     tube_rack_specs=[self._create_tube_rack_specs()])

    def __create_entity(self, attrs=None):
        if attrs is None:
            attrs = self.__get_data()
        return self.model_cls(**attrs)

    def test_init(self):
        attrs = self.__get_data()
        tube_specs = self.__create_entity(attrs)
        self.assert_is_not_none(tube_specs)
        check_attributes(tube_specs, attrs)

    def test_equality(self):
        tube_specs1 = self._create_tube_specs(id=-1, label='ts1')
        tube_specs2 = self._create_tube_specs(id=-2, label='ts2')
        tube_specs3 = self._create_tube_specs()
        tube_specs3.id = tube_specs2.id
        self.assert_not_equal(tube_specs1, tube_specs2)
        self.assert_equal(tube_specs2, tube_specs3)

    def test_tube_specs_tube_factory(self):
        status = self._get_entity(IItemStatus, key='managed')
        tube_specs = self.__create_entity()
        # Need status *and* barcode.
        self.assert_raises(TypeError, tube_specs.create_tube, status)
        barcode = '1111111111'
        tube = tube_specs.create_tube(status, barcode)
        self.assert_false(tube is None)
        attributes = dict(specs=tube_specs,
                          status=status,
                          barcode=barcode)
        check_attributes(tube, attributes)


class WellSpecsModelTest(ThelmaModelTestCase):

    model_cls = WellSpecs

    def __get_data(self):
        return dict(max_volume=0.00075, dead_volume=1e-05,
                     manufacturer=self._get_entity(IOrganization),
                     description='more info', label='my well specs',
                     plate_specs=self._create_plate_specs(well_specs=None))

    def __create_entity(self, attrs=None):
        if attrs is None:
            attrs = self.__get_data()
        return self.model_cls(**attrs)

    def test_init(self):
        attrs = self.__get_data()
        well_specs = self.__create_entity(attrs)
        self.assert_is_not_none(well_specs)
        check_attributes(well_specs, attrs)

    def test_equality(self):
        attrs = self.__get_data()
        well_specs1 = self._create_well_specs(id=-1,
                                              plate_specs=attrs['plate_specs'])
        well_specs2 = self._create_well_specs(id=-2,
                                              plate_specs=attrs['plate_specs'])
        well_specs3 = self.__create_entity(attrs)
        well_specs3.id = well_specs2.id
        self.assert_not_equal(well_specs1, well_specs2)
        self.assert_equal(well_specs2, well_specs3)


class ContainerLocationTestCase(ThelmaModelTestCase):

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.position = RackPosition.from_indices(1, 3)
        self.tube = self._create_tube(location=None)
        self.rack = self._create_tube_rack()
        self.init_data = dict(rack=self.rack,
                              position=self.position,
                              container=self.tube)

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.position
        del self.tube
        del self.rack
        del self.init_data

    def test_init(self):
        cl = self._create_container_location(**self.init_data)
        self.assert_is_not_none(cl)
        check_attributes(cl, self.init_data)

    def test_equality(self):
        rack = self._create_tube_rack()
        pos = self._get_entity(IRackPosition)
        cl1 = self._create_container_location(rack=rack, position=pos)
        cl2 = self._create_container_location(rack=rack, position=pos)
        cl3 = self._create_container_location(**self.init_data)
        self.assert_equal(cl1, cl2)
        self.assert_not_equal(cl2, cl3)

    def test_move_tube(self):
        with RdbContextManager() as session:
            rack = self._create_tube_rack()
            tube = Tube.create_from_rack_and_position(
                        specs=self._get_entity(ITubeSpecs, key='matrix0500'),
                        status=self._get_entity(IItemStatus, key='managed'),
                        barcode='0111111111',
                        rack=rack,
                        position=self.position)
            self.assert_true(tube.location.position is self.position)
            self.assert_true(tube.location.rack is rack)
            self.assert_true(tube.location.container is tube)
            self.assert_true(
                    rack.container_locations[self.position].container
                    is tube)
            #
            empty_position = RackPosition.from_indices(0, 0)
            new_position = RackPosition.from_indices(0, 3)
            # Move within same rack.
            rack.move_tube(self.position, new_position)
            session.flush()
            self.assert_true(tube.location.position is new_position)
            # Move to other rack.
            new_rack = self._create_tube_rack(label='TestDestTubeRack')
            rack.remove_tube(tube)
            # Removing again raises error.
            self.assert_raises(ValueError, rack.remove_tube, tube)
            #
            new_rack.add_tube(tube, new_position)
            # Adding again raises error.
            self.assert_raises(ValueError, rack.add_tube, tube,
                               empty_position)
            session.flush()
            self.assert_true(tube.location.rack is new_rack)
            # Moving from empty position raises ValueError.
            self.assert_raises(
                            ValueError,
                            new_rack.move_tube, empty_position, new_position)
            # Moving to occupied position raises ValueError.
            self.assert_raises(
                            ValueError,
                            new_rack.move_tube, new_position, new_position)
