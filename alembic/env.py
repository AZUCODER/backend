"""
Alembic environment configuration for FastAPI backend.

This module configures Alembic to work with SQLModel and our database models.
"""

import logging
from logging.config import fileConfig

from sqlalchemy import engine_from_config, create_engine, text
from sqlalchemy import pool
from sqlalchemy.exc import OperationalError
from urllib.parse import urlparse

from alembic import context
import os
import sys

# Add app to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import your SQLModel metadata
from sqlmodel import SQLModel

# Import * to ensure **all** models are registered regardless of future
# additions – __all__ is defined in app.models.__init__
from app.models import *
from app.config import get_settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# ---------------------------------------------------------------------------
# Runtime configuration – inject the DB URL taken from runtime settings so we
# never need to hard-code credentials inside `alembic.ini`.
# ---------------------------------------------------------------------------

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name:  # Check if config file name exists
    fileConfig(config.config_file_name)

# Set SQLAlchemy URL from environment or config
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

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


def create_database_if_not_exists(database_url: str) -> None:
    """Create the database if it doesn't exist."""
    parsed_url = urlparse(database_url)

    # Extract database name from URL
    database_name = parsed_url.path.lstrip("/")

    # Create URL without database name (to connect to PostgreSQL server)
    server_url = f"{parsed_url.scheme}://{parsed_url.username}:{parsed_url.password}@{parsed_url.hostname}:{parsed_url.port}"

    try:
        # Connect to PostgreSQL server (not to specific database)
        engine = create_engine(server_url, isolation_level="AUTOCOMMIT")

        with engine.connect() as connection:
            # Check if database exists
            result = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :database_name"),
                {"database_name": database_name},
            )

            if not result.fetchone():
                print(f"Creating database '{database_name}'...")
                # Create database
                connection.execute(text(f'CREATE DATABASE "{database_name}"'))
                print(f"Database '{database_name}' created successfully!")
            else:
                print(f"Database '{database_name}' already exists.")

    except Exception as e:
        print(f"Error creating database: {e}")
        raise


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
    # Create database if it doesn't exist
    database_url = config.get_main_option("sqlalchemy.url")
    if database_url:
        create_database_if_not_exists(database_url)

    connectable = engine_from_config(
        config.get_section(config.config_ini_section) or {},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
