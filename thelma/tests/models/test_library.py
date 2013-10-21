"""
Test cases for model classes related to molecule design libraries.

"""

from everest.testing import RdbContextManager
from everest.testing import check_attributes
from thelma.interfaces import IMoleculeDesignPool
from thelma.models.library import LibraryPlate
from thelma.models.library import MoleculeDesignLibrary
from thelma.testing import ThelmaEntityTestCase


class MoleculeDesignLibraryModelTestCase(ThelmaEntityTestCase):

    model_class = MoleculeDesignLibrary

    def _get_data(self):
        label = 'library1'
        pool = self._get_entity(IMoleculeDesignPool, '205200')
        pool_set = self._create_molecule_design_pool_set(
                                        molecule_design_pools=set([pool]))
        final_volume = 0.000008 # 8 ul
        final_conc = 0.000003000 # 3000 nM = 3 uM
        iso_request = self._create_stock_sample_creation_iso_request()
        number_layouts = 17
        rack_layout = self._create_rack_layout()
        return dict(label=label, creation_iso_request=iso_request,
                    final_volume=final_volume, final_concentration=final_conc,
                    molecule_design_pool_set=pool_set,
                    number_layouts=number_layouts, rack_layout=rack_layout)

    def test_init(self):
        mdl = self._test_init()
        self.assert_equal(len(mdl.library_plates), 0)

    def test_load(self):
        self._test_load(num_entities=1)

    def test_persist(self):
        self._test_persist()


class LibraryPlateModelTestCase(ThelmaEntityTestCase):

    model_class = LibraryPlate

    def _get_data(self):
        lib = self._create_molecule_design_library(label='plate_test_lib')
        rack = self._create_plate()
        layout_number = 19
        return dict(molecule_design_library=lib, rack=rack,
                    layout_number=layout_number)

    def test_init(self):
        self._test_init()

    def test_equality(self):
        self._test_id_based_equality(self._create_library_plate,
                                     self._create_plate)

    def test_load(self):
        self._test_load()

    def test_persist(self):
        self._test_persist()

    def test_persist_with_iso(self):
        with RdbContextManager() as session:
            attrs = self._get_data()
            lp = self._create_library_plate(**attrs)
            self.assert_is_none(lp.lab_iso)
            lp.lab_iso = self._create_lab_iso(
                                iso_request=self._create_lab_iso_request())
            self.assert_is_not_none(lp.lab_iso)
            session.add(lp)
            session.commit()
            session.refresh(lp)
            lp_id = lp.id
            session.expunge(lp)
            del lp
            query = session.query(self.model_class)
            fetched_lp = query.filter_by(id=lp_id).one()
            check_attributes(fetched_lp, attrs)
            self.assert_is_not_none(fetched_lp.lab_iso)
