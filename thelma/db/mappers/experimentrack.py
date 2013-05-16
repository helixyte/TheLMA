"""
Experiment rack mapper.
"""
from sqlalchemy import String
from sqlalchemy import cast
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from thelma.models.experiment import Experiment
from thelma.models.experiment import ExperimentDesignRack
from thelma.models.experiment import ExperimentRack
from thelma.models.rack import Rack

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(experiment_rack_tbl):
    "Mapper factory."
    m = mapper(ExperimentRack, experiment_rack_tbl,
               properties=
                 dict(id=synonym("experiment_rack_id"),
                      design_rack=relationship(ExperimentDesignRack,
                                               uselist=False),
                      rack=relationship(Rack, uselist=False),
                      experiment=
                            relationship(Experiment, uselist=False,
                                         back_populates='experiment_racks',
                                         ),
                      ),
               )
    if isinstance(ExperimentRack.slug, property):
        ExperimentRack.slug = \
            hybrid_property(
                    ExperimentRack.slug.fget,
                    expr=lambda cls: cast(cls.experiment_rack_id, String))
    return m
