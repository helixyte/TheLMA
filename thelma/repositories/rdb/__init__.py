from thelma.repositories.rdb.mappers import initialize_mappers
from thelma.repositories.rdb.schema import initialize_schema


def create_metadata(engine):
    metadata = initialize_schema()
    initialize_mappers(metadata.tables, metadata.views) # pylint: disable=E1101
    metadata.bind = engine
    return metadata
