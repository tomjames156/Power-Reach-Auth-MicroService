import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))

# Get the project root (one level up from alembic/)
project_root = os.path.abspath(os.path.join(current_dir, ".."))

# Add it to sys.path
sys.path.insert(0, project_root)

import asyncio
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# Import your Base and all models so Alembic can see them
from app.config import settings
from app.database import Base
from app.models import (User, AdminProfile, CustomerProfile, VendorProfile, ServiceAgentProfile,
                        RefreshToken)

config = context.config
fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata  # ← tells Alembic what the schema should look like


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    engine = create_async_engine(config.get_main_option("sqlalchemy.url"))
    async with engine.connect() as connection:
        await connection.run_sync(
            lambda sync_conn: context.configure(
                connection=sync_conn,
                target_metadata=target_metadata,
                compare_type=True,  # detect column type changes
                compare_server_default=True,
            )
        )
        async with connection.begin():
            await connection.run_sync(lambda _: context.run_migrations())
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())