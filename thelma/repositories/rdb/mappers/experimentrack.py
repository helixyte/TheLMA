"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Experiment rack mapper.
"""
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import mapper
from thelma.entities.experiment import Experiment
from thelma.entities.experiment import ExperimentDesignRack
from thelma.entities.experiment import ExperimentRack
from thelma.entities.rack import Rack


__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(experiment_rack_tbl):
    "Mapper factory."
    m = mapper(ExperimentRack, experiment_rack_tbl,
               id_attribute='experiment_rack_id',
               properties=
                 dict(design_rack=relationship(ExperimentDesignRack,
                                               uselist=False),
                      rack=relationship(Rack, uselist=False),
                      experiment=
                            relationship(Experiment, uselist=False,
                                         back_populates='experiment_racks',
                                         ),
                      ),
               )
    return m
