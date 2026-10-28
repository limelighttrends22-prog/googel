"""Fail-closed authentication configuration and request isolation."""

import hashlib
import os
import re
from urllib.parse import urlparse


def validate_configuration():
    client = os.getenv("GOOGLE_ADS_MCP_OAUTH_CLIENT_ID")
    secret = os.getenv("GOOGLE_ADS_MCP_OAUTH_CLIENT_SECRET")
    if bool(client) != bool(secret):
        raise ValueError(
            "Configure both OAuth client ID and secret, or neither for local stdio."
        )
    if os.getenv("GOOGLE_ADS_MCP_STORAGE_DISABLE_ENCRYPTION", "").lower() in (
        "true",
        "1",
        "yes",
    ):
        raise ValueError(
            "Disabling OAuth storage encryption is unsupported in this distribution."
        )
    if client:
        base = os.getenv("GOOGLE_ADS_MCP_BASE_URL", "")
        parsed = urlparse(base)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in ("", "/")
        ):
            raise ValueError(
                "HTTP OAuth mode requires a canonical public HTTPS origin in GOOGLE_ADS_MCP_BASE_URL."
            )
        if parsed.hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
            raise ValueError(
                "Use your deployment/tunnel HTTPS hostname as the OAuth base URL."
            )
        if len(os.getenv("GOOGLE_ADS_MCP_JWT_SIGNING_KEY", "")) < 32:
            raise ValueError(
                "HTTP OAuth mode requires a stable random JWT signing key of at least 32 characters."
            )
        storage = os.getenv("GOOGLE_ADS_MCP_STORAGE_TYPE")
        if storage not in ("filetree", "redis", "firestore"):
            raise ValueError(
                "HTTP OAuth mode requires explicit persistent encrypted storage: filetree, redis or firestore."
            )
        redirects = os.getenv("GOOGLE_ADS_MCP_ALLOWED_REDIRECT_URIS", "")
        if not redirects:
            raise ValueError(
                "Configure exact MCP client redirect URIs from the client management page."
            )
        for uri in redirects.split(","):
            target = urlparse(uri.strip())
            if (
                target.scheme != "https"
                or not target.hostname
                or target.username
                or target.password
                or target.fragment
                or "*" in uri
            ):
                raise ValueError(
                    "MCP redirect allowlist must contain exact HTTPS URLs without wildcards."
                )


def customer_id(value):
    text = str(value).strip()
    if not re.fullmatch(r"(?:[0-9]{10}|[0-9]{3}-[0-9]{3}-[0-9]{4})", text):
        raise ValueError(
            "Customer ID must have 10 digits, optionally formatted 123-456-7890."
        )
    return text.replace("-", "")


def check_customer_scope(value):
    cid = customer_id(value)
    configured = os.getenv("GOOGLE_ADS_MCP_ALLOWED_CUSTOMERS", "")
    if configured:
        allowed = {
            customer_id(v.strip()) for v in configured.split(",") if v.strip()
        }
        if cid not in allowed:
            raise PermissionError(
                "Account is outside this deployment's customer allowlist."
            )
    return cid


def principal():
    from fastmcp.server.dependencies import get_access_token

    token = get_access_token()
    if token and token.token:
        # Subject/audience come from GoogleProvider's validated tokeninfo
        # response, never MCP tool arguments. Hash identity, not the rotating
        # token, so snapshots remain private and accessible after refresh.
        claims = getattr(token, "claims", None)
        if (
            not isinstance(claims, dict)
            or not isinstance(claims.get("sub"), str)
            or not isinstance(claims.get("aud"), str)
        ):
            raise PermissionError(
                "Validated Google subject and audience are required for report storage."
            )
        identity = (
            "https://accounts.google.com|" + claims["aud"] + "|" + claims["sub"]
        )
        return "oauth:" + hashlib.sha256(identity.encode()).hexdigest()
    if os.getenv("GOOGLE_ADS_MCP_OAUTH_CLIENT_ID"):
        raise PermissionError(
            "An authenticated request is required; server ADC is never a remote fallback."
        )
    return "local-stdio"
