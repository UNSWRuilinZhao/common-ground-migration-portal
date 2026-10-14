import hashlib

from django.conf import settings
from django.core.cache import cache


def _client_address(request):
    """Return the address set by our trusted reverse proxy, or the direct peer."""
    return request.META.get("HTTP_X_REAL_IP") or request.META.get(
        "REMOTE_ADDR", "unknown"
    )


def rate_limit_exceeded(
    request,
    scope,
    *,
    limit,
    window_seconds,
    identity="",
):
    """Count a request without storing the raw IP address or email address."""
    raw_identifier = "|".join(
        (
            settings.SECRET_KEY,
            scope,
            _client_address(request),
            identity.strip().lower(),
        )
    )
    digest = hashlib.sha256(raw_identifier.encode("utf-8")).hexdigest()
    key = f"flowdesk-rate:{scope}:{digest}"

    if cache.add(key, 1, timeout=window_seconds):
        return False

    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window_seconds)
        return False
    return count > limit


def email_delivery_rate_limited(request, scope, email):
    """Apply both a source limit and a destination-address limit."""
    limit = settings.EMAIL_RATE_LIMIT_COUNT
    window = settings.EMAIL_RATE_LIMIT_WINDOW_SECONDS
    return rate_limit_exceeded(
        request,
        f"{scope}:source",
        limit=limit,
        window_seconds=window,
    ) or rate_limit_exceeded(
        request,
        f"{scope}:address",
        limit=limit,
        window_seconds=window,
        identity=email,
    )
