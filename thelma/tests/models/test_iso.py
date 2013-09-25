"""
Created on Jun 28, 2011

@author: berger
"""

from datetime import datetime
from everest.testing import RdbContextManager
from everest.testing import check_attributes
from everest.testing import persist
from thelma.interfaces import IIso
from thelma.interfaces import IPlate
from thelma.interfaces import IReservoirSpecs
from thelma.interfaces import ITubeRack
from thelma.interfaces import IUser
from thelma.models.iso import ISO_STATUS
from thelma.models.iso import Iso
from thelma.models.iso import IsoAliquotPlate
from thelma.models.iso import IsoJobStockRack
from thelma.models.iso import IsoPreparationPlate
from thelma.models.iso import IsoRequest
from thelma.models.iso import IsoSectorPreparationPlate
from thelma.models.iso import IsoSectorStockRack
from thelma.models.iso import IsoStockRack
from thelma.models.iso import LabIso
from thelma.models.iso import LabIsoRequest
from thelma.models.iso import StockRack
from thelma.models.iso import StockSampleCreationIso
from thelma.models.iso import StockSampleCreationIsoRequest
from thelma.testing import ThelmaEntityTestCase
from thelma.models.rack import Plate
from thelma.models.iso import IsoJobPreparationPlate


class IsoRequestModelTestCase(ThelmaEntityTestCase):

    def _get_data(self):
        label = 'my_iso_request_label'
        expected_number_isos = 3
        number_aliquots = 2
        owner = 'stockmanagment'
        return dict(label=label,
                    expected_number_isos=expected_number_isos,
                    number_aliquots=number_aliquots,
                    owner=owner)


class IsoRequestBaseClassModelTestCase(IsoRequestModelTestCase):

    model_class = IsoRequest

    def test_init(self):
        self._test_init(abstract_class=True)


class LabIsoRequestModelTestCase(IsoRequestModelTestCase):

    model_class = LabIsoRequest

    def _get_data(self):
        kw = IsoRequestModelTestCase._get_data(self)
        kw['requester'] = self._get_entity(IUser, 'it')
        kw['delivery_date'] = datetime.now()
        kw['rack_layout'] = self._create_rack_layout()
        kw['comment'] = 'a comment'
        kw['iso_plate_reservoir_specs'] = self._get_entity(IReservoirSpecs)
        kw['process_job_first'] = False
        return kw

    def test_init(self):
        attrs = self._get_data()
        lir1 = self._create_lab_iso_request(label=attrs['label'],
                                            requester=attrs['requester'],
                                            rack_layout=attrs['rack_layout'])
        self.assert_is_not_none(lir1)
        exp_attrs1 = dict(label=attrs['label'], requester=attrs['requester'],
                      rack_layout=attrs['rack_layout'], isos=[],
                      delivery_date=None, experiment_metadata=None,
                      comment=None, owner='',
                      iso_plate_reservoir_specs=\
                                            attrs['iso_plate_reservoir_specs'],
                      expected_number_isos=1,
                      worklist_series=None, number_aliquots=1,
                      molecule_design_pool_set=None,
                      process_job_first=True)
        check_attributes(lir1, exp_attrs1)
        del lir1.rack_layout # otherwise we get problems with the ORM
        lir2 = self._create_lab_iso_request(**attrs)
        self.assert_is_not_none(lir2)
        check_attributes(lir2, attrs)
        self.assert_equal(len(lir2.isos), 0)

    def test_equality(self):
        self._test_id_based_equality(self._create_lab_iso_request,
                   self._create_stock_sample_creation_iso_request)

    def test_load(self):
        self._test_load()

    def test_persist(self):
        # do not use super class method
        with RdbContextManager() as session:
            attrs = self._get_data()
            del attrs['delivery_date']
            persist(session, self.model_class, attrs, True)


class StockSampleCreationIsoRequestModelTestCase(IsoRequestModelTestCase):

    model_class = StockSampleCreationIsoRequest

    def _get_data(self):
        kw = IsoRequestModelTestCase._get_data(self)
        kw['number_designs'] = 4
        kw['stock_volume'] = 0.0001 # 100 ul
        kw['stock_concentration'] = 0.0001 # 100 uM
        return kw

    def test_init(self):
        self._test_init()

    def test_equality(self):
        self._test_id_based_equality(
                self._create_stock_sample_creation_iso_request,
                self._create_lab_iso_request)

    def test_load(self):
        self._test_load()

    def test_persist(self):
        self._test_persist()

    def test_persist_with_library(self):
        with RdbContextManager() as session:
            attrs = self._get_data()
            attrs['molecule_design_library'] = \
                                        self._create_molecule_design_library()
            persist(session, self.model_class, attrs, True)


