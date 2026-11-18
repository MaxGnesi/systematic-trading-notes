"""Read capstone/configs/.env into the environment (Lecture 24 §3).

Settings and credentials live in that file, outside git, never in code. Values in .env win over values
already in the environment, so a key changed in the file applies on the next start. Nothing here prints
a value.
"""
import os
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent / ".env"


def load_env(path: Path = ENV_FILE) -> bool:
    if not path.exists():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip().strip('"').strip("'")
    return True
