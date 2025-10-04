from dataclasses import dataclass


@dataclass
class RequestContext:
    """Request-scoped context containing user information and API keys"""
    user_id: str
    openrouter_api_key: str

