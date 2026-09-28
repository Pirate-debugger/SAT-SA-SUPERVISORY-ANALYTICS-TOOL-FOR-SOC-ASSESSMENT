from datetime import datetime, timezone


def utc_now() -> datetime:
    """Returns timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)
