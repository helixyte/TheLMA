import pytest

from everest.repositories.rdb.testing import check_attributes
from everest.repositories.rdb.testing import persist
from thelma.entities.rack import Rack
from thelma.entities.rack import RackPosition
from thelma.entities.rack import RackSpecs
from thelma.tests.entity.conftest import TestEntityBase


class Fixtures(object):
    rpos_0_0 = lambda rack_position_fac: rack_position_fac(row_index=0,
                                                           column_index=0)
    rpos_0_1 = lambda rack_position_fac: rack_position_fac(row_index=0,
                                                           column_index=1)
    rpos_0_2 = lambda rack_position_fac: rack_position_fac(row_index=0,
                                                           column_index=2)
    rpos_1_0 = lambda rack_position_fac: rack_position_fac(row_index=1,
                                                           column_index=0)
    rpos_1_1 = lambda rack_position_fac: rack_position_fac(row_index=1,
                                                           column_index=1)
    rpos_1_3 = lambda rack_position_fac: rack_position_fac(row_index=1,
                                                           column_index=3)
    rpos_31_46 = lambda rack_position_fac: rack_position_fac(row_index=31,
                                                           column_index=46)
    rack_positions = \
            lambda rpos_0_1, rpos_0_2, rpos_1_0, rpos_1_1, rpos_1_3: \
                set([rpos_0_1, rpos_0_2, rpos_1_0, rpos_1_1, rpos_1_3])


class TestRackEntity(TestEntityBase):
    def test_abstract(self):
        with pytest.raises(NotImplementedError):
            Rack('test rack', None, None)

    @pytest.mark.parametrize('fac_name,specs_fac_name',
                             [('plate_fac', 'plate_specs_std96'),
                              ('tube_rack_fac', 'tube_rack_specs_matrix'),
                              ])
    def test_init(self, request, fac_name, specs_fac_name, rack_position_fac):
        specs = request.getfuncargvalue(specs_fac_name)
        fac = request.getfuncargvalue(fac_name)
        kw = fac.init_kw
        kw['specs'] = specs
        rack = fac(**kw)
        check_attributes(rack, kw)
        if fac_name == 'plate_fac':
            assert len(rack.containers) == 96
            pos = rack_position_fac(row_index=5, column_index=5)
            location = rack.container_locations[pos]
            assert location.position.row_index == 5
            assert location.position.column_index == 5
            assert location.rack is rack
        else:
            assert len(rack.containers) == 0

    @pytest.mark.parametrize('fac_name',
                             ['plate_fac',
                              'tube_rack_fac',
                              ])
    def test_persist(self, request, nested_session, fac_name):
        fac = request.getfuncargvalue(fac_name)
        rack = fac()
        persist(nested_session, rack, fac.init_kw, True)


class TestRackSpecsEntity(TestEntityBase):
    def test_abstract(self):
        with pytest.raises(NotImplementedError):
            RackSpecs('test rack specs', None)

    @pytest.mark.parametrize('fac_name',
                             ['plate_specs_fac',
                              'tube_rack_specs_fac',
                              ])
    def test_init(self, request, fac_name):
        fac = request.getfuncargvalue(fac_name)
        rs = fac()
        check_attributes(rs, fac.init_kw)
        if fac_name == 'plate_specs_fac':
            assert not rs.has_tubes
        else:
            assert rs.has_tubes
            assert len(rs.tube_specs) == 0

    @pytest.mark.parametrize('fac_name',
                             ['plate_specs_fac',
                              'tube_specs_fac',
                              ])
    def test_persist(self, request, nested_session, fac_name):
        fac = request.getfuncargvalue(fac_name)
        rack = fac()
        persist(nested_session, rack, fac.init_kw, True)


class TestRackShapeEntity(TestEntityBase):

    def test_init(self, rack_shape_fac):
        kw = rack_shape_fac.init_kw
        kw['number_rows'] = 8
        kw['number_columns'] = 12
        rs = rack_shape_fac(**kw)
        check_attributes(rs, kw)
        assert rs.size == 96

    def test_persist(self, nested_session, rack_shape_fac):
        kw = rack_shape_fac.init_kw
        kw['number_rows'] = 12
        kw['number_columns'] = 8
        rs = rack_shape_fac(**kw)
        persist(nested_session, rs, kw, True)

    def test_contains_position(self, rack_shape_fac, rack_position_fac):
        rs = rack_shape_fac(number_rows=8, number_columns=12)
        pos_a1 = rack_position_fac(row_index=0, column_index=0)
        assert rs.contains_position(pos_a1)
        pos_h13 = rack_position_fac(row_index=7, column_index=12)
        assert not rs.contains_position(pos_h13)


class TestRackPosition(TestEntityBase):

    def test_init(self, rack_position_fac):
        rp = rack_position_fac()
        check_attributes(rp, rack_position_fac.init_kw)

    def test_immutablity(self, rack_position_fac):
        rack_pos = rack_position_fac()
        with pytest.raises(AttributeError):
            setattr(rack_pos, 'label', 'A2')
        with pytest.raises(AttributeError):
            setattr(rack_pos, 'row_index', 3)
        with pytest.raises(AttributeError):
            setattr(rack_pos, 'column_index', 3)

    def test_fetcher_methods(self, rack_position_fac):
        rack_pos = rack_position_fac()
        assert rack_pos == RackPosition.from_label(rack_pos.label)
        assert rack_pos == RackPosition.from_indices(rack_pos.row_index,
                                                     rack_pos.column_index)
        assert rack_pos == \
            RackPosition.from_row_column(rack_pos.label[0],
                                         int(rack_pos.label[1]))


class TestRackPositionSetEntity(TestEntityBase):
    def test_init(self, rack_position_set_fac, rpos_0_0):
        kw = rack_position_set_fac.init_kw
        kw['positions'] = set([rpos_0_0])
        rps = rack_position_set_fac(**kw)
        check_attributes(rps, kw)
        assert rps.hash_value == '1_1'

    def test_persist(self, nested_session, rack_position_set_fac):
        rps = rack_position_set_fac()
        persist(nested_session, rps, rack_position_set_fac.init_kw, True)

    def test_immutability(self, rack_position_set_fac, rpos_0_1):
        rps = rack_position_set_fac()
        with pytest.raises(AttributeError):
            setattr(rps, 'positions', set([rpos_0_1]))
        with pytest.raises(AttributeError):
            setattr(rps, 'hash_value', '1_1')

    def test_decoder(self, rack_position_set_fac, rack_positions, rpos_0_0,
                     rpos_31_46):
        # + A1
        rack_positions.add(rpos_0_0)
        rps = rack_position_set_fac(positions=rack_positions)
        assert rps.hash_value == '521_2'
        # + AF47
        rack_positions.remove(rpos_0_0)
        rack_positions.add(rpos_31_46)
        rps = rack_position_set_fac(positions=rack_positions.copy())
        assert rps.hash_value == '011u2u1w1-mF1_32'