class IsoModelTestCase(ThelmaEntityTestCase):

    def _get_data(self):
        label = 'iso_label'
        status = ISO_STATUS.IN_PROGRESS
        pool_set = self._create_molecule_design_pool_set()
        rack_layout = self._create_rack_layout()
        number_stock_racks = 2
        return dict(label=label, molecule_design_pool_set=pool_set,
                    status=status, rack_layout=rack_layout,
                    number_stock_racks=number_stock_racks)


class IsoBaseClassModelTestCase(IsoModelTestCase):

    model_class = Iso

    def test_init(self):
        self._test_init(abstract_class=True)


class LabIsoModelTestCase(IsoModelTestCase):

    model_class = LabIso

    def _get_data(self):
        kw = IsoModelTestCase._get_data(self)
        kw['iso_request'] = self._create_lab_iso_request()
        return kw

    def test_init(self):
        li = self._test_init()
        self.assert_equal(len(li.iso_stock_racks), 0)
        self.assert_equal(len(li.iso_sector_stock_racks), 0)
        self.assert_equal(len(li.iso_preparation_plates), 0)
        self.assert_equal(len(li.iso_aliquot_plates), 0)
        self.assert_equal(len(li.final_plates), 0)

    def test_slug(self):
        attrs = self._get_data()
        label = 'a normal ISO'
        attrs['label'] = label
        label_slug = 'a-normal-iso'
        li = self._create_lab_iso(**attrs)
        self.assert_not_equal(li.slug, label)
        self.assert_equal(li.slug, label_slug)

    def test_equality(self):
        label1 = 'l1'
        label2 = 'l2'
        ir1 = self._create_lab_iso_request()
        ir2 = self._create_lab_iso_request()
        ir2.id = -8
        id1 = -1
        id2 = -2
        iso1 = self._create_lab_iso(label=label1, iso_request=ir1, id=id1)
        iso2 = self._create_lab_iso(label=label1, iso_request=ir1, id=id2)
        iso3 = self._create_lab_iso(label=label2, iso_request=ir1, id=id1)
        iso4 = self._create_lab_iso(label=label1, iso_request=ir2, id=id1)
        self.assert_equal(iso1, iso2)
        self.assert_not_equal(iso1, iso3)
        self.assert_not_equal(iso1, iso4)
        self.assert_not_equal(iso1, id1)
        ssci = self._create_stock_sample_creation_iso(id=id1)
        self.assert_not_equal(iso1, ssci)

    def test_add_aliquot_plates(self):
        li = self._create_lab_iso(**self._get_data())
        plate = self._create_plate()
        self.assert_equal(len(li.final_plates), 0)
        self.assert_equal(len(li.iso_aliquot_plates), 0)
        li.add_aliquot_plate(plate)
        self.assert_equal(len(li.final_plates), 1)
        self.assert_equal(len(li.iso_aliquot_plates), 1)

    def test_add_preparation_plate(self):
        li = self._create_lab_iso(**self._get_data())
        rack_layout = self._create_rack_layout()
        plate = self._create_plate()
        self.assert_equal(len(li.iso_preparation_plates), 0)
        li.add_preparation_plate(plate, rack_layout)
        self.assert_equal(len(li.iso_preparation_plates), 1)

    def test_load(self):
        self._test_load()

    def test_persist(self):
        self._test_persist()

    def test_persist_all_attributes(self):
        with RdbContextManager() as session:
            attrs = self._get_data()
            iso = self._create_lab_iso(**attrs)
            iso_job = self._create_iso_job(isos=[iso])
            self.assert_equal(iso.iso_job.label, iso_job.label)
            iso_stock_rack = self._create_iso_stock_rack(iso=iso)
            self.assert_equal(len(iso.iso_stock_racks), 1)
            iso_sector_stock_rack = self._create_iso_sector_stock_rack(iso=iso)
            self.assert_equal(len(iso.iso_sector_stock_racks), 1)
            query = session.query(Plate)
            plates = query.limit(2).all()
            iso_preparation_plate = self._create_iso_preparation_plate(iso=iso,
                                                               rack=plates[0])
            self.assert_equal(len(iso.iso_preparation_plates), 1)
            iso_aliquot_plate = self._create_iso_aliquot_plate(iso=iso,
                                                        rack=plates[1])
            self.assert_equal(len(iso.iso_aliquot_plates), 1)
            session.add(iso)
            session.commit()
            session.refresh(iso)
            iso_id = iso.id
            session.expunge(iso)
            del iso
            query = session.query(self.model_class)
            fetched_iso = query.filter_by(id=iso_id).one()
            check_attributes(fetched_iso, attrs)
            self.assert_equal(fetched_iso.iso_job.label, iso_job.label)
            self.assert_equal(fetched_iso.iso_stock_racks, [iso_stock_rack])
            self.assert_equal(fetched_iso.iso_sector_stock_racks,
                              [iso_sector_stock_rack])
            self.assert_equal(fetched_iso.iso_preparation_plates,
                              [iso_preparation_plate])
            self.assert_equal(fetched_iso.iso_aliquot_plates,
                              [iso_aliquot_plate])


