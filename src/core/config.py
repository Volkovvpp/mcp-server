from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    BASE_URL: str = ""
    API_KEY: str = ""
    TIMEOUT: int = 10

    DEFAULT_LOCALE: str = "en"
    DEFAULT_CURRENCY: str = "EUR"
    MAX_RESULTS: int = 20

    POSITION_ENDPOINT: str = "/nemo/position/suggest"
    SEARCH_DAY_RESULTS_ENDPOINT: str = "/v2/discovery/results"
    SEARCH_CALENDAR_PRICES_ENDPOINT: str = "/v2/discovery/price-calendar"
    DISCOVERY_CHEAPEST_SUMMARY_ENDPOINT: str = "/v2/discovery/results/summary/cheapest"
    DISCOVERY_FASTEST_SUMMARY_ENDPOINT: str = "/v2/discovery/results/summary/fastest"

    MONGO_USER: str = "admin"
    MONGO_PASSWORD: str = "admin"
    MONGO_HOST: str = "localhost"
    MONGO_PORT: int = 27017
    MONGO_DB: str = "mcp_metrics"

    CLIENT_ID: str = ""
    CLIENT_SECRET: str = ""
    BASE_AUTH_URL: str = ""

settings = Settings()