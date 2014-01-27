"""
Created on May 25, 2011

@author: berger
"""

from everest.repositories.rdb.testing import RdbContextManager
from everest.repositories.rdb.testing import check_attributes
from thelma.interfaces import IItemStatus
from thelma.models.container import WellSpecs
from thelma.models.rack import Plate
from thelma.models.rack import PlateSpecs
from thelma.models.rack import Rack
from thelma.models.rack import RackPosition
from thelma.models.rack import RackPositionSet
from thelma.models.rack import RackShape
from thelma.models.rack import RackSpecs
from thelma.models.rack import TubeRack
from thelma.models.rack import TubeRackSpecs
from thelma.models.rack import rack_shape_from_rows_columns
from thelma.models.status import ItemStatus
from thelma.testing import ThelmaModelTestCase
from everest.repositories.rdb.testing import persist
from thelma.interfaces import IRackPosition
from thelma.interfaces import IRackPositionSet
from thelma.models.status import ITEM_STATUSES
from everest.repositories.rdb.utils import as_slug_expression
from thelma.interfaces import IOrganization


class RackModelTest(ThelmaModelTestCase):

    def __get_data(self):
        plate_specs = self._create_plate_specs()
        status = self._get_entity(IItemStatus,
                                  as_slug_expression(ITEM_STATUSES.MANAGED))
        return dict(label='testrack', specs=plate_specs, status=status)

    def test_init(self):
        attrs = self.__get_data()
        self.assert_raises(NotImplementedError, Rack, **attrs)

    def test_load_100_racks(self):
        with RdbContextManager() as session:
            query = session.query(Rack)
            racks = query.limit(100).all()
            self.assert_equal(len(racks), 100)

    def test_create_rack(self):
        with RdbContextManager() as session:
            specs = session.query(RackSpecs).filter_by(name='STD96').one()
            status = session.query(ItemStatus).filter_by(id='MANAGED').one()
            attrs = dict(label='myfancyrack',
                         specs=specs,
                         status=status,
                         comment='mycomment')
            persist(session, Plate, attrs)

    def test_load_rack_with_wells_and_samples(self):
        with RdbContextManager() as session:
            query = session.query(Rack)
            rack = query.filter_by(barcode='02494292').one()
            self.assert_equal(len(rack.containers), 384)
            self.assert_true(
                all([cont.sample.sample_molecules[0].concentration == 2.5e-6
                     for cont in rack.containers
                     if not cont.sample is None]))

    def test_loopkup_by_position(self):
        with RdbContextManager() as session:
            query = session.query(Rack)
            rack = query.filter_by(barcode='02494292').one()
            pos = RackPosition.from_indices(1, 1)
            location = rack.container_locations[pos]
            self.assert_equal(location.position.row_index, 1)
            self.assert_equal(location.position.column_index, 1)


class TubeRackModelTest(ThelmaModelTestCase):

    model_cls = TubeRack

    def __get_data(self):
        label = 'tube_rack_label'
        comment = 'a comment'
        status = self._get_entity(IItemStatus,
                                  as_slug_expression(ITEM_STATUSES.MANAGED))
        specs = self._create_tube_rack_specs()
        return dict(label=label, specs=specs, status=status, comment=comment)

    def __create_entity(self, attrs=None):
        if attrs is None:
            attrs = self.__get_data()
        return self.model_cls(**attrs)

    def test_init(self):
        kw = self.__get_data()
        tube_rack = self.__create_entity(kw)
        check_attributes(tube_rack, kw)
        self.assert_is_none(tube_rack.slug)
        self.assert_is_none(tube_rack.barcode)
        self.assert_is_none(tube_rack.location)
        self.assert_equal(len(tube_rack.containers), 0)
        self.assert_is_not_none(tube_rack.creation_date)

    def test_location(self):
        loc = self._create_location()
        loc.id = 2
        rack = self.__create_entity()
        rack.location = loc
        self.assert_equal(rack.location, loc)

    def test_equality(self):
        id1 = 1
        id2 = 2
        attrs = self.__get_data()
        tube_rack1 = self.__create_entity(attrs)
        tube_rack1.id = id1
        tube_rack2 = self.__create_entity(attrs)
        tube_rack2.id = id2
        ori_label = attrs['label']
        attrs['label'] = 'another_label'
        tube_rack3 = self.__create_entity(attrs)
        tube_rack3.id = id1
        attrs['label'] = ori_label
        ori_specs = attrs['specs']
        attrs['specs'] = None
        tube_rack4 = self.__create_entity(attrs)
        tube_rack4.id = id1
        attrs['specs'] = ori_specs
        attrs['status'] = self._get_entity(IItemStatus,
                                as_slug_expression(ITEM_STATUSES.DESTROYED))
        tube_rack5 = self.__create_entity(attrs)
        tube_rack5.id = id1
        self.assert_not_equal(tube_rack1, tube_rack2)
        self.assert_equal(tube_rack1, tube_rack3)
        self.assert_equal(tube_rack1, tube_rack4)
        self.assert_equal(tube_rack1, tube_rack5)
        self.assert_not_equal(tube_rack1, id1)


