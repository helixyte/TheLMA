"""
Experiment design rack mapper.
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.models.experiment import ExperimentDesign
from thelma.models.experiment import ExperimentDesignRack
from thelma.models.liquidtransfer import WorklistSeries
from thelma.models.racklayout import RackLayout

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
