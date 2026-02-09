from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict
from src.schemas.enums import JourneyType


class Position(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: int
    name: str
    type: str
    country_code: Optional[str] = Field(None, alias="countryCode")


class AutocompleteParams(BaseModel):
    term: str
    locale: str = "en"
    limit: int = 20


class AutocompleteResponse(BaseModel):
    best_guess: Optional[Position] = None
    alternatives: List[Position] = Field(default_factory=list)


class ResolvePositionsParams(BaseModel):
    from_term: str
    to_term: str
    locale: str = "en"
    limit_each: int = 20


class ResolvedPositionInfo(BaseModel):
    user_term: str
    best_match: Optional[Position] = None
    ranked_candidates: List[Position] = Field(default_factory=list)


class ResolvePositionsSuggestion(BaseModel):
    from_id: Optional[int] = None
    to_id: Optional[int] = None


class ResolvePositionsResponse(BaseModel):
    origin: ResolvedPositionInfo
    destination: ResolvedPositionInfo
    suggestion: ResolvePositionsSuggestion


class TimeInfo(BaseModel):
    datetime: str
    tz: Optional[str] = None


class Itinerary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    from_term: str
    to_term: str
    mode: str
    stable_id: str = Field(..., alias="stableId")
    price_from: float = Field(..., alias="priceFrom")
    currency: str
    duration: str
    departure: TimeInfo
    arrival: TimeInfo
    carrier: Optional[str] = None


class CalendarDay(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    date: str
    priceCents: Optional[float] = Field(None, alias="priceCents")
    currency: Optional[str] = None


class CheapestPriceInfo(BaseModel):
    min_price: float
    currency: str


class FastestVsCheapestInfo(BaseModel):
    fastest_duration: str
    fastest_price: float
    cheapest_price: Optional[float] = None
    currency: str


class CheapestSummary(BaseModel):
    summary: Dict[str, Dict[str, CheapestPriceInfo]] = Field(default_factory=dict)


class FastestSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    summary: Dict[str, Dict[str, FastestVsCheapestInfo]] = Field(default_factory=dict)


class BaseSearchParams(BaseModel):
    from_id: Optional[int] = None
    to_id: Optional[int] = None
    from_term: Optional[str] = None
    to_term: Optional[str] = None
    adults: str = "1"
    children: str = "0"
    infants: str = "0"
    modes: List[str] = Field(default_factory=lambda: ["bus", "train", "flight"], alias="travelModes")
    locale: str = "en"
    currency: str = "EUR"


class SearchDayResultsParams(BaseSearchParams):
    model_config = ConfigDict(populate_by_name=True)

    date_out: str
    date_return: Optional[str] = None
    outbound_id: Optional[str] = Field(None, alias="outboundId")
    journey_type: Optional[JourneyType] = Field(None, alias="journeyType")
    allow_combined_schedules: str = Field(None, description="Specifies whether to return combined schedules. Works only for Round Trips", alias="allowCombinedSchedules")


class SearchCalendarPricesParams(BaseSearchParams):
    date_start: str
    date_end: str
    journey_type: JourneyType = JourneyType.ONE_WAY
    allow_combined_schedules: str = Field(None, description="Specifies whether to return combined schedules. Works only for Round Trips", alias="allowCombinedSchedules")


class SearchSummaryParams(BaseSearchParams):
    date_start: str
    date_end: str


class BaseSearchResponse(BaseModel):
    resolved_from_id: int
    resolved_to_id: int


class SearchDayResultsResponse(BaseSearchResponse):
    results: List[Itinerary]
    note: str


class SearchCalendarPricesResponse(BaseSearchResponse):
    calendar: List[CalendarDay]
    note: str


class SearchCheapestSummaryResponse(BaseSearchResponse):
    summary: CheapestSummary
    insight: Optional[str] = None


class SearchFastestSummaryResponse(BaseSearchResponse):
    summary: FastestSummary
    note: str