"""Log in to Deribit by signature (Lecture 24 §3).

Signature login (grant_type=client_signature), never by sending a secret: we sign the text
f"{timestamp}\\n{nonce}\\n{data}" and send only the signature. The timestamp and the random nonce make every
signature single-use, so a copied one cannot be replayed.

  - **Key pair (preferred): Ed25519.** The private key stays on our machine; Deribit holds only the public
    key, which can check a signature but never make one. Signature = base64url of the Ed25519 signature,
    padding stripped.
  - **Shared secret (fallback): HMAC-SHA256** of the same text, hex-encoded. Deribit keeps a copy of the
    secret, so a leak on either side is a leak.

Credentials from the environment (capstone/configs/.env): DERIBIT_CLIENT_ID, and DERIBIT_PRIVATE_KEY_PATH
(or DERIBIT_CLIENT_SECRET). The same scheme as the course author's own Deribit backend, verified there live.
"""
import base64
import hashlib
import hmac
import os
import secrets
import time
from pathlib import Path


def _private_key():
    raw = os.environ.get("DERIBIT_PRIVATE_KEY_PATH", "").strip().strip('"').strip("'")
    if not raw:
        return None
    from cryptography.hazmat.primitives import serialization
    return serialization.load_pem_private_key(Path(raw).expanduser().read_bytes(), password=None)


def signature_params(client_id: str, private_key=None, client_secret: str | None = None,
                     now_ms: int | None = None, nonce: str | None = None, data: str = "") -> dict:
    """The parameters of public/auth for grant_type=client_signature."""
    timestamp = int(time.time() * 1000) if now_ms is None else int(now_ms)
    nonce = secrets.token_hex(8) if nonce is None else nonce
    to_sign = f"{timestamp}\n{nonce}\n{data}".encode("latin-1")
    if private_key is not None:
        signature = base64.urlsafe_b64encode(private_key.sign(to_sign)).decode().rstrip("=")
    elif client_secret:
        signature = hmac.new(client_secret.encode(), to_sign, hashlib.sha256).hexdigest()
    else:
        raise RuntimeError("no Deribit credentials: set DERIBIT_PRIVATE_KEY_PATH (or DERIBIT_CLIENT_SECRET) in capstone/configs/.env")
    return {"grant_type": "client_signature", "client_id": client_id, "timestamp": timestamp,
            "signature": signature, "nonce": nonce, "data": data}


def login_params() -> dict:
    """Fresh public/auth parameters from the environment."""
    return signature_params(os.environ["DERIBIT_CLIENT_ID"], private_key=_private_key(),
                            client_secret=os.environ.get("DERIBIT_CLIENT_SECRET"))
