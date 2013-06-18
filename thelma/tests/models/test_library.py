"""
Test cases for model classes related to molecule design libraries.

"""

from everest.testing import RdbContextManager
from everest.testing import check_attributes
from everest.testing import persist
from thelma.automation.tools.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.interfaces import IIsoRequest
from thelma.interfaces import IMoleculeDesignPool
from thelma.models.library import LibraryCreationIso
from thelma.models.library import LibrarySourcePlate
from thelma.models.library import MoleculeDesignLibrary
from thelma.testing import ThelmaModelTestCase



class MoleculeDesignLibraryModelTestCase(ThelmaModelTestCase):

    model_class = MoleculeDesignLibrary

    def __get_data(self):
        label = 'library1'
        pool = self._get_entity(IMoleculeDesignPool, '205200')
        pool_set = self._create_molecule_design_pool_set(
                                        molecule_design_pools=set([pool]))
        final_volume = 8 / VOLUME_CONVERSION_FACTOR
        final_conc = 3000 / CONCENTRATION_CONVERSION_FACTOR
        iso_request = self._create_iso_request()
        return dict(label=label, iso_request=iso_request,
                    final_volume=final_volume, final_concentration=final_conc,
                    molecule_design_pool_set=pool_set)

    def test_init(self):
        attrs = self.__get_data()
        lib = self._create_molecule_design_library(**attrs)
        self.assert_is_not_none(lib)
        check_attributes(lib, attrs)

    def test_equality(self):
        attrs = self.__get_data()
        lib1 = self._create_molecule_design_library(**attrs)
        lib2 = self._create_molecule_design_library(**attrs)
        attrs['label'] = 'other_label'
        lib3 = self._create_molecule_design_library(**attrs)
        self.assert_equal(lib1, lib2)
        self.assert_not_equal(lib1, lib3)
        self.assert_not_equal(lib1, 1)

    def test_persist(self):
        with RdbContextManager() as session:
            attrs = self.__get_data()
            persist(session, self.model_class, attrs, True)


class LibraryCreationIsoModelTest(ThelmaModelTestCase):

    model_class = LibraryCreationIso

    def __get_data(self):
        label = 'PoolLib 17'
        status = 'in progress'
        iso_request = self._get_entity(IIsoRequest)
        rack_layout = self._create_rack_layout()
        ticket_number = 1111
        layout_number = 17
        return dict(label=label, iso_request=iso_request, status=status,
                    rack_layout=rack_layout, ticket_number=ticket_number,
                    layout_number=layout_number)

    def test_init(self):
        attrs = self.__get_data()
        lci = self._create_library_creation_iso(**attrs)
        check_attributes(lci, attrs)
        self.assert_is_not_none(lci.slug)
        self.assert_is_none(lci.iso_job)
        self.assert_is_none(lci.iso_preparation_plate)
        self.assert_equal(len(lci.iso_sample_stock_racks), 0)
        self.assert_equal(len(lci.iso_aliquot_plates), 0)

    def test_slug(self):
        label_slug = 'poollib-17'
        lci = self._create_library_creation_iso(**self.__get_data())
        self.assert_not_equal(lci.slug, lci.label)
        self.assert_equal(lci.slug, label_slug)

    def test_equality(self):
        label1 = 'PoolLib 1'
        label2 = 'PoolLib 2'
        iso_request1 = self._create_iso_request()
        iso_request2 = self._create_iso_request()
        iso_request2.id = -8
        id1 = -1
        id2 = -2
        attrs = dict(ticket_number=11, layout_number=11, label=label1,
                     iso_request=iso_request1, id=id1)
        lci1 = self._create_library_creation_iso(**attrs)
        attrs['id'] = id2
        lci2 = lci1 = self._create_library_creation_iso(**attrs)
        attrs['id'] = id1
        attrs['ticket_number'] = 12
        lci3 = self._create_library_creation_iso(**attrs)
        attrs['ticket_number'] = 11
        attrs['layout_number'] = 12
        lci4 = self._create_library_creation_iso(**attrs)
        attrs['layout_number'] = 11
        attrs['label'] = label2
        lci5 = self._create_library_creation_iso(**attrs)
        attrs['label'] = label1
        attrs['iso_request'] = iso_request2
        lci6 = self._create_library_creation_iso(**attrs)
        self.assert_equal(lci1, lci2)
        self.assert_equal(lci1, lci3)
        self.assert_not_equal(lci1, lci4)
        self.assert_equal(lci1, lci5)
        self.assert_not_equal(lci1, lci6)
        self.assert_not_equal(lci1, iso_request1)

    def test_persist(self):
        with RdbContextManager() as session:
            attrs = self.__get_data()
            persist(session, self.model_class, attrs, True)


class LibrarySourcePlateModelTest(ThelmaModelTestCase):

    model_class = LibrarySourcePlate

    def __get_data(self):
        iso = self._create_library_creation_iso()
        plate = self._create_plate(barcode='09999999')
        sector_index = 3
        return dict(iso=iso, plate=plate, sector_index=sector_index)

    def test_init(self):
        attrs = self.__get_data()
        lsp = self._create_library_source_plate(**attrs)
        self.assert_is_not_none(lsp)
        check_attributes(lsp, attrs)

    def test_equality(self):
        iso1 = self._create_library_creation_iso(layout_number=1)
        iso2 = self._create_library_creation_iso(layout_number=2)
        plate1 = self._create_plate(id= -1)
        plate2 = self._create_plate(id= -2)
        lsp1 = self._create_library_source_plate(iso=iso1, plate=plate1)
        lsp2 = self._create_library_source_plate(iso=iso1, plate=plate1)
        lsp3 = self._create_library_source_plate(iso=iso2, plate=plate1)
        lsp4 = self._create_library_source_plate(iso=iso1, plate=plate2)
        self.assert_equal(lsp1, lsp2)
        self.assert_not_equal(lsp1, lsp3)
        self.assert_not_equal(lsp1, lsp4)
        self.assert_not_equal(lsp1, iso1)

    def test_persist(self):
        with RdbContextManager() as session:
            attrs = self.__get_data()
            persist(session, self.model_class, attrs, True)