class PlateModelTest(ThelmaModelTestCase):

    model_cls = Plate

    def __get_data(self):
        label = 'plate_label'
        comment = 'another comment'
        status = self._get_entity(IItemStatus,
                                  as_slug_expression(ITEM_STATUSES.MANAGED))
        specs = self._create_plate_specs()
        return dict(label=label, comment=comment, status=status, specs=specs)

    def __create_entity(self, attrs=None):
        if attrs is None:
            attrs = self.__get_data()
        return self.model_cls(**attrs)

    def test_init(self):
        attrs = self.__get_data()
        plate = self.__create_entity(attrs)
        self.assert_is_not_none(plate)
        check_attributes(plate, attrs)
        self.assert_is_none(plate.slug)
        self.assert_is_none(plate.location)
        self.assert_is_none(plate.barcode)
        self.assert_equal(len(plate.containers), 96)

    def test_equality(self):
        id1 = 1
        id2 = 2
        attrs = self.__get_data()
        plate1 = self.__create_entity(attrs)
        plate1.id = id1
        plate2 = self.__create_entity(attrs)
        plate2.id = id2
        ori_label = attrs['label']
        attrs['label'] = 'another_lavel'
        plate3 = self.__create_entity(attrs)
        plate3.id = id1
        attrs['label'] = ori_label
        ori_specs = attrs['specs']
        attrs['specs'] = None
        plate4 = self.__create_entity(attrs)
        plate4.id = id1
        attrs['specs'] = ori_specs
        attrs['status'] = self._get_entity(IItemStatus,
                                as_slug_expression(ITEM_STATUSES.DESTROYED))
        plate5 = self.__create_entity(attrs)
        plate5.id = id1
        self.assert_not_equal(plate1, plate2)
        self.assert_equal(plate1, plate3)
        self.assert_equal(plate1, plate4)
        self.assert_equal(plate1, plate5)
        self.assert_not_equal(plate1, id1)


class RackSpecModelTest(ThelmaModelTestCase):

    def test_rack_specs_init(self):
        shape = rack_shape_from_rows_columns(8, 12)
        rack_specs_attribute = ('a_name', 'a_label', shape)
        self.assert_raises(NotImplementedError, RackSpecs,
                           * rack_specs_attribute)

class TubeRackSpecsModelTest(ThelmaModelTestCase):

    model_cls = TubeRackSpecs

    def __get_data(self):
        label = 'Matrix 96 tube rack (0.75 ml)'
        shape = rack_shape_from_rows_columns(8, 12)
        manufacturer = self._get_entity(IOrganization)
        return dict(label=label, shape=shape, manufacturer=manufacturer)

    def __create_entity(self, attrs=None):
        if attrs is None:
            attrs = self.__get_data()
        return self.model_cls(**attrs)

    def test_init(self):
        attrs = self.__get_data()
        tube_rs = self.__create_entity(attrs)
        self.assert_is_not_none(tube_rs)
        check_attributes(tube_rs, attrs)
        self.assert_equal(len(tube_rs.tube_specs), 0)
        self.assert_true(tube_rs.has_tubes)

    def test_equality(self):
        id1 = 1
        id2 = 2
        attrs = self.__get_data()
        tube_rs1 = self.__create_entity(attrs)
        tube_rs1.id = id1
        tube_rs2 = self.__create_entity(attrs)
        tube_rs2.id = id2
        tube_rs3 = self.__create_entity(attrs)
        tube_rs3.id = id1
        ori_label = attrs['label']
        attrs['label'] = 'other_label'
        tube_rs4 = self.__create_entity(attrs)
        tube_rs4.id = id1
        attrs['label'] = ori_label
        attrs['shape'] = rack_shape_from_rows_columns(16, 24)
        tube_rs5 = self.__create_entity(attrs)
        tube_rs5.id = id1
        self.assert_not_equal(tube_rs1, tube_rs2)
        self.assert_equal(tube_rs1, tube_rs3)
        self.assert_equal(tube_rs1, tube_rs4)
        self.assert_equal(tube_rs1, tube_rs5)
        self.assert_not_equal(tube_rs1, id1)


