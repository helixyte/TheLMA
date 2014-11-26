import os

from pkg_resources import resource_filename # pylint: disable=E0611

from everest.entities.utils import get_root_aggregate
from everest.querying.specifications import eq
from everest.repositories.rdb.testing import RdbContextManager
from thelma.automation.semiconstants import get_item_status_managed
from thelma.automation.semiconstants import get_rack_position_from_indices
from thelma.automation.tools.iso.libcreation.executor import \
    LibraryCreationIsoExecutor
from thelma.automation.tools.iso.libcreation.isogenerator import \
    LibraryCreationIsoGenerator
from thelma.automation.tools.iso.libcreation.jobcreator import \
    LibraryCreationIsoJobCreator
from thelma.automation.tools.iso.libcreation.requestgenerator import \
    LibraryCreationIsoRequestGenerator
from thelma.automation.tools.iso.libcreation.writer import \
    LibraryCreationIsoWorklistWriter
from thelma.interfaces import ITubeRack
from thelma.interfaces import ITubeRackSpecs
from thelma.interfaces import ITubeSpecs
from thelma.interfaces import IUser
from thelma.entities.container import Tube
from thelma.entities.iso import ISO_TYPES
from thelma.testing import ThelmaEntityTestCase
from thelma.automation.tools.worklists.tubehandler import XL20Executor
from thelma.entities.iso import StockSampleCreationIsoRequest


__docformat__ = 'reStructuredText en'
__all__ = ['TestLibraryGeneration',
           ]


