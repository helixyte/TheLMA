"""
Set the base DB schema revision.
"""

__docformat__ = 'reStructuredText en'
__all__ = []

from alembic import command

from thelma.db import initialize_schema
from .util import create_engine
from .util import parse_config


alembic_cfg = parse_config()
metadata = initialize_schema()
engine = create_engine(alembic_cfg)
metadata.bind = engine
metadata.create_all()
command.stamp(alembic_cfg, "head")
