"""Is the bot alive? Exit 0 if its last heartbeat is less than 3 minutes old, else 1.
Used by Docker's health check (docker-compose.yml); also handy by hand: python -m capstone.tools.healthcheck"""
import sys
from datetime import datetime, timezone

from capstone.database.connection import DB

if __name__ == "__main__":
    rows = DB().query("SELECT at FROM bot_events WHERE kind = 'heartbeat' ORDER BY id DESC LIMIT 1")
    if not rows:
        sys.exit(1)
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(rows[0][0])).total_seconds()
    sys.exit(0 if age < 180 else 1)
