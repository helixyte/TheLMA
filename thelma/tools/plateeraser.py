"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

"""
from pyramid.compat import itervalues_

from everest.entities.utils import get_root_aggregate
from everest.querying.specifications import eq
from everest.repositories.rdb.session import ScopedSessionMaker
from thelma.interfaces import IRack
from thelma.tools.base import BaseTool
from thelma.tools.semiconstants import get_item_status_future


__docformat__ = 'reStructuredText en'
__all__ = ['PlateEraser'
           ]

class PlateEraser(BaseTool):
    NAME = 'Plate Eraser'
    def __init__(self, barcodes, parent=None):
        BaseTool.__init__(self, parent=parent)
        self.__barcodes = barcodes.split(',')

    def run(self):
        sess = ScopedSessionMaker()
        for bc in self.__barcodes:
            rack = self.__get_rack(bc)
            for src_cnt in itervalues_(rack.container_positions):
                if not src_cnt is None:
                    if not src_cnt.sample is None:
                        sess.delete(src_cnt.sample)
            rack.status = get_item_status_future()

    def __get_rack(self, barcode):
        rack_agg = get_root_aggregate(IRack)
        rack_agg.filter = eq(barcode=barcode)
        return next(rack_agg.iterator())
