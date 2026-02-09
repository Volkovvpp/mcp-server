from fastmcp.server.auth.providers.google import GoogleProvider

from src.core.config import settings

auth_provider = GoogleProvider(
    client_id=settings.CLIENT_ID,
    client_secret=settings.CLIENT_SECRET,
    base_url=settings.BASE_AUTH_URL,
)