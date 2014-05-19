"""
"""
from everest.entities.utils import get_root_aggregate
from everest.querying.specifications import eq
from everest.repositories.rdb import Session
from thelma.automation.semiconstants import get_item_status_future
from thelma.automation.tools.base import BaseTool
from thelma.interfaces import IRack


__docformat__ = 'reStructuredText en'
__all__ = ['PlateEraser'
           ]

class PlateEraser(BaseTool):
    NAME = 'Plate Eraser'
    def __init__(self, barcodes, parent=None):
        BaseTool.__init__(self, parent=parent)
        self.__barcodes = barcodes.split(',')

    def run(self):
        sess = Session()
        for bc in self.__barcodes:
            rack = self.__get_rack(bc)
            for src_cnt_loc in rack.container_locations.itervalues():
                if not src_cnt_loc.container is None:
                    src_cnt = src_cnt_loc.container
                    if not src_cnt.sample is None:
                        sess.delete(src_cnt.sample)
            rack.status = get_item_status_future()

    def __get_rack(self, barcode):
        rack_agg = get_root_aggregate(IRack)
        rack_agg.filter = eq(barcode=barcode)
        return next(rack_agg.iterator())
