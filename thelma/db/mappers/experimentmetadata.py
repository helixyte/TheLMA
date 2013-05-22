"""
Experiment metadata mapper.
"""
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import column_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from thelma.db.mappers.utils import CaseInsensitiveComparator
from thelma.db.mappers.utils import as_slug_expression
from thelma.models.experiment import ExperimentDesign
from thelma.models.experiment import ExperimentMetadata
from thelma.models.experiment import ExperimentMetadataType
from thelma.models.iso import IsoRequest
from thelma.models.moleculedesign import MoleculeDesignPoolSet
from thelma.models.subproject import Subproject

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(experiment_metadata_tbl,
                  experiment_metadata_iso_request_tbl,
                  experiment_metadata_pool_set_tbl):
    "Mapper factory."
    m = mapper(
           ExperimentMetadata, experiment_metadata_tbl,
           properties=
             dict(id=synonym('experiment_metadata_id'),
                  label=column_property(
                      experiment_metadata_tbl.c.label,
                      comparator_factory=CaseInsensitiveComparator
                      ),
                  experiment_design=relationship(ExperimentDesign,
                                    uselist=False,
                                    cascade='all,delete,delete-orphan',
                                    back_populates='experiment_metadata'),
                  subproject=relationship(Subproject, uselist=False),
                  molecule_design_pool_set=relationship(
                                MoleculeDesignPoolSet,
                                uselist=False,
                                secondary=experiment_metadata_pool_set_tbl),
                  iso_request=relationship(IsoRequest, uselist=False,
                            secondary=experiment_metadata_iso_request_tbl,
                            back_populates='experiment_metadata',
                            cascade='all,delete,delete-orphan',
                            single_parent=True),

                  experiment_metadata_type=relationship(ExperimentMetadataType,
                                                uselist=False, viewonly=True),
                  ),
           )
    if isinstance(ExperimentMetadata.slug, property):
        ExperimentMetadata.slug = \
            hybrid_property(ExperimentMetadata.slug.fget,
                            expr=lambda cls: as_slug_expression(cls.label))
    return m
