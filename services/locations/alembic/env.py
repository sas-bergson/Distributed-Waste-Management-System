from logging.config import fileConfig

from sqlalchemy import create_engine

from alembic import context
from app.config import get_settings
from app.models import Base

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

settings = get_settings()
OPTIONS = {
    "target_metadata": Base.metadata,
    "include_schemas": True,
    # Alembic's own bookkeeping table lives in our schema too
    "version_table_schema": settings.db_schema,
}


def run() -> None:
    with context.begin_transaction():
        # Before run_migrations(): alembic creates its version table in this schema first
        context.execute(f"CREATE SCHEMA IF NOT EXISTS {settings.db_schema}")
        context.run_migrations()


if context.is_offline_mode():
    # `alembic upgrade head --sql`: print the SQL without a database
    context.configure(url=settings.database_url, literal_binds=True, **OPTIONS)
    run()
else:
    with create_engine(settings.database_url).connect() as connection:
        context.configure(connection=connection, **OPTIONS)
        run()
