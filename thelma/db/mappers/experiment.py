"""
Experiment mapper.
"""
from sqlalchemy import String
from sqlalchemy import cast
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from thelma.models.experiment import Experiment
from thelma.models.experiment import ExperimentDesign
from thelma.models.experiment import ExperimentRack
from thelma.models.job import ExperimentJob
from thelma.models.rack import Rack
from thelma.models.rack import RackSpecs

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(experiment_tbl, experiment_source_rack_tbl):
    "Mapper factory."

    esr = experiment_source_rack_tbl

    m = mapper(Experiment, experiment_tbl,
               properties=
                 dict(id=synonym("experiment_id"),
                      destination_rack_specs=relationship(RackSpecs,
                                                          uselist=False),
                      job=relationship(ExperimentJob, uselist=False,
                          back_populates='experiments',
                          ),
                      source_rack=relationship(Rack, uselist=False,
                                   secondary=esr,
                                   cascade='save-update,merge,' \
                                           'refresh-expire,expunge'),
                      experiment_design=relationship(ExperimentDesign,
                          uselist=False,
                          back_populates='experiments'),
                      experiment_racks=relationship(ExperimentRack,
                          back_populates='experiment',
                          cascade='save-update, merge, delete'
                          ),
                      ),
               )
    if isinstance(Experiment.slug, property):
        Experiment.slug = \
            hybrid_property(Experiment.slug.fget,
                            expr=lambda cls: cast(cls.experiment_id, String))
    return m
