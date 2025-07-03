from app.config import get_settings


def build_frontend_url(path: str) -> str:
    """Return absolute frontend URL based on configured FRONTEND_BASE_URL.

    Args:
        path: Route path beginning with '/'

    Returns:
        Full URL string (e.g., https://example.com/reset-password?token=abc)
    """
    settings = get_settings()
    base = settings.FRONTEND_BASE_URL.rstrip("/")
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{base}{path}"
