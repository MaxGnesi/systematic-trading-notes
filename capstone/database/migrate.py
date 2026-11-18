"""Apply the numbered migrations in database/migrations/, in order, once each (Lecture 24 §5).

The schema is never typed into a database by hand: it lives in ordered .sql files, and this script
records which ones were applied (table schema_migrations). Point DATABASE_URL at any database and run
it to get the identical schema. Usage: python -m capstone.database.migrate
"""
import logging
from pathlib import Path

from capstone.database.connection import DB
from capstone.security.redact import install_log_scrubbing

MIGRATIONS = Path(__file__).resolve().parent / "migrations"
TYPES = {
    "sqlite":   {"ID": "INTEGER PRIMARY KEY AUTOINCREMENT", "DEC": "TEXT", "TS": "TEXT"},
    "postgres": {"ID": "BIGSERIAL PRIMARY KEY", "DEC": "NUMERIC", "TS": "TIMESTAMPTZ"},
}
log = logging.getLogger(__name__)


def migrate(db: DB) -> list[str]:
    db.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
    done = {r[0] for r in db.query("SELECT name FROM schema_migrations")}
    applied = []
    for f in sorted(MIGRATIONS.glob("*.sql")):
        if f.name in done:
            continue
        sql = f.read_text(encoding="utf-8")
        for k, v in TYPES[db.kind].items():
            sql = sql.replace("{" + k + "}", v)
        sql = "\n".join(line.split("--", 1)[0] for line in sql.splitlines())   # drop comments, which may hold ';'
        for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
            db.execute(stmt)
        db.execute("INSERT INTO schema_migrations (name, applied_at) VALUES (?, CURRENT_TIMESTAMP)", (f.name,))
        db.commit()
        applied.append(f.name)
        log.info("applied %s", f.name)
    return applied


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    install_log_scrubbing()
    d = DB()
    new = migrate(d)
    log.info("%s: %s", d.kind, ", ".join(new) if new else "schema up to date")
