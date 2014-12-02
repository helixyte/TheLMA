"""
Planned rack sample transfer mapper.
"""
from sqlalchemy.orm import mapper

from thelma.entities.liquidtransfer import PlannedRackSampleTransfer
from thelma.entities.liquidtransfer import TRANSFER_TYPES


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(planned_liquid_transfer_mapper,
                  planned_rack_sample_transfer_tbl):
    "Mapper factory."
    prst = planned_rack_sample_transfer_tbl
    m = mapper(PlannedRackSampleTransfer, planned_rack_sample_transfer_tbl,
               inherits=planned_liquid_transfer_mapper,
               properties=dict(
                     _number_sectors=prst.c.number_sectors,
                     _source_sector_index=prst.c.source_sector_index,
                     _target_sector_index=prst.c.target_sector_index),
               polymorphic_identity=TRANSFER_TYPES.RACK_SAMPLE_TRANSFER,
               )
    return m
