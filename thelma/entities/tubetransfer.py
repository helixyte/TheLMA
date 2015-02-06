"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Entity classes involved in XL20 run storage.
"""
from everest.entities.base import Entity
from thelma.utils import get_utc_time


__docformat__ = 'reStructuredText en'
__all__ = ['TubeTransfer',
           'TubeTransferWorklist']


class TubeTransfer(Entity):
    """
    This class represents one tube transfer operation performed by the XL20
    tubehandler robot, i.e. the transfer of one closed tube from one position
    in a tube rack to another one (in the same tube rack or a different one).
    """
    #: The transferred tube (:class:`thelma.entities.container.Tube`).
    tube = None
    #: The source rack (:class:`thelma.entities.rack.TubeRack`).
    source_rack = None
    #: The rack position in the source rack
    #: (:class:`thelma.entities.rack.RackPosition`).
    source_position = None
    #: The target rack (:class:`thelma.entities.rack.TubeRack`).
    target_rack = None
    #: The rack position in the target rack
    #: (:class:`thelma.entities.rack.RackPosition`).
    target_position = None

    def __init__(self, tube, source_rack, source_position, target_rack,
                 target_position, **kw):
        Entity.__init__(self, **kw)
        self.tube = tube
        self.source_rack = source_rack
        self.source_position = source_position
        self.target_rack = target_rack
        self.target_position = target_position

    def __str__(self):
        return str(self.id)

    def __repr__(self):
        str_format = '<%s tube: %s, source rack: %s, source position: %s, ' \
                     'target rack: %s, target position: %s>'
        params = (self.__class__.__name__, self.tube.barcode, self.source_rack,
                  self.source_position, self.target_rack, self.target_position)
        return str_format % params


class TubeTransferWorklist(Entity):
    """
    Comprises all tube transfers that have executed in one XL20 tubehandler run.
    """
    #: The tube transfers being part of the worklist (:class:`TubeTransfer`).
    tube_transfers = None
    #: The user who has carried out the transfer
    #: (:class:thelma.entities.user.User`).
    user = None
    #: The time stamp is set upon entity creation. It represents the time
    #: the transfer has been executed on DB level.
    timestamp = None

    def __init__(self, user, tube_transfers=None, timestamp=None, **kw):
        Entity.__init__(self, **kw)
        self.user = user
        if timestamp is None:
            timestamp = get_utc_time()
        self.timestamp = timestamp
        if tube_transfers is None:
            tube_transfers = []
        self.tube_transfers = tube_transfers

    def __len__(self):
        return len(self.tube_transfers)

    def __iter__(self):
        return iter(self.tube_transfers)

    def __str__(self):
        return self.id

    def __repr__(self):
        str_format = '<%s user: %s, number of tube transfers: %i>'
        params = (self.__class__.__name__, self.user, len(self.tube_transfers))
        return str_format % params