class TestLibraryGeneration(ThelmaEntityTestCase):
    __session = None

    def test_workflow(self):
        fn = resource_filename(self.__class__.__module__,
                               os.path.join('data',
                                            'library_generation.xls'))
        with open(fn, 'rb') as f:
            lib_excel_data = f.read()
        with RdbContextManager() as session:
            self.__session = session
            requester = get_root_aggregate(IUser).get_by_slug('it')
            ir = self.__generate_iso_request(lib_excel_data, requester)
            self.__generate_isos(ir, requester)
            self.__create_iso_job(ir, requester, 3)
            # If we have pool stock racks, we need 2 sets of
            # <n quadrants> empty barcodes for each ISO. else just 1.
            # FIXME: Make this configurable.
            WITH_POOL_STOCK_RACKS = False
            if WITH_POOL_STOCK_RACKS:
                number_stock_rack_sets = 2
            else:
                number_stock_rack_sets = 1
            empty_bc_count = 4 * number_stock_rack_sets * 3 - 2
            empty_racks = self.__get_empty_racks(empty_bc_count)
            for (iso_idx, iso) in enumerate(ir.isos):
                if iso_idx == 2:
                    num_quadrants = 2
                else:
                    num_quadrants = 4
                self.__run_worklist_writer_for_iso(iso, empty_racks,
                                                   num_quadrants,
                                                   WITH_POOL_STOCK_RACKS,
                                                   requester)
            for iso in ir.isos:
                self.__run_executor_for_iso(iso, requester)

    def __generate_iso_request(self, excel_data, requester):
        lg = LibraryCreationIsoRequestGenerator('testlib', excel_data, requester,
                                        preparation_plate_volume=98.5,
                                        number_designs=1,
                                        create_pool_racks=False,
                                        number_aliquots=5)
        lg.run()
        assert not lg.has_errors()
        lib = lg.return_value
        assert len(lib.molecule_design_pool_set) == 10
        ir = lib.creation_iso_request
        assert ir.number_designs == 1
        assert len(ir.worklist_series) == 5
        #
        self.__session.add(StockSampleCreationIsoRequest, ir)
        return ir

    def __generate_isos(self, iso_request, reporter):
        sscig = LibraryCreationIsoGenerator(iso_request, reporter=reporter)
        sscig.run()
        assert not sscig.has_errors()
        assert len(sscig.iso_request.isos) == 3
        for idx, iso in enumerate(iso_request.isos):
            ln = idx + 1
            assert iso.iso_type == ISO_TYPES.STOCK_SAMPLE_GENERATION
            assert iso.layout_number == ln
            assert iso.label == 'testlib_0%i' % ln

    def __create_iso_job(self, iso_request, owner, number_isos):
        lcijc = LibraryCreationIsoJobCreator(iso_request, owner, number_isos)
        lcijc.run()
        assert not lcijc.has_errors()
        for iso, number_pools in zip(iso_request.isos, [4, 4, 2]):
            assert not iso.rack_layout is None
            assert iso.rack_layout.has_positions()
            assert len(iso.rack_layout.get_positions()) == number_pools
            assert not iso.molecule_design_pool_set is None
            assert len(iso.molecule_design_pool_set) == number_pools

    def __run_worklist_writer_for_iso(self, iso, empty_racks,
                                      number_quadrants, with_pool_stock_racks,
                                      user):
        single_stock_racks = []
        for sec_idx in range(number_quadrants):
            single_stock_racks.append(empty_racks.pop().barcode)
        if with_pool_stock_racks:
            pool_stock_rack_map = {}
            for sec_idx in range(number_quadrants):
                empty_rack = empty_racks.pop()
                self.__prepare_pool_stock_rack(empty_rack, sec_idx)
                pool_stock_rack_map[sec_idx] = empty_rack.barcode
        else:
            pool_stock_rack_map = None
        lcww = LibraryCreationIsoWorklistWriter(iso,
                                                single_stock_racks,
                                                pool_stock_rack_map,
                                                include_dummy_output=True)
        file_map = lcww.get_result()
        assert not lcww.has_errors()
        assert not file_map is None
        # Move tubes with dummy output file.
        for fn, strm in file_map.iteritems():
            if not 'xl20_dummy_output' in fn:
                continue
            xl20_exc = XL20Executor(strm, user)
            tube_trf_wl = xl20_exc.get_result()
            assert not xl20_exc.has_errors()
            assert not tube_trf_wl is None
            # Make sure the tube racks are reloaded with the new tubes.
            self.__session.commit()

    def __run_executor_for_iso(self, iso, user):
        lce = LibraryCreationIsoExecutor(iso, user)
        result = lce.get_result()
        assert not lce.has_errors()
        assert not result is None
        if iso.layout_number < 3:
            pos_labels = set(['B3', 'B4', 'C3', 'C4'])
        else:
            # For the last ISO, we only have Q1 and Q2.
            pos_labels = set(['C3', 'C4'])
        for isp in iso.iso_sector_preparation_plates:
            isp_cnts_with_samples = [cnt for cnt in isp.rack.containers
                                     if not cnt.sample is None]
            assert len(isp_cnts_with_samples) == 1
            assert set([cnt.sample.volume for cnt in isp_cnts_with_samples]) \
                    == set([((96 + 2.5) - 4 * 5) * 1e-6])
        for ap in iso.iso_aliquot_plates:
            ap_cnts_with_samples = [cnt for cnt in ap.rack.containers
                                    if not cnt.sample is None]
            assert len(ap_cnts_with_samples) == len(pos_labels)
            assert set([cnt.location.position.label.upper()
                        for cnt in ap_cnts_with_samples]) == pos_labels
            assert set([cnt.sample.volume for cnt in ap_cnts_with_samples]) \
                    == set([4e-6])

    def __get_empty_racks(self, count):
        rack_specs_agg = get_root_aggregate(ITubeRackSpecs)
        rs_matrix = rack_specs_agg.get_by_slug('matrix0500')
        is_managed = get_item_status_managed()
        rack_agg = get_root_aggregate(ITubeRack)
        rack_agg.filter = eq(total_containers=0, specs=rs_matrix,
                             status=is_managed)
        rack_agg.slice = slice(0, count)
        return list(iter(rack_agg))

    def __prepare_pool_stock_rack(self, empty_rack, sector_idx):
        tube_specs_agg = get_root_aggregate(ITubeSpecs)
        ts_matrix = tube_specs_agg.get_by_slug('matrix0500')
        is_managed = get_item_status_managed()
        pos_idxs_96 = zip([1, 1, 0, 0], [1, 1, 1, 1])
        (row_idx, col_idx) = pos_idxs_96[sector_idx]
        tube = Tube.create_from_data(dict(barcode=str(9999999990 +
                                                      tube_counter.next()),
                                          status=is_managed,
                                          specs=ts_matrix))
        pos = get_rack_position_from_indices(row_idx, col_idx)
        empty_rack.add_tube(tube, pos)


def _make_tube_counter():
    i = 0
    while True:
        yield i
        i += 1

tube_counter = _make_tube_counter()
