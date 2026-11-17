"""One connection setting for the whole bot: DATABASE_URL (Lecture 24 §5).

    sqlite:///capstone/data/capstone.db      the default: a single file, nothing to install
    postgresql://user@host/dbname           optional: needs `pip install psycopg`; the password comes
                                            from the PGPASSWORD environment variable, never the URL

Queries are written once with `?` placeholders; for Postgres they are converted to `%s`.
Money is exact: `Decimal` values are stored as text in SQLite and as NUMERIC in Postgres, and read back
as `Decimal`, never as `float`.
"""
import os
import sqlite3
from decimal import Decimal
from pathlib import Path

sqlite3.register_adapter(Decimal, str)
DEFAULT_URL = "sqlite:///" + str(Path(__file__).resolve().parents[1] / "data" / "capstone.db")


def database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_URL)


class DB:
    def __init__(self, url: str | None = None):
        self.url = url or database_url()
        if self.url.startswith("sqlite:///"):
            self.kind = "sqlite"
            path = self.url[len("sqlite:///"):]
            if path != ":memory:":
                Path(path).parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(path)
            self.conn.execute("PRAGMA foreign_keys = ON")
            self.conn.execute("PRAGMA journal_mode = WAL")      # the dashboard can read while the bot writes
        elif self.url.startswith(("postgresql://", "postgres://")):
            self.kind = "postgres"
            try:
                import psycopg
            except ImportError as e:
                raise RuntimeError("Postgres needs `pip install psycopg`; or use the SQLite default") from e
            self.conn = psycopg.connect(self.url)
        else:
            raise ValueError("DATABASE_URL must start with sqlite:/// or postgresql://")

    def execute(self, sql: str, params: tuple = ()):
        if self.kind == "postgres":
            sql = sql.replace("?", "%s")
        cur = self.conn.cursor()
        cur.execute(sql, params)
        return cur

    def query(self, sql: str, params: tuple = ()) -> list[tuple]:
        return self.execute(sql, params).fetchall()

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()


def dec(value) -> Decimal | None:
    """Read a stored money value back as an exact Decimal."""
    return None if value is None else Decimal(str(value))
