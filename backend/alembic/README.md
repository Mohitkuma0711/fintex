# Database migrations

Apply the schema using the configured async database URL:

```bash
uv run alembic upgrade head
```

Create later revisions with `uv run alembic revision --autogenerate -m "..."`.
Review and test generated migrations before applying them to a shared database.
