from thelma.repositories.rdb.schema.views import moleculetypemodification
from thelma.repositories.rdb.schema.views import stockinfo


def initialize_views(metadata, tables):
    stockinfo.create_view(
        metadata,
        tables['molecule_design_pool'],
        tables['stock_sample'],
        tables['sample'],
        tables['container'],
        )
    moleculetypemodification.create_view(
        metadata,
        tables['molecule_design'],
        tables['molecule_design_structure'],
        tables['chemical_structure'],
        )
