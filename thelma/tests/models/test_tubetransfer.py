"""
Tube transfer model tests

AAB
"""
from datetime import datetime
from everest.repositories.rdb.testing import RdbContextManager
from everest.repositories.rdb.testing import check_attributes
from everest.repositories.rdb.testing import persist
from everest.utils import id_generator
from thelma.interfaces import ITube
from thelma.interfaces import IUser
from thelma.models.rack import RackPosition
from thelma.models.tubetransfer import TubeTransfer
from thelma.models.tubetransfer import TubeTransferWorklist
from thelma.testing import ThelmaModelTestCase
import pytz


class TubeTransferModelTest(ThelmaModelTestCase):

    model_class = TubeTransfer
    id_gen = id_generator()

    def __get_init_data(self):
        tube = self._get_entity(ITube)
        source_rack = self._create_tube_rack(label='source_rack')
        source_pos = RackPosition.from_label('A1')
        target_rack = self._create_tube_rack(label='target_rack')
        target_pos = RackPosition.from_label('B1')
        return dict(tube=tube, source_rack=source_rack, target_rack=target_rack,
                    source_position=source_pos, target_position=target_pos)

    def test_init(self):
        attrs = self.__get_init_data()
        tt = self._create_tube_transfer(**attrs)
        self.assert_is_not_none(tt)
        check_attributes(tt, attrs)

    def test_equality(self):
        id1 = self.id_gen.next()
        id2 = self.id_gen.next()
        tt1 = self._create_tube_transfer(id=id1)
        tt2 = self._create_tube_transfer(id=id1)
        tt3 = self._create_tube_transfer(id=id2)
        self.assert_equal(tt1, tt2)
        self.assert_not_equal(tt1, tt3)
        self.assert_not_equal(tt1, id1)

    def test_persist(self):
        with RdbContextManager() as session:
            attrs = self.__get_init_data()
            persist(session, self.model_class, attrs, True)


class TubeTransferWorklistModelTest(ThelmaModelTestCase):

    model_class = TubeTransferWorklist
    id_gen = id_generator()

    def __get_init_data(self):
        user = self._get_entity(IUser)
        timestamp = datetime(2012, 8, 23, 12, 42, 1, tzinfo=pytz.UTC)
        return dict(user=user, timestamp=timestamp)

    def test_init(self):
        attrs = self.__get_init_data()
        ttw = self._create_tube_transfer_worklist(**attrs)
        self.assert_is_not_none(ttw)
        check_attributes(ttw, attrs)

    def test_equality(self):
        id1 = self.id_gen.next()
        id2 = self.id_gen.next()
        ttw1 = self._create_tube_transfer_worklist(id=id1)
        ttw2 = self._create_tube_transfer_worklist(id=id1)
        ttw3 = self._create_tube_transfer_worklist(id=id2)
        self.assert_equal(ttw1, ttw2)
        self.assert_not_equal(ttw1, ttw3)
        self.assert_not_equal(ttw1, id1)

    def test_persist(self):
        with RdbContextManager() as session:
            attrs = self.__get_init_data()
            persist(session, self.model_class, attrs, True)

    def test_persist_all_attributes(self):
        with RdbContextManager() as session:
            attrs = self.__get_init_data()
            tt = self._create_tube_transfer()
            attrs['tube_transfers'] = [tt]
            ttw = self._create_tube_transfer_worklist(**attrs)
            self.assert_equal(len(ttw), 1)
            session.add(type(ttw), ttw)
            session.commit()
            session.refresh(ttw)
            ttw_id = ttw.id
            session.expunge(ttw)
            del ttw
            query = session.query(self.model_class)
            fetched_ttw = query.filter_by(id=ttw_id).one()
            check_attributes(fetched_ttw, attrs)
