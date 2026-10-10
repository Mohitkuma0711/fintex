from collections.abc import AsyncIterator
from uuid import uuid4

from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings


def _uses_supabase_transaction_pooler(url: URL) -> bool:
    return (
        url.drivername == "postgresql+asyncpg"
        and (url.host or "").endswith(".pooler.supabase.com")
        and url.port == 6543
    )


def _engine_options(database_url: str) -> tuple[URL, dict[str, object]]:
    """Return asyncpg options safe for Supabase's transaction-mode pooler."""
    url = make_url(database_url)
    if not _uses_supabase_transaction_pooler(url):
        return url, {}

    # PgBouncer transaction pooling can route consecutive operations through
    # one PostgreSQL connection. The default asyncpg statement names then
    # collide across clients. Disable the SQLAlchemy cache, generate unique
    # names, and let PgBouncer own connection pooling.
    return (
        url.update_query_dict({"prepared_statement_cache_size": "0"}),
        {
            "poolclass": NullPool,
            "connect_args": {
                "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
            },
        },
    )


database_url, engine_options = _engine_options(settings.database_url)
engine = create_async_engine(database_url, pool_pre_ping=True, **engine_options)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session
