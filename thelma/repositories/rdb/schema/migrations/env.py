"""Pylons bootstrap environment.

Place 'pylons_config_file' into alembic.ini, and the application will
be loaded from there.

"""
from alembic import context
from sqlalchemy.engine import create_engine
from sqlalchemy.engine.base import Engine

from thelma.repositories.rdb.schema import initialize_schema
from thelma.repositories.rdb.schema.migrations.util import get_db_url


config = context.config # pylint:disable=E1101
db_url = get_db_url(config)

# customize this section for non-standard engine configurations.
target_metadata = initialize_schema()


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
     # pylint:disable=E1101
    context.configure(url=db_url,
                      target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
    # pylint:enable=E1101


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # specify here how the engine is acquired
    engine = create_engine(db_url)
    if isinstance(engine, Engine):
        connection = engine.connect()
    else:
        raise Exception(
            'Expected engine instance got %s instead' % type(engine)
        )
    # pylint:disable=E1101
    context.configure(connection=connection,
                      target_metadata=target_metadata
                      )

    try:
        with context.begin_transaction():
            context.run_migrations()
    finally:
        connection.close()
    # pylint:disable=E1101

if context.is_offline_mode():
    run_migrations_offline() # pylint:disable=E1101
else:
    run_migrations_online()