class PlateSpecsModelTest(ThelmaModelTestCase):

    model_cls = PlateSpecs

    def __get_data(self):
        label = 'Nunc 384 clear'
        manufacturer = self._get_entity(IOrganization)
        shape = rack_shape_from_rows_columns(16, 24)
        well_specs = self._create_well_specs()
        return dict(label=label, shape=shape, well_specs=well_specs,
                    manufacturer=manufacturer)

    def __create_entity(self, attrs=None):
        if attrs is None:
            attrs = self.__get_data()
        return self.model_cls(**attrs)

    def test_init(self):
        attrs = self.__get_data()
        plate_specs = self.__create_entity(attrs)
        self.assert_is_not_none(plate_specs)
        check_attributes(plate_specs, attrs)
        self.assert_false(plate_specs.has_tubes)

    def test_equality(self):
        id1 = 1
        id2 = 2
        attrs = self.__get_data()
        plate_rs1 = self.__create_entity(attrs)
        plate_rs1.id = id1
        plate_rs2 = self.__create_entity(attrs)
        plate_rs2.id = id2
        plate_rs3 = self.__create_entity(attrs)
        plate_rs3.id = id1
        ori_label = attrs['label']
        attrs['label'] = 'other_label'
        plate_rs4 = self.__create_entity(attrs)
        plate_rs4.id = id1
        attrs['label'] = ori_label
        ori_shape = attrs['shape']
        attrs['shape'] = rack_shape_from_rows_columns(8, 16)
        plate_rs5 = self.__create_entity(attrs)
        plate_rs5.id = id1
        attrs['shape'] = ori_shape
        attrs['well_specs'] = WellSpecs('wellspecs', 100, 15, None)
        plate_rs6 = self.__create_entity(attrs)
        plate_rs6.id = id1
        self.assert_not_equal(plate_rs1, plate_rs2)
        self.assert_equal(plate_rs1, plate_rs3)
        self.assert_equal(plate_rs1, plate_rs4)
        self.assert_equal(plate_rs1, plate_rs5)
        self.assert_equal(plate_rs1, plate_rs6)
        self.assert_not_equal(plate_rs1, id1)


class RackShapeModelTest(ThelmaModelTestCase):

    model_cls = RackShape

    def __get_data(self):
        name = '8x12'
        label = name
        row_number = 8
        column_number = 12
        return dict(name=name, label=label, number_rows=row_number,
                    number_columns=column_number)

    def __create_entity(self, attrs=None):
        if attrs is None:
            attrs = self.__get_data()
        return self.model_cls(**attrs)

    def test_rack_shape_init(self):
        kw = self.__get_data()
        rack_shape = self.__create_entity(kw)
        self.assert_is_not_none(rack_shape)
        check_attributes(rack_shape, kw)
        self.assert_equal(rack_shape.size, 96)

    def test_equality(self):
        kw = self.__get_data()
        rack_shape1 = self.__create_entity(kw)
        ori_name = kw['name']
        kw['name'] = 'other name'
        rack_shape2 = self.__create_entity(kw)
        kw['name'] = ori_name
        ori_label = kw['label']
        kw['label'] = 'other label'
        rack_shape3 = self.__create_entity(kw)
        kw['label'] = ori_label
        ori_rows = kw['number_rows']
        kw['number_rows'] = ori_rows * 2
        rack_shape4 = self.__create_entity(kw)
        kw['number_rows'] = ori_rows
        kw['number_columns'] = kw['number_columns'] * 2
        rack_shape5 = RackShape(**kw)
        self.assert_not_equal(rack_shape1, rack_shape2)
        self.assert_equal(rack_shape1, rack_shape3)
        self.assert_equal(rack_shape1, rack_shape4)
        self.assert_equal(rack_shape1, rack_shape5)
        self.assert_not_equal(rack_shape1, kw['name'])

    def test_factory(self):
        kw = self.__get_data()
        rs_direct = self.__create_entity(kw)
        rs_factory = rack_shape_from_rows_columns(kw['number_rows'],
                                                  kw['number_columns'])
        self.assert_equal(rs_direct, rs_factory)

    def test_contains_position(self):
        rack_shape = self.__create_entity()
        a1_pos = RackPosition.from_label('A1')
        self.assert_true(rack_shape.contains_position(a1_pos))
        h13_pos = RackPosition.from_label('H13')
        self.assert_false(rack_shape.contains_position(h13_pos))


