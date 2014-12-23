"""
Created on Dec 09, 2014.
"""
from pyramid.httpexceptions import HTTPOk
import transaction

from everest.mime import XmlMime
from everest.resources.utils import get_root_collection
from thelma.interfaces import ITubeRack
from thelma.tests.functional.conftest import TestFunctionalBase


class TestRackFunctional(TestFunctionalBase):
    path = '/racks'
    setup_rdb_context = True

    def test_load_racks(self, app_creator):
        rsp = app_creator.get(self.path,
                              params=dict(size=10),
                              status=HTTPOk.code)
        assert not rsp is None

    def test_patch_set_location(self, app_creator,
                                rack_patch_set_location_data):
        rack_bc = '02490469'
        loc_id = 1513
        rsp = app_creator.patch('%s/%s' % (self.path, rack_bc),
                                params=rack_patch_set_location_data,
                                content_type=XmlMime.mime_type_string,
                                status=HTTPOk.code)
        assert not rsp is None
        transaction.commit()
        coll = get_root_collection(ITubeRack)
        rack = coll[rack_bc]
        lr = rack.get_entity().location_rack
        assert not lr is None
        assert lr.location.id == loc_id

    def test_patch_unset_location(self, app_creator):
        rack_bc = '02481966'
        rsp = app_creator.delete('%s/%s/location' % (self.path, rack_bc),
                                 status=HTTPOk.code)
        assert not rsp is None
        transaction.commit()
        coll = get_root_collection(ITubeRack)
        rack = coll[rack_bc]
        assert rack.get_entity().location_rack is None
