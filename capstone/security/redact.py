"""Keep secrets out of logs and messages.

A secret must never leave the program as text: not in a log line, not in an error shown on a page. Every
program calls `install_log_scrubbing()` right after setting up logging, and any error text shown to a
person goes through `scrub()` first.

How `scrub()` knows what is secret: every environment variable whose name contains SECRET, TOKEN,
PASSWORD, KEY or WEBHOOK, and whose value is long enough to be a credential, is replaced by a marker.
Name every new credential that way.
"""
import logging
import os
import re

_MARKERS = ("SECRET", "TOKEN", "PASSWORD", "KEY", "WEBHOOK")
_MIN_LEN = 8
# signatures and keys that may appear in URLs or headers even when not in the environment
_PATTERNS = [re.compile(r"(?i)(signature|client_secret|access_token|refresh_token|api[_-]?key)([\"'=:\s]+)([A-Za-z0-9+/=_.\-]{8,})")]


def _secret_values():
    vals = []
    for name, value in os.environ.items():
        if any(m in name.upper() for m in _MARKERS) and value and len(value) >= _MIN_LEN:
            vals.append(value)
    return sorted(vals, key=len, reverse=True)


def scrub(text) -> str:
    """Return `text` with every known secret value and every signature-like field replaced by a marker."""
    s = str(text)
    for v in _secret_values():
        s = s.replace(v, "[REDACTED]")
    for rx in _PATTERNS:
        s = rx.sub(lambda m: m.group(1) + m.group(2) + "[REDACTED]", s)
    return s


class _ScrubFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = scrub(record.getMessage())
        record.args = ()
        return True


def install_log_scrubbing() -> None:
    """Scrub every log record on every handler of the root logger. Call once, after logging.basicConfig()."""
    root = logging.getLogger()
    for h in root.handlers:
        h.addFilter(_ScrubFilter())
