"""
Test cases for model classes related to molecule design libraries.

"""

from thelma.automation.tools.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.interfaces import IMoleculeDesignPool
from thelma.models.library import MoleculeDesignLibrary
from thelma.testing import ThelmaEntityTestCase


class MoleculeDesignLibraryModelTestCase(ThelmaEntityTestCase):

    model_class = MoleculeDesignLibrary

    def _get_data(self):
        label = 'library1'
        pool = self._get_entity(IMoleculeDesignPool, '205200')
        pool_set = self._create_molecule_design_pool_set(
                                        molecule_design_pools=set([pool]))
        final_volume = 8 / VOLUME_CONVERSION_FACTOR
        final_conc = 3000 / CONCENTRATION_CONVERSION_FACTOR
        iso_request = self._create_stock_sample_creation_iso_request()
        return dict(label=label, iso_request=iso_request,
                    final_volume=final_volume, final_concentration=final_conc,
                    molecule_design_pool_set=pool_set)

    def test_init(self):
        self._test_init()

    def test_equality(self):
        attrs = self._get_data()
        lib1 = self._create_molecule_design_library(**attrs)
        lib2 = self._create_molecule_design_library(**attrs)
        attrs['label'] = 'other_label'
        lib3 = self._create_molecule_design_library(**attrs)
        self.assert_equal(lib1, lib2)
        self.assert_not_equal(lib1, lib3)
        self.assert_not_equal(lib1, 1)

    def test_load(self):
        self._test_load()

    def test_persist(self):
        self._test_persist()
