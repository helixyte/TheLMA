"""
Experiment metadata mapper.
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import column_property
from sqlalchemy.orm import relationship
from thelma.db.mappers.utils import CaseInsensitiveComparator
from everest.repositories.rdb.utils import as_slug_expression
from thelma.models.experiment import ExperimentDesign
from thelma.models.experiment import ExperimentMetadata
from thelma.models.experiment import ExperimentMetadataType
from thelma.models.subproject import Subproject
from thelma.models.iso import LabIsoRequest

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(experiment_metadata_tbl,
                  experiment_metadata_iso_request_tbl):
    "Mapper factory."
    m = mapper(
           ExperimentMetadata, experiment_metadata_tbl,
           id_attribute='experiment_metadata_id',
           slug_expression=lambda cls: as_slug_expression(cls.label),
           properties=
             dict(label=column_property(
                      experiment_metadata_tbl.c.label,
                      comparator_factory=CaseInsensitiveComparator
                      ),
                  experiment_design=relationship(ExperimentDesign,
                                    uselist=False,
                                    cascade='all,delete,delete-orphan',
                                    back_populates='experiment_metadata'),
                  subproject=relationship(Subproject, uselist=False),
                  lab_iso_request=relationship(LabIsoRequest, uselist=False,
                            secondary=experiment_metadata_iso_request_tbl,
                            back_populates='experiment_metadata',
                            cascade='all,delete,delete-orphan',
                            single_parent=True),

                  experiment_metadata_type=relationship(ExperimentMetadataType,
                                                        uselist=False),
                  ),
           )
    return m
