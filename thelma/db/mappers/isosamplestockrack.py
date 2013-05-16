"""
ISO sample stock rack mapper.
"""
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from thelma.models.iso import IsoSampleStockRack
from thelma.models.liquidtransfer import PlannedWorklist
from thelma.models.rack import Rack

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(iso_sample_stock_rack_tbl):
    "Mapper factory."
    m = mapper(IsoSampleStockRack, iso_sample_stock_rack_tbl,
               properties=dict(
                    id=synonym('iso_sample_stock_rack_id'),
#                    iso=relationship(Iso, uselist=False,
#                        back_populates='iso_sample_stock_racks',
#                        cascade='save-update'),
                    rack=relationship(Rack, uselist=False),
                    planned_worklist=relationship(PlannedWorklist,
                                                  uselist=False)
                    )
               )
    return m
