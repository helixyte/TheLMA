from datetime import datetime

import pytest

from everest.entities.utils import slug_from_string
from everest.repositories.rdb.testing import check_attributes
from everest.repositories.rdb.testing import persist
from thelma.entities.iso import Iso
from thelma.entities.iso import IsoPlate
from thelma.entities.iso import IsoRequest
from thelma.entities.iso import StockRack
from thelma.tests.entity.conftest import TestEntityBase


class Fixtures(object):
    iso_plate1 = lambda plate_fac: plate_fac(label='iso plate 1')
    iso_plate2 = lambda plate_fac: plate_fac(label='iso plate 2')
    iso_plate3 = lambda plate_fac: plate_fac(label='iso plate 3')


class TestIsoRequestEntity(TestEntityBase):
    def test_init_abstract(self):
        with pytest.raises(NotImplementedError):
            IsoRequest('test iso request')


class TestLabIsoRequestEntity(TestEntityBase):
    @pytest.mark.parametrize('kw',
                             [dict(),
                              dict(number_aliquots=2,
                                   owner='stockmanagement',
                                   delivery_date=datetime.now(),
                                   comment='test comment',
                                   process_job_first=False,
                                   )])
    def test_init(self, lab_iso_request_fac, kw):
        _kw = lab_iso_request_fac.init_kw
        _kw.update(kw)
        lir = lab_iso_request_fac(**_kw)
        check_attributes(lir, _kw)
        assert len(lir.isos) == 0

    def test_persist(self, nested_session, lab_iso_request_fac):
        lir = lab_iso_request_fac()
        persist(nested_session, lir, lab_iso_request_fac.init_kw, True)


class TestStockSampleCreationIsoRequestEntity(TestEntityBase):
    def test_init(self, stock_sample_creation_iso_request_fac):
        ssir = stock_sample_creation_iso_request_fac()
        check_attributes(ssir, stock_sample_creation_iso_request_fac.init_kw)

    def test_persist(self, nested_session,
                     stock_sample_creation_iso_request_fac,
                     molecule_design_library_fac):
        ssir1 = stock_sample_creation_iso_request_fac()
        persist(nested_session, ssir1,
                stock_sample_creation_iso_request_fac.init_kw,
                True)
        kw = stock_sample_creation_iso_request_fac.init_kw
        kw['molecule_design_library'] = molecule_design_library_fac()
        ssir = stock_sample_creation_iso_request_fac(**kw)
        persist(nested_session, ssir, kw, True)


class TestIsoEntity(TestEntityBase):
    def test_init_abstract(self):
        with pytest.raises(NotImplementedError):
            Iso('test iso', 4, None)

    @pytest.mark.parametrize('iso_fac_name', ['lab_iso_fac',
                                              'stock_sample_creation_iso_fac'])
    def test_init(self, request, iso_fac_name):
        iso_fac = request.getfuncargvalue(iso_fac_name)
        iso = iso_fac()
        check_attributes(iso, iso_fac.init_kw)
        assert len(iso.iso_stock_racks) == 0
        assert len(iso.iso_sector_stock_racks) == 0
        assert len(iso.iso_preparation_plates) == 0
        assert len(iso.iso_aliquot_plates) == 0
        if iso_fac_name == 'stock_sample_creation_iso_fac':
            assert len(iso.iso_sector_preparation_plates) == 0
        else:
            assert len(iso.final_plates) == 0
        assert iso.slug == slug_from_string(iso.label)

    @pytest.mark.parametrize('iso_fac_name', ['lab_iso_fac',
                                              'stock_sample_creation_iso_fac'])
    def test_persist(self, request, nested_session, iso_fac_name):
        iso_fac = request.getfuncargvalue(iso_fac_name)
        iso = iso_fac()
        persist(nested_session, iso, iso_fac.init_kw, True)

    def test_add_aliquot_plate(self, lab_iso_fac, iso_plate1):
        iso = lab_iso_fac()
        assert len(iso.final_plates) == 0
        assert len(iso.iso_aliquot_plates) == 0
        iso.add_aliquot_plate(iso_plate1)
        assert len(iso.final_plates) == 1
        assert len(iso.iso_aliquot_plates) == 1

    def test_add_preparation_plate(self, lab_iso_fac, iso_plate1,
                                   rack_layout_fac):
        iso = lab_iso_fac()
        assert len(iso.iso_preparation_plates) == 0
        iso.add_preparation_plate(iso_plate1, rack_layout_fac())
        assert len(iso.iso_preparation_plates) == 1

    @pytest.mark.parametrize('iso_fac_name',
                             ['lab_iso_fac',
                              'stock_sample_creation_iso_fac'])
    def test_persist_all_attributes(self, request, nested_session,
                                    iso_fac_name,
                                    iso_job_fac, iso_stock_rack_fac,
                                    iso_sector_stock_rack_fac,
                                    iso_preparation_plate_fac, iso_plate1,
                                    iso_plate2, iso_plate3,
                                    iso_aliquot_plate_fac,
                                    iso_sector_preparation_plate_fac,
                                    rack_layout_fac):
        iso_fac = request.getfuncargvalue(iso_fac_name)
        rl1 = rack_layout_fac.new()
        iso = iso_fac(rack_layout=rl1)
        iso_job = iso_job_fac(isos=[iso])
        assert iso.iso_job.label == iso_job.label
        kw = iso_fac.init_kw
        kw['rack_layout'] = rl1
        iso_stock_rack = iso_stock_rack_fac(iso=iso,
                                            rack_layout=rack_layout_fac.new())
        assert len(iso.iso_stock_racks) == 1
        kw['iso_stock_racks'] = [iso_stock_rack]
        iso_sector_stock_rack = iso_sector_stock_rack_fac(
                                            iso=iso,
                                            rack_layout=rack_layout_fac.new())
        assert len(iso.iso_sector_stock_racks) == 1
        kw['iso_sector_stock_racks'] = [iso_sector_stock_rack]
        iso_preparation_plate = iso_preparation_plate_fac(
                                            iso=iso,
                                            rack=iso_plate1,
                                            rack_layout=rack_layout_fac.new())
        assert len(iso.iso_preparation_plates) == 1
        kw['iso_preparation_plates'] = [iso_preparation_plate]
        iso_aliquot_plate = iso_aliquot_plate_fac(iso=iso,
                                                  rack=iso_plate2)
        assert len(iso.iso_aliquot_plates) == 1
        kw['iso_aliquot_plates'] = [iso_aliquot_plate]
        if iso_fac_name == 'stock_sample_creation_iso_fac':
            iso_sector_prep_plate = iso_sector_preparation_plate_fac(
                                            iso=iso,
                                            rack=iso_plate3,
                                            rack_layout=rack_layout_fac.new())
            assert len(iso.iso_sector_preparation_plates) == 1
            kw['iso_sector_preparation_plates'] = [iso_sector_prep_plate]
        persist(nested_session, iso, kw, True)


