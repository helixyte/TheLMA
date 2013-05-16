"""
ISO mapper.
"""
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from thelma.db.mappers.utils import as_slug_expression
from thelma.models.iso import ISO_TYPES
from thelma.models.iso import Iso
from thelma.models.iso import IsoAliquotPlate
from thelma.models.iso import IsoPreparationPlate
from thelma.models.iso import IsoRequest
from thelma.models.iso import IsoSampleStockRack
from thelma.models.job import IsoJob
from thelma.models.moleculedesign import MoleculeDesignPoolSet
from thelma.models.racklayout import RackLayout

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(iso_tbl, iso_job_tbl, iso_job_member_tbl,
                  iso_pool_set_tbl):
    "Mapper factory."
    ij = iso_job_tbl
    ijm = iso_job_member_tbl
    m = mapper(Iso, iso_tbl,
        properties=
            dict(id=synonym('iso_id'),
                 type=synonym('iso_type'),
                 iso_request=relationship(IsoRequest,
                                         uselist=False,
                                         back_populates='isos'),
                 molecule_design_pool_set=
                        relationship(MoleculeDesignPoolSet,
                                     uselist=False,
                                     secondary=iso_pool_set_tbl),
                 rack_layout=relationship(RackLayout, uselist=False,
                                          cascade='all,delete,delete-orphan',
                                          single_parent=True),
                 iso_sample_stock_racks=relationship(IsoSampleStockRack,
                             backref='iso',
                             cascade='all, delete-orphan'),
                 iso_aliquot_plates=relationship(IsoAliquotPlate,
                              back_populates='iso',
                              cascade='all,delete-orphan'),
                 iso_preparation_plate=relationship(IsoPreparationPlate,
                              uselist=False,
                              back_populates='iso'),
                 iso_job=relationship(IsoJob, uselist=False,
                             primaryjoin=(iso_tbl.c.iso_id == ijm.c.iso_id),
                             secondaryjoin=(ijm.c.job_id == ij.c.job_id),
                             secondary=ijm,
                             back_populates='isos',
                             cascade='all'),
                 ),
               polymorphic_on=iso_tbl.c.iso_type,
               polymorphic_identity=ISO_TYPES.STANDARD,
               )

    if isinstance(Iso.slug, property):
        Iso.slug = hybrid_property(
                            Iso.slug.fget,
                            expr=lambda cls: as_slug_expression(cls.label))
    return m
