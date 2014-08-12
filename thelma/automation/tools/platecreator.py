"""
"""
from collections import defaultdict

from everest.entities.utils import get_root_aggregate
from everest.querying.specifications import cntd
from everest.querying.specifications import eq
from thelma.automation.semiconstants import get_item_status_managed
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.tools.base import BaseTool
from thelma.automation.tools.stock.tubepicking import TubePicker
from thelma.interfaces import IMoleculeDesignPool
from thelma.interfaces import IRack
from thelma.interfaces import ITube


__docformat__ = 'reStructuredText en'
__all__ = ['PlateCreator96To384'
           ]

class PlateCreator96To384(BaseTool):
    NAME = 'Plate Creator 96 -> 384'
    ROW_LABELS = [chr(ord('A') + c) for c in range(16)]
    def __init__(self, iso_concentration, iso_volume, layout_filename_q1,
                 layout_filename_q2, layout_filename_q3, layout_filename_q4,
                 target_barcode, parent=None):
        BaseTool.__init__(self, parent=parent)
        self.__iso_concentration = float(iso_concentration) * 1e-9
        self.__iso_volume = float(iso_volume) * 1e-6
        self.__layout_filename_q1 = layout_filename_q1
        self.__layout_filename_q2 = layout_filename_q2
        self.__layout_filename_q3 = layout_filename_q3
        self.__layout_filename_q4 = layout_filename_q4
        self.__target_barcode = target_barcode

    def run(self):
        layout_map = {}
        for sector, lfn in enumerate((self.__layout_filename_q1,
                                      self.__layout_filename_q2,
                                      self.__layout_filename_q3,
                                      self.__layout_filename_q4)):
            layout_map.update(self.__parse_layout_file(sector, lfn))
        pool_map = self.__get_md_pool_map(set(layout_map.values()))
        stock_conc_map = self.__find_stock_concentrations(pool_map)
        pool_tube_barcode_map = self.__get_tube_barcode_map(pool_map,
                                                            stock_conc_map)
        tube_map = self.__get_tube_map(pool_tube_barcode_map.values())
        tgt_rack = self.__get_target_rack(self.__target_barcode)
        for pos_label, pool_id in layout_map.iteritems():
            pos = get_rack_position_from_label(pos_label)
            cnt_loc = tgt_rack.container_locations[pos]
            smpl = cnt_loc.container.make_sample(self.__iso_volume)
            tube = tube_map[pool_tube_barcode_map[pool_id]]
            sm_conc = \
                self.__iso_concentration / len(tube.sample.sample_molecules)
            for sm in tube.sample.sample_molecules:
                smpl.make_sample_molecule(sm.molecule, sm_conc)
        tgt_rack.status = get_item_status_managed()

    def __parse_layout_file(self, sector, layout_filename):
        with open(layout_filename, 'rU') as lf:
            buf = lf.readlines()
        pos_map = {}
        offset_row, offset_col = divmod(sector, 2)
        for row_idx, line in enumerate(buf[1:]):
            values = line.strip().split(',')
            row_label = self.ROW_LABELS[row_idx * 2 + offset_row]
            line_pos_map = \
                dict([("%s%d" % (row_label, col_idx * 2 + offset_col + 1),
                       int(pool_id))
                      for (col_idx, pool_id) in enumerate(values[1:])
                      if not pool_id == ''])
            pos_map.update(line_pos_map)
        return pos_map

    def __find_stock_concentrations(self, pool_map):
        conc_map = defaultdict(list)
        for pool in pool_map.itervalues():
            # The tube picker tool expects concentrations in nM.
            s_conc = pool.default_stock_concentration * 1e9
            conc_map[s_conc].append(pool.id)
        return conc_map

    def __get_md_pool_map(self, pool_ids):
        agg = get_root_aggregate(IMoleculeDesignPool)
        agg.filter = cntd(id=pool_ids)
        return dict([(md.id, md) for md in agg.iterator()])

    def __get_tube_barcode_map(self, pool_map, stock_concentration_map):
        pool_tube_bc_map = {}
        for conc, pool_ids in stock_concentration_map.iteritems():
            pools = [pool_map[pool_id] for pool_id in pool_ids]
            conc_ptbc_map = self.__run_tube_picker(pools, conc)
            pool_tube_bc_map.update(conc_ptbc_map)
        return pool_tube_bc_map

    def __run_tube_picker(self, pools, conc):
        tube_picker = TubePicker(pools, conc, parent=self)
        return dict([(pool.id, tbs[0].tube_barcode)
                     for (pool, tbs) in tube_picker.get_result().iteritems()
                     if len(tbs) > 0])

    def __get_tube_map(self, tube_barcodes):
        tb_agg = get_root_aggregate(ITube)
        tb_agg.filter = cntd(barcode=tube_barcodes)
        return dict([(tb.barcode, tb) for tb in tb_agg.iterator()])

    def __get_target_rack(self, barcode):
        rack_agg = get_root_aggregate(IRack)
        rack_agg.filter = eq(barcode=barcode)
        return next(rack_agg.iterator())
