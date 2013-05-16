from thelma.db.mappers import initialize_mappers
from thelma.db.schema import initialize_schema


def create_metadata(engine):
    metadata = initialize_schema()
    initialize_mappers(metadata.tables, metadata.views) # pylint: disable=E1101
    metadata.bind = engine
    return metadata
