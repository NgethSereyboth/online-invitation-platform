#!/usr/bin/env python3
"""
Admin IP allowlist parsing and matching.

This module handles the EINVITE_ADMIN_IP_ALLOWLIST environment variable,
which contains a comma-separated list of CIDR ranges and bare IPs that
are permitted to access /api/admin/* routes.

Empty or unset allowlist -> unrestricted (only valid in non-production).
Malformed entries raise ValueError at parse time.
"""

from __future__ import annotations

import ipaddress
import os
import threading
import time
from typing import List, Optional, Set, Tuple


# In-process audit throttle: {ip: last_audit_timestamp}
_AUDIT_THROTTLE: dict[str, float] = {}
_AUDIT_THROTTLE_LOCK = threading.Lock()
_AUDIT_THROTTLE_WINDOW = 60.0  # seconds


class AdminIPAllowlist:
    """
    Parses and matches client IPs against a configured allowlist.

    The allowlist is a comma-separated string of CIDR ranges and bare IPs.
    Examples:
        "10.0.0.0/8,192.168.1.5,2001:db8::/32"
        "127.0.0.1,::1"  # localhost only
    """

    def __init__(self, raw_value: str):
        """
        Initialize from raw environment variable value.

        Args:
            raw_value: Comma-separated CIDRs and IPs. Empty string means unrestricted.

        Raises:
            ValueError: If any entry is malformed.
        """
        self.networks: List[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        self._parse(raw_value)

    def _parse(self, raw_value: str) -> None:
        """Parse the raw allowlist string into a list of IP networks."""
        if not raw_value or not raw_value.strip():
            return

        entries = [entry.strip() for entry in raw_value.split(",")]
        for entry in entries:
            if not entry:
                # Ignore empty entries between commas (e.g., "10.0.0.0/8,,192.168.1.1")
                continue
            try:
                # ipaddress.ip_network handles both CIDR and bare IPs.
                # For bare IPs, strict=False allows host bits to be set.
                network = ipaddress.ip_network(entry, strict=False)
                self.networks.append(network)
            except ValueError as exc:
                raise ValueError(f"Invalid CIDR/IP in EINVITE_ADMIN_IP_ALLOWLIST: {entry}") from exc

    def is_allowed(self, client_ip: str) -> bool:
        """
        Check if the given client IP is allowed.

        Args:
            client_ip: IPv4 or IPv6 address string (may be IPv4-mapped IPv6).

        Returns:
            True if allowed, False otherwise. Empty allowlist -> True.
        """
        if not self.networks:
            return True

        # Normalize IPv4-mapped IPv6 addresses (::ffff:10.0.0.1 -> 10.0.0.1)
        # This mirrors the behavior of TRUSTED_PROXY_IPS resolution which
        # operates on the direct socket IP before any header parsing.
        normalized_ip = self._normalize_ip(client_ip)
        if normalized_ip is None:
            return False

        try:
            ip_obj = ipaddress.ip_address(normalized_ip)
        except ValueError:
            return False

        for network in self.networks:
            if ip_obj in network:
                return True
        return False

    def _normalize_ip(self, ip_str: str) -> Optional[str]:
        """Normalize IPv4-mapped IPv6 to plain IPv4."""
        ip_str = ip_str.strip()
        if not ip_str:
            return None
        try:
            ip_obj = ipaddress.ip_address(ip_str)
            # Manually normalize IPv4-mapped IPv6 (::ffff:10.0.0.1 -> 10.0.0.1)
            # ipaddress does not do this automatically
            if ip_obj.version == 6 and ip_obj.ipv4_mapped is not None:
                return str(ip_obj.ipv4_mapped)
            return str(ip_obj)
        except ValueError:
            return None

    def has_wildcard(self) -> bool:
        """Check if the allowlist contains a /0 network (matches everything)."""
        for network in self.networks:
            if network.prefixlen == 0:
                return True
        return False


# Global singleton, initialized at startup
_ADMIN_IP_ALLOWLIST: Optional[AdminIPAllowlist] = None
_ADMIN_IP_ALLOWLIST_RAW: str = ""


def init_admin_ip_allowlist(raw_value: str) -> AdminIPAllowlist:
    """
    Initialize the global admin IP allowlist.

    Called once at server startup. Raises ValueError on malformed entries.

    Args:
        raw_value: Raw EINVITE_ADMIN_IP_ALLOWLIST environment variable value.

    Returns:
        The initialized AdminIPAllowlist instance.
    """
    global _ADMIN_IP_ALLOWLIST, _ADMIN_IP_ALLOWLIST_RAW
    _ADMIN_IP_ALLOWLIST_RAW = raw_value or ""
    _ADMIN_IP_ALLOWLIST = AdminIPAllowlist(_ADMIN_IP_ALLOWLIST_RAW)
    return _ADMIN_IP_ALLOWLIST


def get_admin_ip_allowlist() -> AdminIPAllowlist:
    """Get the global admin IP allowlist instance."""
    global _ADMIN_IP_ALLOWLIST
    if _ADMIN_IP_ALLOWLIST is None:
        # Lazy init with empty allowlist (unrestricted) if not explicitly initialized
        _ADMIN_IP_ALLOWLIST = AdminIPAllowlist("")
    return _ADMIN_IP_ALLOWLIST


def check_admin_ip_allowed(client_ip: str) -> Tuple[bool, Optional[str]]:
    """
    Check if the client IP is allowed to access admin routes.

    Args:
        client_ip: The resolved client IP address.

    Returns:
        Tuple of (allowed: bool, deny_reason: Optional[str]).
        deny_reason is set only when denied, for audit logging.
    """
    allowlist = get_admin_ip_allowlist()
    allowed = allowlist.is_allowed(client_ip)
    if not allowed:
        return False, "ip_not_allowed"
    return True, None


def audit_admin_ip_denied(client_ip: str, path: str, method: str) -> None:
    """
    Write an admin.ip_denied audit event, throttled to once per IP per 60 seconds.

    Args:
        client_ip: The denied client IP.
        path: The request path.
        method: The HTTP method.
    """
    now = time.time()
    with _AUDIT_THROTTLE_LOCK:
        last_audit = _AUDIT_THROTTLE.get(client_ip, 0)
        if now - last_audit < _AUDIT_THROTTLE_WINDOW:
            return  # Throttled - silently drop
        _AUDIT_THROTTLE[client_ip] = now

    # Import here to avoid circular dependency
    from server import write_audit_event
    try:
        write_audit_event(
            user_id=None,
            action="admin.ip_denied",
            target_type="ip",
            target_id=client_ip,
            metadata={"path": path, "method": method},
            ip_address=client_ip,
        )
    except Exception:
        # Audit failures must not affect the request flow
        pass


def is_production_mode() -> bool:
    """Check if running in production mode (EINVITE_PRODUCTION=1)."""
    return os.environ.get("EINVITE_PRODUCTION", "0").lower() in {"1", "true", "yes"}


def validate_admin_ip_allowlist_for_production() -> List[str]:
    """
    Validate the admin IP allowlist for production deployment.

    Returns:
        List of error messages. Empty list means valid.
    """
    errors: List[str] = []
    raw = os.environ.get("EINVITE_ADMIN_IP_ALLOWLIST", "").strip()

    if is_production_mode():
        if not raw:
            errors.append(
                "EINVITE_ADMIN_IP_ALLOWLIST must be set in production "
                "(comma-separated CIDRs/IPs, e.g. '10.0.0.0/8,192.168.1.5')"
            )
        else:
            # Validate parseability
            try:
                allowlist = AdminIPAllowlist(raw)
                if allowlist.has_wildcard():
                    errors.append(
                        "EINVITE_ADMIN_IP_ALLOWLIST contains a /0 network which "
                        "allows all IPs and defeats the purpose of the allowlist"
                    )
            except ValueError as exc:
                errors.append(str(exc))
    else:
        # Non-production: empty is allowed, but warn if /0 is present
        if raw:
            try:
                allowlist = AdminIPAllowlist(raw)
                if allowlist.has_wildcard():
                    errors.append(
                        "WARNING: EINVITE_ADMIN_IP_ALLOWLIST contains a /0 network "
                        "which allows all IPs and defeats the purpose of the allowlist"
                    )
            except ValueError as exc:
                errors.append(str(exc))
        else:
            # Log a warning once at startup (caller should log this)
            pass

    return errors