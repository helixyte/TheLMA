from everest.mime import JsonMime
from pyramid.httpexceptions import HTTPCreated
import json


class TestFunctionalBase(object):
    package_name = 'thelma'
    app_name = 'thelma'


class TestSampleRegistrationItemFunctional(TestFunctionalBase):
    path = '/supplier-sample-registration-items'
    setup_rdb_context = True

    def test_post(self, app_creator, sample_registration_data):
        rsp = app_creator.post(self.path,
                               params=sample_registration_data,
                               content_type=JsonMime.mime_type_string,
                               status=HTTPCreated.code)
        rsp_data = json.loads(rsp.body)
        assert len(rsp_data) == 2
        assert rsp_data[0]['tube_barcode'] == '9999999998'
        assert rsp_data[0]['rack_position'] == 'A1'
        assert not rsp_data[0]['molecule_design_pool_id'] is None
        assert rsp_data[0]['volume'] == 0.0002
        assert rsp_data[0]['concentration'] == 5e-5
        assert rsp_data[0]['is_new_molecule_design_pool'] == True
        assert rsp_data[1]['tube_barcode'] == '9999999999'
        assert rsp_data[1]['rack_position'] == 'A2'
        assert not rsp_data[1]['molecule_design_pool_id'] is None
        assert rsp_data[1]['volume'] == 0.0001
        assert rsp_data[1]['concentration'] == 5e-5
        assert rsp_data[1]['is_new_molecule_design_pool'] == True
