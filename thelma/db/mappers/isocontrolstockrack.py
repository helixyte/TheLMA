"""
ISO control stock rack mapper
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.models.iso import IsoControlStockRack
from thelma.models.job import IsoJob
from thelma.models.liquidtransfer import PlannedWorklist
from thelma.models.rack import Rack
from thelma.models.racklayout import RackLayout

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(iso_control_stock_rack_tbl):
    "Mapper factory."
    m = mapper(IsoControlStockRack, iso_control_stock_rack_tbl,
               id_attribute='iso_control_stock_rack_id',
               properties=dict(
                    iso_job=relationship(IsoJob, uselist=False,
                        back_populates='iso_control_stock_rack'),
                    rack_layout=relationship(RackLayout, uselist=False),
                    rack=relationship(Rack, uselist=False),
                    planned_worklist=relationship(PlannedWorklist,
                                                  uselist=False)
                    )
               )
    return m
