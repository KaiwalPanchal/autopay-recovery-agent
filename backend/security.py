"""Authentication and CORS configuration.

Two separate bearer tokens, both read from the environment at request time:

* ``OPERATOR_API_TOKEN``  - protects every ``/api/*`` operator route (dashboard).
* ``INTERNAL_API_TOKEN``  - protects ``/internal/*`` (the voice-agent tool API).

There is NO built-in default token. If a token is unset or empty, every request to
the routes it protects is rejected (fail closed).

The only exception is an explicit opt-in for local development and tests: setting
``ENVIRONMENT=test`` or ``ENVIRONMENT=dev`` makes an unset token fall back to
``dev-operator-token`` / ``dev-internal-token``. Never set that in a deployed
environment. Tokens are compared in constant time with ``hmac.compare_digest``.
"""
import hmac
import logging
import os

from fastapi import Header, HTTPException

log = logging.getLogger("autopay.security")

DEV_ENVIRONMENTS = {"test", "dev"}
_DEV_DEFAULTS = {"OPERATOR_API_TOKEN": "dev-operator-token", "INTERNAL_API_TOKEN": "dev-internal-token"}
DEFAULT_CORS_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"


def envelope(code, data=None, actions=None):
    return {"ok": code == "OK", "code": code, "data": data or {}, "allowed_next_actions": actions or []}


def configured_token(env_name):
    """Return the configured token, the dev fallback (only if explicitly enabled), or None."""
    value = os.getenv(env_name, "")
    if value:
        return value
    if os.getenv("ENVIRONMENT", "").strip().lower() in DEV_ENVIRONMENTS:
        return _DEV_DEFAULTS[env_name]
    return None


def token_matches(presented, expected):
    if not presented or not expected:
        return False
    return hmac.compare_digest(presented.encode("utf-8"), expected.encode("utf-8"))


def _check(authorization, env_name):
    expected = configured_token(env_name)
    if expected is None:
        log.warning("%s is not configured; rejecting request (fail closed)", env_name)
        raise HTTPException(401, detail=envelope("UNAUTHORIZED"))
    scheme, _, presented = (authorization or "").partition(" ")
    if scheme != "Bearer" or not token_matches(presented, expected):
        raise HTTPException(401, detail=envelope("UNAUTHORIZED"))


def require_operator(authorization: str | None = Header(None)):
    _check(authorization, "OPERATOR_API_TOKEN")


def require_internal(authorization: str | None = Header(None)):
    _check(authorization, "INTERNAL_API_TOKEN")


def parse_cors_origins(raw):
    """Parse a comma-separated origin list. A wildcard is never honoured."""
    raw = DEFAULT_CORS_ORIGINS if raw is None else raw
    return [o.strip() for o in raw.split(",") if o.strip() and o.strip() != "*"]
