from dataclasses import dataclass
from typing import Any, Callable
from openai import OpenAI



@dataclass
class LlmMessage:
    role: str
    content: str


@dataclass
class FunctionArgument:
    name: str
    type: str
    description: str
    required: bool


@dataclass
class LlmFunctionSpec:
    name: str
    description: str
    parameters: list[FunctionArgument]
    execute: Callable[[dict[str, Any]], Any]


class LlmService:
    async def get_completion(
        self,
        model: str,
        messages: list[LlmMessage],
        tools: list[LlmFunctionSpec] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        ...