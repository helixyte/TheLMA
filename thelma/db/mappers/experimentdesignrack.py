"""
Experiment design rack mapper.
"""
from sqlalchemy import String
from sqlalchemy import cast
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
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
          properties=
            dict(id=synonym("experiment_design_rack_id"),
                 layout=relationship(RackLayout,
                                     uselist=False,
                                     cascade='all,delete,delete-orphan',
                                     single_parent=True),
                 experiment_design=relationship(ExperimentDesign,
                                     back_populates='design_racks',
                                     cascade_backrefs=False),
                 worklist_series=relationship(WorklistSeries, uselist=False,
                        secondary=worklist_series_experiment_design_rack_tbl,
                        cascade='all,delete,delete-orphan',
                        single_parent=True)
                 ),
          )
    if isinstance(ExperimentDesignRack.slug, property):
        ExperimentDesignRack.slug = \
          hybrid_property(ExperimentDesignRack.slug.fget,
                          expr=lambda cls: cast(cls.experiment_design_rack_id,
                                                String))
    return m
