from app.core.database import _engine_options


def test_supabase_transaction_pooler_disables_prepared_statement_cache() -> None:
    url, options = _engine_options(
        "postgresql+asyncpg://user:password@db.pooler.supabase.com:6543/postgres"
    )

    assert url.query["prepared_statement_cache_size"] == "0"
    assert options["connect_args"]
    assert options["poolclass"].__name__ == "NullPool"


def test_direct_postgres_connection_keeps_normal_pooling() -> None:
    url, options = _engine_options(
        "postgresql+asyncpg://user:password@127.0.0.1:5432/fintax"
    )

    assert "prepared_statement_cache_size" not in url.query
    assert options == {}