class StockSampleCreationIsoModelTestCase(IsoModelTestCase):

    model_class = StockSampleCreationIso

    def _get_data(self):
        kw = IsoModelTestCase._get_data(self)
        kw['ticket_number'] = 9876
        kw['layout_number'] = 6
        kw['iso_request'] = self._create_stock_sample_creation_iso_request()
        return kw

    def test_init(self):
        ssci = self._test_init()
        self.assert_equal(len(ssci.iso_stock_racks), 0)
        self.assert_equal(len(ssci.iso_sector_stock_racks), 0)
        self.assert_equal(len(ssci.iso_preparation_plates), 0)
        self.assert_equal(0, len(ssci.iso_sector_preparation_plates))
        self.assert_equal(len(ssci.iso_aliquot_plates), 0)

    def test_slug(self):
        attrs = self._get_data()
        label = 'a normal ISO'
        attrs['label'] = label
        label_slug = 'a-normal-iso'
        ssci = self._create_stock_sample_creation_iso(**attrs)
        self.assert_not_equal(ssci.slug, label)
        self.assert_equal(ssci.slug, label_slug)

    def test_equality(self):
        label1 = 'l1'
        label2 = 'l2'
        ir1 = self._create_stock_sample_creation_iso_request()
        ir2 = self._create_stock_sample_creation_iso_request()
        ir2.id = -8
        id1 = -1
        id2 = -2
        layout_number1 = 4
        layout_number2 = 5
        iso1 = self._create_stock_sample_creation_iso(label=label1,
                          iso_request=ir1, layout_number=layout_number1, id=id1)
        iso2 = self._create_stock_sample_creation_iso(label=label1,
                          iso_request=ir1, layout_number=layout_number1, id=id2)
        iso3 = self._create_stock_sample_creation_iso(label=label2,
                          iso_request=ir1, layout_number=layout_number1, id=id1)
        iso4 = self._create_stock_sample_creation_iso(label=label1,
                          iso_request=ir2, layout_number=layout_number1, id=id1)
        iso5 = self._create_stock_sample_creation_iso(label=label1,
                          iso_request=ir1, layout_number=layout_number2, id=id1)
        self.assert_equal(iso1, iso2)
        self.assert_not_equal(iso1, iso3)
        self.assert_not_equal(iso1, iso4)
        self.assert_not_equal(iso1, iso5)
        self.assert_not_equal(iso1, id1)
        li = self._create_lab_iso(id=id1)
        self.assert_not_equal(iso1, li)

    def test_load(self):
        self._test_load()

    def test_persist(self):
        self._test_persist()

    def test_persist_all_attributes(self):
        with RdbContextManager() as session:
            attrs = self._get_data()
            iso = self._create_stock_sample_creation_iso(**attrs)
            iso_job = self._create_iso_job(isos=[iso])
            self.assert_equal(iso.iso_job.label, iso_job.label)
            iso_stock_rack = self._create_iso_stock_rack(iso=iso)
            self.assert_equal(len(iso.iso_stock_racks), 1)
            iso_sector_stock_rack = self._create_iso_sector_stock_rack(iso=iso)
            self.assert_equal(len(iso.iso_sector_stock_racks), 1)
            query = session.query(Plate)
            plates = query.limit(3).all()
            iso_preparation_plate = self._create_iso_preparation_plate(iso=iso,
                                                               rack=plates[0])
            self.assert_equal(len(iso.iso_preparation_plates), 1)
            iso_sector_prep_plate = self._create_iso_sector_preparation_plate(
                                                        iso=iso, rack=plates[1])
            self.assert_equal(len(iso.iso_sector_preparation_plates), 1)
            iso_aliquot_plate = self._create_iso_aliquot_plate(iso=iso,
                                                        rack=plates[2])
            self.assert_equal(len(iso.iso_aliquot_plates), 1)
            session.add(iso)
            session.commit()
            session.refresh(iso)
            iso_id = iso.id
            session.expunge(iso)
            del iso
            query = session.query(self.model_class)
            fetched_iso = query.filter_by(id=iso_id).one()
            check_attributes(fetched_iso, attrs)
            self.assert_equal(fetched_iso.iso_job.label, iso_job.label)
            self.assert_equal(fetched_iso.iso_stock_racks, [iso_stock_rack])
            self.assert_equal(fetched_iso.iso_sector_stock_racks,
                              [iso_sector_stock_rack])
            self.assert_equal(fetched_iso.iso_preparation_plates,
                              [iso_preparation_plate])
            self.assert_equal(fetched_iso.iso_sector_preparation_plates,
                              [iso_sector_prep_plate])
            self.assert_equal(fetched_iso.iso_aliquot_plates,
                              [iso_aliquot_plate])


