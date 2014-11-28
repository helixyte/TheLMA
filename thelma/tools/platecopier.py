"""
"""
from everest.entities.utils import get_root_aggregate
from everest.querying.specifications import eq
from thelma.tools.base import BaseTool
from thelma.interfaces import IRack
from thelma.tools.semiconstants import get_item_status_managed


__docformat__ = 'reStructuredText en'
__all__ = ['PlateCopier'
           ]

class PlateCopier(BaseTool):
    NAME = 'Plate Copier'
    def __init__(self, source_barcode, target_barcodes, transfer_volume,
                 parent=None):
        BaseTool.__init__(self, parent=parent)
        self.__source_barcode = source_barcode
        self.__target_barcodes = target_barcodes.split(',')
        self.__transfer_volume = float(transfer_volume) * 1e-6

    def run(self):
        src_rack = self.__get_rack(self.__source_barcode)
        for tgt_bc in self.__target_barcodes:
            tgt_rack = self.__get_rack(tgt_bc)
            for pos, src_cnt_loc in src_rack.container_locations.iteritems():
                if not src_cnt_loc.container is None:
                    src_cnt = src_cnt_loc.container
                    if not src_cnt.sample is None:
                        src_smpl = src_cnt.sample
                        tgt_cnt_loc = tgt_rack.container_locations[pos]
                        tgt_cnt = tgt_cnt_loc.container
                        tgt_smpl = tgt_cnt.make_sample(self.__transfer_volume)
                        for sm in src_smpl.sample_molecules:
                            tgt_smpl.make_sample_molecule(sm.molecule,
                                                          sm.concentration)
            tgt_rack.status = get_item_status_managed()

    def __get_rack(self, barcode):
        rack_agg = get_root_aggregate(IRack)
        rack_agg.filter = eq(barcode=barcode)
        return next(rack_agg.iterator())
