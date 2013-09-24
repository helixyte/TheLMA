"""
Planned rack sample transfer mapper.
"""
from sqlalchemy.orm import mapper
from thelma.models.liquidtransfer import PlannedRackSampleTransfer
from thelma.models.liquidtransfer import TRANSFER_TYPES

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(planned_liquid_transfer_mapper,
                  planned_rack_sample_transfer_tbl):
    "Mapper factory."
    prst = planned_rack_sample_transfer_tbl

    m = mapper(PlannedRackSampleTransfer, planned_rack_sample_transfer_tbl,
               inherits=planned_liquid_transfer_mapper,
               properties=dict(
                     _sector_number=prst.c.sector_number,
                     _source_sector_index=prst.c.source_sector_index,
                     _target_sector_index=prst.c.target_sector_index),
               polymorphic_identity=TRANSFER_TYPES.RACK_SAMPLE_TRANSFER,
               )
    return m
