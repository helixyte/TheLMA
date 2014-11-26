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
    fn = 'thelma:oldtests/tools/stock/registration/' + \
         'ambion_delivery_samples_with_locations.json'
    ftokens = fn.split(':')
    fn = resource_filename(*ftokens)
    return open(fn, 'rU').read()


