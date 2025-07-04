"""
Alembic environment configuration for FastAPI backend.

This module configures Alembic to work with SQLModel and our database models.
"""

import logging
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Import your SQLModel metadata
from sqlmodel import SQLModel

# Import * to ensure **all** models are registered regardless of future
# additions – __all__ is defined in app.models.__init__
from app import models  # noqa: F401  (imports side-effects)
from app.config import get_settings

# This is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# ---------------------------------------------------------------------------
# Runtime configuration – inject the DB URL taken from runtime settings so we
# never need to hard-code credentials inside `alembic.ini`.
# ---------------------------------------------------------------------------

settings = get_settings()

# Alembic requires a *sync* driver. If the main DATABASE_URL is async, attempt
# to down-convert (e.g. asyncpg ➜ psycopg).
database_url = settings.DATABASE_URL

if "+asyncpg" in database_url:
    database_url = database_url.replace("+asyncpg", "+psycopg")
elif "+aiosqlite" in database_url:
    database_url = database_url.replace("+aiosqlite", "")

config.set_main_option("sqlalchemy.url", database_url)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Reduce Alembic's default spam in INFO level if user prefers a higher level.
root_logger = logging.getLogger()
if root_logger.level > logging.INFO:
    logging.getLogger("sqlalchemy.engine").setLevel(root_logger.level)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = SQLModel.metadata

# Other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
