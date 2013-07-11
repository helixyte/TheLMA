"""
Lab ISO mapper
"""

from everest.repositories.rdb.utils import mapper
from thelma.models.iso import ISO_TYPES
from thelma.models.iso import LabIso

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(iso_mapper, iso_tbl):
    "Mapper factory."
    m = mapper(LabIso, iso_tbl,
               inherits=iso_mapper,
               polymorphic_identity=ISO_TYPES.LAB,
               )
    return m
