from typing import Optional, Dict, Any


class MCPError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class InvalidInputError(MCPError):
    def __init__(self, message: str, hint: Optional[str] = None):
        super().__init__(message)
        self.hint = hint
        self.error_type = "bad_input"

    def to_dict(self) -> Dict[str, Any]:
        error_body = {
            "error_type": self.error_type,
            "message": self.message,
        }
        if self.hint:
            error_body["hint"] = self.hint
        return error_body


class UpstreamApiError(MCPError):
    def __init__(self, message: str):
        super().__init__(message)
        self.error_type = "upstream_unavailable"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.error_type,
            "message": "The external travel data provider is currently unavailable.",
            "hint": "This is a temporary issue. Please try your request again in a few moments.",
            "details": self.message
        }


class LocationResolutionError(MCPError):
    def __init__(self, message: str):
        super().__init__(message)
        self.error_type = "resolution_failed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.error_type,
            "message": self.message,
            "hint": "Could not find a match for the provided location. Try being more specific or check for typos."
        }


class ConfigurationError(MCPError):
    pass
