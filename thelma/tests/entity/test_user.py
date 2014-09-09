from everest.entities.utils import slug_from_string
from everest.repositories.rdb.testing import check_attributes
from everest.repositories.rdb.testing import persist
from thelma.tests.entity.conftest import TestEntityBase


class TestUserEntity(TestEntityBase):

    def test_init(self, user_fac):
        user = user_fac()
        check_attributes(user, user_fac.init_kw)
        assert user.slug == slug_from_string(user.directory_user_id)



class TestUserPreferencesEntity(TestEntityBase):

    def test_init(self, user_preferences_fac):
        up = user_preferences_fac()
        check_attributes(up, user_preferences_fac.init_kw)
        assert up.slug == slug_from_string("%s_%s"
                                           % (up.user.username, up.app_name))

    def test_persist(self, nested_session, user_preferences_fac):
        up = user_preferences_fac()
        persist(nested_session, up, user_preferences_fac.init_kw, True)
