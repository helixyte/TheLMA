"""
Experiment metadata type mapper.
"""

from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import synonym
from thelma.db.mappers.utils import as_slug_expression
from thelma.models.experiment import ExperimentMetadataType

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']

def create_mapper(experiment_metadata_type_tbl):
    """
    Mapper factory.
    """
    m = mapper(ExperimentMetadataType, experiment_metadata_type_tbl,
               properties=dict(
                        id=synonym('experiment_metadata_type_id')))

    if isinstance(ExperimentMetadataType.slug, property):
        ExperimentMetadataType.slug = hybrid_property(
                            ExperimentMetadataType.slug.fget,
                            expr=lambda cls: as_slug_expression(cls.id))

    return m