class RackPositionModelTest(ThelmaModelTestCase):

    def __get_data(self):
        row_index = 2
        column_index = 3
        label = 'C4'
        return dict(label=label, row_index=row_index,
                    column_index=column_index)

    def test_attributes(self):
        attrs = self.__get_data()
        rack_position = self._get_entity(IRackPosition,
                                         attrs['label'].lower())
        self.assert_is_not_none(rack_position)
        check_attributes(rack_position, attrs)
        self.assert_is_not_none(rack_position.id)

    def test_immutablity(self):
        attrs = self.__get_data()
        rack_pos = self._get_entity(IRackPosition, attrs['label'])
        self.assert_raises(AttributeError, setattr, *(rack_pos, 'label', 'A2'))
        self.assert_raises(AttributeError, setattr, *(rack_pos, 'row_index', 3))
        self.assert_raises(AttributeError, setattr,
                           *(rack_pos, 'column_index', 3))

    def test_fetcher_methods(self):
        attrs = self.__get_data()
        pos1 = RackPosition.from_label(attrs['label'])
        check_attributes(pos1, attrs)
        pos2 = RackPosition.from_indices(attrs['row_index'],
                                         attrs['column_index'])
        check_attributes(pos2, attrs)
        pos3 = RackPosition.from_row_column(row=attrs['label'][0],
                                            column=int(attrs['label'][1]))
        check_attributes(pos3, attrs)

    def test_equality(self):
        pos1 = RackPosition.from_label('A1')
        pos2 = RackPosition.from_label('A1')
        pos3 = RackPosition.from_label('B1')
        pos4 = RackPosition.from_label('A2')
        self.assert_equal(pos1, pos2)
        self.assert_not_equal(pos1, pos3)
        self.assert_not_equal(pos1, pos4)
        self.assert_not_equal(pos1, 'A1')


class RackPositionSetModelTest(ThelmaModelTestCase):
    """
    Also tests the hash value encoding.
    """

    def __get_data(self):
        positions = set([RackPosition.from_indices(pos[0], pos[1])
                         for pos in [(0, 1), (0, 2), (1, 0), (1, 1), (1, 3)]])
        hash_value = '01421_2'
        return dict(positions=positions, hash_value=hash_value)

    def test_load(self):
        # load existing from the DB
        attrs = dict(positions=set([RackPosition.from_label('A1')]),
                     hash_value='1_1')
        rps = self._get_entity(IRackPositionSet, attrs['hash_value'])
        self.assert_is_not_none(rps)
        check_attributes(rps, attrs)
        self.assert_is_not_none(rps.id)

    def test_factory_method(self):
        # creates a new RackPositionSet (none in the DB for this hash value)
        attrs = self.__get_data()
        rps = RackPositionSet.from_positions(attrs['positions'])
        self.assert_is_not_none(rps)
        check_attributes(rps, attrs)
        self.assert_is_none(rps.id)

    def test_immutability(self):
        attrs = self.__get_data()
        rps = RackPositionSet.from_positions(attrs['positions'])
        self.assert_raises(AttributeError, setattr, *(rps, 'positions',
                           set([RackPosition.from_label('A1')])))
        self.assert_raises(AttributeError, setattr, *(rps, 'hash_value', '1_1'))

    def test_equality(self):
        attrs = self.__get_data()
        rps1 = RackPositionSet.from_positions(attrs['positions'])
        rps2 = RackPositionSet.from_positions(attrs['positions'])
        attrs = dict(positions=set([RackPosition.from_label('A1')]))
        rps3 = RackPositionSet.from_positions(attrs['positions'])
        self.assert_equal(rps1, rps2)
        self.assert_not_equal(rps1, rps3)
        rp = RackPosition.from_label('A1')
        self.assert_not_equal(rps1, rp)

    def test_decoder_startwith_tag(self):
        # + A1
        attrs = self.__get_data()
        attrs['positions'].add(RackPosition.from_label('A1'))
        rps = RackPositionSet.from_positions(attrs['positions'])
        self.assert_equal('521_2', rps.hash_value)

    def test_1536_set(self):
        # + AF47
        attrs = self.__get_data()
        attrs['positions'].add(RackPosition.from_indices(31, 46))
        rps = RackPositionSet.from_positions(attrs['positions'])
        self.assert_equal('011u2u1w1-mF1_32', rps.hash_value)
