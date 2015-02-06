"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Sample registration mapper.
"""
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship

from thelma.entities.sample import SampleRegistration
from thelma.entities.sample import StockSample


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(sample_registration_tbl):
    "Mapper factory."
    m = mapper(SampleRegistration, sample_registration_tbl,
        properties=dict(
            sample=relationship(StockSample, uselist=False,
                                back_populates='registration'
                                ),
            ),
        )
    return m
