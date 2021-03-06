from sqlalchemy import MetaData

from thelma.repositories.rdb.schema.tables import initialize_tables
from thelma.repositories.rdb.schema.views import initialize_views


def initialize_schema():
    metadata = MetaData()
    initialize_tables(metadata)
    initialize_views(metadata, metadata.tables)
    return metadata
