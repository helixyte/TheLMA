"""
Created on Jun 28, 2011

@author: berger
"""

from datetime import datetime
from everest.testing import RdbContextManager
from everest.testing import check_attributes
from everest.testing import persist
from thelma.interfaces import IIso
from thelma.interfaces import IIsoRequest
from thelma.interfaces import IPlate
from thelma.interfaces import IUser
from thelma.models.iso import Iso
from thelma.models.iso import IsoAliquotPlate
from thelma.models.iso import IsoControlStockRack
from thelma.models.iso import IsoPreparationPlate
from thelma.models.iso import IsoRequest
from thelma.models.iso import IsoSampleStockRack
from thelma.testing import ThelmaModelTestCase
from thelma.interfaces import ITubeRack


class IsoModelTest(ThelmaModelTestCase):

    model_class = Iso

    def __get_data(self):
        label = 'iso_label'
        status = 'in progress'
        iso_request = self._get_entity(IIsoRequest)
        pool_set = self._create_molecule_design_pool_set()
        rack_layout = self._create_rack_layout()
        return dict(label=label, iso_request=iso_request,
                    molecule_design_pool_set=pool_set,
                    status=status, rack_layout=rack_layout)

    def test_init(self):
        attrs = self.__get_data()
        iso1 = Iso(label=attrs['label'], iso_request=attrs['iso_request'])
        self.assert_false(iso1 is None)
        attr1 = dict(label=attrs['label'],
                     iso_request=attrs['iso_request'],
                     molecule_design_pool_set=None,
                     status=Iso.DEFAULT_STATUS)
        check_attributes(iso1, attr1)
        self.assert_is_not_none(iso1.slug)
        self.assert_is_none(iso1.iso_job)
        self.assert_is_none(iso1.iso_preparation_plate)
        self.assert_equal(len(iso1.iso_sample_stock_racks), 0)
        self.assert_equal(len(iso1.iso_aliquot_plates), 0)
        iso2 = Iso(**attrs)
        check_attributes(iso2, attrs)
        self.assert_is_not_none(iso2.slug)
        self.assert_is_none(iso2.iso_job)
        self.assert_is_none(iso2.iso_preparation_plate)
        self.assert_equal(len(iso2.iso_sample_stock_racks), 0)
        self.assert_equal(len(iso2.iso_aliquot_plates), 0)

    def test_slug(self):
        iso_request = self._create_iso_request()
        label = 'a normal ISO'
        label_slug = 'a-normal-iso'
        iso = Iso(label, iso_request)
        self.assert_not_equal(iso.slug, label)
        self.assert_equal(iso.slug, label_slug)

    def test_equality(self):
        label1 = 'iso_label_1'
        label2 = 'iso_label_2'
        iso_request1 = self._create_iso_request()
        iso_request2 = self._create_iso_request()
        iso_request2.id = -8
        id1 = -1
        id2 = -2
        iso1 = self._create_iso(label=label1, iso_request=iso_request1, id=id1)
        iso2 = self._create_iso(label=label1, iso_request=iso_request1, id=id2)
        iso3 = self._create_iso(label=label2, iso_request=iso_request1, id=id1)
        iso4 = self._create_iso(label=label1, iso_request=iso_request2, id=id1)
        self.assert_equal(iso1, iso2)
        self.assert_not_equal(iso1, iso3)
        self.assert_not_equal(iso1, iso4)
        self.assert_not_equal(iso1, id1)

    def test_load(self):
        with RdbContextManager() as session:
            query = session.query(self.model_class)
            isos = query.limit(10).all()
            self.assert_equal(len(isos), 10)

    def test_persist(self):
        with RdbContextManager() as session:
            attrs = self.__get_data()
            persist(session, self.model_class, attrs, True)

    def test_persist_all_attributes(self):
        with RdbContextManager() as session:
            attrs = self.__get_data()
            iso = self._create_iso(**attrs)
            iso_job = self._create_iso_job(isos=[iso])
            self.assert_equal(iso.iso_job.label, iso_job.label)
            self._create_iso_sample_stock_rack(iso=iso)
            self.assert_equal(len(iso.iso_sample_stock_racks), 1)
            iso_preparation_plate = self._create_iso_preparation_plate(iso=iso)
            self.assert_equal(iso.iso_preparation_plate, iso_preparation_plate)
            self._create_iso_aliquot_plate(iso=iso)
            self.assert_equal(len(iso.iso_aliquot_plates), 1)
            session.merge(iso)
            session.commit()
            session.refresh(iso)
            iso_id = iso.id
            session.expunge(iso)
            del iso
            query = session.query(self.model_class)
            fetched_iso = query.filter_by(id=iso_id).one()
            check_attributes(fetched_iso, attrs)
            self.assert_equal(fetched_iso.iso_job.label, iso_job.label)
            self.assert_equal(len(fetched_iso.iso_sample_stock_racks), 1)
            self.assert_equal(fetched_iso.iso_preparation_plate,
                              iso_preparation_plate)
            self.assert_equal(len(fetched_iso.iso_aliquot_plates), 1)



