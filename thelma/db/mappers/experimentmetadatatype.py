"""
Experiment metadata type mapper.
"""

from everest.repositories.rdb.utils import mapper
from thelma.models.experiment import ExperimentMetadataType

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']

def create_mapper(experiment_metadata_type_tbl):
    """
    Mapper factory.
    """
    m = mapper(ExperimentMetadataType, experiment_metadata_type_tbl,
               id_attribute='experiment_metadata_type_id')
    return m
