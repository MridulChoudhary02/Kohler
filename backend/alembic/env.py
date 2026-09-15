"""
Alembic env.py — configured for synchronous migrations against PostgreSQL.
Imports all SQLAlchemy models so autogenerate detects all tables.
"""
from logging.config import fileConfig
import os
import sys

from sqlalchemy import engine_from_config, pool
from alembic import context

# Ensure app is importable from the backend root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all models so Alembic can detect them
from app.models import Base  # noqa: F401 — side-effect import loads all submodels
from app.core.config import settings

# Alembic Config object
config = context.config

# Override the sqlalchemy.url from settings (respects .env)
config.set_main_option("sqlalchemy.url", settings.SYNC_DATABASE_URL)

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — generates SQL without a live DB connection."""
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
    """Run migrations with a live DB connection."""
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
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