class TestLabIsoEntity(TestEntityBase):

    @pytest.mark.parametrize('kw1,kw2,result',
                             [(dict(id=-1), dict(id=-1, label='foo'), False),
                              (dict(id=-1), dict(id=-2), True)])
    def test_equality(self, lab_iso_fac, rack_layout_fac, kw1, kw2, result):
        kw1['rack_layout'] = rack_layout_fac.new()
        li1 = lab_iso_fac(**kw1)
        kw2['rack_layout'] = rack_layout_fac.new()
        li2 = lab_iso_fac(**kw2)
        assert (li1 == li2) is result



class TestStockSampleCreationIsoEntity(TestEntityBase):

    @pytest.mark.parametrize('kw1,kw2,result',
                             [(dict(id=-1), dict(id=-1, layout_number='5'),
                               False),
                              (dict(id=-1), dict(id=-2), True)])
    def test_equality(self, stock_sample_creation_iso_fac, rack_layout_fac,
                      kw1, kw2, result):
        kw1['rack_layout'] = rack_layout_fac.new()
        ssci1 = stock_sample_creation_iso_fac(**kw1)
        kw2['rack_layout'] = rack_layout_fac.new()
        ssci2 = stock_sample_creation_iso_fac(**kw2)
        assert (ssci1 == ssci2) is result


class TestStockRackEntity(TestEntityBase):

    def test_init_abstract(self):
        with pytest.raises(NotImplementedError):
            StockRack('test stock rack', None, None, None)

    @pytest.mark.parametrize('stock_rack_fac_name',
                             ['iso_job_stock_rack_fac',
                              'iso_stock_rack_fac',
                              'iso_sector_stock_rack_fac'])
    def test_init(self, request, stock_rack_fac_name):
        stock_rack_fac = request.getfuncargvalue(stock_rack_fac_name)
        sr = stock_rack_fac()
        check_attributes(sr, stock_rack_fac.init_kw)

    @pytest.mark.parametrize('stock_rack_fac_name',
                             ['iso_job_stock_rack_fac',
                              'iso_stock_rack_fac',
                              'iso_sector_stock_rack_fac'])
    def test_persist(self, request, nested_session, stock_rack_fac_name):
        stock_rack_fac = request.getfuncargvalue(stock_rack_fac_name)
        sr = stock_rack_fac()
        persist(nested_session, sr, stock_rack_fac.init_kw, True)


class TestIsoPlateEntity(TestEntityBase):
    # TODO: Do we need to add equality tests here?

    def test_init_abstract(self):
        with pytest.raises(NotImplementedError):
            IsoPlate(None, None)

    @pytest.mark.parametrize('iso_plate_fac_name',
                             ['iso_preparation_plate_fac',
                              'iso_sector_preparation_plate_fac',
                              'iso_aliquot_plate_fac',
                              'iso_job_preparation_plate_fac'
                              ])
    def test_init(self, request, iso_plate_fac_name):
        iso_plate_fac = request.getfuncargvalue(iso_plate_fac_name)
        ip = iso_plate_fac()
        check_attributes(ip, iso_plate_fac.init_kw)

    @pytest.mark.parametrize('iso_plate_fac_name',
                             ['iso_preparation_plate_fac',
                              'iso_sector_preparation_plate_fac',
                              'iso_aliquot_plate_fac',
                              'iso_job_preparation_plate_fac'
                              ])
    def test_persist(self, request, nested_session, iso_plate_fac_name):
        iso_plate_fac = request.getfuncargvalue(iso_plate_fac_name)
        ip = iso_plate_fac()
        persist(nested_session, ip, iso_plate_fac.init_kw, True)
