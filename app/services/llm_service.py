from dataclasses import dataclass
from typing import Any, Callable
from openai import OpenAI
import json


@dataclass
class LlmMessage:
    role: str
    content: str
    additional_data: dict[str, str]


@dataclass
class ModelDescription:
    name: str
    description: str
    provider: str
    ...


class LlmService:
    def __init__(self) -> None:
        self._base_url = "https://openrouter.ai/api/v1"
    
    async def get_completion(
        self,
        api_key: str,
        model: str,
        prompt: str,
        additional_requested_data: dict[str, str] | None = None,
        previous_messages: list[LlmMessage] | None = None,
        temperature: float = 0.7,
    ):
        """
        Prompt a model and get an answer.
        `prompt` contains just the user prompt.
        `additional_requested_data` is a dictionary with keys being the names of the additional data to request, and values being the descriptions of the data.
        The model should respond with a response, which might contain addidional data that was requested.
        Additional data should be returned in response text, between `<additional_data name="...">` and `</additional_data>` tags.
        """
        pass

    async def get_completion_streamed(
        self,
        api_key: str,
        model: str,
        prompt: str,
        additional_requested_data: dict[str, str] | None = None,
        previous_messages: list[LlmMessage] | None = None,
        temperature: float = 0.7,
    ):
        """
        Same as `get_completion`, but but all fields are streamed.
        We get a stream text response from the model, and stream it back, detecting the additional data tags.
        When a tag is detected, response stream is paused, and that field value is streamed.
        """
        pass

    async def get_models(self) -> list[ModelDescription]:
        """
        Get a list of available models.
        """
        pass