class StockRackModelTestCase(ThelmaEntityTestCase):

    def _get_data(self):
        label = 'sr_label'
        rack = self._get_entity(ITubeRack)
        rack_layout = self._create_rack_layout()
        worklist_series = self._create_worklist_series()
        return dict(rack=rack, rack_layout=rack_layout, label=label,
                    worklist_series=worklist_series)


class StockRackBaseClassModelTestCase(StockRackModelTestCase):

    model_class = StockRack

    def test_init(self):
        self._test_init(abstract_class=True)


class IsoJobStockRackModelTest(StockRackModelTestCase):

    model_class = IsoJobStockRack

    def _get_data(self):
        kw = StockRackModelTestCase._get_data(self)
        kw['iso_job'] = self._create_iso_job()
        return kw

    def test_init(self):
        self._test_init()

    def test_equality(self):
        self._test_id_based_equality(self._create_iso_job_stock_rack,
                                     self._create_iso_stock_rack)

    def test_load(self):
        self._test_load()

    def test_persist(self):
        self._test_persist()


class IsoStockRackModelTest(StockRackModelTestCase):

    model_class = IsoStockRack

    def _get_data(self):
        kw = StockRackModelTestCase._get_data(self)
        kw['iso'] = self._get_entity(IIso)
        return kw

    def test_init(self):
        self._test_init()

    def test_equality(self):
        self._test_id_based_equality(self._create_iso_stock_rack)

        # TODO: activate as soon there are some records in the DB
#    def test_load(self):
#        self._test_load()

    def test_persist(self):
        self._test_persist()


class IsoSectorStockRackModelTestCase(StockRackModelTestCase):

    model_class = IsoSectorStockRack

    def _get_data(self):
        kw = StockRackModelTestCase._get_data(self)
        kw['iso'] = self._get_entity(IIso)
        kw['sector_index'] = 2
        return kw

    def test_init(self):
        self._test_init()

    def test_equality(self):
        self._test_id_based_equality(self._create_iso_sector_stock_rack)

    def x_test_load(self):
        self._test_load()

    def test_persist(self):
        self._test_persist()


class IsoPlateModelTestCase(ThelmaEntityTestCase):

    def _get_data(self):
        rack = self._get_entity(IPlate)
        return dict(rack=rack)


class IsoPlateBaseClassModelTestCase(IsoPlateModelTestCase):

    def test_init(self):
        attrs = self._get_data()
        attrs['iso'] = self._create_stock_sample_creation_iso()
        self._test_init(attrs, abstract_class=True)


class IsoPreparationPlateModelTest(IsoPlateModelTestCase):

    model_class = IsoPreparationPlate

    def _get_data(self):
        kw = IsoPlateModelTestCase._get_data(self)
        iso_request = self._create_lab_iso_request()
        kw['iso'] = self._create_lab_iso(iso_request=iso_request)
        kw['rack_layout'] = self._create_rack_layout()
        return kw

    def test_init(self):
        self._test_init()

    def test_equality(self):
        iso1 = self._create_lab_iso(label='iso1')
        iso2 = self._create_lab_iso(label='iso2')
        plate1 = self._create_plate(id= -1)
        plate2 = self._create_plate(id= -2)
        ipp1 = self._create_iso_preparation_plate(iso=iso1, rack=plate1)
        ipp2 = self._create_iso_preparation_plate(iso=iso1, rack=plate1)
        ipp3 = self._create_iso_preparation_plate(iso=iso2, rack=plate1)
        ipp4 = self._create_iso_preparation_plate(iso=iso1, rack=plate2)
        self.assert_equal(ipp1, ipp2)
        self.assert_not_equal(ipp1, ipp3)
        self.assert_not_equal(ipp1, ipp4)
        self.assert_not_equal(ipp1, iso1)

    def test_load(self):
        self._test_load()

    def test_persist(self):
        self._test_persist()


