"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Experiment design rack mapper.
"""
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import mapper
from thelma.entities.experiment import ExperimentDesign
from thelma.entities.experiment import ExperimentDesignRack
from thelma.entities.liquidtransfer import WorklistSeries
from thelma.entities.racklayout import RackLayout


__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(experiment_design_rack_tbl,
                  worklist_series_experiment_design_rack_tbl):
    "Mapper factory."
    m = mapper(
          ExperimentDesignRack, experiment_design_rack_tbl,
          id_attribute='experiment_design_rack_id',
          properties=
            dict(rack_layout=relationship(RackLayout,
                                     uselist=False,
                                     cascade='all,delete,delete-orphan',
                                     single_parent=True),
                 experiment_design=relationship(ExperimentDesign,
                                     back_populates='experiment_design_racks',
                                     cascade_backrefs=False),
                 worklist_series=relationship(WorklistSeries, uselist=False,
                        secondary=worklist_series_experiment_design_rack_tbl,
                        cascade='all,delete,delete-orphan',
                        single_parent=True)
                 ),
          )
    return m
