"""
"""
from pkg_resources import resource_filename # pylint: disable=E0611
import pytest


__docformat__ = 'reStructuredText en'
__all__ = []


class TestFunctionalBase(object):
    package_name = 'thelma'
    app_name = 'thelma'
    setup_request = True
    remote_user_id = 'cenixadm'


@pytest.fixture
def sample_registration_data():
    fn = 'thelma:tests/functional/data/' + \
         'ambion_delivery_samples_with_locations.json'
    return open(resource_filename(*fn.split(':')), 'rU').read()


@pytest.fixture
def rack_patch_set_location_data():
    fn = 'thelma:tests/functional/data/' + \
         'rack_patch_set_location.xml'
    return open(resource_filename(*fn.split(':')), 'rU').read()
