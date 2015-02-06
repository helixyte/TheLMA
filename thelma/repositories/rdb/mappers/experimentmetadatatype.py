"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Experiment metadata type mapper.
"""
from sqlalchemy import func

from everest.repositories.rdb.utils import mapper
from thelma.entities.experiment import ExperimentMetadataType


__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']

def create_mapper(experiment_metadata_type_tbl):
    "Mapper factory."
    m = mapper(ExperimentMetadataType, experiment_metadata_type_tbl,
               id_attribute='experiment_metadata_type_id',
               slug_expression=lambda cls: func.lower(cls.id))
    return m
