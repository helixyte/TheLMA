"""
ISO job mapper.
"""
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from thelma.models.iso import Iso
from thelma.models.iso import IsoControlStockRack
from thelma.models.job import IsoJob
from thelma.models.job import JOB_TYPES

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(job_mapper, iso_job_tbl, iso_tbl, iso_job_member_tbl):
    "Mapper factory."
    ij = iso_job_tbl
    iso = iso_tbl
    ijm = iso_job_member_tbl
    m = mapper(IsoJob, iso_job_tbl,
               inherits=job_mapper,
               properties=dict(
                    iso_control_stock_rack=relationship(IsoControlStockRack,
                            uselist=False, back_populates='iso_job',
                            cascade='all, delete-orphan'),
                    isos=relationship(Iso,
                            primaryjoin=(ij.c.job_id == ijm.c.job_id),
                            secondaryjoin=(ijm.c.iso_id == iso.c.iso_id),
                            secondary=ijm,
                            back_populates='iso_job')
                    ),
               polymorphic_identity=JOB_TYPES.ISO_PROCESSING,
            )
    return m
