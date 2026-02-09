from datetime import datetime

from src.core.exceptions import InvalidInputError
from src.schemas.models import AutocompleteParams, ResolvePositionsParams


def validate_autocomplete_params(params: AutocompleteParams) -> None:
    """Проверяет, что введённый term непустой и разумной длины."""
    if not params.term.strip():
        raise ValueError("Autocomplete term cannot be empty.")
    if len(params.term) < 2:
        raise ValueError("Autocomplete term must contain at least 2 characters.")


def validate_resolve_params(params: ResolvePositionsParams) -> None:
    """Проверяет валидность поисковых терминов."""
    if not params.from_term.strip() or not params.to_term.strip():
        raise ValueError("Both 'from_term' and 'to_term' must be provided.")


def validate_date_range(start_str: str, end_str: str, max_days: int):
    """
    Проверяет, что диапазон дат не превышает допустимый интервал.
    Формат дат должен быть ISO: YYYY-MM-DD.
    """
    try:
        start_date = datetime.fromisoformat(start_str)
        end_date = datetime.fromisoformat(end_str)
    except ValueError:
        raise InvalidInputError("Invalid date format. Use YYYY-MM-DD.")

    if (end_date - start_date).days > max_days:
        raise InvalidInputError(
            f"Date range exceeds the maximum of {max_days} days.",
            f"Please provide a smaller range between date_start and date_end."
        )
