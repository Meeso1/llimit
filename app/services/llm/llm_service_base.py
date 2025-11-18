from abc import abstractmethod, ABC
from dataclasses import dataclass, field
from typing import AsyncGenerator

from app.services.llm.config.llm_config import LlmConfig


@dataclass
class LlmMessage:
    role: str
    content: str
    additional_data: dict[str, str] = field(default_factory=dict)


@dataclass
class StreamedChunk:
    """Represents a chunk of streamed data"""
    content: str
    additional_data_key: str | None = None


class LlmService(ABC):
    """Abstract base class for LLM service implementations"""
    
    @abstractmethod
    async def get_completion(
        self,
        api_key: str,
        model: str,
        messages: list[LlmMessage],
        additional_requested_data: dict[str, str] | None = None,
        temperature: float = 0.7,
        config: LlmConfig | None = None,
    ) -> LlmMessage:
        """
        Prompt a model and get an answer.
        `messages` contains the conversation history including system, user, and assistant messages.
        `additional_requested_data` is a dictionary with keys being the names of the additional data to request, and values being the descriptions of the data.
        The model should respond with a response, which might contain additional data that was requested.
        Additional data should be returned in response text, between `<additional_data name="...">` and `</additional_data>` tags.
        """
        pass

    @abstractmethod
    async def get_completion_streamed(
        self,
        api_key: str,
        model: str,
        messages: list[LlmMessage],
        additional_requested_data: dict[str, str] | None = None,
        temperature: float = 0.7,
        config: LlmConfig | None = None,
    ) -> AsyncGenerator[StreamedChunk, None]:
        """
        Same as `get_completion`, but all fields are streamed.
        We get a stream text response from the model, and stream it back, detecting the additional data tags.
        When a tag is detected, response stream is paused, and that field value is streamed.
        Yields StreamedChunk instances.
        """
        pass