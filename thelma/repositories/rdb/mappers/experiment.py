"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Experiment mapper.
"""
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import mapper
from thelma.entities.experiment import Experiment
from thelma.entities.experiment import ExperimentDesign
from thelma.entities.experiment import ExperimentRack
from thelma.entities.job import ExperimentJob
from thelma.entities.rack import Rack


__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(experiment_tbl, experiment_source_rack_tbl):
    "Mapper factory."
    esr = experiment_source_rack_tbl
    m = mapper(Experiment, experiment_tbl,
               id_attribute='experiment_id',
               properties=
                 dict(job=relationship(ExperimentJob, uselist=False,
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
    return m