class IsoRequestModelTest(ThelmaModelTestCase):

    model_class = IsoRequest

    def __get_data(self):
        iso_layout = self._create_rack_layout()
        requester = self._get_entity(IUser, 'it')
        number_plates = 3
        number_aliquots = 2
        delivery_date = datetime.now()
        plate_set_label = 'test_plate_set_label'
        owner = 'stockmanagment'
        comment = 'a comment'
        return dict(iso_layout=iso_layout,
                    requester=requester,
                    number_plates=number_plates,
                    delivery_date=delivery_date,
                    plate_set_label=plate_set_label,
                    comment=comment,
                    number_aliquots=number_aliquots,
                    owner=owner,
                    worklist_series=self._create_worklist_series())

    def test_init(self):
        attrs = self.__get_data()
        ir1 = IsoRequest(iso_layout=attrs['iso_layout'],
                         requester=attrs['requester'])
        self.assert_is_not_none(ir1)
        self.assert_equal(len(ir1.isos), 0)
        exp_attrs1 = dict(iso_layout=attrs['iso_layout'],
                          requester=attrs['requester'],
                          delivery_date=None,
                          number_plates=1,
                          number_aliquots=1,
                          owner='',
                          comment='',
                          experiment_metadata=None,
                          worklist_series=None,
                          plate_set_label='')
        check_attributes(ir1, exp_attrs1)
        del ir1.iso_layout # otherwise we get problems with the ORM
        ir2 = self._create_iso_request(**attrs)
        self.assert_is_not_none(ir2)
        check_attributes(ir2, attrs)
        self.assert_equal(len(ir2.isos), 0)

    def test_equality(self):
        sp1 = self._create_iso_request(id=1)
        sp2 = self._create_iso_request(id=2)
        sp3 = IsoRequest(**self.__get_data())
        sp3.id = sp2.id
        self.assert_not_equal(sp1, sp2)
        self.assert_equal(sp2, sp3)

    def test_load(self):
        with RdbContextManager() as session:
            query = session.query(self.model_class)
            iso_requests = query.limit(2).all()
            self.assert_equal(len(iso_requests), 2)

    def test_persist(self):
        with RdbContextManager() as session:
            attrs = self.__get_data()
            del attrs['delivery_date']
            persist(session, self.model_class, attrs, True)


class IsoControlStockRackModelTest(ThelmaModelTestCase):

    model_class = IsoControlStockRack

    def __get_data(self):
        job = self._create_iso_job()
        rack = self._get_entity(ITubeRack)
        rack_layout = self._create_rack_layout()
        planned_worklist = self._create_planned_worklist()
        return dict(iso_job=job, rack=rack,
                    rack_layout=rack_layout, planned_worklist=planned_worklist)

    def test_init(self):
        attrs = self.__get_data()
        icsr = self._create_iso_control_stock_rack(**attrs)
        self.assert_is_not_none(icsr)
        check_attributes(icsr, attrs)

    def test_equality(self):
        job1 = self._create_iso_job(label='IsoJob1')
        job2 = self._create_iso_job(label='IsoJob2')
        rack1 = self._create_tube_rack(id= -1)
        rack2 = self._create_tube_rack(id= -2)
        icsr1 = self._create_iso_control_stock_rack(iso_job=job1,
                                    rack=rack1)
        icsr2 = self._create_iso_control_stock_rack(iso_job=job2,
                                    rack=rack1)
        icsr3 = self._create_iso_control_stock_rack(iso_job=job1,
                                    rack=rack2)
        self.assert_not_equal(icsr1, icsr2)
        self.assert_equal(icsr1, icsr3)
        self.assert_not_equal(icsr1, job1)

    def test_persist(self):
        with RdbContextManager() as session:
            attrs = self.__get_data()
            persist(session, self.model_class, attrs, True)


