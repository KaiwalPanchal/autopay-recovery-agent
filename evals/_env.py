"""Shared bootstrap for offline eval scripts: throwaway DB + random per-run tokens.

Import this BEFORE importing anything from ``backend``. It refuses to touch data/app.db
unless AUTOPAY_DB_PATH is already set by the caller.
"""
import os
import secrets
import tempfile
from pathlib import Path

if not os.getenv("AUTOPAY_DB_PATH"):
    os.environ["AUTOPAY_DB_PATH"] = str(Path(tempfile.mkdtemp(prefix="autopay-evals-")) / "evals.db")
os.environ["INTERNAL_API_TOKEN"] = "eval-internal-" + secrets.token_hex(8)
os.environ["OPERATOR_API_TOKEN"] = "eval-operator-" + secrets.token_hex(8)
for _n in ("ENVIRONMENT", "LIVEKIT_SIP_TRUNK_ID", "SIP_TRUNK_ID", "CORS_ALLOWED_ORIGINS"):
    os.environ.pop(_n, None)
