"""
Empty tube sample registrar.

Created on November 30, 2012.
"""
from everest.entities.utils import get_root_aggregate
from everest.querying.specifications import eq
from thelma.automation.parsers.rackscanning import RackScanningParser
from thelma.automation.semiconstants import ITEM_STATUS_NAMES
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.tools.base import BaseTool
from thelma.interfaces import IContainerSpecs
from thelma.interfaces import IItemStatus
from thelma.interfaces import IRack
from thelma.entities.container import Tube
import glob
import os

__docformat__ = 'reStructuredText en'
__all__ = ['EmptyTubeRegistrar',
           ]


class EmptyTubeRegistrar(BaseTool):
    # FIXME: Make these configurable.
    STATUS = ITEM_STATUS_NAMES.MANAGED.lower()
    SPECS = 'matrix0500'
    NAME = 'Empty Tube Registrar'
    def __init__(self, scanfile_directory, parent=None):
        BaseTool.__init__(self, parent=parent)
        self.__scanfile_directory = os.path.realpath(scanfile_directory)

    def run(self):
        rack_agg = get_root_aggregate(IRack)
        is_agg = get_root_aggregate(IItemStatus)
        status = is_agg.get_by_slug(self.STATUS)
        cnt_specs_agg = get_root_aggregate(IContainerSpecs)
        cnt_specs = cnt_specs_agg.get_by_slug(self.SPECS)
        tubes = []
        for scan_fn in glob.glob("%s/*.txt" % self.__scanfile_directory):
            strm = open(scan_fn, 'r')
            try:
                prs = RackScanningParser(strm, parent=self)
                prs.run()
            finally:
                strm.close()
            if prs.has_errors():
                raise RuntimeError('Could not parse rack scan file "%s". '
                                   'Error messages: %s'
                                   % (scan_fn, self.get_messages()))
            rack_agg.filter = eq(barcode=prs.rack_barcode)
            try:
                rack = rack_agg.iterator().next()
            except StopIteration:
                self.add_error('Rack with barcode "%s" does not exist.'
                               % prs.rack_barcode)
                continue
            if not rack.specs.has_tubes:
                self.add_error('Rack with barcode "%s" is not a tube '
                               'rack.' % rack.barcode)
                continue
            for pos_label, barcode in prs.position_map.iteritems():
                if barcode is None:
                    continue
                pos = get_rack_position_from_label(pos_label)
                # FIXME: Enable this test once pulling a tube by barcode is
                #        fast.
#                if tube_agg.get_by_slug(barcode):
#                    self.add_error('Tube with barcode "%s" already '
#                                   'exists.' % barcode)
#                    continue
                if not rack.is_empty(pos):
                    self.add_error('Trying to place a tube in an occupied '
                                   'position (%s on rack %s).' %
                                   (pos_label, rack.barcode))
                    continue
                tube = Tube.create_from_rack_and_position(cnt_specs, status,
                                                          barcode, rack, pos)
                tubes.append(tube)
                self.add_info('Creating tube with barcode %s at '
                              'position %s in rack %s.' %
                              (barcode, pos_label, rack.barcode))
        if not self.has_errors():
            self.return_value = tubes
