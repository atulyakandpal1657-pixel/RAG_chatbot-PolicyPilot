import ipaddress
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Union
from fastapi import HTTPException, Request, status
from backend.app.config import settings

logger = logging.getLogger(__name__)

TrustedProxyItem = Union[ipaddress.IPv4Network, ipaddress.IPv6Network, str]


def parse_trusted_proxies(trusted_proxies_str: str) -> List[TrustedProxyItem]:
    """
    Parses a comma-separated list of trusted proxy IPs, CIDR networks, or hostnames.
    Wildcard ranges ('*' or '/0') are strictly disallowed.
    """
    proxies: List[TrustedProxyItem] = []
    for item in trusted_proxies_str.split(","):
        cleaned = item.strip()
        if not cleaned:
            continue
        if cleaned == "*":
            raise ValueError("Wildcard trusted proxy '*' is not permitted.")
        try:
            # Parses exact IP (e.g. 127.0.0.1 -> 127.0.0.1/32) or CIDR (e.g. 10.0.0.0/24)
            net = ipaddress.ip_network(cleaned, strict=False)
            if net.prefixlen == 0:
                raise ValueError(f"Wildcard trusted proxy range '{cleaned}' (/0) is not permitted.")
            proxies.append(net)
        except ValueError as ve:
            if "not permitted" in str(ve):
                raise
            # Hostname fallback (e.g. 'testclient' or local hostname)
            proxies.append(cleaned)
    return proxies


def is_trusted_peer(ip_or_host: str, trusted_items: List[TrustedProxyItem]) -> bool:
    """
    Checks if an IP or hostname matches any trusted exact IP, CIDR network, or hostname.
    """
    try:
        ip_obj = ipaddress.ip_address(ip_or_host)
        for item in trusted_items:
            if isinstance(item, (ipaddress.IPv4Network, ipaddress.IPv6Network)):
                if ip_obj.version == item.version and ip_obj in item:
                    return True
            elif isinstance(item, str) and item == ip_or_host:
                return True
        return False
    except ValueError:
        for item in trusted_items:
            if isinstance(item, str) and item == ip_or_host:
                return True
        return False


class RateLimiter:
    """
    In-memory rate limiter with verified proxy-header handling
    and a global daily request cap.
    """

    def __init__(self):
        # Maps client_id -> list of float timestamps (last 60s)
        self._requests: Dict[str, List[float]] = {}
        # Daily cap tracking
        self._daily_date = datetime.now(timezone.utc).date()
        self._daily_count = 0

    def get_client_ip(self, request: Request) -> str:
        """
        Derives client IP from the request.
        Only trusts X-Forwarded-For if the direct peer IP is in TRUSTED_PROXIES.
        Never trusts arbitrary X-Forwarded-For headers from untrusted clients.
        """
        peer_ip = request.client.host if request.client else "127.0.0.1"
        trusted_proxies = parse_trusted_proxies(settings.TRUSTED_PROXIES)

        # If peer is untrusted, strictly use peer IP (ignore any forged headers)
        if not is_trusted_peer(peer_ip, trusted_proxies):
            return peer_ip

        # If peer is a trusted proxy, parse X-Forwarded-For chain
        forwarded_for = request.headers.get("X-Forwarded-For")
        if not forwarded_for:
            return peer_ip

        # X-Forwarded-For is client, proxy1, proxy2...
        # Walking right-to-left, find the first IP that is not a trusted proxy
        parts = [p.strip() for p in forwarded_for.split(",") if p.strip()]
        for ip in reversed(parts):
            if not is_trusted_peer(ip, trusted_proxies):
                try:
                    # Validate that it is a parseable IP address
                    ipaddress.ip_address(ip)
                    return ip
                except ValueError:
                    continue

        return parts[0] if parts else peer_ip

    def check_rate_limit(self, request: Request) -> None:
        """
        Enforces both per-client minute limit and global daily cap.
        Raises HTTPException 429 if either is exceeded.
        """
        now = time.time()
        today = datetime.now(timezone.utc).date()

        # 1. Check Global Daily Cap
        if today != self._daily_date:
            self._daily_date = today
            self._daily_count = 0

        if self._daily_count >= settings.DAILY_REQUEST_CAP:
            logger.warning(f"Global daily request cap ({settings.DAILY_REQUEST_CAP}) reached.")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Daily demo request quota exceeded ({settings.DAILY_REQUEST_CAP} requests/day). This in-memory demo limit resets daily.",
            )

        # 2. Check Per-Client Rate Limit
        client_id = self.get_client_ip(request)
        user_timestamps = self._requests.setdefault(client_id, [])

        # Prune timestamps older than 60s
        window_start = now - 60.0
        user_timestamps = [ts for ts in user_timestamps if ts > window_start]
        self._requests[client_id] = user_timestamps

        if len(user_timestamps) >= settings.RATE_LIMIT_PER_MINUTE:
            logger.warning(f"Rate limit exceeded for client {client_id}: {len(user_timestamps)} req/min")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded ({settings.RATE_LIMIT_PER_MINUTE} requests/minute). Please wait before trying again.",
            )

        # Record this request
        user_timestamps.append(now)
        self._daily_count += 1

    def reset_for_tests(self) -> None:
        """Helper to clear state between tests."""
        self._requests.clear()
        self._daily_date = datetime.now(timezone.utc).date()
        self._daily_count = 0


limiter = RateLimiter()


def rate_limit_chat(request: Request) -> None:
    """FastAPI dependency for rate limiting."""
    limiter.check_rate_limit(request)

