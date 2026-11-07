# ==============================================================================
# File: src/python/api/v2/utils/idp_gate.py
# Purpose: Launchpad gate on user applications.
#
# Only NASA Launchpad logins may apply for DAAC accounts or the ESDIS Security
# group. Everyone else (Google, EDL, any other IdP, or a token without the
# claim) may only apply for, and be approved as, a Data Provider.
#
# The sign-in method comes from the `identity_provider` claim that Keycloak
# signs into every access token, so this needs no extra calls and stores
# nothing.
#
# APPLICATION_IDP_GATE: off (default) | log | enforce
# LAUNCHPAD_IDP_ALIASES: comma-separated claim values that count as Launchpad
# APPLICATION_IDP_GATE_BYPASS_EMAILS: comma-separated test emails that skip the
#   gate; always ignored when APP_ENV=prod.
# ==============================================================================
import os
from typing import Optional, Set
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)

ESDIS_SECURITY_NGROUP_ID = UUID('0259fb55-1146-4461-ade2-57504e0c3ace')
MODES = ("off", "log", "enforce")

DENY_MESSAGE = (
    "DAAC and Security accounts require signing in with NASA Launchpad. "
    "Sign out and sign in with Launchpad, or apply for a Data Provider account."
)
APPROVE_DENY_MESSAGE = (
    "This applicant did not sign in with NASA Launchpad, so the application "
    "can only be approved with the 'provider' role."
)


class IdpNotAllowedError(Exception):
    """The applicant's sign-in method isn't allowed for what they asked for."""


def _csv_set(name: str, default: str = "") -> Set[str]:
    raw = os.getenv(name)
    if raw is None:
        raw = default
    return {part.strip().lower() for part in raw.split(",") if part.strip()}


def gate_mode() -> str:
    mode = (os.getenv("APPLICATION_IDP_GATE") or "off").strip().lower()
    return mode if mode in MODES else "off"


def is_launchpad(identity_provider: Optional[str]) -> bool:
    """Allow-list: only the configured Launchpad aliases count. Missing claim = not Launchpad."""
    if not identity_provider:
        return False
    return identity_provider.strip().lower() in _csv_set("LAUNCHPAD_IDP_ALIASES", "launchpad")


def _is_bypassed(email: Optional[str]) -> bool:
    if not email:
        return False
    if (os.getenv("APP_ENV") or "").strip().lower() == "prod":
        return False
    return email.strip().lower() in _csv_set("APPLICATION_IDP_GATE_BYPASS_EMAILS")


def provider_only(identity_provider: Optional[str], email: Optional[str]) -> bool:
    """True when this login may only apply as a Data Provider (gate enforced, not Launchpad, not bypassed)."""
    return gate_mode() == "enforce" and not is_launchpad(identity_provider) and not _is_bypassed(email)


def check_application(
    identity_provider: Optional[str],
    email: Optional[str],
    user_id: UUID,
    account_type: str,
    ngroup_id: UUID,
) -> None:
    """Raises IdpNotAllowedError when the gate is enforced and this application needs Launchpad."""
    mode = gate_mode()
    if mode == "off":
        return
    needs_launchpad = account_type != "provider" or ngroup_id == ESDIS_SECURITY_NGROUP_ID
    if not needs_launchpad or is_launchpad(identity_provider):
        return
    log_fields = dict(
        user_id=str(user_id),
        identity_provider=identity_provider,
        account_type=account_type,
        ngroup_id=str(ngroup_id),
    )
    if _is_bypassed(email):
        logger.warning("application.idp_gate.bypassed", email=email, **log_fields)
        return
    if mode == "log":
        logger.warning("application.idp_gate.would_deny", **log_fields)
        return
    logger.warning("application.idp_gate.denied", **log_fields)
    raise IdpNotAllowedError(DENY_MESSAGE)


def check_approval(app_data: dict, role_to_assign: str) -> None:
    """
    Under enforce, a 'provider' application (the only kind a non-Launchpad login
    can submit) can only be approved with the 'provider' role. Uses the stored
    account type, so no lookup of the applicant's sign-in is needed.
    ESDIS Security applications always needed Launchpad at submit, so they're skipped.
    """
    if gate_mode() != "enforce":
        return
    if app_data.get("ngroup_id") == ESDIS_SECURITY_NGROUP_ID:
        return
    account_type = str(getattr(app_data.get("account_type"), "value", app_data.get("account_type")))
    if account_type == "provider" and role_to_assign != "provider":
        logger.warning(
            "application.idp_gate.approval_denied",
            application_id=str(app_data.get("id")),
            role=role_to_assign,
        )
        raise ValueError(APPROVE_DENY_MESSAGE)


# Log-only report of non-Launchpad logins that hold more than the provider role
# (the owner's and dev team's test accounts, for example). Logged once per user
# per container so it doesn't repeat on every request. Never blocks.
_reported_users: Set[str] = set()
_MAX_REPORTED = 10000


def report_non_launchpad_privileged(user_id, identity_provider: Optional[str], roles) -> None:
    if gate_mode() == "off" or is_launchpad(identity_provider):
        return
    privileged = sorted(set(roles or []) - {"provider"})
    if not privileged:
        return
    key = str(user_id)
    if key in _reported_users:
        return
    if len(_reported_users) >= _MAX_REPORTED:
        _reported_users.clear()
    _reported_users.add(key)
    logger.warning(
        "auth.idp_gate.non_launchpad_privileged",
        user_id=key,
        identity_provider=identity_provider,
        roles=privileged,
    )
