"""
Experiment design mapper.
"""
from sqlalchemy import String
from sqlalchemy import cast
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from thelma.models.experiment import Experiment
from thelma.models.experiment import ExperimentDesign
from thelma.models.experiment import ExperimentDesignRack
from thelma.models.experiment import ExperimentMetadata
from thelma.models.rack import RackShape
from thelma.models.liquidtransfer import WorklistSeries

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(experiment_design_tbl, worklist_series_experiment_design_tbl):
    "Mapper factory."
    m = mapper(ExperimentDesign, experiment_design_tbl,
               properties=
                dict(id=synonym("experiment_design_id"),
                     rack_shape=relationship(RackShape, uselist=False),
                     design_racks=relationship(ExperimentDesignRack,
                                        back_populates='experiment_design',
                                        cascade="all, delete, delete-orphan"),
                     experiments=relationship(Experiment,
                                              back_populates='experiment_design',
                                              cascade_backrefs=False),
                     experiment_metadata=relationship(ExperimentMetadata,
                                        back_populates='experiment_design',
                                        uselist=False),
                     worklist_series=relationship(WorklistSeries,
                                uselist=False,
                                cascade='all, delete, delete-orphan',
                                secondary=worklist_series_experiment_design_tbl,
                                single_parent=True)
                     ),
               )
    if isinstance(ExperimentDesign.slug, property):
        ExperimentDesign.slug = \
            hybrid_property(ExperimentDesign.slug.fget,
                            expr=lambda cls: cast(cls.experiment_design_id,
                                                  String))
    return m
