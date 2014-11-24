"""
"""
from pkg_resources import resource_filename # pylint: disable=E0611
import pytest

#from everest.mime import JsonMime
#from everest.representers.utils import as_representer
#from everest.resources.utils import get_collection_class
#from thelma.interfaces import ISupplierSampleRegistrationItem


__docformat__ = 'reStructuredText en'
__all__ = []

@pytest.fixture
def sample_registration_data():
    fn = 'thelma:oldtests/tools/stock/registration/' + \
         'ambion_delivery_samples_with_locations.json'
    ftokens = fn.split(':')
    fn = resource_filename(*ftokens)
    return open(fn, 'rU').read()
