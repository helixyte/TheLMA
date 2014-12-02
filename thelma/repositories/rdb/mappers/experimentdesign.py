"""
Experiment design mapper.
"""
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import mapper
from thelma.entities.experiment import Experiment
from thelma.entities.experiment import ExperimentDesign
from thelma.entities.experiment import ExperimentDesignRack
from thelma.entities.experiment import ExperimentMetadata
from thelma.entities.liquidtransfer import WorklistSeries
from thelma.entities.rack import RackShape


__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(experiment_design_tbl, worklist_series_experiment_design_tbl):
    "Mapper factory."
    m = mapper(ExperimentDesign, experiment_design_tbl,
               id_attribute='experiment_design_id',
               properties=
                dict(rack_shape=relationship(RackShape, uselist=False),
                     experiment_design_racks=relationship(ExperimentDesignRack,
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
    return m
