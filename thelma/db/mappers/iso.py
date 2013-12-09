"""
ISO mapper.
"""
from everest.repositories.rdb.utils import as_slug_expression
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.models.iso import ISO_TYPES
from thelma.models.iso import Iso
from thelma.models.iso import IsoAliquotPlate
from thelma.models.iso import IsoPreparationPlate
from thelma.models.iso import IsoRequest
from thelma.models.iso import IsoStockRack
from thelma.models.job import IsoJob
from thelma.models.moleculedesign import MoleculeDesignPoolSet
from thelma.models.racklayout import RackLayout
from thelma.models.iso import IsoSectorStockRack

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(iso_tbl, job_tbl, iso_job_member_tbl, iso_pool_set_tbl):
    "Mapper factory."
    j = job_tbl
    ijm = iso_job_member_tbl
    m = mapper(Iso, iso_tbl,
        id_attribute='iso_id',
        slug_expression=lambda cls: as_slug_expression(cls.label),
        properties=
            dict(iso_request=relationship(IsoRequest,
                                         uselist=False,
                                         back_populates='isos'),
                 molecule_design_pool_set=
                        relationship(MoleculeDesignPoolSet,
                                     uselist=False,
                                     secondary=iso_pool_set_tbl),
                 rack_layout=relationship(RackLayout, uselist=False,
                                          cascade='all,delete,delete-orphan',
                                          single_parent=True),
                 iso_stock_racks=relationship(IsoStockRack,
                             back_populates='iso',
                             cascade='all,delete,delete-orphan'),
                 iso_sector_stock_racks=relationship(IsoSectorStockRack,
                             back_populates='iso',
                             cascade='all,delete,delete-orphan'),
                 iso_aliquot_plates=relationship(IsoAliquotPlate,
                              back_populates='iso',
                              cascade='all,delete-orphan'),
                 iso_preparation_plates=relationship(IsoPreparationPlate,
                              back_populates='iso'),
                 iso_job=relationship(IsoJob, uselist=False,
                             primaryjoin=(iso_tbl.c.iso_id == ijm.c.iso_id),
                             secondaryjoin=(ijm.c.job_id == j.c.job_id),
                             secondary=ijm,
                             back_populates='isos',
                             cascade='all'),
                 ),
               polymorphic_on=iso_tbl.c.iso_type,
               polymorphic_identity=ISO_TYPES.BASE,
               )
    return m
