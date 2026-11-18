"""Read-only check of the testnet account: log in by signature, read the balance and the position.
Sends no order. Prints only non-secret numbers. Usage: python -m capstone.tools.check_account"""
import logging
import os

from capstone.configs.settings import load_env
from capstone.executors.gateway import Gateway
from capstone.security.redact import install_log_scrubbing

log = logging.getLogger("check_account")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    install_log_scrubbing()
    if not load_env() and "DERIBIT_CLIENT_ID" not in os.environ:      # a container gets them from its environment
        raise SystemExit("no settings: create capstone/configs/.env (see configs/env.example) or set them in the environment")
    g = Gateway()
    s = g.account_summary("BTC")
    perms = sorted(x for x in g.scope.split() if ":" in x and not x.startswith(("session:", "name:")))
    log.info("logged in by signature on the %s; permissions: %s", g.env, ", ".join(perms))
    extra = [x for x in perms if x not in ("account:read", "trade:read_write")]
    if extra:
        log.warning("the key has more permissions than the bot needs: %s; narrow them on the exchange's API page", ", ".join(extra))
    log.info("account (BTC): %s", {k: str(v) for k, v in s.items()})
    log.info("position BTC-PERPETUAL: %s", {k: str(v) for k, v in g.position("BTC-PERPETUAL").items()})
