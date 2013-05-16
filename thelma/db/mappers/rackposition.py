"""
Rack position mapper.
"""
from sqlalchemy import func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import synonym
from thelma.models.rack import RackPosition

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(rack_position_tbl):
    "Mapper factory."

    m = mapper(RackPosition, rack_position_tbl,
               properties=
                 dict(id=synonym('rack_position_id'),
                      _label=rack_position_tbl.c.label,
                      _row_index=rack_position_tbl.c.row_index,
                      _column_index=rack_position_tbl.c.column_index
                      ),
               )
    if isinstance(RackPosition.slug, property):
        RackPosition.slug = \
            hybrid_property(RackPosition.slug.fget,
                            expr=lambda cls: func.lower(cls._label)) # pylint: disable=W0212
    return m

