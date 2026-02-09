from src.core.config import settings
from src.http.discovery_client import DiscoveryApiClient
from src.services.position_service import LocationService
from src.services.search_service import SearchService

_discovery_client: DiscoveryApiClient | None = None
_client_instance: DiscoveryApiClient | None = None
_location_service_instance: LocationService | None = None
_search_service_instance: SearchService | None = None


def get_lclient() -> DiscoveryApiClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = DiscoveryApiClient()
    return _client_instance


def get_dclient() -> DiscoveryApiClient:
    global _discovery_client
    if _discovery_client is None:
        _discovery_client = DiscoveryApiClient(api_key=settings.API_KEY)
    return _discovery_client


def get_location_service() -> LocationService:
    global _location_service_instance
    if _location_service_instance is None:
        client = get_lclient()
        _location_service_instance = LocationService(client)
    return _location_service_instance


def get_search_service() -> SearchService:
    global _search_service_instance
    if _search_service_instance is None:
        dclient = get_dclient()
        location_service = get_location_service()
        _search_service_instance = SearchService(dclient, location_service)
    return _search_service_instance