class IsoSampleStockRackModelTest(ThelmaModelTestCase):

    model_class = IsoSampleStockRack

    def __get_data(self):
        iso = self._get_entity(IIso)
        rack = self._get_entity(ITubeRack)
        planned_worklist = self._create_planned_worklist()
        return dict(iso=iso, rack=rack, sector_index=0,
                    planned_worklist=planned_worklist)

    def test_init(self):
        attrs = self.__get_data()
        issr = self._create_iso_sample_stock_rack(**attrs)
        self.assert_is_not_none(issr)
        check_attributes(issr, attrs)

    def test_equality(self):
        iso1 = self._create_iso(label='iso1')
        iso2 = self._create_iso(label='iso2')
        rack1 = self._create_tube_rack(id= -1)
        rack2 = self._create_tube_rack(id= -2)
        issr1 = self._create_iso_sample_stock_rack(iso=iso1, rack=rack1)
        issr2 = self._create_iso_sample_stock_rack(iso=iso1, rack=rack1)
        issr3 = self._create_iso_sample_stock_rack(iso=iso2, rack=rack1)
        issr4 = self._create_iso_sample_stock_rack(iso=iso1, rack=rack2)
        issr5 = self._create_iso_sample_stock_rack(iso=iso1, rack=rack1,
                                                   sector_index=1)
        self.assert_equal(issr1, issr2)
        self.assert_not_equal(issr1, issr3)
        self.assert_not_equal(issr1, issr4)
        self.assert_equal(issr1, issr5)
        self.assert_not_equal(issr1, iso1)

    def test_persist(self):
        with RdbContextManager() as session:
            attrs = self.__get_data()
            persist(session, self.model_class, attrs, True)


class IsoPreparationPlateModelTest(ThelmaModelTestCase):

    model_class = IsoPreparationPlate

    def __get_data(self, with_iso_request=False):
        if with_iso_request:
            iso_request = self._create_iso_request()
            iso = self._create_iso(iso_request=iso_request)
        else:
            iso = self._create_iso()
        plate = self._get_entity(IPlate)
        return dict(iso=iso, plate=plate)

    def test_init(self):
        attrs = self.__get_data()
        ipp = self._create_iso_preparation_plate(**attrs)
        self.assert_is_not_none(ipp)
        check_attributes(ipp, attrs)

    def test_equality(self):
        iso1 = self._create_iso(label='iso1')
        iso2 = self._create_iso(label='iso2')
        plate1 = self._create_plate(id= -1)
        plate2 = self._create_plate(id= -2)
        ipp1 = self._create_iso_preparation_plate(iso=iso1, plate=plate1)
        ipp2 = self._create_iso_preparation_plate(iso=iso1, plate=plate1)
        ipp3 = self._create_iso_preparation_plate(iso=iso2, plate=plate1)
        ipp4 = self._create_iso_preparation_plate(iso=iso1, plate=plate2)
        self.assert_equal(ipp1, ipp2)
        self.assert_not_equal(ipp1, ipp3)
        self.assert_not_equal(ipp1, ipp4)
        self.assert_not_equal(ipp1, iso1)

    def test_persist(self):
        with RdbContextManager() as session:
            attrs = self.__get_data(with_iso_request=True)
            persist(session, self.model_class, attrs, True)


class IsoAliquotPlateModelTest(ThelmaModelTestCase):

    model_class = IsoAliquotPlate

    def __get_data(self):
        iso = self._get_entity(IIso)
        plate = self._get_entity(IPlate)
        return dict(iso=iso, plate=plate)

    def test_init(self):
        attrs = self.__get_data()
        iap = self._create_iso_aliquot_plate(**attrs)
        self.assert_is_not_none(iap)
        check_attributes(iap, attrs)

    def test_equality(self):
        iso1 = self._create_iso(label='iso1')
        iso2 = self._create_iso(label='iso2')
        plate1 = self._create_plate(id= -1)
        plate2 = self._create_plate(id= -2)
        iap1 = self._create_iso_aliquot_plate(iso=iso1, plate=plate1)
        iap2 = self._create_iso_aliquot_plate(iso=iso1, plate=plate1)
        iap3 = self._create_iso_aliquot_plate(iso=iso2, plate=plate1)
        iap4 = self._create_iso_aliquot_plate(iso=iso1, plate=plate2)
        self.assert_equal(iap1, iap2)
        self.assert_not_equal(iap1, iap3)
        self.assert_not_equal(iap1, iap4)
        self.assert_not_equal(iap1, iso1)

    def test_persist(self):
        with RdbContextManager() as session:
            attrs = self.__get_data()
            persist(session, self.model_class, attrs, True)