class IsoSectorPreparationPlateModelTestCase(IsoPlateModelTestCase):

    model_class = IsoSectorPreparationPlate

    def _get_data(self):
        kw = IsoPlateModelTestCase._get_data(self)
        iso_request = self._create_stock_sample_creation_iso_request()
        kw['iso'] = self._create_stock_sample_creation_iso(
                                                    iso_request=iso_request)
        kw['rack_layout'] = self._create_rack_layout()
        kw['sector_index'] = 3
        return kw

    def test_init(self):
        self._test_init()

    def test_equality(self):
        iso1 = self._create_stock_sample_creation_iso(label='iso1')
        iso2 = self._create_stock_sample_creation_iso(label='iso2')
        plate1 = self._create_plate(id= -1)
        plate2 = self._create_plate(id= -2)
        sector1 = 1
        sector2 = 2
        ispp1 = self._create_iso_sector_preparation_plate(iso=iso1, rack=plate1,
                                                         sector_index=sector1)
        ispp2 = self._create_iso_sector_preparation_plate(iso=iso1, rack=plate1,
                                                         sector_index=sector1)
        ispp3 = self._create_iso_sector_preparation_plate(iso=iso2, rack=plate1,
                                                         sector_index=sector1)
        ispp4 = self._create_iso_sector_preparation_plate(iso=iso1, rack=plate2,
                                                         sector_index=sector1)
        ispp5 = self._create_iso_sector_preparation_plate(iso=iso1, rack=plate1,
                                                         sector_index=sector2)
        self.assert_equal(ispp1, ispp2)
        self.assert_not_equal(ispp1, ispp3)
        self.assert_not_equal(ispp1, ispp4)
        self.assert_not_equal(ispp1, ispp5)
        self.assert_not_equal(ispp1, iso1)

    def test_load(self):
        self._test_load()

    def test_persist(self):
        self._test_persist()


class IsoAliquotPlateModelTest(IsoPlateModelTestCase):

    model_class = IsoAliquotPlate

    def _get_data(self):
        kw = IsoPlateModelTestCase._get_data(self)
        iso_request = self._create_lab_iso_request()
        kw['iso'] = self._create_lab_iso(iso_request=iso_request)
        kw['has_been_used'] = True
        return kw

    def test_init(self):
        self._test_init()

    def test_equality(self):
        iso1 = self._create_lab_iso(label='iso1')
        iso2 = self._create_lab_iso(label='iso2')
        plate1 = self._create_plate(id= -1)
        plate2 = self._create_plate(id= -2)
        iap1 = self._create_iso_aliquot_plate(iso=iso1, rack=plate1)
        iap2 = self._create_iso_aliquot_plate(iso=iso1, rack=plate1)
        iap3 = self._create_iso_aliquot_plate(iso=iso2, rack=plate1)
        iap4 = self._create_iso_aliquot_plate(iso=iso1, rack=plate2)
        self.assert_equal(iap1, iap2)
        self.assert_not_equal(iap1, iap3)
        self.assert_not_equal(iap1, iap4)
        self.assert_not_equal(iap1, iso1)

    def test_load(self):
        self._test_load()

    def test_persist(self):
        self._test_persist()


class IsoJobPreparationPlateModelTest(ThelmaEntityTestCase):

    model_class = IsoJobPreparationPlate

    def _get_data(self):
        iso_job = self._create_iso_job(label='modeltestjob')
        rack = self._create_plate()
        rack_layout = self._create_rack_layout()
        return dict(iso_job=iso_job, rack=rack, rack_layout=rack_layout)

    def test_init(self):
        self._test_init()

    def test_equality(self):
        ij1 = self._create_iso_job(id= -1)
        ij2 = self._create_iso_job(id= -2)
        plate1 = self._create_plate(id= -3)
        plate2 = self._create_plate(id= -4)
        ijpp1 = self._create_iso_job_preparation_plate(iso_job=ij1, rack=plate1)
        ijpp2 = self._create_iso_job_preparation_plate(iso_job=ij1, rack=plate1)
        ijpp3 = self._create_iso_job_preparation_plate(iso_job=ij2, rack=plate1)
        ijpp4 = self._create_iso_job_preparation_plate(iso_job=ij1, rack=plate2)
        self.assert_equal(ijpp1, ijpp2)
        self.assert_not_equal(ijpp1, ijpp3)
        self.assert_not_equal(ijpp1, ijpp4)
        self.assert_not_equal(ijpp1, ij1)

        # TODO: activate as soon there are some records in the DB
#    def test_load(self):
#        self._test_load()

    def test_persist(self):
        self._test_persist()
